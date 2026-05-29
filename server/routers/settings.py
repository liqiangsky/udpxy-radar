from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from db.database import get_db, get_setting
from db.models import GlobalSettingsUpdate
from services.log_buffer import get_recent_logs
import hashlib

router = APIRouter()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@router.get("/settings")
def api_get_settings():
    return {
        "github": {
            "enabled": get_setting("github_enabled", "1") == "1",
            "token": get_setting("github_token", ""),
            "userResultQuery": get_setting("github_user_result_query", "filename:result.txt path:output/ipv4"),
            "userResultFetchCron": get_setting("github_user_result_fetch_cron", ""),
            "userResultUrls": get_setting("github_user_result_urls", "")
        },
        "ozone": {
            "enabled": get_setting("ozone_enabled", "0") == "1",
            "fetchCron": get_setting("ozone_fetch_cron", "")
        },
        "zoomeye": {
            "enabled": get_setting("zoomeye_enabled", "0") == "1",
            "fetchCron": get_setting("zoomeye_fetch_cron", "")
        },
        "daydaymap": {
            "enabled": get_setting("daydaymap_enabled", "0") == "1",
            "fetchCron": get_setting("daydaymap_fetch_cron", "")
        },
        "hunter": {
            "enabled": get_setting("hunter_enabled", "0") == "1",
            "apiKey": get_setting("hunter_api_key", ""),
            "fetchCron": get_setting("hunter_fetch_cron", "")
        },
        "engine": {
            "concurrency": int(get_setting("concurrency", "64")),
            "timeout": int(get_setting("timeout", "2000")),
            "configDelay": int(get_setting("config_delay", "3"))
        },
        "scheduling": {
            "scanCron": get_setting("scan_cron", ""),
            "janitorCron": get_setting("janitor_cron", "")
        },
        "security": {
            "callbackToken": get_setting("callback_token", "")
        }
    }


@router.put("/settings")
def api_update_settings(data: GlobalSettingsUpdate):
    with get_db() as conn:
        # github
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_enabled', ?)", ("1" if data.githubEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_token', ?)", (data.githubToken,))
        # github user result
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_user_result_fetch_cron', ?)", (data.githubUserResultFetchCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_user_result_query', ?)", (data.githubUserResultQuery,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_user_result_urls', ?)", (data.githubUserResultUrls or "",))
        # 0zone
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ozone_enabled', ?)", ("1" if data.ozoneEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ozone_fetch_cron', ?)", (data.ozoneFetchCron,))
        # zoomeye
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('zoomeye_enabled', ?)", ("1" if data.zoomeyeEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('zoomeye_fetch_cron', ?)", (data.zoomeyeFetchCron,))
        # daydaymap
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('daydaymap_enabled', ?)", ("1" if data.daydaymapEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('daydaymap_fetch_cron', ?)", (data.daydaymapFetchCron,))
        # hunter
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('hunter_enabled', ?)", ("1" if data.hunterEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('hunter_api_key', ?)", (data.hunterApiKey,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('hunter_fetch_cron', ?)", (data.hunterFetchCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('concurrency', ?)", (str(data.concurrency),))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('timeout', ?)", (str(data.timeout),))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('config_delay', ?)", (str(data.configDelay),))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('janitor_cron', ?)", (data.janitorCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('scan_cron', ?)", (data.scanCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('callback_token', ?)", (data.callbackToken,))
    from core.engine import janitor
    janitor.stop()
    janitor.start()
    return {"ok": True}


@router.get("/logs")
def api_get_logs(
    lines: int = Query(100, ge=10, le=500),
    level: str = Query(None)
):
    """获取最近日志，可选按级别过滤 (INFO/WARNING/ERROR)"""
    logs = get_recent_logs(lines=lines, level=level)
    return {"logs": logs, "total": len(logs)}


class GitHubUserResultFetchRequest(BaseModel):
    query: str = ""
    urls: list[str] = []


@router.post("/github-user-result/fetch")
async def api_manual_github_user_result_fetch(req: GitHubUserResultFetchRequest):
    """
    手动触发 GitHub UserResult 数据拉取。
    支持自定义搜索关键词和多个 raw URL 列表。
    """
    if get_setting("github_enabled", "1") != "1":
        raise HTTPException(400, "GitHub 数据源未启用")

    from services.github import fetch_github_user_result_sources
    from services.source_cache import cache_sources
    import aiohttp

    # 如果有自定义 URL 列表，覆盖设置中的 query
    if req.urls:
        urls_text = "\n".join(req.urls)
        # 临时覆盖：将 URL 列表写入设置，让 fetch 函数使用
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_user_result_urls', ?)", (urls_text,))

    # 如果有自定义搜索关键词
    if req.query:
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_user_result_query', ?)", (req.query,))

    timeout = int(get_setting("timeout", "2000")) / 1000.0
    connector = aiohttp.TCPConnector(limit=128, ssl=False)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout * 2), connector=connector) as session:
        sources = await fetch_github_user_result_sources(session=session)

    if sources:
        cache_sources("github_user_result", sources)

    return {
        "ok": True,
        "fetched": len(sources),
        "hosts": [s["host"] for s in sources]
    }
