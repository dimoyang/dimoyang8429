"""进程内限流：登录失败、注册、找回密码邮件与验证邮件重发。

局限：状态只存在于当前进程；多 worker / 多实例部署时各自计数，
重启后清零。生产若需要全局一致，应替换为 Redis 等共享存储。
内存占用随“不同的限流键”增长；键数量超过阈值时清理空队列与过期冷却记录。
"""

import threading
import time
from collections import defaultdict, deque

MAX_FAILURES = 5
WINDOW_SECONDS = 300

_lock = threading.Lock()
_failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_windows: dict[str, deque[float]] = defaultdict(deque)
_cooldowns: dict[str, float] = {}

# 超过这个键数量时顺带清理过期窗口；正常业务量远低于该值。
_PRUNE_THRESHOLD = 4096


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


def begin_attempt(client_ip: str | None, email: str) -> int | None:
    """原子地「检查阈值 + 预占一次失败名额」。

    返回 None 表示允许继续校验密码；返回秒数表示已达到上限，应直接 429。
    预占的名额在登录成功后由 `clear` 释放，因此并发请求不会同时穿过阈值检查。
    同一个 IP + 邮箱的并发登录尝试中，最多只有 `MAX_FAILURES` 个能进入密码校验。
    """
    now = time.monotonic()
    key = _key(client_ip, email)
    with _lock:
        queue = _failures.get(key)
        if queue is None:
            queue = deque()
            _failures[key] = queue
        while queue and now - queue[0] > WINDOW_SECONDS:
            queue.popleft()
        if len(queue) >= MAX_FAILURES:
            return max(1, int(WINDOW_SECONDS - (now - queue[0])) + 1)
        queue.append(now)
        return None


def clear(client_ip: str | None, email: str) -> None:
    with _lock:
        _failures.pop(_key(client_ip, email), None)


def hit(key: str, limit: int, window_seconds: int) -> int | None:
    """原子地「检查窗口 + 记录一次命中」。

    返回 None 表示本次允许；返回秒数表示已达上限，调用方应返回 429。
    计数不区分成功失败——注册、发信这类动作本身就是被保护的资源。
    """
    now = time.monotonic()
    with _lock:
        _prune_if_needed(now)
        queue = _windows.get(key)
        if queue is None:
            queue = deque()
            _windows[key] = queue
        while queue and now - queue[0] > window_seconds:
            queue.popleft()
        if len(queue) >= limit:
            return max(1, int(window_seconds - (now - queue[0])) + 1)
        queue.append(now)
        return None


def begin_cooldown(key: str, seconds: int) -> int | None:
    """按 key 做冷却：冷却内返回剩余秒数且不更新计时，冷却外记录本次时间。"""
    if seconds <= 0:
        return None
    now = time.monotonic()
    with _lock:
        last = _cooldowns.get(key)
        if last is not None and now - last < seconds:
            return max(1, int(seconds - (now - last)) + 1)
        _cooldowns[key] = now
        return None


def _prune_if_needed(now: float) -> None:
    """调用方已持有 `_lock`。只清理空队列，避免常规请求承担全量扫描成本。"""
    if len(_windows) < _PRUNE_THRESHOLD:
        return
    for key in [key for key, queue in _windows.items() if not queue]:
        _windows.pop(key, None)
    for key, last in list(_cooldowns.items()):
        if now - last > 86400:
            _cooldowns.pop(key, None)


def reset_all() -> None:
    """仅供测试使用。"""
    with _lock:
        _failures.clear()
        _windows.clear()
        _cooldowns.clear()
