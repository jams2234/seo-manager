"""
Content Analyzer Service
Analyzes content quality, readability, and keyword optimization
"""
import re
import logging
from typing import Dict, List, Optional, Set
from collections import Counter
from bs4 import BeautifulSoup
import requests
from django.utils.text import slugify

from .base import AnalyzerService

logger = logging.getLogger(__name__)


class ContentAnalyzer(AnalyzerService):
    """
    Service for analyzing content quality and optimization
    """

    # Common stop words (English) - in production, use nltk or similar
    STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'this', 'but', 'they', 'have', 'had',
        'what', 'when', 'where', 'who', 'which', 'why', 'how', 'or', 'not'
    }

    # Readability thresholds (Flesch Reading Ease Score)
    READABILITY_THRESHOLDS = {
        'very_easy': 90,      # 5th grade
        'easy': 80,           # 6th grade
        'fairly_easy': 70,    # 7th grade
        'standard': 60,       # 8th-9th grade
        'fairly_difficult': 50,  # 10th-12th grade
        'difficult': 30,      # College
        'very_difficult': 0   # College graduate
    }

    def __init__(self):
        super().__init__()

    def analyze(self, page_obj, html_content: Optional[str] = None, **kwargs) -> Dict:
        """
        Analyze content quality and optimization

        Args:
            page_obj: Page model instance
            html_content: HTML content (optional, will fetch if not provided)
            **kwargs: Additional options (e.g., target_keywords)

        Returns:
            Analysis result dictionary
        """
        try:
            # Fetch content if not provided
            if not html_content:
                html_content = self._fetch_content(page_obj.url)
                if not html_content:
                    return {
                        'error': True,
                        'message': 'Failed to fetch page content'
                    }

            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract text content
            text_content = self._extract_text_content(soup)

            if not text_content:
                return {
                    'error': True,
                    'message': 'No text content found on page'
                }

            # Perform analyses
            word_count = self._count_words(text_content)
            keyword_analysis = self._analyze_keywords(text_content, kwargs.get('target_keywords'))
            readability = self._analyze_readability(text_content, word_count)
            content_structure = self._analyze_content_structure(soup)
            duplicate_check = self._check_duplicate_content(page_obj, text_content)

            # Calculate content quality score
            quality_score = self._calculate_content_quality(
                word_count,
                keyword_analysis,
                readability,
                content_structure
            )

            result = {
                'error': False,
                'page_id': page_obj.id,
                'url': page_obj.url,
                'word_count': word_count,
                'character_count': len(text_content),
                'keyword_analysis': keyword_analysis,
                'readability': readability,
                'content_structure': content_structure,
                'duplicate_content': duplicate_check,
                'quality_score': quality_score,
                'recommendations': self._generate_recommendations(
                    word_count,
                    keyword_analysis,
                    readability,
                    content_structure
                )
            }

            self.log_info(f"Content analysis completed for {page_obj.url}")
            return result

        except Exception as e:
            self.log_error(f"Content analysis failed for {page_obj.url}: {e}", exc_info=True)
            return {
                'error': True,
                'message': f"Analysis failed: {str(e)}"
            }

    def _fetch_content(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.log_error(f"Failed to fetch content from {url}: {e}")
            return None

    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract visible text content from HTML"""
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _count_words(self, text: str) -> int:
        """Count words in text"""
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return len(words)

    def _analyze_keywords(
        self,
        text: str,
        target_keywords: Optional[List[str]] = None
    ) -> Dict:
        """
        Analyze keyword usage and density

        Args:
            text: Text content
            target_keywords: Optional list of target keywords to check

        Returns:
            Keyword analysis results
        """
        # Extract all words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        total_words = len(words)

        # Filter out stop words
        meaningful_words = [w for w in words if w not in self.STOP_WORDS and len(w) > 2]

        # Calculate word frequency
        word_freq = Counter(meaningful_words)

        # Get top keywords
        top_keywords = word_freq.most_common(10)

        # Calculate keyword density
        keyword_density = {}
        for word, count in top_keywords:
            density = (count / total_words) * 100 if total_words > 0 else 0
            keyword_density[word] = {
                'count': count,
                'density': round(density, 2)
            }

        # Check target keywords if provided
        target_keyword_analysis = {}
        if target_keywords:
            for keyword in target_keywords:
                keyword_lower = keyword.lower()
                count = text.lower().count(keyword_lower)
                density = (count / total_words) * 100 if total_words > 0 else 0

                target_keyword_analysis[keyword] = {
                    'count': count,
                    'density': round(density, 2),
                    'status': self._evaluate_keyword_density(density)
                }

        return {
            'total_words': total_words,
            'unique_words': len(set(meaningful_words)),
            'top_keywords': keyword_density,
            'target_keywords': target_keyword_analysis,
            'keyword_diversity': round(len(set(meaningful_words)) / total_words * 100, 2) if total_words > 0 else 0
        }

    def _evaluate_keyword_density(self, density: float) -> str:
        """Evaluate if keyword density is optimal"""
        if density < 0.5:
            return 'too_low'
        elif density > 3.0:
            return 'too_high'
        else:
            return 'optimal'

    def _analyze_readability(self, text: str, word_count: int) -> Dict:
        """
        Analyze readability using Flesch Reading Ease formula

        Args:
            text: Text content
            word_count: Total word count

        Returns:
            Readability analysis results
        """
        if word_count == 0:
            return {
                'score': 0,
                'level': 'N/A',
                'grade_level': 'N/A',
                'status': 'insufficient_content'
            }

        # Count sentences
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])

        if sentence_count == 0:
            sentence_count = 1

        # Count syllables (simplified approximation)
        syllable_count = self._count_syllables(text)

        # Calculate Flesch Reading Ease Score
        # Score = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
        avg_words_per_sentence = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count

        flesch_score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
        flesch_score = max(0, min(100, flesch_score))  # Clamp to 0-100

        # Determine readability level
        readability_level = self._get_readability_level(flesch_score)
        grade_level = self._get_grade_level(flesch_score)

        # Evaluate status
        status = 'good'
        if flesch_score < 30:
            status = 'too_difficult'
        elif flesch_score > 90:
            status = 'too_easy'

        return {
            'score': round(flesch_score, 1),
            'level': readability_level,
            'grade_level': grade_level,
            'status': status,
            'avg_words_per_sentence': round(avg_words_per_sentence, 1),
            'avg_syllables_per_word': round(avg_syllables_per_word, 2),
            'total_sentences': sentence_count
        }

    def _count_syllables(self, text: str) -> int:
        """
        Count syllables in text (simplified approximation)

        This is a simplified method. For production, use pyphen or similar library.
        """
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)

        syllable_count = 0
        for word in words:
            # Simple vowel-based syllable counting
            vowels = 'aeiou'
            word_syllables = 0
            previous_was_vowel = False

            for char in word:
                is_vowel = char in vowels
                if is_vowel and not previous_was_vowel:
                    word_syllables += 1
                previous_was_vowel = is_vowel

            # Handle silent e
            if word.endswith('e'):
                word_syllables -= 1

            # At least 1 syllable per word
            if word_syllables == 0:
                word_syllables = 1

            syllable_count += word_syllables

        return syllable_count

    def _get_readability_level(self, score: float) -> str:
        """Get readability level from Flesch score"""
        if score >= 90:
            return 'Very Easy'
        elif score >= 80:
            return 'Easy'
        elif score >= 70:
            return 'Fairly Easy'
        elif score >= 60:
            return 'Standard'
        elif score >= 50:
            return 'Fairly Difficult'
        elif score >= 30:
            return 'Difficult'
        else:
            return 'Very Difficult'

    def _get_grade_level(self, score: float) -> str:
        """Get grade level from Flesch score"""
        if score >= 90:
            return '5th grade'
        elif score >= 80:
            return '6th grade'
        elif score >= 70:
            return '7th grade'
        elif score >= 60:
            return '8th-9th grade'
        elif score >= 50:
            return '10th-12th grade'
        elif score >= 30:
            return 'College'
        else:
            return 'College graduate'

    def _analyze_content_structure(self, soup: BeautifulSoup) -> Dict:
        """Analyze content structure (paragraphs, lists, media)"""
        paragraphs = soup.find_all('p')
        lists = soup.find_all(['ul', 'ol'])
        images = soup.find_all('img')
        videos = soup.find_all(['video', 'iframe'])
        tables = soup.find_all('table')
        blockquotes = soup.find_all('blockquote')

        # Calculate average paragraph length
        paragraph_lengths = [len(p.get_text().split()) for p in paragraphs]
        avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0

        return {
            'paragraph_count': len(paragraphs),
            'avg_paragraph_length': round(avg_paragraph_length, 1),
            'list_count': len(lists),
            'image_count': len(images),
            'video_count': len(videos),
            'table_count': len(tables),
            'blockquote_count': len(blockquotes),
            'has_rich_media': len(images) > 0 or len(videos) > 0,
            'structure_score': self._calculate_structure_score(
                len(paragraphs),
                len(lists),
                len(images),
                len(videos)
            )
        }

    def _calculate_structure_score(
        self,
        paragraph_count: int,
        list_count: int,
        image_count: int,
        video_count: int
    ) -> int:
        """Calculate content structure score (0-100)"""
        score = 0

        # Paragraphs (up to 30 points)
        if paragraph_count >= 5:
            score += 30
        else:
            score += paragraph_count * 6

        # Lists (up to 20 points)
        if list_count >= 2:
            score += 20
        else:
            score += list_count * 10

        # Images (up to 30 points)
        if image_count >= 3:
            score += 30
        else:
            score += image_count * 10

        # Videos (up to 20 points)
        if video_count >= 1:
            score += 20

        return min(100, score)

    def _check_duplicate_content(self, page_obj, text_content: str) -> Dict:
        """
        Check for duplicate content within the same domain

        Args:
            page_obj: Page model instance
            text_content: Text content to check

        Returns:
            Duplicate content analysis
        """
        from seo_analyzer.models import Page

        # Get first 200 characters as content fingerprint
        content_fingerprint = text_content[:200].lower().strip()

        if len(content_fingerprint) < 50:
            return {
                'status': 'insufficient_content',
                'duplicates_found': 0,
                'duplicate_pages': []
            }

        try:
            # Find pages in same domain with similar content
            domain = page_obj.domain
            similar_pages = []

            # Check other pages in the same domain
            other_pages = Page.objects.filter(
                domain=domain
            ).exclude(id=page_obj.id)[:100]  # Limit to 100 for performance

            for other_page in other_pages:
                # This is a simplified check - in production, use more sophisticated methods
                # like SimHash, MinHash, or cosine similarity
                if hasattr(other_page, 'content_fingerprint'):
                    # Compare fingerprints if available
                    similarity = self._calculate_similarity(
                        content_fingerprint,
                        other_page.content_fingerprint
                    )

                    if similarity > 0.8:  # 80% similarity threshold
                        similar_pages.append({
                            'page_id': other_page.id,
                            'url': other_page.url,
                            'similarity': round(similarity * 100, 1)
                        })

            status = 'unique'
            if len(similar_pages) > 0:
                status = 'duplicates_found'

            return {
                'status': status,
                'duplicates_found': len(similar_pages),
                'duplicate_pages': similar_pages[:5],  # Return top 5
                'content_fingerprint': content_fingerprint
            }

        except Exception as e:
            self.log_error(f"Duplicate content check failed: {e}")
            return {
                'status': 'check_failed',
                'duplicates_found': 0,
                'duplicate_pages': []
            }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simplified)"""
        # Convert to sets of words
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_content_quality(
        self,
        word_count: int,
        keyword_analysis: Dict,
        readability: Dict,
        content_structure: Dict
    ) -> Dict:
        """Calculate overall content quality score"""
        score = 0
        max_score = 100

        # Word count (25 points)
        if word_count >= 1000:
            score += 25
        elif word_count >= 500:
            score += 20
        elif word_count >= 300:
            score += 15
        else:
            score += word_count / 300 * 15

        # Readability (25 points)
        readability_score = readability.get('score', 0)
        if 60 <= readability_score <= 80:  # Optimal range
            score += 25
        elif 50 <= readability_score <= 90:
            score += 20
        else:
            score += 15

        # Keyword diversity (25 points)
        diversity = keyword_analysis.get('keyword_diversity', 0)
        if diversity >= 50:
            score += 25
        elif diversity >= 40:
            score += 20
        elif diversity >= 30:
            score += 15
        else:
            score += diversity / 30 * 15

        # Structure (25 points)
        structure_score = content_structure.get('structure_score', 0)
        score += structure_score / 100 * 25

        # Determine quality level
        if score >= 80:
            quality_level = 'excellent'
        elif score >= 60:
            quality_level = 'good'
        elif score >= 40:
            quality_level = 'fair'
        else:
            quality_level = 'poor'

        return {
            'score': round(score, 1),
            'max_score': max_score,
            'level': quality_level,
            'breakdown': {
                'word_count_score': round((word_count / 1000) * 25 if word_count < 1000 else 25, 1),
                'readability_score': round(readability_score / 100 * 25, 1),
                'keyword_diversity_score': round(diversity / 100 * 25, 1),
                'structure_score': round(structure_score / 100 * 25, 1)
            }
        }

    def _generate_recommendations(
        self,
        word_count: int,
        keyword_analysis: Dict,
        readability: Dict,
        content_structure: Dict
    ) -> List[Dict]:
        """Generate content improvement recommendations"""
        recommendations = []

        # Word count recommendations
        if word_count < 300:
            recommendations.append({
                'type': 'word_count',
                'severity': 'critical',
                'message': f'Content is too short ({word_count} words). Aim for at least 300 words.',
                'action': 'Expand content with more detailed information'
            })
        elif word_count < 500:
            recommendations.append({
                'type': 'word_count',
                'severity': 'warning',
                'message': f'Content could be more comprehensive ({word_count} words). Consider expanding to 500+ words.',
                'action': 'Add more in-depth information and examples'
            })

        # Readability recommendations
        readability_score = readability.get('score', 0)
        if readability_score < 30:
            recommendations.append({
                'type': 'readability',
                'severity': 'warning',
                'message': 'Content is too difficult to read. Simplify language and sentence structure.',
                'action': 'Break long sentences into shorter ones, use simpler words'
            })
        elif readability_score > 90:
            recommendations.append({
                'type': 'readability',
                'severity': 'info',
                'message': 'Content might be too simple. Consider adding more depth.',
                'action': 'Add more detailed technical information where appropriate'
            })

        # Structure recommendations
        paragraph_count = content_structure.get('paragraph_count', 0)
        if paragraph_count < 3:
            recommendations.append({
                'type': 'structure',
                'severity': 'warning',
                'message': 'Add more paragraphs to improve content structure.',
                'action': 'Break content into logical sections with multiple paragraphs'
            })

        if content_structure.get('list_count', 0) == 0:
            recommendations.append({
                'type': 'structure',
                'severity': 'info',
                'message': 'Consider adding bullet points or numbered lists.',
                'action': 'Use lists to present information in an easy-to-scan format'
            })

        if not content_structure.get('has_rich_media'):
            recommendations.append({
                'type': 'media',
                'severity': 'warning',
                'message': 'No images or videos found. Add visual content.',
                'action': 'Include relevant images, infographics, or videos'
            })

        # Keyword diversity recommendations
        diversity = keyword_analysis.get('keyword_diversity', 0)
        if diversity < 30:
            recommendations.append({
                'type': 'keywords',
                'severity': 'info',
                'message': 'Keyword diversity is low. Use more varied vocabulary.',
                'action': 'Incorporate synonyms and related terms naturally'
            })

        return recommendations
