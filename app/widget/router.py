"""
Widget API routes - serve standalone HTML widgets.
"""
import logging
import os
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/widget", tags=["widget"])

_widget_html_cache = None
_widget_file_mtime = None

def get_widget_html():
    """Load widget HTML content with cache busting."""
    global _widget_html_cache, _widget_file_mtime
    
    widget_path = os.path.join(os.path.dirname(__file__), 'prediction.html')
    current_mtime = os.path.getmtime(widget_path)
    
    # Reload if file changed
    if _widget_html_cache is None or _widget_file_mtime != current_mtime:
        with open(widget_path, 'r', encoding='utf-8') as f:
            _widget_html_cache = f.read()
        _widget_file_mtime = current_mtime
        logger.info(f"Widget HTML reloaded from file")
    
    return _widget_html_cache


@router.get("/prediction", response_class=HTMLResponse)
async def prediction_widget():
    """
    Serve prediction widget as standalone HTML page.
    WordPress embeds via iframe at: https://litimez.ai/api/widget/prediction
    """
    html = get_widget_html()
    return HTMLResponse(
        content=html,
        headers={
            "X-Frame-Options": "ALLOW-FROM https://litimez.ai",
            "Content-Security-Policy": "frame-ancestors 'self' https://litimez.ai; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline';",
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Vary": "Cache-Control",
        }
    )


@router.get("/prediction/v2", response_class=HTMLResponse)
async def prediction_widget_v2():
    """
    Serve prediction widget v2 - always fresh from file.
    """
    widget_path = os.path.join(os.path.dirname(__file__), 'prediction.html')
    with open(widget_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    return HTMLResponse(
        content=html,
        headers={
            "X-Frame-Options": "ALLOW-FROM *",
            "Content-Security-Policy": "frame-ancestors 'self' *; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline';",
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@router.get("/prediction/embed", response_class=HTMLResponse)
async def prediction_widget_embed():
    """Return embed code snippet for iframe."""
    embed_code = '''
    <iframe 
        src="https://litimez.ai/api/widget/prediction" 
        width="100%" 
        height="700" 
        frameborder="0" 
        style="border:none; border-radius:12px; max-width:720px; display:block; margin:0 auto;"
        loading="lazy"
        title="Linews Analysis - Market Prediction">
    </iframe>
    '''
    return HTMLResponse(content=f"<pre>{embed_code.strip()}</pre>")
