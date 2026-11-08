"""登录失败限流（进程内实现）。

局限：状态只存在于当前进程；多 worker / 多实例部署时各自计数，
重启后清零。生产若需要全局一致，应替换为 Redis 等共享存储。
"""

import threading
import time
from collections import defaultdict, deque

MAX_FAILURES = 5
WINDOW_SECONDS = 300

_lock = threading.Lock()
_failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def _key(client_ip: str | None, email: str) -> tuple[str, str]:
    return (client_ip or "unknown", email.strip().lower())


def retry_after(client_ip: str | None, email: str) -> int | None:
    """达到上限时返回建议等待秒数，否则返回 None。"""
    now = time.monotonic()
    key = _key(client_ip, email)
    with _lock:
        queue = _failures.get(key)
        if not queue:
            return None
        while queue and now - queue[0] > WINDOW_SECONDS:
            queue.popleft()
        if not queue:
            _failures.pop(key, None)
            return None
        if len(queue) < MAX_FAILURES:
            return None
        return max(1, int(WINDOW_SECONDS - (now - queue[0])) + 1)


def record_failure(client_ip: str | None, email: str) -> None:
    now = time.monotonic()
    key = _key(client_ip, email)
    with _lock:
        queue = _failures[key]
        while queue and now - queue[0] > WINDOW_SECONDS:
            queue.popleft()
        queue.append(now)


def clear(client_ip: str | None, email: str) -> None:
    with _lock:
        _failures.pop(_key(client_ip, email), None)


def reset_all() -> None:
    """仅供测试使用。"""
    with _lock:
        _failures.clear()
