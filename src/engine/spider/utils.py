import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

import requests

# 常用 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
]


def get_random_user_agent() -> str:
    """返回随机的 User-Agent"""
    return random.choice(USER_AGENTS)


def get_default_headers() -> dict:
    """返回默认的请求头"""
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (requests.RequestException, Exception),
) -> Callable:
    """
    装饰器：在发生异常时进行重试

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 重试延迟的增长因子
        exceptions: 需要重试的异常类型
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:  # 不是最后一次尝试
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                        continue

            # 所有重试都失败后，抛出最后一个异常
            raise last_exception

        return wrapper

    return decorator


def safe_request(
    url: str,
    method: str = "GET",
    **kwargs: Any,
) -> requests.Response:
    """
    发送安全的 HTTP 请求，带有重试机制和随机延迟

    Args:
        url: 请求的URL
        method: 请求方法
        **kwargs: 传递给 requests 的其他参数
    """
    # 添加默认请求头
    headers = kwargs.pop("headers", {})
    default_headers = get_default_headers()
    default_headers.update(headers)

    # 添加随机延迟
    time.sleep(random.uniform(1, 3))

    response = requests.request(method, url, headers=default_headers, **kwargs)
    response.raise_for_status()
    return response
