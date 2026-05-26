# main.py
import os
import time
os.environ["TZ"] = "Asia/Shanghai"
if hasattr(time, "tzset"):
    time.tzset()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from db.database import init_db, init_cache_db
from services.hf_sync import pull_from_hf, push_to_hf
from core.engine import janitor
from routers import settings, configs, iptv, templates  # 导入拆分出去的路由模块

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

@asynccontextmanager
async def system_lifespan(app: FastAPI):
    # 启动：先同步云端，再初始化本地，最后唤醒守卫
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

# 🔌 像插排一样，把各个子路由插进来
app.include_router(settings.router, prefix="/api", tags=["全局设置"])
app.include_router(templates.router, prefix="/api", tags=["配置模板"])
app.include_router(configs.router, prefix="/api", tags=["扫描配置"])
app.include_router(iptv.router, prefix="/api", tags=["纯净活源池"])
