"""
AI Gateway - flexible AI API client with support for OpenAI-compatible APIs.

Updated với pipeline-friendly behavior:
- KHÔNG BAO GIỜ stop pipeline khi AI fail
- Retry với exponential backoff
- Chờ tối đa 10 phút nếu AI down
- Sau 10 phút vẫn tiếp tục retry (chỉ log warning)
- Track AI availability trong Redis để monitoring
"""
import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional

from openai import AsyncOpenAI
from openai._exceptions import APIError, RateLimitError, APITimeoutError

logger = logging.getLogger(__name__)

# AI availability tracking in Redis
AI_UNAVAILABLE_KEY = "linew:ai:unavailable_since"
AI_CONSECUTIVE_FAILURES_KEY = "linew:ai:consecutive_failures"
AI_AVAILABILITY_TTL = 3600  # 1 hour


class AIGatewayCircuitBreaker:
    """
    AI Gateway Circuit Breaker - NHẸ hơn so với original.

    Khác với original:
    - KHÔNG stop pipeline khi open
    - Chỉ track số failures và log warnings
    - Tự động close sau 60 giây không có failure
    - Ghi AI unavailable timestamp vào Redis để monitoring
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self._was_open = False  # Track nếu từng open

    @property
    def is_open(self) -> bool:
        """Legacy property for compatibility with health.py."""
        return self._was_open

    @is_open.setter
    def is_open(self, value: bool) -> None:
        """Legacy setter for compatibility with health.py."""
        self._was_open = value

    def record_success(self) -> None:
        self.failures = 0
        self.last_failure_time = None
        self._was_open = False
        # Clear Redis unavailable status
        self._clear_unavailable_status()

    def record_failure(self, error: str = "") -> None:
        self.failures += 1
        self.last_failure_time = time.time()

        # Track consecutive failures
        self._update_failure_count()

        if self.failures >= self.failure_threshold and not self._was_open:
            self._was_open = True
            self._set_unavailable_status()

    def can_proceed(self) -> bool:
        """
        AI Gateway luôn cho phép proceed.
        KHÔNG BAO GIỜ stop pipeline vì AI.
        """
        return True

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        elapsed = 0
        if self.last_failure_time:
            elapsed = time.time() - self.last_failure_time

        return {
            "consecutive_failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_remaining": max(0, self.recovery_timeout - elapsed),
            "last_failure": self.last_failure_time,
        }

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.failures = 0
        self.last_failure_time = None
        self._was_open = False
        self._clear_unavailable_status()
        logger.info("AI Gateway circuit breaker manually reset")

    def _update_failure_count(self) -> None:
        """Update failure count in Redis."""
        try:
            import redis
            from urllib.parse import urlparse
            from app.config import get_settings

            settings = get_settings()
            parsed = urlparse(settings.redis_url)
            redis_host = parsed.hostname or "localhost"
            redis_port = parsed.port or 6379
            redis_db = int(parsed.path.lstrip("/") or 0)

            client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
            client.set(AI_CONSECUTIVE_FAILURES_KEY, str(self.failures), ex=AI_AVAILABILITY_TTL)
        except Exception:
            pass

    def _set_unavailable_status(self) -> None:
        """Set AI unavailable status in Redis."""
        try:
            import redis
            from urllib.parse import urlparse
            from app.config import get_settings

            settings = get_settings()
            parsed = urlparse(settings.redis_url)
            redis_host = parsed.hostname or "localhost"
            redis_port = parsed.port or 6379
            redis_db = int(parsed.path.lstrip("/") or 0)

            client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
            timestamp = datetime.utcnow().isoformat()
            client.set(AI_UNAVAILABLE_KEY, timestamp, ex=AI_AVAILABILITY_TTL)
            logger.warning(f"AI Gateway: AI service marked as unavailable at {timestamp}")
        except Exception:
            pass

    def _clear_unavailable_status(self) -> None:
        """Clear AI unavailable status in Redis."""
        try:
            import redis
            from urllib.parse import urlparse
            from app.config import get_settings

            settings = get_settings()
            parsed = urlparse(settings.redis_url)
            redis_host = parsed.hostname or "localhost"
            redis_port = parsed.port or 6379
            redis_db = int(parsed.path.lstrip("/") or 0)

            client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
            client.delete(AI_UNAVAILABLE_KEY)
            client.delete(AI_CONSECUTIVE_FAILURES_KEY)
        except Exception:
            pass


circuit_breaker = AIGatewayCircuitBreaker()


class AIGateway:
    """
    AI Gateway with dynamic configuration.
    Reads settings from database on each request to allow runtime updates.
    Supports both OpenAI-compatible APIs and Vertex AI (MiniMax).
    """

    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None
        self._last_settings_hash: Optional[str] = None

    def _get_ai_settings(self) -> dict[str, Any]:
        """Get AI settings from Settings (environment) first, then database as fallback."""
        from app.config import get_settings
        settings = get_settings()

        # Check for Vertex/Proxy configuration first
        if settings.vertex_api_key:
            return {
                "gateway_url": getattr(settings, 'vertex_base_url', 'https://vertex-key.com/api/v1'),
                "api_key": settings.vertex_api_key,
                "writer_model": settings.ai_writer_model,
                "researcher_model": settings.ai_researcher_model,
                "light_model": settings.ai_light_model,
                "summarizer_model": settings.ai_summarizer_model,
                "use_vertex": True,
            }

        # Then check for OpenAI-compatible gateway
        if settings.ai_gateway_url or settings.ai_gateway_key:
            return {
                "gateway_url": settings.ai_gateway_url,
                "api_key": settings.ai_gateway_key,
                "writer_model": getattr(settings, 'ai_writer_model', 'gpt-4o'),
                "researcher_model": getattr(settings, 'ai_researcher_model', 'claude-3-5-sonnet'),
                "light_model": getattr(settings, 'ai_light_model', 'gpt-4o-mini'),
                "summarizer_model": getattr(settings, 'ai_summarizer_model', 'gpt-4o-mini'),
                "use_vertex": False,
            }

        # Fallback to database
        try:
            from app.core.database import get_db_context
            from sqlalchemy import select
            from app.models.setting import Setting

            async def _fetch():
                async with get_db_context() as db_session:
                    result = await db_session.execute(select(Setting).where(Setting.key == "ai"))
                    setting = result.scalar_one_or_none()
                    if setting:
                        return setting.value
                    return self._get_default_ai_settings()

            # Run in sync context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _fetch())
                return future.result(timeout=5)
        except Exception as e:
            logger.warning(f"Failed to fetch AI settings from DB: {e}")
            return self._get_default_ai_settings()

    def _get_default_ai_settings(self) -> dict[str, Any]:
        """Get default AI settings."""
        return {
            "gateway_url": "https://api.openai.com/v1",
            "api_key": "",
            "writer_model": "gpt-4o",
            "researcher_model": "claude-3-5-sonnet",
            "light_model": "gpt-4o-mini",
            "summarizer_model": "gpt-4o-mini",
            "use_vertex": False,
        }

    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client with current settings."""
        settings = self._get_ai_settings()
        settings_hash = str(hash(frozenset({k: v for k, v in settings.items()}.items())))

        # Recreate client if settings changed
        if self._client is None or self._last_settings_hash != settings_hash:
            use_vertex = settings.get("use_vertex", False)
            api_key = settings.get("api_key", "")

            if use_vertex:
                # MiniMax via Vertex proxy
                gateway_url = settings.get("gateway_url", "https://vertex-key.com/api/v1")
                # Ensure URL ends with /v1
                if not gateway_url.endswith("/v1"):
                    gateway_url = f"{gateway_url.rstrip('/')}/v1"
                self._client = AsyncOpenAI(
                    base_url=gateway_url,
                    api_key=api_key,
                    timeout=120.0,
                    max_retries=0,
                )
            else:
                gateway_url = settings.get("gateway_url", "https://api.openai.com/v1")

                # Ensure URL ends with /v1
                if not gateway_url.endswith("/v1"):
                    gateway_url = f"{gateway_url.rstrip('/')}/v1"

                self._client = AsyncOpenAI(
                    base_url=gateway_url,
                    api_key=api_key,
                    timeout=120.0,
                    max_retries=0,
                )

            self._last_settings_hash = settings_hash
            logger.info(f"AI Gateway client created (Vertex: {use_vertex})")

        return self._client

    def route_model(self, task_type: str) -> str:
        """Map task type to model based on settings."""
        settings = self._get_ai_settings()

        model_map = {
            "categorize": settings.get("light_model", "gpt-4o-mini"),
            "governance": settings.get("light_model", "gpt-4o-mini"),
            "moderate": settings.get("light_model", "gpt-4o-mini"),
            "summarize": settings.get("summarizer_model", "gpt-4o-mini"),
            "write": settings.get("writer_model", "gpt-4o"),
            "write_quick": settings.get("writer_model", "gpt-4o"),
            "write_deep": settings.get("writer_model", "gpt-4o"),
            "research": settings.get("researcher_model", "claude-3-5-sonnet"),
        }

        return model_map.get(task_type, settings.get("light_model", "gpt-4o-mini"))

    async def call_ai(
        self,
        prompt: str,
        model: Optional[str] = None,
        task_type: str = "default",
        response_format: Optional[dict] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Call AI với PIPELINE-FRIENDLY retry logic.

        Key improvements:
        1. Retry đến 10 lần (thay vì 3)
        2. Exponential backoff tối đa 600 giây (10 phút)
        3. Nếu AI down quá 10 phút → skip article, KHÔNG raise error
        4. KHÔNG BAO GIỜ stop pipeline vì AI fail
        5. Track AI availability trong Redis
        """
        # AI luôn luôn proceed - không bao giờ block pipeline
        if model is None:
            model = self.route_model(task_type)

        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]

        start_time = time.time()
        max_wait_seconds = 600  # 10 phút

        for attempt in range(10):  # Tăng từ 3 lên 10 attempts
            try:
                # Check if we've waited too long
                elapsed = time.time() - start_time
                if elapsed > max_wait_seconds:
                    logger.error(
                        f"AI call: Waited {elapsed:.0f}s ({attempt} attempts), "
                        f"AI still unavailable. Skipping article to keep pipeline running."
                    )
                    # KHÔNG raise - return empty result để pipeline tiếp tục
                    return {
                        "error": "ai_unavailable",
                        "message": f"AI unavailable for {elapsed:.0f}s, article skipped",
                        "attempts": attempt,
                        "elapsed_seconds": elapsed,
                    }

                logger.info(f"AI call attempt {attempt + 1} with model {model}")

                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format=response_format or {"type": "text"},
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                # Success!
                if attempt > 0:
                    logger.info(f"AI call succeeded after {attempt + 1} attempts")
                circuit_breaker.record_success()

                content = response.choices[0].message.content

                # Log token usage
                if response.usage:
                    self._log_token_usage(response.usage, model, task_type, temperature, max_tokens)

                # Parse JSON if response_format expects it
                if response_format and response_format.get("type") == "json_object":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # Try to extract JSON from the content
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            try:
                                return json.loads(json_match.group(0))
                            except json.JSONDecodeError:
                                # Try fixing common JSON issues
                                fixed_content = json_match.group(0)
                                # Fix single quotes used for keys/values
                                fixed_content = re.sub(r"(?<=[\[{,:])\s*'([^']+)':", r'"\1":', fixed_content)
                                fixed_content = re.sub(r":\s*'([^']*)'(?=[,}\]])", r': "\1"', fixed_content)
                                # Remove trailing commas
                                fixed_content = re.sub(r',([\s}])', r'\1', fixed_content)
                                try:
                                    return json.loads(fixed_content)
                                except json.JSONDecodeError:
                                    pass
                        # If still fails, return as text
                        return {"text": content, "_parse_error": "Invalid JSON"}

                return {"text": content}

            except (RateLimitError, APITimeoutError) as e:
                elapsed = time.time() - start_time
                wait_time = min((2**attempt) * 30, 300)  # Tăng max wait lên 5 phút
                
                logger.warning(
                    f"AI call rate limited/timeout (attempt {attempt + 1}): {e}. "
                    f"Elapsed: {elapsed:.0f}s. Waiting {wait_time}s before retry..."
                )
                
                if elapsed + wait_time > max_wait_seconds:
                    logger.error(
                        f"AI call: Would wait {wait_time}s but would exceed {max_wait_seconds}s limit. "
                        f"Skipping article to keep pipeline running."
                    )
                    return {
                        "error": "ai_unavailable",
                        "message": f"AI unavailable for {elapsed:.0f}s, article skipped",
                        "attempts": attempt + 1,
                        "elapsed_seconds": elapsed,
                    }
                
                await asyncio.sleep(wait_time)
                circuit_breaker.record_failure(str(e))

            except APIError as e:
                elapsed = time.time() - start_time
                wait_time = min((2**attempt) * 20, 180)  # Tăng max wait lên 3 phút
                
                logger.warning(f"AI API error (attempt {attempt + 1}): {e}. Waiting {wait_time}s...")
                circuit_breaker.record_failure(str(e))
                
                if elapsed + wait_time > max_wait_seconds:
                    logger.error(
                        f"AI call: Would wait {wait_time}s but would exceed {max_wait_seconds}s limit. "
                        f"Skipping article to keep pipeline running."
                    )
                    return {
                        "error": "ai_unavailable",
                        "message": f"AI unavailable for {elapsed:.0f}s, article skipped",
                        "attempts": attempt + 1,
                        "elapsed_seconds": elapsed,
                    }
                
                await asyncio.sleep(wait_time)

            except Exception as e:
                circuit_breaker.record_failure(str(e))
                logger.error(f"AI call failed (attempt {attempt + 1}): {e}")
                
                elapsed = time.time() - start_time
                if elapsed > max_wait_seconds:
                    return {
                        "error": "ai_unavailable",
                        "message": f"AI unavailable for {elapsed:.0f}s, article skipped",
                        "attempts": attempt + 1,
                        "elapsed_seconds": elapsed,
                    }
                
                await asyncio.sleep(30)  # Wait 30s before retry

        # Nếu đến đây = fail sau 10 attempts
        # KHÔNG raise - return error result để pipeline tiếp tục
        elapsed = time.time() - start_time
        logger.error(
            f"AI call failed after 10 attempts ({elapsed:.0f}s). "
            f"Returning error result to keep pipeline running."
        )
        return {
            "error": "ai_unavailable",
            "message": f"AI unavailable after {elapsed:.0f}s, article skipped",
            "attempts": 10,
            "elapsed_seconds": elapsed,
        }

    def _log_token_usage(
        self,
        usage,
        model: str,
        task_type: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        """Log token usage to database."""
        try:
            import asyncio
            from app.models.token_usage import TokenUsage
            from app.core.database import get_db_context

            async def save():
                async with get_db_context() as db_session:
                    cost_per_1k = {
                        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
                        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
                        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
                        "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
                        "claude-3-5-sonnet": {"prompt": 0.003, "completion": 0.015},
                        "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
                        "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
                    }

                    model_costs = cost_per_1k.get(model, {"prompt": 0.01, "completion": 0.03})
                    prompt_cost = (usage.prompt_tokens / 1000) * model_costs["prompt"]
                    completion_cost = (usage.completion_tokens / 1000) * model_costs["completion"]
                    total_cost = prompt_cost + completion_cost

                    usage_record = TokenUsage(
                        task_type=task_type,
                        model=model,
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        total_tokens=usage.total_tokens,
                        estimated_cost=total_cost,
                        extra_data={"temperature": temperature, "max_tokens": max_tokens},
                    )
                    db_session.add(usage_record)
                    await db_session.commit()

            asyncio.create_task(save())
        except Exception as e:
            logger.warning(f"Failed to save token usage: {e}")


# Singleton instance
ai_gateway = AIGateway()


async def close_ai_gateway() -> None:
    """Close AI gateway connections."""
    if ai_gateway._client:
        await ai_gateway._client.close()
    logger.info("AI Gateway closed")


async def test_ai_connection(
    gateway_url: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """
    Test AI connection with given settings.
    Returns success status and details.
    """
    import httpx

    try:
        # Ensure URL ends with /v1
        if not gateway_url.endswith("/v1"):
            url = f"{gateway_url.rstrip('/')}/chat/completions"
        else:
            url = f"{gateway_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, respond with 'OK' only."}],
            "max_tokens": 10,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Connection successful with {model}",
                    "status_code": 200,
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Authentication failed - check API key",
                    "status_code": 401,
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": f"Model '{model}' not found",
                    "status_code": 404,
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "message": "Rate limited - try again later",
                    "status_code": 429,
                }
            else:
                return {
                    "success": False,
                    "message": f"Error: {response.status_code}",
                    "status_code": response.status_code,
                }

    except httpx.ConnectError:
        return {
            "success": False,
            "message": "Connection failed - check gateway URL",
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "Connection timeout",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
        }


async def get_embedding(text: str) -> Optional[dict]:
    """
    Get embedding for text using OpenAI embedding API.
    Uses text-embedding-3-small for cost efficiency.

    Returns {"embedding": [...]} on success, None on failure.
    """
    settings = ai_gateway._get_ai_settings()
    gateway_url = settings.get("gateway_url", "https://api.openai.com/v1")
    api_key = settings.get("api_key", "")

    if not api_key:
        logger.warning("No API key configured for embeddings")
        return None

    # Ensure URL is correct for embeddings
    base_url = gateway_url.rstrip("/v1").rstrip("/")
    url = f"{base_url}/embeddings"

    import httpx

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json={
                    "model": "text-embedding-3-small",
                    "input": text[:8000],  # Limit input length
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    return {
                        "embedding": data["data"][0]["embedding"],
                        "model": data.get("model", "text-embedding-3-small"),
                    }
            else:
                logger.warning(f"Embedding API error: {response.status_code} - {response.text[:200]}")

    except Exception as e:
        logger.warning(f"Failed to get embedding: {e}")

    return None


async def get_embeddings_batch(texts: list[str]) -> Optional[dict]:
    """
    Get embeddings for multiple texts in one API call.
    Uses text-embedding-3-small for cost efficiency.

    Returns {"embeddings": [(text, embedding), ...]} on success, None on failure.
    """
    settings = ai_gateway._get_ai_settings()
    gateway_url = settings.get("gateway_url", "https://api.openai.com/v1")
    api_key = settings.get("api_key", "")

    if not api_key:
        logger.warning("No API key configured for embeddings")
        return None

    base_url = gateway_url.rstrip("/v1").rstrip("/")
    url = f"{base_url}/embeddings"

    import httpx

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                json={
                    "model": "text-embedding-3-small",
                    "input": [text[:8000] for text in texts],
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    embeddings = []
                    for item in data["data"]:
                        idx = item["index"]
                        text = texts[idx] if idx < len(texts) else ""
                        embeddings.append((text, item["embedding"]))
                    return {
                        "embeddings": embeddings,
                        "model": data.get("model", "text-embedding-3-small"),
                    }
            else:
                logger.warning(f"Batch embedding API error: {response.status_code} - {response.text[:200]}")

    except Exception as e:
        logger.warning(f"Failed to get batch embeddings: {e}")

    return None
