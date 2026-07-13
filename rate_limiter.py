import time
from collections import defaultdict
from fastapi import HTTPException, status, Request


_login_attempts: dict[str, list[float]] = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 900


def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < WINDOW_SECONDS]
    if len(_login_attempts[ip]) >= MAX_ATTEMPTS:
        remaining = int(WINDOW_SECONDS - (now - _login_attempts[ip][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Intentá de nuevo en {remaining // 60} minutos",
        )


def record_failed_attempt(request: Request):
    ip = request.client.host if request.client else "unknown"
    _login_attempts[ip].append(time.time())


def clear_attempts(request: Request):
    ip = request.client.host if request.client else "unknown"
    _login_attempts[ip] = []
