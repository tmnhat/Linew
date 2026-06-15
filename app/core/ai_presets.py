"""
AI Prompt Templates for all tasks.
"""

CATEGORIZE_PROMPT = """You are a news classification system. Classify the article into ONE of these categories:
- technology: Technology, AI, Software, Hardware, Internet, Computer Science, Robotics
- finance: Finance, Stock Market, Crypto, Economy, Banking, Investment, Trading
- sports: Sports, Football, Basketball, Tennis, Racing, Olympics, UFC
- entertainment: Entertainment, Movies, Music, Games, TV, Celebrity, Hollywood
- health: Health, Healthcare, Medical, Nutrition, Fitness, Disease, Vaccine
- education: Education, University, School, Student, Research, Learning, Academic
- politics: Politics, Government, Election, Congress, Legislation, Trump, Biden
- world: International, World, Europe, Asia, China, Russia, Ukraine, Middle East
- exploration: Exploration, Space, NASA, Mars, Ocean, Archaeology, Environment, Climate
- automotive: Automotive, Cars, Electric Vehicle, Tesla, Toyota, Ford, BMW

Title: {title}
Summary: {summary}

Respond with JSON:
{{"category": "technology|finance|sports|entertainment|health|education|politics|world|exploration|automotive", "confidence": 0.0-1.0}}"""

WRITE_QUICK_PROMPT = """You are a professional journalist writing news articles in ENGLISH.

TASK: The original article may be in Chinese, English, or other languages. YOU MUST:
1. Read and UNDERSTAND the original content (translate if needed)
2. REWRITE completely in proper ENGLISH

Original article information:
- Original Title: {original_title}
- Summary: {original_summary}
- Source: {source_name}
- Category: {category}

MANDATORY REQUIREMENTS:
1. First: DETERMINE the original language of the article
2. If in Chinese (Chinese), English, or other languages -> TRANSLATE and REWRITE in ENGLISH
3. If already in English -> Rewrite in professional journalism style
4. Final article must be: 400-800 words, entirely in ENGLISH
5. Tone: professional, objective, easy to read
6. Structure: Title -> Lead (opening summary paragraph) -> Body -> Conclusion
7. Body uses HTML format (<h2>, <p>, <strong>, <em>, <ul>, <li>)
8. INSERT IMAGE PLACEHOLDERS: After every 2-3 paragraphs, insert placeholder [IMAGE_1], [IMAGE_2]...
   to mark positions for images. Example:
   <p>Paragraph 1...</p>
   <p>Paragraph 2...</p>
   [IMAGE_1]
   <p>Paragraph 3...</p>
   [IMAGE_2]
9. Clearly state the reference source at the end
10. DO NOT fabricate information not present in the source

CRITICAL - COPYRIGHT COMPLIANCE:
- You MUST rewrite COMPLETELY using your own words, sentence structures, and phrasing
- Do NOT translate or paraphrase closely from the original source
- Do NOT copy phrases, sentences, or paragraphs from the source material
- Create original sentences that convey the same information in a fresh way
- Write in Linews's distinctive voice and style, clearly different from the original source
- At the end of the article, include source attribution: "Tong hop tu: [source_name]"

CRITICAL - TAGS REQUIREMENT:
You MUST generate 5-8 relevant tags for this article. Tags should be:
- Specific topics or entities mentioned in the article (e.g., "AI", "Bitcoin", "Ukraine")
- Related keywords that readers might search for
- Mix of broad (e.g., "Technology") and specific (e.g., "GPT-5") tags
- Include the category as a tag: {category}

IMPORTANT: body_html must be entirely in ENGLISH. Do not keep Chinese characters or other languages in body_html.

Respond with JSON:
{{
  "body_html": "...",
  "meta_title": "English SEO title (max 60 characters)",
  "meta_description": "English SEO description (max 155 characters)",
  "slug": "english-article-title-no-spaces",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"]
}}"""

WRITE_PREMIUM_PROMPT = """You are a senior editor writing in-depth news articles in ENGLISH.

TASK: Create a comprehensive, well-researched article from the provided information.

Original article information:
- Original Title: {original_title}
- Summary: {original_summary}
- Source: {source_name}
- Category: {category}

ARTICLE REQUIREMENTS:
1. Write entirely in professional ENGLISH
2. Article length: 800-1500 words
3. Structure:
   - Compelling headline
   - Informative subheadline
   - Lead paragraph (who, what, when, where, why, how)
   - Supporting paragraphs with context and analysis
   - Expert quotes or expert opinions (if applicable)
   - Conclusion with implications
4. Use HTML formatting: <h2>, <p>, <strong>, <blockquote>, <ul>, <li>
5. Include relevant [IMAGE_1], [IMAGE_2], etc. placeholders for images
6. Cite sources clearly

CRITICAL - COPYRIGHT COMPLIANCE:
- You MUST rewrite COMPLETELY using your own words, sentence structures, and phrasing
- Do NOT translate or paraphrase closely from the original source
- Do NOT copy phrases, sentences, or paragraphs from the source material
- Create original sentences that convey the same information in a fresh way
- Write in Linews's distinctive voice and style, clearly different from the original source
- At the end of the article, include source attribution: "Tong hop tu: [source_name]"

CRITICAL - TAGS REQUIREMENT:
You MUST generate 5-8 relevant tags for this article. Tags should be:
- Specific topics or entities mentioned in the article (e.g., "AI", "Bitcoin", "Ukraine")
- Related keywords that readers might search for
- Mix of broad (e.g., "Technology") and specific (e.g., "GPT-5") tags
- Include the category as a tag: {category}

IMPORTANT: Entire article must be in ENGLISH. No Vietnamese, Chinese, or other language characters in body_html.

Respond with JSON:
{{
  "body_html": "...",
  "meta_title": "English SEO title (max 60 characters)",
  "meta_description": "English SEO description (max 155 characters)",
  "slug": "english-article-slug",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"]
}}"""

RESEARCH_PROMPT = """Analyze this article and provide key insights in ENGLISH:

Title: {title}
Content: {content}

Provide:
1. Key facts (3-5 bullet points)
2. Main entities mentioned
3. Related topics
4. Sentiment (positive/negative/neutral)
5. Keywords for related articles

Respond with JSON:
{{
  "key_facts": ["..."],
  "entities": ["..."],
  "related_topics": ["..."],
  "sentiment": "positive|negative|neutral",
  "keywords": ["..."]
}}"""

GOVERNANCE_PROMPT = """You are a content moderation system. Review the following article for policy violations.

Article content:
{body_html}

Check for:
1. Hate speech or discriminatory content
2. Violence or dangerous instructions
3. Misinformation or fake news
4. Copyright infringement (extensive copying from source)
5. Spam or misleading content
6. Adult/inappropriate content

Respond with JSON:
{{"result": "pass|fail|review", "reason": "explanation if fail"}}"""

# Legacy alias
WRITE_DEEP_PROMPT = WRITE_PREMIUM_PROMPT
