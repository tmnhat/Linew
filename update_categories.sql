UPDATE settings 
SET value = jsonb_set(
    value::jsonb, 
    '{active_categories}', 
    '["tech", "technology", "finance", "crypto", "cryptocurrency", "stock", "stocks", "business", "công nghệ", "tài chính", "sức khỏe", "khám phá", "ô tô", "giáo dục", "kinh tế", "thể thao", "chính trị", "quốc tế", "giải trí", "world", "politics", "health", "sports", "education", "automotive", "exploration", "entertainment", "Finance", "Technology", "Politics", "World", "Entertainment", "Education", "Health", "Sports", "Exploration", "Automotive"]'::jsonb
)
WHERE key = 'pipeline';
