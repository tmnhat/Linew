# Google News Setup Guide

## Overview

This guide explains how to set up Linew for Google News inclusion and search engine optimization.

---

## 1. Google Search Console Setup

### 1.1 Create Account

1. Go to [Google Search Console](https://search.google.com/search-console)
2. Sign in with your Google account
3. Click "Add property"
4. Choose "URL prefix" and enter `https://litimez.ai`

### 1.2 Verify Ownership

Choose one of these verification methods:

**Method 1: HTML Meta Tag (Recommended)**

1. In Search Console, select "HTML tag" verification method
2. Copy the meta tag content (the `content` attribute value)
3. Update the `linew-search-console.php` mu-plugin:

```php
define('GOOGLE_SITE_VERIFICATION', 'YOUR_VERIFICATION_CODE_HERE');
```

Or set the environment variable:
```env
GOOGLE_SITE_VERIFICATION=your_verification_code
```

**Method 2: DNS Record**

If you prefer DNS verification, add a TXT record to your domain's DNS settings.

### 1.3 Submit Sitemap

1. After verification, go to "Sitemaps"
2. Enter `sitemap.xml` in the "Add a sitemap" field
3. Click "Submit"
4. Also submit `sitemap-news.xml` for Google News

### 1.4 Monitor Performance

- Check "Performance" tab for search impressions
- Review "Coverage" for indexing issues
- Fix any errors reported

---

## 2. Google News Publisher Center Setup

### 2.1 Access Publisher Center

1. Go to [Google Publisher Center](https://publishercenter.google.com)
2. Sign in with your Google account

### 2.2 Add Publication

1. Click "Add publication"
2. Select "Website"
3. Enter publication name: "Linews"
4. Website URL: `https://litimez.ai`
5. Click "Continue"

### 2.3 Publication Details

**Basic Information:**
- Publication name: Linews
- Publication URL: `https://litimez.ai`
- Description: Tin tức Khoa học Công nghệ và Tài chính cập nhật 24/7

**Content Language:**
- Primary language: Vietnamese

**Location:**
- Primary location: Vietnam

### 2.4 Content Categories

Select relevant categories:
- Technology
- Business
- Science

### 2.5 Content Labels

- Label: "Blog" or "News"

### 2.6 Add RSS Feed

1. Go to "Content" section
2. Add RSS feed: `https://litimez.ai/feed/`
3. Google will fetch articles from this feed

### 2.7 Add Logo

Upload a logo that meets Google's requirements:
- Minimum size: 300x300 pixels
- Recommended: 512x512 pixels
- Formats: PNG, JPG, or WebP
- Must be square

### 2.8 Add Contact Information

Provide:
- Email address
- Website URL
- Social media links (optional)

### 2.9 Review and Submit

1. Review all information
2. Agree to the terms
3. Submit for review

**Note:** Google's review process typically takes 1-4 weeks.

---

## 3. WordPress Configuration

### 3.1 Required Pages

Ensure these pages exist in WordPress:

**About Page (`/about`):**
```html
<h1>Về Linews</h1>
<p>Linews là nền tảng tin tức Khoa học Công nghệ và Tài chính, 
cung cấp thông tin cập nhật 24/7 với phân tích chuyên sâu từ Linews Analysis.</p>

<h2>Chúng tôi cung cấp gì?</h2>
<ul>
    <li>Tin tức Công nghệ từ hơn 50 nguồn uy tín quốc tế</li>
    <li>Tin tức Tài chính, Chứng khoán, Crypto</li>
    <li>Phân tích và dự đoán thị trường từ Linews Analysis</li>
</ul>

<h2>Nguồn tin</h2>
<p>Linews tổng hợp từ các nguồn uy tín như TechCrunch, The Verge, BBC, 
Bloomberg, Reuters, VnExpress, CafeF và nhiều nguồn khác.</p>
```

**Contact Page (`/contact`):**
```html
<h1>Liên hệ</h1>
<p>Email: contact@litimez.ai</p>
<p>Telegram: @linews_vn</p>
<p>Facebook: facebook.com/linews</p>
```

**Privacy Policy Page (`/privacy-policy`):**
Include a standard privacy policy covering:
- Information collection
- Use of information
- Cookie policy
- Third-party services (Google Analytics, etc.)
- User rights

### 3.2 Author Information

Ensure articles have proper author attribution. The Linews SEO plugin sets author to "Linews" organization.

### 3.3 Article Requirements

For Google News inclusion, ensure:

1. **Original Content**: Articles must be original (AI-written content is fine)
2. **Clear Dates**: Published and modified dates are set correctly
3. **Proper Headlines**: Headlines are descriptive and accurate
4. **Byline**: Each article has clear attribution
5. **Images**: Articles should have featured images

---

## 4. SEO Checklist

### 4.1 Technical SEO

- [ ] HTTPS is enabled
- [ ] Site is mobile-friendly
- [ ] Page load speed is acceptable
- [ ] No crawl errors in Search Console
- [ ] Proper canonical URLs

### 4.2 Content SEO

- [ ] Articles have unique, descriptive titles
- [ ] Meta descriptions are set
- [ ] Proper heading structure (H1, H2, H3)
- [ ] Images have alt text
- [ ] Internal linking

### 4.3 Structured Data

- [ ] NewsArticle schema is implemented
- [ ] Schema validates at Google's Rich Results Test
- [ ] All required fields are present

---

## 5. RSS Feed Requirements

Google News requires a valid RSS feed. Linew's WordPress RSS feed at `/feed/` should:

1. Include full article content or excerpts
2. Have proper publication dates
3. Include categories
4. Include author information
5. Be updated regularly

The SEO plugin enhances the RSS feed with:
- Proper excerpts
- Category information
- Author attribution

---

## 6. Monitoring and Maintenance

### 6.1 Regular Checks

- Check Search Console daily for new errors
- Monitor indexing status
- Review performance reports
- Check for manual actions

### 6.2 Content Quality

- Ensure consistent publishing schedule
- Maintain article quality standards
- Avoid duplicate content
- Keep topics relevant to Google News

### 6.3 Common Issues

**Issue: Articles not indexed**
- Check for crawl errors
- Verify robots.txt allows crawling
- Ensure proper canonical URLs

**Issue: Manual action taken**
- Review message in Search Console
- Fix reported issues
- Submit reconsideration request

**Issue: Not appearing in Google News**
- Wait for review (can take weeks)
- Ensure all requirements are met
- Check Publisher Center status

---

## 7. Useful Resources

- [Google Search Console Help](https://support.google.com/webmasters/)
- [Google News Publisher Guidelines](https://support.google.com/news/publisher-center/)
- [Google News Technical Guidelines](https://support.google.com/news/publisher-center/articles/7124556)
- [Schema.org NewsArticle](https://schema.org/NewsArticle)
- [Rich Results Test](https://search.google.com/test/rich-results)
- [XML Sitemap Validator](https://www.xml-sitemaps.com/validate)

---

## 8. Timeline

1. **Day 1-2**: Set up Search Console and verify site
2. **Day 2-3**: Submit sitemap, review robots.txt
3. **Day 3-5**: Set up Publisher Center
4. **Week 1-2**: Monitor for issues, fix errors
5. **Week 2-4**: Wait for Google News review
6. **Ongoing**: Monitor performance, maintain quality
