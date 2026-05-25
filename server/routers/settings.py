from fastapi import APIRouter
from db.database import get_db, get_setting
from db.models import GlobalSettingsUpdate

router = APIRouter()

@router.get("/settings")
def api_get_settings():
    return {
        "github": {
            "enabled": get_setting("github_enabled", "1") == "1",
            "token": get_setting("github_token", ""),
            "searchDepth": int(get_setting("github_search_depth", "5")),
            "scanCron": get_setting("github_scan_cron", "")
        },
        "ozone": {
            "enabled": get_setting("ozone_enabled", "0") == "1",
            "fetchCron": get_setting("ozone_fetch_cron", ""),
            "scanCron": get_setting("ozone_scan_cron", "")
        },
        "zoomeye": {
            "enabled": get_setting("zoomeye_enabled", "0") == "1",
            "fetchCron": get_setting("zoomeye_fetch_cron", "")
        },
        "engine": {
            "concurrency": int(get_setting("concurrency", "64")),
            "timeout": int(get_setting("timeout", "2000")),
            "configDelay": int(get_setting("config_delay", "3"))
        },
        "scheduling": {
            "janitorCron": get_setting("janitor_cron", "")
        }
    }

@router.put("/settings")
def api_update_settings(data: GlobalSettingsUpdate):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_enabled', ?)", ("1" if data.githubEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_token', ?)", (data.githubToken,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_search_depth', ?)", (str(data.githubSearchDepth),))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_scan_cron', ?)", (data.githubScanCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ozone_enabled', ?)", ("1" if data.ozoneEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ozone_fetch_cron', ?)", (data.ozoneFetchCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ozone_scan_cron', ?)", (data.ozoneScanCron,))
        # zoomeye
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('zoomeye_enabled', ?)", ("1" if data.zoomeyeEnabled else "0",))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('zoomeye_fetch_cron', ?)", (data.zoomeyeFetchCron,))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('concurrency', ?)", (str(data.concurrency),))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('timeout', ?)", (str(data.timeout),))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('config_delay', ?)", (str(data.configDelay),))
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('janitor_cron', ?)", (data.janitorCron,))
    from core.engine import janitor
    janitor.stop()
    janitor.start()
    return {"ok": True}
