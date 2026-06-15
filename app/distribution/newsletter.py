"""
Newsletter service for email digest distribution.
"""
import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db_context
from app.models.distribution import NewsletterSubscriber
from app.models.article import Article, ArticleState

logger = logging.getLogger(__name__)

NEWSLETTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: white;
            padding: 30px;
            border-radius: 12px 12px 0 0;
            text-align: center;
        }
        .header h1 { margin: 0; font-size: 28px; font-weight: 700; }
        .header p { margin: 10px 0 0; opacity: 0.9; font-size: 14px; }
        .date-badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 10px;
        }
        .content { background: white; padding: 20px; }
        .stats {
            display: flex;
            justify-content: space-around;
            padding: 15px 0;
            border-bottom: 1px solid #eee;
            margin-bottom: 20px;
        }
        .stat { text-align: center; }
        .stat-value { font-size: 24px; font-weight: 700; color: #2563eb; }
        .stat-label { font-size: 12px; color: #666; }
        .prediction-section {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .prediction-section h2 { margin: 0 0 10px; color: #92400e; font-size: 16px; }
        .prediction-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
        .prediction-item:last-child { border-bottom: none; }
        .prediction-symbol { font-weight: 600; color: #333; }
        .prediction-price { font-weight: 600; }
        .prediction-change {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .prediction-change.positive { background: #dcfce7; color: #166534; }
        .prediction-change.negative { background: #fee2e2; color: #991b1b; }
        .section-title {
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid;
        }
        .section-title.tech { color: #1e40af; border-color: #2563eb; }
        .section-title.finance { color: #92400e; border-color: #f59e0b; }
        .article { margin: 15px 0; padding: 15px; border-left: 3px solid; background: #f8fafc; }
        .article.tech { border-left-color: #2563eb; }
        .article.finance { border-left-color: #f59e0b; }
        .article h3 { margin: 0 0 8px; font-size: 16px; }
        .article h3 a { color: #1a1a1a; text-decoration: none; }
        .article h3 a:hover { color: #2563eb; }
        .article p { margin: 5px 0; font-size: 14px; color: #666; }
        .category-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .category-badge.tech { background: #dbeafe; color: #1e40af; }
        .category-badge.finance { background: #fef3c7; color: #92400e; }
        .footer { background: #f1f5f9; padding: 20px; border-radius: 0 0 12px 12px; text-align: center; }
        .footer p { margin: 5px 0; font-size: 12px; color: #666; }
        .unsubscribe { color: #999; text-decoration: none; font-size: 12px; }
        .unsubscribe:hover { color: #2563eb; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Linews Daily Digest</h1>
        <p>Tin tức Công nghệ & Tài chính</p>
        <span class="date-badge">{{ date }} - {{ total_articles }} bài viết mới</span>
    </div>
    <div class="content">
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{{ total_articles }}</div>
                <div class="stat-label">Bài viết</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{ tech_count }}</div>
                <div class="stat-label">Công nghệ</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{ finance_count }}</div>
                <div class="stat-label">Tài chính</div>
            </div>
        </div>
        {% if predictions %}
        <div class="prediction-section">
            <h2>Linews Analysis - Dự đoán thị trường</h2>
            {% for p in predictions %}
            <div class="prediction-item">
                <span class="prediction-symbol">{{ p.symbol }}</span>
                <span class="prediction-price">${{ p.current_price }}</span>
                <span class="prediction-change {{ 'positive' if p.change_pct > 0 else 'negative' }}">
                    {{ p.change_pct_str }}
                </span>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% if tech_articles %}
        <h2 class="section-title tech">Công nghệ</h2>
        {% for article in tech_articles %}
        <div class="article tech">
            <h3><a href="{{ article.wp_url }}">{{ article.title }}</a></h3>
            <p>{{ article.excerpt }}</p>
            <span class="category-badge tech">Tech</span>
        </div>
        {% endfor %}
        {% endif %}
        {% if finance_articles %}
        <h2 class="section-title finance">Tài chính</h2>
        {% for article in finance_articles %}
        <div class="article finance">
            <h3><a href="{{ article.wp_url }}">{{ article.title }}</a></h3>
            <p>{{ article.excerpt }}</p>
            <span class="category-badge finance">Finance</span>
        </div>
        {% endfor %}
        {% endif %}
    </div>
    <div class="footer">
        <p>Bạn nhận email này vì đã đăng ký Linews Newsletter.</p>
        <p><a href="{{ unsubscribe_url }}" class="unsubscribe">Hủy đăng ký</a></p>

        <!-- CAN-SPAM Compliant Section -->
        <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #e5e7eb;">
            <p style="margin: 0 0 8px 0; font-size: 11px; color: #666;">
                <strong>Disclaimer:</strong> This newsletter is for informational purposes only and does not
                constitute investment advice, financial advice, or any professional advice. Market predictions
                and analysis are estimates based on historical data and AI models. Past performance does not
                guarantee future results. All investments involve risk.
            </p>
            <p style="margin: 0 0 8px 0; font-size: 11px; color: #666;">
                Content is created with the assistance of AI from publicly available news sources.
                <a href="{{ site_url }}/ai-disclosure" style="color: #2563eb;">AI Disclosure</a> |
                <a href="{{ site_url }}/financial-disclaimer" style="color: #2563eb;">Financial Disclaimer</a> |
                <a href="{{ site_url }}/privacy-policy" style="color: #2563eb;">Privacy Policy</a>
            </p>
            <p style="margin: 0; font-size: 11px; color: #666;">
                Litimez / Linews | [YOUR_PHYSICAL_ADDRESS]<br>
                <a href="{{ unsubscribe_url }}" style="color: #2563eb;">Unsubscribe</a> from this newsletter.
            </p>
        </div>

        <p style="margin-top: 16px;">&copy; {{ year }} Linews - litimez.ai</p>
    </div>
</body>
</html>
"""


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


async def subscribe(
    db: AsyncSession,
    email: str,
    name: Optional[str] = None,
    categories: Optional[list[str]] = None,
    frequency: str = "daily",
) -> tuple[bool, str]:
    """Subscribe an email to the newsletter."""
    stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.is_active:
            return False, "Email đã được đăng ký"
        else:
            existing.is_active = True
            existing.subscribed_at = datetime.utcnow()
            existing.unsubscribed_at = None
            existing.categories = categories or ["tech", "finance"]
            existing.frequency = frequency
            await db.commit()
            return True, "Tài khoản đã được kích hoạt lại"

    subscriber = NewsletterSubscriber(
        email=email,
        name=name,
        categories=categories or ["tech", "finance"],
        frequency=frequency,
    )
    db.add(subscriber)
    await db.commit()
    return True, "Đăng ký thành công"


async def unsubscribe(db: AsyncSession, email: str) -> tuple[bool, str]:
    """Unsubscribe an email from the newsletter."""
    stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    result = await db.execute(stmt)
    subscriber = result.scalar_one_or_none()

    if not subscriber:
        return False, "Email không tồn tại trong hệ thống"
    if not subscriber.is_active:
        return True, "Email đã được hủy trước đó"

    subscriber.is_active = False
    subscriber.unsubscribed_at = datetime.utcnow()
    await db.commit()
    return True, "Hủy đăng ký thành công"


async def get_active_subscribers(db: AsyncSession) -> list[NewsletterSubscriber]:
    """Get all active subscribers."""
    stmt = (
        select(NewsletterSubscriber)
        .where(NewsletterSubscriber.is_active == True)
        .order_by(NewsletterSubscriber.subscribed_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_newsletter_articles(db: AsyncSession, target_date: date) -> tuple[list, list]:
    """Get articles for the newsletter by category."""
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())

    stmt = (
        select(Article)
        .where(Article.state == ArticleState.PUBLISHED.value)
        .where(Article.published_at >= start_of_day)
        .where(Article.published_at <= end_of_day)
        .order_by(Article.published_at.desc())
    )
    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    tech_articles = []
    finance_articles = []

    for article in articles:
        excerpt = strip_html(article.body_html or "")[:150].strip()
        if excerpt:
            excerpt += "..."
        article_data = {
            "title": article.meta_title or article.original_title,
            "excerpt": excerpt,
            "wp_url": article.wp_url,
        }
        if article.category == "tech":
            tech_articles.append(article_data)
        elif article.category == "finance":
            finance_articles.append(article_data)

    return tech_articles[:10], finance_articles[:10]


async def get_predictions(db: AsyncSession) -> list:
    """Get latest predictions for the newsletter."""
    from app.models.prediction import Prediction
    from sqlalchemy import desc

    stmt = (
        select(Prediction)
        .where(Prediction.actual_price.is_(None))
        .order_by(desc(Prediction.generated_at))
        .limit(5)
    )
    result = await db.execute(stmt)
    predictions = list(result.scalars().all())

    return [
        {
            "symbol": p.symbol,
            "current_price": f"{float(p.predicted_price):,.0f}",
            "change_pct": float(p.final_change_pct) if hasattr(p, 'final_change_pct') else 0,
            "change_pct_str": f"{float(p.final_change_pct):+.1f}%" if hasattr(p, 'final_change_pct') else "N/A",
        }
        for p in predictions
    ]


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via SMTP."""
    settings = get_settings()
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.newsletter_from_name} <{settings.newsletter_from_email}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        # Gmail port 587 requires STARTTLS, not implicit TLS
        if settings.smtp_port == 587:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                start_tls=True,
            )
        else:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=True,
            )
        logger.info(f"Newsletter email sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


async def send_daily_digest() -> dict:
    """Send daily newsletter digest to all subscribers."""
    settings = get_settings()
    if not settings.newsletter_enabled:
        return {"sent": 0, "reason": "newsletter_disabled"}

    yesterday = date.today() - timedelta(days=1)

    async with get_db_context() as db:
        tech_articles, finance_articles = await get_newsletter_articles(db, yesterday)
        if not tech_articles and not finance_articles:
            return {"sent": 0, "reason": "no_articles", "date": str(yesterday)}

        predictions = await get_predictions(db)
        subscribers = await get_active_subscribers(db)
        if not subscribers:
            return {"sent": 0, "reason": "no_subscribers"}

        template = Template(NEWSLETTER_TEMPLATE)
        total_articles = len(tech_articles) + len(finance_articles)
        sent_count = 0
        failed_count = 0

        for subscriber in subscribers:
            try:
                unsubscribe_url = f"{settings.site_url}/api/newsletter/unsubscribe?email={subscriber.email}"
                site_url = settings.site_url
                html = template.render(
                    date=yesterday.strftime("%d/%m/%Y"),
                    year=yesterday.year,
                    total_articles=total_articles,
                    tech_count=len(tech_articles),
                    finance_count=len(finance_articles),
                    tech_articles=tech_articles,
                    finance_articles=finance_articles,
                    predictions=predictions,
                    unsubscribe_url=unsubscribe_url,
                    site_url=site_url,
                )
                subject = f"Linews Digest - {yesterday.strftime('%d/%m/%Y')} - {total_articles} bài mới"
                success = await send_email(to=subscriber.email, subject=subject, html=html)

                if success:
                    sent_count += 1
                    subscriber.total_sent += 1
                    subscriber.last_sent_at = datetime.utcnow()
                else:
                    failed_count += 1
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to send newsletter to {subscriber.email}: {e}")
                failed_count += 1
                await db.rollback()

        return {
            "sent": sent_count,
            "failed": failed_count,
            "total_subscribers": len(subscribers),
            "total_articles": total_articles,
            "date": str(yesterday),
        }


async def test_smtp_connection() -> dict:
    """Test SMTP connection."""
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_username:
        return {"success": False, "error": "SMTP not configured"}
    try:
        msg = MIMEText("Test email from Linews Newsletter system", "plain")
        msg["From"] = f"{settings.newsletter_from_name} <{settings.newsletter_from_email}>"
        msg["To"] = settings.smtp_username
        msg["Subject"] = "Linews Newsletter Test"
        # Gmail port 587 requires STARTTLS, not implicit TLS
        if settings.smtp_port == 587:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                start_tls=True,
            )
        else:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=True,
            )
        return {"success": True, "message": "SMTP connection successful"}
    except Exception as e:
        return {"success": False, "error": str(e)}
