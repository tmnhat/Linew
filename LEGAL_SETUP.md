# Linew Legal Compliance Setup Guide

Hướng dẫn hoàn thiện hệ thống pháp lý cho **litimez.ai** hoạt động tại Mỹ.

---

## Mục lục

1. [WordPress Pages](#1-wordpress-pages)
2. [Email Setup](#2-email-setup)
3. [DMCA Agent Registration](#3-dmca-agent-registration)
4. [Testing Checklist](#4-testing-checklist)
5. [Notes](#5-notes)

---

## 1. WordPress Pages

Tạo các trang sau trong WordPress Admin. Mỗi trang cần được set as "Published".

### 1.1 /terms-of-service

```html
<h1>Terms of Service</h1>
<p><strong>Last Updated: [AUTO_DATE]</strong></p>
<p><strong>Effective Date: [AUTO_DATE]</strong></p>

<p>Welcome to Litimez ("Linews," "we," "us," or "our"), a news aggregation and market analysis platform operated at litimez.ai. By accessing or using our website, you agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, please do not use our website.</p>

<h2>1. Description of Service</h2>
<p>Litimez provides automated news aggregation, AI-assisted content creation, and market analysis tools including the Linews Analysis market prediction feature. Our content is compiled from publicly available news sources and enhanced using artificial intelligence technologies. Litimez is a media and information platform — we are NOT a financial advisor, broker-dealer, or registered investment adviser.</p>

<h2>2. Acceptance of Terms</h2>
<p>By using this website, subscribing to our newsletter, or accessing any content on litimez.ai, you agree to these Terms, our Privacy Policy, our Cookie Policy, and our DMCA Policy, all of which are incorporated by reference into these Terms.</p>

<h2>3. Content and Intellectual Property</h2>
<p><strong>3.1 Our Content:</strong> The content on Litimez is created with the assistance of artificial intelligence and is based on information from third-party sources. We make reasonable efforts to ensure accuracy but do not guarantee the completeness, reliability, or timeliness of any content published on our platform.</p>
<p><strong>3.2 Third-Party Sources:</strong> Litimez aggregates and synthesizes information from third-party news sources. Original source attributions are provided where applicable. We respect the intellectual property rights of others and expect our users to do the same.</p>
<p><strong>3.3 Your Use:</strong> You may access and read our content for personal, non-commercial purposes. You may not reproduce, distribute, modify, or create derivative works from our content without prior written permission, except as permitted by fair use under U.S. copyright law.</p>

<h2>4. AI-Generated Content Disclosure</h2>
<p>A significant portion of content on Litimez is created, curated, or enhanced using artificial intelligence. While we employ editorial oversight and quality controls, AI-generated content may contain errors, omissions, or inaccuracies. Users should independently verify any information before relying on it for decisions, particularly financial decisions. For more details, please see our <a href="/ai-disclosure">AI Disclosure</a> page.</p>

<h2>5. Financial Information Disclaimer</h2>
<p>The Linews Analysis feature and all financial content on Litimez are provided for <strong>informational and educational purposes only</strong>. Nothing on this website constitutes investment advice, financial advice, trading advice, or any other sort of professional advice. You should not treat any of our content as such. We do not recommend that any financial instrument should be bought, sold, or held by you. We are not registered with the U.S. Securities and Exchange Commission (SEC) or any state securities regulatory authority as an investment adviser or broker-dealer. For full details, please see our <a href="/financial-disclaimer">Financial Disclaimer</a>.</p>

<h2>6. User Comments and Contributions</h2>
<p><strong>6.1</strong> Users may post comments on articles. By posting a comment, you grant Litimez a non-exclusive, royalty-free, worldwide license to use, reproduce, and display your comment in connection with our platform.</p>
<p><strong>6.2</strong> You agree not to post content that is defamatory, obscene, abusive, infringing, or otherwise illegal. We reserve the right to remove any comment at our sole discretion without notice.</p>
<p><strong>6.3 Repeat Infringer Policy:</strong> In accordance with the Digital Millennium Copyright Act (DMCA), we will terminate access for users who are repeat copyright infringers. See our <a href="/dmca-policy">DMCA Policy</a> for details.</p>

<h2>7. Newsletter and Email Communications</h2>
<p>By subscribing to our newsletter, you consent to receive periodic emails containing news digests, market analysis summaries, and occasional promotional content. You may unsubscribe at any time using the unsubscribe link in every email. We comply with the CAN-SPAM Act. Our physical mailing address is: <strong>[YOUR_PHYSICAL_ADDRESS]</strong>.</p>

<h2>8. Limitation of Liability</h2>
<p>TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, LITIMEZ AND ITS OPERATORS SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES, WHETHER INCURRED DIRECTLY OR INDIRECTLY, OR ANY LOSS OF DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES RESULTING FROM:</p>
<ul>
<li>Your access to or use of (or inability to access or use) the website;</li>
<li>Any content obtained from the website, including financial predictions and market analysis;</li>
<li>Any investment or financial decision made based on information provided on this website;</li>
<li>Unauthorized access, use, or alteration of your transmissions or content.</li>
</ul>

<h2>9. Disclaimer of Warranties</h2>
<p>THE WEBSITE AND ALL CONTENT ARE PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. WE DO NOT WARRANT THAT THE WEBSITE WILL BE UNINTERRUPTED, SECURE, OR ERROR-FREE, OR THAT ANY CONTENT WILL BE ACCURATE, RELIABLE, OR COMPLETE.</p>

<h2>10. Indemnification</h2>
<p>You agree to indemnify, defend, and hold harmless Litimez and its operators from any claims, damages, liabilities, costs, and expenses (including reasonable attorney's fees) arising from your use of the website, violation of these Terms, or infringement of any third-party rights.</p>

<h2>11. Governing Law and Dispute Resolution</h2>
<p>These Terms are governed by the laws of the State of California, United States, without regard to conflict of law provisions. Any dispute arising from these Terms shall be resolved through binding arbitration in accordance with the rules of the American Arbitration Association, conducted in California. You waive any right to participate in a class action lawsuit or class-wide arbitration.</p>

<h2>12. Modifications</h2>
<p>We reserve the right to modify these Terms at any time. Material changes will be communicated by posting a notice on the website. Continued use of the website after changes constitutes acceptance of the modified Terms.</p>

<h2>13. Severability</h2>
<p>If any provision of these Terms is found to be unenforceable, the remaining provisions will remain in full force and effect.</p>

<h2>14. Contact</h2>
<p>For questions about these Terms, contact us at: <a href="mailto:legal@litimez.ai">legal@litimez.ai</a></p>
```

### 1.2 /privacy-policy

```html
<h1>Privacy Policy</h1>
<p><strong>Last Updated: [AUTO_DATE]</strong></p>
<p><strong>Effective Date: [AUTO_DATE]</strong></p>

<p>Litimez ("Linews," "we," "us," or "our") respects your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit litimez.ai, subscribe to our newsletter, or interact with our services.</p>

<h2>1. Information We Collect</h2>

<h3>1.1 Information You Provide</h3>
<ul>
<li><strong>Newsletter subscription:</strong> Email address, name (optional)</li>
<li><strong>Comments:</strong> Name, email address, comment content</li>
<li><strong>Contact form:</strong> Name, email address, message</li>
</ul>

<h3>1.2 Information Collected Automatically</h3>
<ul>
<li><strong>Usage data:</strong> Pages viewed, time spent, referral source, click patterns</li>
<li><strong>Device data:</strong> Browser type, operating system, device type, screen resolution</li>
<li><strong>Location data:</strong> Approximate location based on IP address (country/city level only)</li>
<li><strong>Cookies:</strong> See our <a href="/cookie-policy">Cookie Policy</a> for details</li>
</ul>

<h3>1.3 Analytics</h3>
<p>We use Google Analytics 4 to understand how visitors interact with our website. Google Analytics collects data through cookies and similar technologies. This data is aggregated and anonymized. You can opt out of Google Analytics by installing the <a href="https://tools.google.com/dlpage/gaoptout" target="_blank">Google Analytics Opt-out Browser Add-on</a>.</p>

<h2>2. How We Use Your Information</h2>
<ul>
<li>To send newsletter digests (if you subscribe)</li>
<li>To improve our website content and user experience</li>
<li>To respond to your inquiries</li>
<li>To analyze website traffic and usage patterns</li>
<li>To detect and prevent technical issues or abuse</li>
</ul>
<p>We do <strong>NOT</strong> use your information to: sell to third parties, serve targeted advertising, or make automated decisions that significantly affect you.</p>

<h2>3. Information Sharing</h2>
<p>We do not sell, rent, or trade your personal information. We may share information with:</p>
<ul>
<li><strong>Service providers:</strong> Email delivery services (for newsletter), hosting providers, analytics providers (Google Analytics)</li>
<li><strong>Legal requirements:</strong> If required by law, regulation, legal process, or governmental request</li>
<li><strong>Protection:</strong> To protect the rights, property, or safety of Litimez, our users, or the public</li>
</ul>

<h2>4. Your Rights (California Residents — CCPA)</h2>
<p>If you are a California resident, you have the following rights under the California Consumer Privacy Act (CCPA):</p>
<ul>
<li><strong>Right to Know:</strong> You may request details about the personal information we collect, use, and disclose.</li>
<li><strong>Right to Delete:</strong> You may request deletion of your personal information, subject to certain exceptions.</li>
<li><strong>Right to Opt-Out of Sale:</strong> We do not sell personal information. No opt-out is necessary.</li>
<li><strong>Right to Non-Discrimination:</strong> We will not discriminate against you for exercising your privacy rights.</li>
</ul>
<p>To exercise these rights, email us at <a href="mailto:privacy@litimez.ai">privacy@litimez.ai</a>. We will respond within 45 days.</p>

<h2>5. Data Retention</h2>
<ul>
<li>Newsletter subscriber data: Until you unsubscribe + 30 days</li>
<li>Comments: Indefinitely (or until you request removal)</li>
<li>Analytics data: 26 months (Google Analytics default)</li>
<li>Server logs: 90 days</li>
</ul>

<h2>6. Data Security</h2>
<p>We implement reasonable security measures including encryption in transit (HTTPS/TLS), secure database access controls, and regular backups. However, no method of electronic storage or transmission is 100% secure.</p>

<h2>7. Children's Privacy</h2>
<p>Our website is not directed to children under 13. We do not knowingly collect personal information from children under 13. If you believe we have collected information from a child, please contact us immediately.</p>

<h2>8. International Users</h2>
<p>This website is operated in the United States. If you access it from outside the U.S., your information may be transferred to, stored, and processed in the U.S. By using our website, you consent to such transfer.</p>

<h2>9. Changes to This Policy</h2>
<p>We may update this Privacy Policy periodically. We will notify you of material changes by posting the new policy on this page with an updated date.</p>

<h2>10. Contact</h2>
<p>Privacy inquiries: <a href="mailto:privacy@litimez.ai">privacy@litimez.ai</a></p>
<p>General inquiries: <a href="mailto:contact@litimez.ai">contact@litimez.ai</a></p>
<p>Mailing address: <strong>[YOUR_PHYSICAL_ADDRESS]</strong></p>
```

### 1.3 /dmca-policy

```html
<h1>DMCA Policy — Copyright Infringement Notice & Takedown Procedure</h1>
<p><strong>Last Updated: [AUTO_DATE]</strong></p>

<p>Litimez ("Linews") respects the intellectual property rights of others and expects our users to do the same. In accordance with the Digital Millennium Copyright Act of 1998 ("DMCA"), 17 U.S.C. § 512, we will respond promptly to claims of copyright infringement committed using our website.</p>

<h2>1. Designated DMCA Agent</h2>
<p>Our designated agent for receiving DMCA takedown notices is:</p>
<p>
<strong>DMCA Agent</strong><br>
Litimez / Linews<br>
Email: <a href="mailto:dmca@litimez.ai">dmca@litimez.ai</a><br>
Mailing Address: <strong>[YOUR_PHYSICAL_ADDRESS]</strong><br>
</p>
<p>Our DMCA agent is also registered with the U.S. Copyright Office Designated Agent Directory.</p>

<h2>2. Filing a DMCA Takedown Notice</h2>
<p>If you believe that content on litimez.ai infringes your copyright, please send a written notice to our DMCA Agent containing:</p>
<ol>
<li>A physical or electronic signature of the copyright owner or a person authorized to act on their behalf.</li>
<li>Identification of the copyrighted work claimed to have been infringed.</li>
<li>Identification of the material claimed to be infringing, including the URL(s) where it appears on our website.</li>
<li>Your contact information: name, address, telephone number, and email address.</li>
<li>A statement that you have a good faith belief that the use of the material is not authorized by the copyright owner, its agent, or the law.</li>
<li>A statement, under penalty of perjury, that the information in the notice is accurate and that you are authorized to act on behalf of the copyright owner.</li>
</ol>

<h2>3. How We Process Takedown Notices</h2>
<p>Upon receiving a valid DMCA takedown notice, we will:</p>
<ul>
<li>Remove or disable access to the allegedly infringing content promptly, typically within 24-48 hours.</li>
<li>Notify the content provider (if applicable) that the content has been removed.</li>
<li>Document the notice for our records.</li>
</ul>

<h2>4. Counter-Notification</h2>
<p>If you believe your content was wrongly removed, you may file a counter-notification containing:</p>
<ol>
<li>Your physical or electronic signature.</li>
<li>Identification of the material that was removed and the URL where it appeared before removal.</li>
<li>A statement under penalty of perjury that you have a good faith belief that the material was removed by mistake or misidentification.</li>
<li>Your name, address, telephone number, and a statement that you consent to the jurisdiction of the federal court in your district and that you will accept service of process from the person who filed the original notice.</li>
</ol>
<p>Upon receiving a valid counter-notification, we will forward it to the original complainant. If the complainant does not file a lawsuit within 14 business days, we may restore the removed content.</p>

<h2>5. Repeat Infringer Policy</h2>
<p>Litimez will terminate access for users who are found to be repeat copyright infringers. We track DMCA notices and will take appropriate action against repeat offenders, including permanent bans.</p>

<h2>6. Good Faith</h2>
<p>Please note that under Section 512(f) of the DMCA, any person who knowingly materially misrepresents that material or activity is infringing may be subject to liability for damages.</p>
```

### 1.4 /financial-disclaimer

```html
<h1>Financial Disclaimer</h1>
<p><strong>Last Updated: [AUTO_DATE]</strong></p>

<h2>Not Investment Advice</h2>
<p>All content on Litimez (litimez.ai), including but not limited to the Linews Analysis market prediction feature, news articles, market commentary, charts, data, and all other financial information, is provided for <strong>informational and educational purposes only</strong>.</p>

<p><strong>Nothing on this website constitutes:</strong></p>
<ul>
<li>Investment advice or a recommendation to buy, sell, or hold any financial instrument</li>
<li>Financial advice, trading advice, or any other professional advice</li>
<li>A solicitation or offer to buy or sell any securities or financial products</li>
<li>Tax, legal, or accounting advice</li>
</ul>

<h2>No Investment Adviser Registration</h2>
<p>Litimez is NOT registered with the U.S. Securities and Exchange Commission (SEC) as an investment adviser, broker-dealer, or in any other capacity. We are NOT affiliated with any registered investment adviser or broker-dealer. We do not provide personalized investment recommendations.</p>

<h2>Market Predictions and Analysis</h2>
<p>The Linews Analysis feature uses statistical models and data analysis to generate market predictions. These predictions are:</p>
<ul>
<li><strong>Estimates only</strong> — they are not guarantees of future performance</li>
<li><strong>Based on historical data</strong> — past performance does not guarantee or predict future results</li>
<li><strong>Subject to significant error</strong> — actual market prices may differ materially from predictions</li>
<li><strong>Not personalized</strong> — they do not account for your individual financial situation, goals, or risk tolerance</li>
</ul>

<h2>Risk Warning</h2>
<p><strong>All investments involve risk, including the potential loss of principal.</strong></p>
<ul>
<li>The value of investments can go down as well as up.</li>
<li>Cryptocurrency markets are highly volatile and speculative. You may lose some or all of your investment.</li>
<li>Stock markets fluctuate and individual securities may lose value.</li>
<li>Leveraged products (futures, options, margin trading) carry additional risk — you may lose more than your initial investment.</li>
</ul>

<h2>Do Your Own Research</h2>
<p>Before making any investment decision, you should:</p>
<ul>
<li>Consult with a qualified financial advisor who understands your individual circumstances</li>
<li>Conduct your own independent research and due diligence</li>
<li>Consider your financial situation, investment objectives, and risk tolerance</li>
<li>Never invest money you cannot afford to lose</li>
</ul>

<h2>Accuracy of Information</h2>
<p>While we strive to provide accurate and timely information, we make no representations or warranties regarding the accuracy, completeness, or reliability of any content. Market data may be delayed. Information may contain errors or become outdated. We are not responsible for any errors or omissions.</p>

<h2>Third-Party Content</h2>
<p>Our website may contain links to third-party websites or references to third-party content. We do not endorse, control, or assume responsibility for any third-party content or websites.</p>

<h2>Limitation of Liability</h2>
<p>Under no circumstances shall Litimez, its operators, contributors, or affiliates be liable for any loss or damage (including, without limitation, loss of profit, loss of data, or consequential loss) arising from the use of, or reliance on, information provided on this website.</p>

<h2>Regulatory Compliance</h2>
<p>The content on this website may not be appropriate or available for use in all jurisdictions. Users are responsible for compliance with their local laws and regulations. Financial instruments or products referenced may not be available in your jurisdiction.</p>
```

### 1.5 /ai-disclosure

```html
<h1>AI Disclosure — How Litimez Uses Artificial Intelligence</h1>
<p><strong>Last Updated: [AUTO_DATE]</strong></p>

<h2>Transparency Commitment</h2>
<p>At Litimez, we believe in transparency about how our content is created. This page explains how we use artificial intelligence (AI) in our operations.</p>

<h2>How We Use AI</h2>

<h3>News Content</h3>
<p>Litimez uses AI technology to:</p>
<ul>
<li><strong>Aggregate:</strong> Collect news from over 50 reputable international sources</li>
<li><strong>Analyze:</strong> Identify trending topics and categorize news by subject</li>
<li><strong>Write:</strong> Generate Vietnamese-language articles based on source material from multiple outlets</li>
<li><strong>Review:</strong> Check content against editorial guidelines before publication</li>
</ul>
<p>Every article published on Litimez is AI-assisted — meaning AI helps draft the content based on factual information from cited sources. Human editorial oversight is applied through our governance system.</p>

<h3>Market Analysis (Linews Analysis)</h3>
<p>Our market prediction feature uses:</p>
<ul>
<li>Statistical time-series models to analyze historical price patterns</li>
<li>AI to research and synthesize current market news and events</li>
<li>Algorithmic analysis of technical indicators</li>
</ul>
<p>These tools provide estimates and analysis for informational purposes only. They are not investment advice. See our <a href="/financial-disclaimer">Financial Disclaimer</a> for details.</p>

<h2>Source Attribution</h2>
<p>We aggregate information from publicly available sources including major news outlets. Original sources are referenced in our articles. If you believe we have improperly used your content, please see our <a href="/dmca-policy">DMCA Policy</a>.</p>

<h2>Limitations of AI Content</h2>
<p>AI-generated content may:</p>
<ul>
<li>Contain factual errors or inaccuracies</li>
<li>Lack the nuance of human-written journalism</li>
<li>Not reflect the most current information if sources are delayed</li>
<li>Occasionally produce awkward phrasing or unclear statements</li>
</ul>
<p>We encourage readers to verify important information through original sources and to use our content as a starting point for their own research.</p>

<h2>Your Feedback</h2>
<p>If you find errors in our content, please contact us at <a href="mailto:editorial@litimez.ai">editorial@litimez.ai</a>. We appreciate corrections and strive to improve our systems continuously.</p>
```

### 1.6 /cookie-policy

```html
<h1>Cookie Policy</h1>
<p><strong>Last Updated: [AUTO_DATE]</strong></p>

<p>This Cookie Policy explains how Litimez (litimez.ai) uses cookies and similar tracking technologies.</p>

<h2>What Are Cookies?</h2>
<p>Cookies are small text files stored on your device when you visit a website. They help websites remember your preferences and understand how you interact with the site.</p>

<h2>Cookies We Use</h2>

<h3>Essential Cookies</h3>
<p>Required for the website to function. Cannot be disabled.</p>
<ul>
<li>WordPress session cookies</li>
<li>Cookie consent preference</li>
</ul>

<h3>Analytics Cookies</h3>
<p>Help us understand how visitors interact with our website.</p>
<ul>
<li><strong>Google Analytics (_ga, _gid, _gat):</strong> Collects anonymized data about page views, session duration, and traffic sources. Data is processed by Google. <a href="https://policies.google.com/privacy" target="_blank">Google Privacy Policy</a>.</li>
</ul>

<h3>Functional Cookies</h3>
<ul>
<li>Theme preference (dark/light mode)</li>
<li>Language preference</li>
</ul>

<h2>How to Manage Cookies</h2>
<p>You can control cookies through:</p>
<ul>
<li>Our cookie consent banner (shown on first visit)</li>
<li>Your browser settings — most browsers allow you to block or delete cookies</li>
<li>Google Analytics Opt-out: <a href="https://tools.google.com/dlpage/gaoptout" target="_blank">Browser Add-on</a></li>
</ul>
<p>Disabling cookies may affect website functionality.</p>

<h2>Contact</h2>
<p>Questions about our cookie practices: <a href="mailto:privacy@litimez.ai">privacy@litimez.ai</a></p>
```

---

## 2. Email Setup

### 2.1 Recommended: Domain Email Forwarding

Cấu hình email forwarding từ domain registrar (Namecheap, GoDaddy, etc.) hoặc sử dụng Google Workspace.

### 2.2 Email Addresses to Create

| Email | Purpose | Forward to |
|-------|---------|-----------|
| legal@litimez.ai | Terms of Service, general legal | litimez.ai@gmail.com |
| privacy@litimez.ai | Privacy Policy, CCPA requests | litimez.ai@gmail.com |
| dmca@litimez.ai | DMCA takedown notices | litimez.ai@gmail.com |
| editorial@litimez.ai | Content corrections, AI feedback | litimez.ai@gmail.com |
| contact@litimez.ai | General inquiries | litimez.ai@gmail.com |

### 2.3 Configuration Steps

1. **Google Workspace** (Recommended):
   - Mua Google Workspace subscription
   - Thêm các email addresses trên
   - Set up email routing/filtering

2. **Domain Registrar Forwarding**:
   - Log in vào domain registrar
   - Tìm "Email Forwarding" hoặc "Email Management"
   - Tạo forwarders cho mỗi email trên

3. **Third-party Email Services** (e.g., Forwardemail.net):
   - Sử dụng MX records forwarding service
   - Miễn phí cho basic forwarding

---

## 3. DMCA Agent Registration

### 3.1 Why Register?

- Required for safe harbor protection under DMCA
- Shows commitment to protecting copyright
- Required for efficient takedown process

### 3.2 Registration Steps

1. **Go to**: https://www.copyright.gov/dmca-directory/

2. **Create account** at U.S. Copyright Office:
   - Click "Sign In" → "Create Account"
   - Fill in your information
   - Verify email

3. **Designate New Agent**:
   - Click "Designate a New Agent"
   - Fill in information:
     - **Service Provider Name**: Litimez / litimez.ai
     - **Designated Agent Name**: [Your Name or Company Name]
     - **Email**: dmca@litimez.ai
     - **Phone**: [Your Phone Number]
     - **Street Address**: [YOUR_PHYSICAL_ADDRESS]
     - **City**: [City]
     - **State**: [State]
     - **Postal Code**: [ZIP]
     - **Country**: United States of America

4. **Pay Fee**: $6 USD (online payment)

5. **Receive Confirmation**:
   - Save confirmation email
   - Update DMCA Policy page with actual information

### 3.3 Physical Address Requirements

Bạn cần một địa chỉ vật lý tại Mỹ. Options:
- **Virtual mailbox service** (e.g., EarthClassMail, Anytime Mailbox)
- **Registered Agent service** (e.g., Incfile, LegalZoom)
- **Friend/family address** in the U.S.

---

## 4. Testing Checklist

### 4.1 Legal Pages

- [ ] /terms-of-service hiển thị đúng, đầy đủ nội dung
- [ ] /privacy-policy hiển thị đúng, có CCPA section
- [ ] /dmca-policy hiển thị đúng, có DMCA agent info
- [ ] /financial-disclaimer hiển thị đúng, có risk warnings
- [ ] /ai-disclosure hiển thị đúng, giải thích cách dùng AI
- [ ] /cookie-policy hiển thị đúng, liệt kê cookies

### 4.2 Cookie Consent

- [ ] Banner hiện khi truy cập lần đầu (chưa có consent)
- [ ] Click "Accept All" → banner ẩn + GTM/GA load
- [ ] Click "Essential Only" → banner ẩn + analytics KHÔNG load
- [ ] Sau khi chọn, banner KHÔNG hiện lại khi reload
- [ ] Clear localStorage → banner hiện lại

### 4.3 Disclaimers

- [ ] Mỗi bài viết có disclaimer cuối bài (AI Disclosure + general disclaimer)
- [ ] Prediction widget có disclaimer ĐẦU + CUỐI
- [ ] Newsletter email có CAN-SPAM compliant footer (physical address + unsubscribe + disclaimer)
- [ ] Comment form có policy notice

### 4.4 Footer

- [ ] Site footer hiển thị links: Terms, Privacy, DMCA, Financial Disclaimer, AI Disclosure, Cookie Policy
- [ ] Copyright notice: "© [YEAR] Litimez (Linews). All rights reserved."
- [ ] Footer ghi: "Content is AI-assisted and for informational purposes only. Not investment advice."

### 4.5 Copyright Protection

- [ ] Governor copyright threshold = 0.30 (trong governor.py line 23)
- [ ] AI write prompts có copyright requirements
- [ ] Bài viết output có "Tong hop tu: [nguon]" cuối bài

### 4.6 [AUTO_DATE] Replacement

- [ ] Tất cả [AUTO_DATE] trong legal pages được thay bằng ngày thực tế
- [ ] Tất cả [YOUR_PHYSICAL_ADDRESS] được thay bằng địa chỉ thực tại Mỹ

### 4.7 Emails

- [ ] legal@litimez.ai forward hoạt động
- [ ] privacy@litimez.ai forward hoạt động
- [ ] dmca@litimez.ai forward hoạt động
- [ ] editorial@litimez.ai forward hoạt động
- [ ] contact@litimez.ai forward hoạt động

---

## 5. Notes

### 5.1 Governor Threshold

Đã kiểm tra: `app/pipeline/governor.py` line 23 có `COPYRIGHT_SIMILARITY_THRESHOLD = 0.30`. Không cần thay đổi.

### 5.2 Files Created

```
wordpress/mu-plugins/
├── linew-cookie-consent.php    # Cookie banner
├── linew-article-disclaimer.php # Article disclaimer
├── linew-footer-legal.php      # Footer legal links
├── linew-comment-notice.php   # Comment policy notice
├── linew-dmca-info.php         # DMCA info
├── linew-copyright-notice.php  # Source attribution
└── linew-canonical-links.php   # SEO canonical
```

### 5.3 Files Updated

```
app/widget/prediction.html      # Added financial disclaimer
app/distribution/newsletter.py   # CAN-SPAM compliant footer
app/core/ai_presets.py          # Copyright requirements in prompts
```

### 5.4 DMCA Agent Registration Status

- [ ] Chưa đăng ký - cần hoàn thành
- URL: https://www.copyright.gov/dmca-directory/
- Fee: $6

---

## Quick Reference

| Item | Status | Notes |
|------|--------|-------|
| Terms of Service | Pending | Tạo page trong WordPress |
| Privacy Policy | Pending | Tạo page trong WordPress |
| DMCA Policy | Pending | Tạo page + đăng ký agent |
| Financial Disclaimer | Pending | Tạo page trong WordPress |
| AI Disclosure | Pending | Tạo page trong WordPress |
| Cookie Policy | Pending | Tạo page trong WordPress |
| Email Setup | Partial | Sử dụng litimez.ai@gmail.com |
| Physical Address | Pending | Cần cung cấp địa chỉ Mỹ |
