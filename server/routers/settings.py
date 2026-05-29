from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from db.database import get_db, get_cache_db, get_iptv_db, get_setting
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
            "janitorCron": get_setting("janitor_cron", ""),
            "hfSyncCron": get_setting("hf_sync_cron", "")
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
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('hf_sync_cron', ?)", (data.hfSyncCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('scan_cron', ?)", (data.scanCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('callback_token', ?)", (data.callbackToken,))
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
        cache_sources("github", sources)

    return {
        "ok": True,
        "fetched": len(sources),
        "hosts": [s["host"] for s in sources]
    }


@router.get("/cache/stats")
def api_source_cache_stats():
    """
    查看 source_cache 各数据源统计信息。
    """
    with get_cache_db() as conn:
        rows = conn.execute(
            "SELECT sourceType, COUNT(*) as count FROM source_cache GROUP BY sourceType"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM source_cache").fetchone()[0]
    return {
        "total": total,
        "bySource": [dict(r) for r in rows]
    }


@router.post("/cache/clear")
def api_clear_source_cache(
    sourceType: str = Query(None, alias="sourceType", description="指定数据源类型，不传则清空所有")
):
    """
    清理 source_cache 表中的缓存数据。
    传入 sourceType 只清指定源，不传则清空整表。
    """
    with get_cache_db() as conn:
        if sourceType:
            count = conn.execute("SELECT COUNT(*) FROM source_cache WHERE sourceType=?", (sourceType,)).fetchone()[0]
            conn.execute("DELETE FROM source_cache WHERE sourceType=?", (sourceType,))
        else:
            count = conn.execute("SELECT COUNT(*) FROM source_cache").fetchone()[0]
            conn.execute("DELETE FROM source_cache")
    return {"ok": True, "deleted": count}


class IptvImportItem(BaseModel):
    id: int = None
    host: str
    ip: str
    port: int
    sourceType: str = ""
    sourceName: str = ""
    region: str = ""
    operator: str = ""
    geoRegion: str = ""
    geoOperator: str = ""
    delay: int = 0
    protocol: str = ""
    target: str = ""
    channelName: str = ""
    createTime: int = 0
    updateTime: int = 0


@router.get("/iptv-db/list")
def api_iptv_db_list():
    """
    查询 iptv_list.db 中的活源数据。
    """
    with get_iptv_db() as conn:
        rows = conn.execute("SELECT * FROM iptv_list ORDER BY id").fetchall()
    return {"total": len(rows), "data": [dict(r) for r in rows]}


@router.post("/iptv-db/import")
def api_iptv_db_import(items: list[IptvImportItem]):
    """
    批量导入活源数据到 iptv_list.db。
    支持 ON CONFLICT 覆盖更新。
    """
    now = int(__import__("time").time() * 1000)
    with get_iptv_db() as conn:
        imported = 0
        for item in items:
            conn.execute("""
                INSERT OR REPLACE INTO iptv_list (
                    id, host, ip, port, sourceType, sourceName,
                    region, operator, geoRegion, geoOperator,
                    delay, protocol, target, channelName,
                    createTime, updateTime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, item.host, item.ip, item.port,
                item.sourceType, item.sourceName,
                item.region, item.operator,
                item.geoRegion, item.geoOperator,
                item.delay, item.protocol, item.target, item.channelName,
                item.createTime or now, item.updateTime or now
            ))
            imported += 1
    return {"ok": True, "imported": imported}
