# Distribution & SEO Testing Checklist

## Overview

This document provides a comprehensive testing checklist for the Distribution and SEO features of Linew.

---

## 1. SEO Testing

### 1.1 Google Analytics

- [ ] Google Analytics tracking code is present in WordPress `<head>`
- [ ] GA4 script loads correctly
- [ ] Page views are tracked
- [ ] Events are tracked (searches, etc.)

### 1.2 Meta Tags

- [ ] `<meta name="description">` is present on all article pages
- [ ] `<meta name="keywords">` contains relevant tags
- [ ] `<link rel="canonical">` is correct on all pages
- [ ] `<meta name="author">` is set to "Linews"

### 1.3 Open Graph (Facebook)

- [ ] `og:type` is set to "article" for posts
- [ ] `og:title` matches article title
- [ ] `og:description` matches excerpt
- [ ] `og:image` is present with correct dimensions (1200x630)
- [ ] `og:url` matches article URL
- [ ] `og:site_name` is "Linews"
- [ ] `og:locale` is "vi_VN"
- [ ] `article:published_time` is set correctly
- [ ] `article:modified_time` is set correctly
- [ ] `article:section` matches category

### 1.4 Twitter Card

- [ ] `twitter:card` is "summary_large_image"
- [ ] `twitter:title` matches article title
- [ ] `twitter:description` matches excerpt
- [ ] `twitter:image` is present
- [ ] `twitter:site` is "@linews_vn"

### 1.5 Schema Markup (JSON-LD)

- [ ] NewsArticle schema is present on article pages
- [ ] All required fields are present:
  - [ ] `@type`: "NewsArticle"
  - [ ] `headline`: Article title
  - [ ] `description`: Article excerpt
  - [ ] `image`: Featured image URL
  - [ ] `url`: Article URL
  - [ ] `datePublished`: Publication date
  - [ ] `dateModified`: Last modified date
  - [ ] `author`: Linews organization
  - [ ] `publisher`: Linews organization with logo
  - [ ] `articleSection`: Category
  - [ ] `inLanguage`: "vi"
- [ ] Schema validates at https://search.google.com/test/rich-results

### 1.6 Google News Meta

- [ ] `<meta name="news_keywords">` contains article tags
- [ ] `<link rel="original-source">` points to article URL
- [ ] Standout tag present for breaking/exclusive articles

### 1.7 Sitemap

- [ ] `/sitemap.xml` returns valid XML
- [ ] All published articles are included (last 2 days)
- [ ] Google News extension is present
- [ ] Category pages are included
- [ ] Homepage is included
- [ ] Correct priority values are set
- [ ] Sitemap validates at https://www.xml-sitemaps.com/validate
- [ ] Submitted in Google Search Console

### 1.8 Robots.txt

- [ ] `/robots.txt` is accessible
- [ ] Sitemap URL is referenced
- [ ] Admin areas are disallowed
- [ ] API endpoints are disallowed
- [ ] Correct user-agents are specified

### 1.9 Google Search Console

- [ ] Verification meta tag is present
- [ ] Site is verified in Search Console
- [ ] Sitemap is submitted
- [ ] Core Web Vitals are passing
- [ ] No critical crawl errors

---

## 2. Distribution Testing

### 2.1 Telegram Channel

- [ ] Bot is created and has API token
- [ ] Bot is admin of target channel (@linews_vn)
- [ ] Channel ID is configured correctly
- [ ] Test post sends successfully
- [ ] Article auto-posts to channel after publish
- [ ] Post contains:
  - [ ] Category emoji
  - [ ] Article title
  - [ ] Excerpt (max 200 chars)
  - [ ] Link to article
  - [ ] Hashtags
- [ ] Images are included when available
- [ ] Distribution log is created in database
- [ ] Error handling works (retry logic)

### 2.2 Facebook Page

- [ ] Facebook App is created with required permissions
- [ ] Long-lived Page Access Token is obtained
- [ ] Page ID is configured
- [ ] Test post sends successfully
- [ ] Article auto-posts after publish
- [ ] Post contains:
  - [ ] Message with title and excerpt
  - [ ] Link preview
- [ ] Distribution log is created
- [ ] Error handling works

### 2.3 Twitter/X

- [ ] Twitter Developer App is created
- [ ] API credentials are configured
- [ ] App has write permissions
- [ ] Test tweet sends successfully
- [ ] Article auto-tweets after publish
- [ ] Tweet contains:
  - [ ] Article title (truncated if needed)
  - [ ] Hashtags
  - [ ] Link
  - [ ] Under 280 characters
- [ ] Distribution log is created
- [ ] Error handling works (rate limit handling)

### 2.4 Newsletter

- [ ] SMTP credentials are configured
- [ ] Test email sends successfully
- [ ] Subscribe API works
- [ ] Unsubscribe API works
- [ ] Daily digest sends at 7:00 AM
- [ ] Digest contains:
  - [ ] Header with site branding
  - [ ] Article count statistics
  - [ ] Predictions (if available)
  - [ ] Tech articles section
  - [ ] Finance articles section
  - [ ] Unsubscribe link
- [ ] HTML renders correctly
- [ ] Subscriber stats are tracked

### 2.5 Cross-post (Medium)

- [ ] Medium integration token is configured
- [ ] Test post sends successfully
- [ ] Canonical URL is set correctly (avoids duplicate content)
- [ ] Attribution link to original article is present

### 2.6 Distribution Independence

- [ ] If Telegram fails, Facebook and Twitter still post
- [ ] If Facebook fails, other channels still post
- [ ] If Twitter fails, other channels still post
- [ ] All failures are logged to `distribution_logs` table
- [ ] Retry logic works correctly (3 retries with exponential backoff)

### 2.7 Manual Trigger

- [ ] `/api/distribution/trigger/{article_id}` works
- [ ] Can manually redistribute to specific channels

---

## 3. Settings Testing

### 3.1 Distribution Toggles

- [ ] `/api/settings` returns distribution settings
- [ ] Can enable/disable each channel via PUT
- [ ] Disabled channel does not post
- [ ] Settings persist after restart

### 3.2 Newsletter Settings

- [ ] Frequency setting works (daily/weekly)
- [ ] Send time setting works

---

## 4. Database Testing

### 4.1 Distribution Logs

- [ ] `distribution_logs` table exists
- [ ] Logs are created for each distribution attempt
- [ ] Logs contain correct status (success/failed/pending/skipped)
- [ ] External IDs and URLs are stored
- [ ] Errors are captured
- [ ] Retry count is tracked

### 4.2 Newsletter Subscribers

- [ ] `newsletter_subscribers` table exists
- [ ] Can add new subscriber
- [ ] Duplicate email is handled
- [ ] Can unsubscribe
- [ ] Stats are updated (total_sent, total_opened)

---

## 5. Performance Testing

- [ ] Distribution does not slow down publish process
- [ ] Social media API calls are non-blocking
- [ ] Newsletter generation completes within reasonable time
- [ ] Sitemap generation is fast (uses caching)

---

## 6. Error Handling Testing

- [ ] API timeout handling works
- [ ] Rate limit handling works
- [ ] Invalid credentials are handled gracefully
- [ ] Network failures do not crash the system
- [ ] Errors are logged with context

---

## 7. Security Testing

- [ ] Newsletter subscribe validates email format
- [ ] Admin endpoints are protected (if applicable)
- [ ] API keys are not exposed in responses
- [ ] SQL injection is prevented
- [ ] XSS is prevented in newsletter form

---

## Test Execution Order

1. Run database migration: `alembic upgrade head`
2. Test each SEO component individually
3. Test distribution channels one at a time
4. Test error conditions
5. Test the full pipeline (publish → distribute)
6. Test manual trigger
7. Verify all logs are created correctly

---

## Reporting Issues

When testing, document:
1. Expected behavior
2. Actual behavior
3. Steps to reproduce
4. Error messages
5. Browser/OS (for frontend issues)
