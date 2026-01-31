# Search Console Integration Documentation

## Overview
This document describes the Search Console integration for accurate page indexing status detection.

## Problem Statement
**Issue:** All pages were showing as "not indexed" even when actually indexed by Google.

**Root Cause:** The original logic used `impressions > 0` to determine indexing status, which is unreliable because:
- Indexed pages can have 0 impressions if they haven't received search traffic
- Analytics data is delayed and may not reflect current index status

## Solution
Use Google Search Console's **URL Inspection API** to get accurate, real-time indexing status.

## Architecture

### Components

#### 1. SearchConsoleService (`seo_analyzer/services/search_console.py`)
**Responsibility:** Interface to Google Search Console API

**Key Methods:**
- `get_index_status(site_url, page_url)` - Get accurate index status using URL Inspection API
  - Returns: `is_indexed`, `verdict`, `coverage_state`, `indexing_state`, etc.
  - Verdict values: PASS (indexed), PARTIAL, FAIL, NEUTRAL (not indexed), UNKNOWN

- `get_page_analytics(site_url, page_url)` - Get search analytics (impressions, clicks)
  - Returns: impressions, clicks, CTR, avg_position

**Changes Made:**
- Updated scope from `webmasters.readonly` to `webmasters` (required for URL Inspection)
- Replaced impression-based logic with URL Inspection API
- Added proper error handling for API failures

#### 2. DomainRefreshService (`seo_analyzer/services/domain_refresh_service.py`)
**Responsibility:** Orchestrate domain scanning and metrics collection

**Key Method:**
- `_fetch_search_console_data(page)` - Fetch and store Search Console data

**Changes Made:**
- Now fetches index status via URL Inspection API
- Stores index status in SEOMetrics (not Page model)
- Uses `sc-domain:` format for site URL (required for domain properties)
- Handles SSL/network errors gracefully

**Data Flow:**
```
1. Scanner discovers pages → Page model
2. PageSpeed fetches metrics → SEOMetrics created
3. _fetch_search_console_data() called:
   a. Get latest SEOMetrics for page
   b. Call URL Inspection API → get actual index status
   c. Update SEOMetrics with index status
   d. Call Search Analytics API → get impressions/clicks
   e. Update SEOMetrics with analytics data
```

#### 3. Data Model (SEOMetrics)
**Responsibility:** Store historical snapshots of page metrics

**Index Status Fields:**
- `is_indexed` (Boolean) - True if verdict == 'PASS'
- `index_status` (String) - Verdict from URL Inspection API
- `coverage_state` (String) - Detailed coverage information

**Why SEOMetrics, not Page?**
- Index status changes over time (snapshot data)
- Consistent with other metrics (SEO scores, Core Web Vitals)
- Allows historical tracking of indexing changes

#### 4. API Views (`seo_analyzer/views.py`)
**Responsibility:** Expose data to frontend

**Changes Made:**
- Added `is_indexed`, `index_status`, `coverage_state` to tree endpoint
- Frontend can now display accurate index status for each node

## Site URL Format
**Important:** Use `sc-domain:` format for domain-level properties

```python
# ✓ Correct - Domain property
site_url = "sc-domain:coingry.com"

# ✗ Wrong - URL-prefix property (requires exact permission)
site_url = "https://coingry.com/"
```

## Error Handling

### SSL/Network Errors
**Issue:** Intermittent SSL errors during bulk scanning
```
ssl.SSLError: [SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]
```

**Mitigation:**
- Non-fatal: Errors logged but don't stop scan
- Graceful degradation: Pages without index status show "N/A"
- Can be retried manually or in next scan

### API Rate Limits
**PageSpeed Insights:** 4 req/sec, handled by RateLimiter
**Search Console:** No explicit rate limit, but network errors suggest throttling

**Current Approach:**
- Sequential API calls (not parallelized)
- Error logging and graceful failure
- Future: Add retry logic with exponential backoff

## Testing

### Manual Test Script
```bash
python3 test_url_inspection.py
```
Tests URL Inspection API for sample pages.

### Full Scan Test
```bash
python3 test_full_scan.py
```
Runs full domain scan with Search Console integration.

## Maintenance

### Service Account Permissions
**Required:**
1. Service Account: `seo-manager@seo-manager-485608.iam.gserviceaccount.com`
2. Added to Search Console with "Full" permissions
3. API enabled: Google Search Console API

**Verification:**
```python
from seo_analyzer.services.search_console import SearchConsoleService
sc = SearchConsoleService()
sites = sc.list_sites()  # Should return sc-domain:coingry.com
```

### Monitoring
**Check index status in database:**
```sql
SELECT
  p.url,
  m.is_indexed,
  m.index_status,
  m.coverage_state,
  m.snapshot_date
FROM seo_pages p
JOIN seo_metrics m ON m.page_id = p.id
WHERE m.id IN (
  SELECT MAX(id) FROM seo_metrics GROUP BY page_id
)
ORDER BY p.url;
```

### Troubleshooting

**Problem:** All pages show is_indexed=False
1. Check Service Account has Search Console access
2. Verify API is enabled in Google Cloud Console
3. Check site_url format (use `sc-domain:`)
4. Review logs for API errors

**Problem:** SSL errors during scan
1. Normal for some pages during bulk scanning
2. Re-run scan or manually refresh specific pages
3. Consider adding retry logic

## Future Improvements

1. **Retry Logic:** Add exponential backoff for failed API calls
2. **Batch Processing:** Use URL Inspection API batch endpoint if available
3. **Caching:** Cache index status for 24 hours to reduce API calls
4. **Historical Tracking:** Track index status changes over time
5. **Alerts:** Notify when indexed pages become de-indexed

## References
- [URL Inspection API Documentation](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect)
- [Search Console API Overview](https://developers.google.com/webmaster-tools/search-console-api-original)
- [Service Account Authentication](https://cloud.google.com/iam/docs/service-accounts)
