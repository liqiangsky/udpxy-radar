import hashlib
import os
import uuid
import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from db.database import get_db, get_setting

router = APIRouter()

# 简单内存存储 session
_sessions: dict[str, dict] = {}

# 登录失败限制：key=IP, value={count, locked_until}
_login_attempts: dict[str, dict] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 分钟


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_admin_password_hash() -> str:
    """从环境变量 PASSWORD 获取密码，默认 admin123"""
    env_pass = os.environ.get("PASSWORD", "")
    if env_pass:
        return hash_password(env_pass)
    return hash_password("admin123")


def check_rate_limit(client_ip: str):
    """检查是否被锁定"""
    if client_ip not in _login_attempts:
        return
    record = _login_attempts[client_ip]
    if time.time() < record.get("locked_until", 0):
        remaining = int(record["locked_until"] - time.time())
        raise HTTPException(429, f"登录被锁定，请 {remaining} 秒后重试")


def record_failure(client_ip: str):
    """记录登录失败"""
    if client_ip not in _login_attempts:
        _login_attempts[client_ip] = {"count": 0, "locked_until": 0}
    _login_attempts[client_ip]["count"] += 1
    if _login_attempts[client_ip]["count"] >= MAX_FAILED_ATTEMPTS:
        _login_attempts[client_ip]["locked_until"] = time.time() + LOCKOUT_SECONDS


def reset_attempts(client_ip: str):
    """登录成功后重置计数"""
    if client_ip in _login_attempts:
        del _login_attempts[client_ip]


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def api_login(request: Request, req: LoginRequest):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)
    expected_hash = get_admin_password_hash()

    if hash_password(req.password) != expected_hash:
        record_failure(client_ip)
        raise HTTPException(401, "密码错误")

    reset_attempts(client_ip)
    token = uuid.uuid4().hex
    _sessions[token] = {
        "username": "admin",
        "created_at": int(time.time()),
    }
    return {"ok": True, "token": token, "username": "admin"}


@router.post("/logout")
def api_logout(token: str = ""):
    if token in _sessions:
        del _sessions[token]
    return {"ok": True}


@router.get("/auth")
def api_check_auth(token: str = ""):
    if not token or token not in _sessions:
        return {"ok": False}
    return {"ok": True, "username": _sessions[token]["username"]}
