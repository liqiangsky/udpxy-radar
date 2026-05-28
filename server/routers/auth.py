import hashlib
import uuid
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.database import get_db, get_setting

router = APIRouter()

# 简单内存存储 session
_sessions: dict[str, dict] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_admin_username() -> str:
    return get_setting("admin_username", "admin")


def get_admin_password_hash() -> str:
    """获取管理员密码哈希，默认密码为 admin123"""
    raw = get_setting("admin_password_hash", "")
    if raw:
        return raw
    return hash_password("admin123")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def api_login(req: LoginRequest):
    expected_user = get_admin_username()
    expected_hash = get_admin_password_hash()

    if req.username != expected_user or hash_password(req.password) != expected_hash:
        raise HTTPException(401, "用户名或密码错误")

    token = uuid.uuid4().hex
    _sessions[token] = {
        "username": req.username,
        "created_at": int(time.time()),
    }
    return {"ok": True, "token": token, "username": req.username}


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
