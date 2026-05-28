# main.py
import os
import time
os.environ["TZ"] = "Asia/Shanghai"
if hasattr(time, "tzset"):
    time.tzset()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from db.database import init_db, init_cache_db, get_setting
from services.hf_sync import pull_from_hf, push_to_hf
from services.log_buffer import setup_log_buffer
from core.engine import janitor
from routers import settings, configs, iptv, templates, cron, auth  # 导入拆分出去的路由模块

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

@asynccontextmanager
async def system_lifespan(app: FastAPI):
    # 启动：先同步云端，再初始化本地，最后唤醒守卫
    setup_log_buffer()
    pull_from_hf()
    init_db()
    init_cache_db()
    janitor.start()
    yield
    # 关闭：安全退出，同步备份
    janitor.stop()
    push_to_hf()

app = FastAPI(title="udpxy-radar", lifespan=system_lifespan)

# 跨域设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 内存 session 存储（由 auth 模块导入）
from routers.auth import _sessions as auth_sessions


@app.middleware("http")
async def check_auth(request, call_next):
    """所有接口都需要认证：X-Auth-Token（登录 session）或 X-Callback-Token（外部服务）"""
    # 豁免路径：登录、登出、iptv-pool
    if request.url.path in ("/api/login", "/api/logout", "/api/iptv-pool"):
        return await call_next(request)

    # 方式 1：用户登录 session 认证
    auth_token = request.headers.get("X-Auth-Token", "")
    if auth_token and auth_token in auth_sessions:
        return await call_next(request)

    # 方式 2：外部服务 callback_token 认证（CF Worker / GitHub Action）
    callback_token = get_setting("callback_token", "")
    if callback_token:
        cb_header = request.headers.get("X-Callback-Token", "")
        if cb_header == callback_token:
            return await call_next(request)

    # 两种认证都不通过
    return JSONResponse(status_code=401, content={"detail": "未认证"})


# 🔌 像插排一样，把各个子路由插进来
app.include_router(auth.router, prefix="/api", tags=["认证"])
app.include_router(settings.router, prefix="/api", tags=["全局设置"])
app.include_router(templates.router, prefix="/api", tags=["配置模板"])
app.include_router(configs.router, prefix="/api", tags=["扫描配置"])
app.include_router(iptv.router, prefix="/api", tags=["纯净活源池"])
app.include_router(cron.router, prefix="/api", tags=["定时心跳"])
