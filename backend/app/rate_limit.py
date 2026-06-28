"""内存限流工具 — FastAPI 可用的 Depends 工厂。

注意：基于进程内存，多进程部署（如 gunicorn -w 4）下每进程独立计数，
实际限流上限会乘以进程数。生产强限流场景建议改用 Redis 后端。
"""
import time
from collections import defaultdict

from fastapi import HTTPException, Request

_store: dict[str, list[float]] = defaultdict(list)


def make_rate_limiter(max_requests: int = 5, window_seconds: int = 60):
    """返回一个可用作 FastAPI Depends 的限流依赖函数。"""

    async def limiter(request: Request):
        now_ts = time.time()
        ip = request.client.host if request.client else "unknown"
        cutoff = now_ts - window_seconds
        _store[ip] = [t for t in _store[ip] if t > cutoff]
        if len(_store[ip]) >= max_requests:
            raise HTTPException(429, "请求过于频繁，请稍后再试")
        _store[ip].append(now_ts)

    return limiter


# 预设限流器：登录防爆破
login_limiter = make_rate_limiter(max_requests=5, window_seconds=60)
# AI 分析：单 IP 每分钟 3 次（调用外部 API，成本高）
ai_limiter = make_rate_limiter(max_requests=3, window_seconds=60)
# 文件上传：单 IP 每分钟 20 次
upload_limiter = make_rate_limiter(max_requests=20, window_seconds=60)
# 集成同步：单 IP 每分钟 5 次（可能触发外部 HTTP 拉取）
sync_limiter = make_rate_limiter(max_requests=5, window_seconds=60)


def reset_store():
    """测试专用：清空限流计数，避免用例间相互影响。"""
    _store.clear()
