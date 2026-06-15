$baseUrl = "http://localhost:8888/wp-json/wp/v2"
$creds = "TGl0aW1lejo4OUJvIGF0MGwgY096byB3QURMIGRIMjEgRHJmZg=="
$headers = @{
    "Authorization" = "Basic $creds"
    "Content-Type" = "application/json"
}

$pages = @{
    "about" = @{
        title = "About Us"
        content = "<h2>Welcome to Litimez</h2>
<p>Litimez is a leading AI-powered news aggregator that curates the most important stories from around the world. Our mission is to provide readers with accurate, timely, and diverse news coverage across multiple topics.</p>
<h3>Our Vision</h3>
<p>We believe in the power of information to inform, educate, and empower. Through advanced AI technology, we deliver news content that matters to our readers, helping them stay informed about the events shaping our world.</p>
<h3>Contact</h3>
<p>For inquiries, please contact us at <a href='mailto:info@litimez.ai'>info@litimez.ai</a></p>"
    }
    "contact" = @{
        title = "Contact Us"
        content = "<h2>Get in Touch</h2>
<p>We'd love to hear from you! Whether you have a question about our content, would like to collaborate, or have any feedback, please don't hesitate to reach out.</p>
<h3>Email</h3>
<p>For general inquiries: <a href='mailto:info@litimez.ai'>info@litimez.ai</a></p>
<h3>Response Time</h3>
<p>We typically respond to inquiries within 24-48 hours on business days.</p>"
    }
    "terms-of-service" = @{
        title = "Terms of Service"
        content = "<h2>Terms of Service</h2>
<p><strong>Last updated: April 2026</strong></p>
<h3>1. Acceptance of Terms</h3>
<p>By accessing and using Litimez, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our website.</p>
<h3>2. Description of Service</h3>
<p>Litimez is an AI-powered news aggregation service that collects, curates, and presents news content from various sources around the world.</p>
<h3>3. User Responsibilities</h3>
<p>You agree to use the service for lawful purposes only and will not attempt to gain unauthorized access to any part of the website.</p>
<h3>4. Intellectual Property</h3>
<p>All original content produced by Litimez is protected by copyright. News content from external sources remains the property of respective publishers.</p>
<h3>5. Disclaimer</h3>
<p>Litimez provides news content for informational purposes only. We do not guarantee the accuracy, completeness, or timeliness of any content.</p>
<h3>6. Limitation of Liability</h3>
<p>Litimez shall not be liable for any direct, indirect, incidental, or consequential damages arising from the use of our service.</p>
<h3>7. Changes to Terms</h3>
<p>We reserve the right to modify these terms at any time. Continued use of the service constitutes acceptance of modified terms.</p>
<h3>8. Contact</h3>
<p>For questions about these terms, please contact us at <a href='mailto:info@litimez.ai'>info@litimez.ai</a></p>"
    }
    "privacy-policy" = @{
        title = "Privacy Policy"
        content = "<h2>Privacy Policy</h2>
<p><strong>Last updated: April 2026</strong></p>
<h3>1. Information We Collect</h3>
<p>We may collect information you provide directly, such as when you subscribe to our newsletter, contact us, or interact with our content.</p>
<h3>2. How We Use Your Information</h3>
<p>We use collected information to improve our service, personalize your experience, and communicate with you about relevant news content.</p>
<h3>3. Cookies and Tracking</h3>
<p>We use cookies to enhance your browsing experience and analyze site traffic. You may disable cookies in your browser settings.</p>
<h3>4. Third-Party Services</h3>
<p>Our website may contain links to third-party sites. We are not responsible for the privacy practices of these external sites.</p>
<h3>5. Data Security</h3>
<p>We implement appropriate security measures to protect your personal information from unauthorized access or disclosure.</p>
<h3>6. Your Rights</h3>
<p>You have the right to access, correct, or delete your personal information. Contact us to exercise these rights.</p>
<h3>7. Children's Privacy</h3>
<p>Our service is not intended for children under 13 years of age. We do not knowingly collect information from children.</p>
<h3>8. Contact</h3>
<p>For privacy-related questions, please contact us at <a href='mailto:info@litimez.ai'>info@litimez.ai</a></p>"
    }
    "dmca-policy" = @{
        title = "DMCA Policy"
        content = "<h2>DMCA Copyright Policy</h2>
<p><strong>Last updated: April 2026</strong></p>
<h3>1. Digital Millennium Copyright Act</h3>
<p>Litimez respects the intellectual property rights of others and complies with the Digital Millennium Copyright Act (DMCA).</p>
<h3>2. Reporting Copyright Infringement</h3>
<p>If you believe that content on our website infringes your copyright, please provide our designated agent with the following information:</p>
<ul>
<li>A physical or electronic signature of the copyright owner or authorized representative</li>
<li>Identification of the copyrighted work claimed to have been infringed</li>
<li>Identification of the material that is claimed to be infringing</li>
<li>Your contact information (address, telephone, email)</li>
<li>A statement that you have a good faith belief that the use is not authorized</li>
<li>A statement, under penalty of perjury, that the information is accurate</li>
</ul>
<h3>3. DMCA Agent Contact</h3>
<p>Copyright Agent<br>Email: <a href='mailto:dmca@litimez.ai'>dmca@litimez.ai</a></p>
<h3>4. Counter-Notification</h3>
<p>If you believe your content was removed by mistake, you may submit a counter-notification containing your details and a statement of good faith.</p>"
    }
    "cookie-policy" = @{
        title = "Cookie Policy"
        content = "<h2>Cookie Policy</h2>
<p><strong>Last updated: April 2026</strong></p>
<h3>1. What Are Cookies</h3>
<p>Cookies are small text files stored on your device when you visit websites. They help websites remember your preferences and improve your experience.</p>
<h3>2. How We Use Cookies</h3>
<p>We use cookies for:</p>
<ul>
<li>Essential site functionality</li>
<li>Analytics and performance tracking</li>
<li>Personalized content recommendations</li>
<li>Remembering your preferences</li>
</ul>
<h3>3. Types of Cookies We Use</h3>
<p><strong>Essential Cookies:</strong> Required for basic site functionality<br>
<strong>Analytics Cookies:</strong> Help us understand how visitors use our site<br>
<strong>Preference Cookies:</strong> Remember your settings and choices</p>
<h3>4. Managing Cookies</h3>
<p>You can control cookie preferences through your browser settings. Disabling cookies may affect site functionality.</p>
<h3>5. Third-Party Cookies</h3>
<p>Some cookies are placed by third-party services. Review third-party privacy policies for more information.</p>
<h3>6. Contact</h3>
<p>Questions? Email us at <a href='mailto:info@litimez.ai'>info@litimez.ai</a></p>"
    }
    "financial-disclaimer" = @{
        title = "Financial Disclaimer"
        content = "<h2>Financial Disclaimer</h2>
<p><strong>Last updated: April 2026</strong></p>
<h3>1. No Financial Advice</h3>
<p>Content on Litimez, including any financial news, market analysis, or investment-related information, is provided for informational purposes only and does not constitute financial advice.</p>
<h3>2. Not a Financial Advisor</h3>
<p>Litimez is a news aggregation service and is not a registered financial advisor, broker, or dealer. We do not provide personalized investment recommendations.</p>
<h3>3. Investment Risks</h3>
<p>All investments carry risk. Past performance is not indicative of future results. The value of investments can decrease as well as increase.</p>
<h3>4. Do Your Own Research</h3>
<p>Before making any investment decisions, conduct your own research and consult with qualified financial professionals.</p>
<h3>5. Market Volatility</h3>
<p>Financial markets can be highly volatile. News events can significantly impact asset prices. Make informed decisions based on multiple sources.</p>
<h3>6. Limitation of Liability</h3>
<p>Litimez shall not be held liable for any losses incurred as a result of relying on our financial news content.</p>
<h3>7. Contact</h3>
<p>For financial advice, please consult a licensed financial advisor.</p>"
    }
    "ai-disclosure" = @{
        title = "AI Content Disclosure"
        content = "<h2>AI Content Disclosure</h2>
<p><strong>Last updated: April 2026</strong></p>
<h3>1. AI-Generated Content</h3>
<p>Litimez uses artificial intelligence (AI) to research, summarize, and rewrite news content from various sources around the world.</p>
<h3>2. Our AI Process</h3>
<p>Our AI system:</p>
<ul>
<li>Collects news from trusted RSS sources</li>
<li>Summarizes and translates content using AI</li>
<li>Rewrites articles in our editorial style</li>
<li>Sources and optimizes images</li>
</ul>
<h3>3. Editorial Oversight</h3>
<p>While our AI handles content generation, we maintain quality standards to ensure accuracy and relevance.</p>
<h3>4. Source Attribution</h3>
<p>All articles include proper attribution to original sources. We respect copyright and intellectual property rights.</p>
<h3>5. Content Quality</h3>
<p>We strive for accuracy, but AI-generated content may occasionally contain errors. Verify important information from primary sources.</p>
<h3>6. Transparency</h3>
<p>This disclosure explains how AI is used in our content creation process. We believe in being transparent about our methods.</p>
<h3>7. Benefits of AI</h3>
<p>AI allows us to curate and present a diverse range of news content efficiently, keeping readers informed about events worldwide.</p>
<h3>8. Contact</h3>
<p>Questions about our AI process? Email us at <a href='mailto:info@litimez.ai'>info@litimez.ai</a></p>"
    }
}

# Create each page
foreach ($slug in $pages.Keys) {
    $page = $pages[$slug]
    $body = @{
        title = $page.title
        slug = $slug
        content = $page.content
        status = "publish"
    } | ConvertTo-Json -Compress

    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/pages" -Method Post -ContentType "application/json" -Headers $headers -Body $body
        Write-Host "Created page: $($page.title) (ID: $($response.id))" -ForegroundColor Green
    } catch {
        Write-Host "Error creating $($page.title): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nAll pages created!" -ForegroundColor Cyan
