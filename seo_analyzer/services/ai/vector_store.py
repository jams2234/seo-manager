"""
SEO Vector Store Service
ChromaDB 기반 벡터 저장소 - RAG 시스템의 핵심

Features:
- 도메인/페이지/수정이력 임베딩
- 관련 컨텍스트 검색
- 효과적 패턴 학습
"""
import logging
import hashlib
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SEOVectorStore:
    """
    ChromaDB 기반 벡터 저장소
    SEO 데이터 임베딩 및 RAG 검색 담당
    """

    def __init__(self, persist_directory: str = None):
        """
        벡터 저장소 초기화

        Args:
            persist_directory: ChromaDB 저장 경로
        """
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'data', 'chromadb'
            )

        self.persist_directory = persist_directory
        self._client = None
        self._collections = None

    @property
    def client(self):
        """Lazy initialization of ChromaDB client"""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings

                print(f"[VectorStore] Initializing ChromaDB at {self.persist_directory}", flush=True)

                # 디렉토리 생성
                os.makedirs(self.persist_directory, exist_ok=True)

                self._client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )
                print(f"[VectorStore] ChromaDB initialized successfully", flush=True)
            except ImportError as e:
                print(f"[VectorStore] ChromaDB not installed: {e}", flush=True)
                return None
            except Exception as e:
                import traceback
                print(f"[VectorStore] Failed to initialize ChromaDB: {e}\n{traceback.format_exc()}", flush=True)
                return None

        return self._client

    @property
    def collections(self):
        """Lazy initialization of collections"""
        if self._collections is None and self.client:
            self._collections = self._init_collections()
        return self._collections or {}

    def _init_collections(self) -> Dict:
        """컬렉션 초기화"""
        collections = {}
        collection_names = [
            ('domain_knowledge', '도메인 메타정보, 구조, 히스토리'),
            ('page_context', '페이지 SEO 상태, 메트릭'),
            ('fix_history', 'AI 수정 이력 및 효과성'),
            ('analysis_cache', 'AI 분석 결과'),
            ('site_structure', '사이트 트리 구조, 내부 링크, 계층'),
        ]

        for name, description in collection_names:
            try:
                collections[name] = self.client.get_or_create_collection(
                    name=name,
                    metadata={
                        "hnsw:space": "cosine",
                        "description": description,
                    }
                )
                logger.debug(f"Collection '{name}' initialized")
            except Exception as e:
                logger.error(f"Failed to create collection '{name}': {e}")

        return collections

    def is_available(self) -> bool:
        """벡터 저장소 사용 가능 여부"""
        return self.client is not None

    # =========================================================================
    # 임베딩 메서드
    # =========================================================================

    def embed_domain(self, domain) -> Optional[str]:
        """
        도메인 데이터 임베딩

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            from .seo_knowledge_builder import SEOKnowledgeBuilder

            # SEOKnowledgeBuilder로 컨텍스트 빌드
            builder = SEOKnowledgeBuilder(domain)
            context = builder.build_full_context()
            text = builder.to_ai_context()

            doc_id = f"domain_{domain.id}"

            # 메타데이터
            metadata = {
                "domain_id": domain.id,
                "domain_name": domain.domain_name,
                "total_pages": getattr(domain, 'total_pages', 0) or 0,
                "avg_seo_score": float(domain.avg_seo_score or 0),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            self.collections['domain_knowledge'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.info(f"Embedded domain: {domain.domain_name}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed domain {domain.id}: {e}")
            return None

    def embed_page(self, page) -> Optional[str]:
        """
        페이지 데이터 임베딩 (트리 구조 포함)

        Args:
            page: Page 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            # 트리 구조 정보 수집
            children_count = page.children.count() if hasattr(page, 'children') else 0
            parent_url = page.parent_page.url if page.parent_page else None
            sibling_count = page.domain.pages.filter(
                depth_level=page.depth_level
            ).exclude(id=page.id).count()

            # 텍스트 구성 (트리 구조 정보 추가)
            text_parts = [
                f"URL: {page.url}",
                f"Title: {page.title or 'N/A'}",
                f"Path: {page.path}",
                f"Depth Level: {page.depth_level}",
                f"Parent URL: {parent_url or 'Root'}",
                f"Children Count: {children_count}",
                f"Sibling Count: {sibling_count}",
            ]

            # 자식 페이지 URL 목록 (최대 5개)
            if children_count > 0:
                child_urls = list(page.children.values_list('url', flat=True)[:5])
                text_parts.append(f"Child Pages: {', '.join(child_urls)}")

            # 최신 메트릭 추가
            latest_metrics = page.seo_metrics.first()
            if latest_metrics:
                text_parts.extend([
                    f"SEO Score: {latest_metrics.seo_score}",
                    f"Performance: {latest_metrics.performance_score}",
                    f"Indexed: {latest_metrics.is_indexed}",
                ])

                if latest_metrics.top_queries:
                    keywords = [q.get('query', '') for q in latest_metrics.top_queries[:5]]
                    text_parts.append(f"Top Keywords: {', '.join(keywords)}")

            # 이슈 추가
            issues = page.seo_issues.filter(status='open')[:5]
            if issues:
                issue_texts = [f"{i.issue_type}: {i.title}" for i in issues]
                text_parts.append(f"Issues: {'; '.join(issue_texts)}")

            text = "\n".join(text_parts)
            doc_id = f"page_{page.id}"

            metadata = {
                "page_id": page.id,
                "domain_id": page.domain_id,
                "url": page.url,
                "seo_score": float(latest_metrics.seo_score) if latest_metrics and latest_metrics.seo_score else 0,
                "issue_count": page.seo_issues.filter(status='open').count(),
                "depth_level": page.depth_level,
                "children_count": children_count,
                "sibling_count": sibling_count,
                "has_parent": page.parent_page is not None,
                "is_leaf": children_count == 0,
            }

            self.collections['page_context'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.debug(f"Embedded page: {page.url}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed page {page.id}: {e}")
            return None

    def embed_site_structure(self, domain) -> Optional[str]:
        """
        사이트 전체 트리 구조 임베딩

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            from collections import defaultdict

            pages = domain.pages.all().select_related('parent_page')

            # 트리 구조 분석
            depth_stats = defaultdict(int)
            orphan_pages = []
            leaf_pages = []
            hub_pages = []  # 많은 자식을 가진 페이지

            for page in pages:
                depth_stats[page.depth_level] += 1

                # 고아 페이지 (depth > 0인데 parent 없음)
                if page.depth_level > 0 and not page.parent_page:
                    orphan_pages.append(page.url)

                # 리프 페이지 (자식 없음)
                children_count = page.children.count()
                if children_count == 0:
                    leaf_pages.append(page.url)

                # 허브 페이지 (자식 3개 이상)
                if children_count >= 3:
                    hub_pages.append({
                        'url': page.url,
                        'children': children_count,
                        'title': page.title,
                    })

            # 트리 구조 텍스트 생성
            text_parts = [
                f"=== Site Structure for {domain.domain_name} ===",
                f"Total Pages: {pages.count()}",
                f"Max Depth: {max(depth_stats.keys()) if depth_stats else 0}",
                "",
                "Depth Distribution:",
            ]

            for depth in sorted(depth_stats.keys()):
                text_parts.append(f"  Level {depth}: {depth_stats[depth]} pages")

            text_parts.extend([
                "",
                f"Orphan Pages (no parent): {len(orphan_pages)}",
            ])
            if orphan_pages[:5]:
                text_parts.append(f"  Examples: {', '.join(orphan_pages[:5])}")

            text_parts.extend([
                "",
                f"Leaf Pages (no children): {len(leaf_pages)}",
                f"Hub Pages (3+ children): {len(hub_pages)}",
            ])

            if hub_pages[:5]:
                text_parts.append("Top Hub Pages:")
                for hub in sorted(hub_pages, key=lambda x: x['children'], reverse=True)[:5]:
                    text_parts.append(f"  - {hub['url']} ({hub['children']} children)")

            # 구조 품질 평가
            quality_issues = []
            if len(orphan_pages) > 0:
                quality_issues.append(f"{len(orphan_pages)} orphan pages need parents")
            if max(depth_stats.keys(), default=0) > 4:
                quality_issues.append("Deep hierarchy (>4 levels) may hurt SEO")
            if len(hub_pages) == 0 and pages.count() > 10:
                quality_issues.append("No hub pages - consider creating topic clusters")

            text_parts.extend([
                "",
                "Structure Quality Issues:",
                "  " + ("; ".join(quality_issues) if quality_issues else "No major issues"),
            ])

            text = "\n".join(text_parts)
            doc_id = f"structure_{domain.id}"

            metadata = {
                "domain_id": domain.id,
                "domain_name": domain.domain_name,
                "total_pages": pages.count(),
                "max_depth": max(depth_stats.keys()) if depth_stats else 0,
                "orphan_count": len(orphan_pages),
                "leaf_count": len(leaf_pages),
                "hub_count": len(hub_pages),
                "has_quality_issues": len(quality_issues) > 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            self.collections['site_structure'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.info(f"Embedded site structure for {domain.domain_name}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed site structure for domain {domain.id}: {e}")
            return None

    def embed_fix_history(self, fix_history) -> Optional[str]:
        """
        AI 수정 이력 임베딩

        Args:
            fix_history: AIFixHistory 모델 인스턴스

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            text = f"""
Issue Type: {fix_history.issue_type}
Original: {fix_history.original_value or 'N/A'}
Fixed: {fix_history.fixed_value}
Explanation: {fix_history.ai_explanation or 'N/A'}
Effectiveness: {fix_history.effectiveness}
Recurred: {fix_history.issue_recurred}
Confidence: {fix_history.ai_confidence or 0}
"""

            doc_id = f"fix_{fix_history.id}"

            metadata = {
                "fix_id": fix_history.id,
                "page_id": fix_history.page_id,
                "domain_id": fix_history.page.domain_id if fix_history.page else None,
                "issue_type": fix_history.issue_type,
                "effectiveness": fix_history.effectiveness,
                "recurred": fix_history.issue_recurred,
                "confidence": float(fix_history.ai_confidence or 0),
            }

            self.collections['fix_history'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.debug(f"Embedded fix history: {fix_history.id}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed fix history {fix_history.id}: {e}")
            return None

    def embed_analysis_result(self, domain, analysis_type: str, result: Dict) -> Optional[str]:
        """
        AI 분석 결과 임베딩

        Args:
            domain: Domain 모델 인스턴스
            analysis_type: 분석 유형
            result: 분석 결과 딕셔너리

        Returns:
            문서 ID 또는 None
        """
        if not self.is_available():
            return None

        try:
            import json

            text = f"""
Domain: {domain.domain_name}
Analysis Type: {analysis_type}
Summary: {result.get('summary', {})}
Top Priorities: {result.get('top_priorities', [])}
Insights: {result.get('insights', [])}
"""

            # 해시 기반 ID
            content_hash = hashlib.sha256(
                f"{domain.id}_{analysis_type}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            doc_id = f"analysis_{content_hash}"

            metadata = {
                "domain_id": domain.id,
                "domain_name": domain.domain_name,
                "analysis_type": analysis_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            self.collections['analysis_cache'].upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata],
            )

            logger.debug(f"Embedded analysis result for {domain.domain_name}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to embed analysis result: {e}")
            return None

    # =========================================================================
    # 검색 메서드
    # =========================================================================

    def query_relevant_context(
        self,
        query: str,
        domain_id: int = None,
        collection_names: List[str] = None,
        n_results: int = 5,
    ) -> Dict:
        """
        쿼리에 관련된 컨텍스트 검색 (RAG Retrieval)

        Args:
            query: 검색 쿼리
            domain_id: 도메인 ID (필터링)
            collection_names: 검색할 컬렉션 목록
            n_results: 결과 수

        Returns:
            컬렉션별 검색 결과
        """
        if not self.is_available():
            return {}

        results = {}
        collections = collection_names or list(self.collections.keys())

        for coll_name in collections:
            collection = self.collections.get(coll_name)
            if not collection:
                continue

            where_filter = None
            if domain_id:
                where_filter = {"domain_id": domain_id}

            try:
                result = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_filter,
                )
                results[coll_name] = {
                    'documents': result['documents'][0] if result['documents'] else [],
                    'metadatas': result['metadatas'][0] if result['metadatas'] else [],
                    'distances': result['distances'][0] if result.get('distances') else [],
                }
            except Exception as e:
                logger.error(f"Query failed for collection '{coll_name}': {e}")
                results[coll_name] = {'error': str(e)}

        return results

    def get_effective_fixes(
        self,
        issue_type: str = None,
        domain_id: int = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        효과적이었던 수정 패턴 조회

        Args:
            issue_type: 이슈 유형 필터
            domain_id: 도메인 ID 필터
            limit: 결과 수

        Returns:
            효과적 수정 패턴 목록
        """
        if not self.is_available():
            return []

        try:
            # where 필터 구성
            where_filter = {"effectiveness": "effective"}
            if issue_type:
                where_filter["issue_type"] = issue_type
            if domain_id:
                where_filter["domain_id"] = domain_id

            query_text = f"effective fix patterns"
            if issue_type:
                query_text += f" for {issue_type}"

            result = self.collections['fix_history'].query(
                query_texts=[query_text],
                n_results=limit,
                where=where_filter if len(where_filter) > 1 else None,
            )

            fixes = []
            for doc, meta in zip(
                result['documents'][0] if result['documents'] else [],
                result['metadatas'][0] if result['metadatas'] else [],
            ):
                fixes.append({
                    'document': doc,
                    'metadata': meta,
                })

            return fixes

        except Exception as e:
            logger.error(f"Failed to get effective fixes: {e}")
            return []

    def get_similar_pages(
        self,
        page,
        n_results: int = 5
    ) -> List[Dict]:
        """
        유사한 페이지 검색

        Args:
            page: Page 모델 인스턴스
            n_results: 결과 수

        Returns:
            유사 페이지 목록
        """
        if not self.is_available():
            return []

        try:
            query = f"URL: {page.url}\nTitle: {page.title}\nPath: {page.path}"

            result = self.collections['page_context'].query(
                query_texts=[query],
                n_results=n_results + 1,  # 자기 자신 제외
                where={"domain_id": page.domain_id},
            )

            pages = []
            for doc, meta in zip(
                result['documents'][0] if result['documents'] else [],
                result['metadatas'][0] if result['metadatas'] else [],
            ):
                # 자기 자신 제외
                if meta.get('page_id') != page.id:
                    pages.append({
                        'document': doc,
                        'metadata': meta,
                    })

            return pages[:n_results]

        except Exception as e:
            logger.error(f"Failed to get similar pages: {e}")
            return []

    # =========================================================================
    # 관리 메서드
    # =========================================================================

    def sync_domain(self, domain) -> Dict:
        """
        도메인 전체 동기화

        Args:
            domain: Domain 모델 인스턴스

        Returns:
            동기화 결과
        """
        if not self.is_available():
            return {'success': False, 'error': 'Vector store not available'}

        result = {
            'domain_embedded': False,
            'structure_embedded': False,
            'pages_embedded': 0,
            'fixes_embedded': 0,
            'errors': [],
        }

        try:
            # 도메인 임베딩
            if self.embed_domain(domain):
                result['domain_embedded'] = True

            # 사이트 트리 구조 임베딩
            if self.embed_site_structure(domain):
                result['structure_embedded'] = True

            # 페이지 임베딩 (트리 정보 포함)
            for page in domain.pages.select_related('parent_page').all():
                if self.embed_page(page):
                    result['pages_embedded'] += 1

            # 수정 이력 임베딩
            from ..models import AIFixHistory
            fixes = AIFixHistory.objects.filter(page__domain=domain)
            for fix in fixes:
                if self.embed_fix_history(fix):
                    result['fixes_embedded'] += 1

            logger.info(f"Synced domain {domain.domain_name}: {result}")

        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Domain sync failed: {e}")

        return result

    def delete_domain_data(self, domain_id: int) -> bool:
        """
        도메인 데이터 삭제

        Args:
            domain_id: 도메인 ID

        Returns:
            성공 여부
        """
        if not self.is_available():
            return False

        try:
            # 각 컬렉션에서 도메인 데이터 삭제
            for coll_name, collection in self.collections.items():
                try:
                    # domain_id로 필터링된 문서 삭제
                    collection.delete(
                        where={"domain_id": domain_id}
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete from {coll_name}: {e}")

            logger.info(f"Deleted vector data for domain {domain_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete domain data: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        벡터 저장소 통계

        Returns:
            컬렉션별 문서 수
        """
        if not self.is_available():
            return {'available': False}

        stats = {'available': True, 'collections': {}}

        for name, collection in self.collections.items():
            try:
                stats['collections'][name] = collection.count()
            except Exception as e:
                stats['collections'][name] = f"Error: {e}"

        return stats


# 싱글톤 인스턴스
_vector_store_instance = None


def get_vector_store() -> SEOVectorStore:
    """벡터 저장소 싱글톤 인스턴스 반환"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = SEOVectorStore()
    return _vector_store_instance
