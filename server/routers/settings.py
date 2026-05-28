from fastapi import APIRouter, Query
from db.database import get_db, get_setting
from db.models import GlobalSettingsUpdate
from services.log_buffer import get_recent_logs

router = APIRouter()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@router.get("/settings")
def api_get_settings():
    return {
        "github": {
            "enabled": get_setting("github_enabled", "1") == "1",
            "token": get_setting("github_token", "")
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
