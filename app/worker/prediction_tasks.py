"""
Celery wrappers for prediction tasks.
These wrappers convert async functions to Celery tasks.
"""
import logging
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def task_fetch_prices_celery(self):
    """Celery wrapper for fetching all prices."""
    import asyncio
    from app.prediction.tasks import task_fetch_all_prices

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_fetch_all_prices())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def task_run_model_inference_celery(self):
    """Celery wrapper for model inference."""
    import asyncio
    from app.prediction.tasks import task_run_model_inference

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_run_model_inference())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def task_run_ai_analysis_celery(self):
    """Celery wrapper for AI analysis."""
    import asyncio
    from app.prediction.tasks import task_run_ai_analysis

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_run_ai_analysis())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_update_accuracy_celery(self):
    """Celery wrapper for accuracy update."""
    import asyncio
    from app.prediction.tasks import task_update_accuracy

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_update_accuracy())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_check_alerts_celery(self):
    """Celery wrapper for alert checking."""
    import asyncio
    from app.prediction.tasks import task_check_alerts

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_check_alerts())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=180)
def task_run_full_prediction_celery(self, symbol: str = None):
    """Celery wrapper for full prediction pipeline."""
    import asyncio
    from app.prediction.tasks import task_run_full_prediction

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_run_full_prediction(symbol=symbol))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_run_ai_analysis_single_celery(self, symbol: str):
    """Celery wrapper for single symbol AI analysis."""
    import asyncio
    from app.prediction.tasks import task_run_ai_analysis_single

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_run_ai_analysis_single(symbol=symbol))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def task_fetch_single_symbol_celery(self, symbol: str):
    """Celery wrapper for single symbol price fetch."""
    import asyncio
    from app.prediction.tasks import task_fetch_single_symbol

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_fetch_single_symbol(symbol=symbol))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=180)
def task_predict_single_symbol_celery(self, symbol: str, horizon: int = 7):
    """Celery wrapper for single symbol prediction."""
    import asyncio
    from app.prediction.tasks import task_predict_single_symbol

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task_predict_single_symbol(symbol=symbol, horizon=horizon))
