"""
Test script to publish a sample article to Facebook Page.
Run with: python -m app.distribution.test_facebook
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockArticle:
    """Mock article object for testing."""
    
    def __init__(self):
        self.id = "test-article-001"
        self.meta_title = "AI GPT-5 Đạt Điểm Số Cao Nhất Trong Bài Kiểm Tra Y Khoa Khó Nhất Thế Giới"
        self.original_title = "GPT-5 passes medical licensing exam with highest score ever recorded"
        self.body_html = """
<p>OpenAI vừa công bố rằng GPT-5, mô hình AI thế hệ mới nhất của họ, đã đạt điểm số cao nhất từ trước đến nay trong bài kiểm tra y khoa cực kỳ khó khăn.</p>

<h2>Thành tích ấn tượng của GPT-5</h2>

<p>Theo báo cáo chính thức từ OpenAI, GPT-5 đã vượt qua kỳ thi US Medical Licensing Examination (USMLE) với số điểm 92.3%, cao hơn đáng kể so với mức điểm đạt của các bác sĩ thực thụ (trung bình khoảng 85%).</p>

<p>Đặc biệt, trong phần thi chẩn đoán lâm sàng, GPT-5 đã đưa ra chẩn đoán chính xác cho 97.8% các ca bệnh phức tạp, bao gồm cả những ca hiếm gặp mà ngay cả các chuyên gia y khoa hàng đầu cũng gặp khó khăn.</p>

<h2>Ý nghĩa đối với ngành y tế</h2>

<p>Tiến sĩ Sarah Chen, Trưởng khoa Y khoa tại Đại học Stanford, nhận định: "Đây là một bước tiến đột phá. GPT-5 không chỉ hỗ trợ được các bác sĩ trong chẩn đoán mà còn có thể đề xuất phác đồ điều trị tối ưu dựa trên dữ liệu bệnh nhân."</p>

<h3>Ứng dụng thực tế</h3>

<ul>
<li>Hỗ trợ chẩn đoán ban đầu cho bệnh nhân ở vùng sâu vùng xa</li>
<li>Phân tích hình ảnh y khoa (X-quang, MRI, CT scan)</li>
<li>Nghiên cứu thuốc mới và tương tác thuốc</li>
<li>Đào tạo y khoa và mô phỏng tình huống lâm sàng</li>
</ul>

<h2>Những lo ngại về an toàn</h2>

<p>Tuy nhiên, nhiều chuyên gia cũng bày tỏ lo ngại. Tiến sĩ Michael Roberts, Chủ tịch Hội đồng Y khoa Hoa Kỳ, cho biết: "Mặc dù GPT-5 đạt điểm cao trong bài thi, nhưng chúng ta không thể thay thế hoàn toàn sự tương tác giữa bác sĩ và bệnh nhân. AI cần được sử dụng như một công cụ hỗ trợ, không phải thay thế."</p>

<p>OpenAI cam kết sẽ tiếp tục hợp tác với các tổ chức y tế để đảm bảo GPT-5 được sử dụng an toàn và hiệu quả trong thực tế.</p>

<blockquote>Đây là minh chứng rõ ràng rằng AI có tiềm năng to lớn trong việc cải thiện chăm sóc sức khỏe toàn cầu. - Sam Altman, CEO OpenAI</blockquote>
        """
        self.crawled_content = self.body_html
        self.original_summary = "GPT-5 đạt điểm cao nhất trong kỳ thi y khoa USMLE với 92.3%, vượt mặt các bác sĩ thực thụ."
        self.category = "công nghệ"
        self.trend_score = 0.85
        self.tags = ["AI", "GPT-5", "OpenAI", "y khoa", "công nghệ"]
        self.original_image_url = "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800"
        self.featured_image_url = "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800"
        self.crawled_images = [
            {"url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800", "alt": "AI Medical"}
        ]
        self.word_count = 350


async def test_facebook_post():
    """Test posting to Facebook with full content."""
    from app.distribution.facebook import format_article_for_facebook, post_to_facebook_no_link
    import logging
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Create mock article
    article = MockArticle()
    
    print("=" * 60)
    print("TESTING FACEBOOK POST FORMAT")
    print("=" * 60)
    print()
    
    # Test format_facebook_message
    print("1. Testing format_facebook_message()...")
    message, image_url = format_facebook_message(article)
    
    print(f"\n📋 Message length: {len(message)} characters")
    print(f"🖼️ Image URL: {image_url}")
    print()
    print("-" * 60)
    print("MESSAGE PREVIEW:")
    print("-" * 60)
    print(message[:2000])
    if len(message) > 2000:
        print(f"\n... [truncated, total {len(message)} chars]")
    print("-" * 60)
    
    # Ask user if they want to actually post
    print()
    print("=" * 60)
    response = input("Do you want to POST this to Facebook Page? (y/N): ").strip().lower()
    
    if response == 'y':
        print("\n📤 Posting to Facebook...")
        result = await post_to_facebook_no_link(article)
        
        print()
        print("=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(f"Status: {result.get('status')}")
        print(f"Has Image: {result.get('has_image')}")
        if result.get('external_url'):
            print(f"URL: {result.get('external_url')}")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
    else:
        print("\nSkipped posting to Facebook.")


if __name__ == "__main__":
    asyncio.run(test_facebook_post())
