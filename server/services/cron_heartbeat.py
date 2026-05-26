# services/cron_heartbeat.py
"""
Cloudflare Worker 心跳端点服务
CF Worker 每分钟 ping 此接口，HF 内部检查当前时间是否匹配任何 cron 任务
"""
import datetime
import logging
from db.database import get_db, get_cache_db, get_setting
from core.engine import trigger_background_queue
from core.status import task_runner
from services.source_cache import cache_sources

logger = logging.getLogger("udpxy_radar")


def cron_field_match(pattern: str, value: str) -> bool:
    if pattern == "*":
        return True
    if "/" in pattern:
        base, step = pattern.split("/", 1)
        v = int(value)
        s = int(step)
        if base == "*":
            return v % s == 0
        else:
            return v >= int(base) and (v - int(base)) % s == 0
    if "," in pattern:
        return value in pattern.split(",")
    if "-" in pattern:
        start, end = pattern.split("-", 1)
        return int(start) <= int(value) <= int(end)
    return pattern == value


def cron_match(cron_expr: str, cron_str: str) -> bool:
    if not cron_expr:
        return False
    try:
        c_min, c_hour, c_dom, c_mon, c_dow = cron_expr.strip().split()
        n_min, n_hour, n_dom, n_mon, n_dow = cron_str.strip().split()
        return (
            cron_field_match(c_min, n_min) and
            cron_field_match(c_hour, n_hour) and
            cron_field_match(c_dom, n_dom) and
            cron_field_match(c_mon, n_mon) and
            cron_field_match(c_dow, n_dow)
        )
    except Exception:
        return False


# 执行记录：同一任务在同一分钟内只执行一次
_last_exec_records = {}


def _should_exec(task_key: str, now: datetime.datetime) -> bool:
    exec_key = now.strftime("%Y-%m-%d %H:%M")
    last = _last_exec_records.get(task_key)
    if last == exec_key:
        return False
    _last_exec_records[task_key] = exec_key
    return True


async def handle_heartbeat() -> dict:
    """
    处理 Cloudflare Worker 心跳请求，检查并执行匹配的 cron 任务。
    返回本次执行的任务列表。
    """
    now = datetime.datetime.now()
    cron_now = f"{now.minute} {now.hour} {now.day} {now.month} {now.weekday() + 1}"

    triggered = []

    # 扫描任务触发
    scan_cron = get_setting("scan_cron", "")
    if cron_match(scan_cron, cron_now) and _should_exec("scan", now):
        if task_runner.is_idle():
            logger.info(f"⏰ [心跳触发] 定时扫描 -> cron: {scan_cron}")
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id FROM scan_config WHERE enabled=1"
                ).fetchall()
            if rows:
                ids = [r["id"] for r in rows]
                trigger_background_queue(ids, skip_disabled=True)
                triggered.append({"task": "scan", "config_ids": ids})
            else:
                logger.warning("⚠️ [心跳触发] 无可用激活配置")
        else:
            logger.info("⏰ [心跳触发] 扫描任务忙碌，跳过")

    # 复测任务触发
    janitor_cron = get_setting("janitor_cron", "")
    if cron_match(janitor_cron, cron_now) and _should_exec("janitor", now):
        if task_runner.is_idle():
            logger.info(f"⏰ [心跳触发] 定时复测 -> cron: {janitor_cron}")
            from db.database import get_cache_db
            with get_cache_db() as conn:
                rows = conn.execute(
                    "SELECT id FROM iptv_list"
                ).fetchall()
            if rows:
                ids = [r["id"] for r in rows]
                task_runner.start_rechecking(ids)
                triggered.append({"task": "recheck", "count": len(ids)})

    # 0.zone 定时拉取
    ozone_fetch_cron = get_setting("ozone_fetch_cron", "")
    if cron_match(ozone_fetch_cron, cron_now) and _should_exec("ozone_fetch", now):
        logger.info(f"⏰ [心跳触发] 0.zone 定时拉取 -> cron: {ozone_fetch_cron}")
        from services.ozone import fetch_ozone_sources
        sources = await fetch_ozone_sources(page=1)
        if sources:
            cache_sources("ozone", sources)
        triggered.append({"task": "ozone_fetch"})

    # zoomeye 定时拉取（通过 GitHub Action）
    zoomeye_fetch_cron = get_setting("zoomeye_fetch_cron", "")
    if cron_match(zoomeye_fetch_cron, cron_now) and _should_exec("zoomeye_fetch", now):
        logger.info(f"⏰ [心跳触发] zoomeye 定时拉取 -> cron: {zoomeye_fetch_cron}")
        from services.github_action import trigger_source_fetch
        source_url = get_setting("zoomeye_source_url", "https://www.zoomeye.ai/api/search?q=YXBwPSJ1ZHB4eSBtdWx0aWNhc3QgVURQLXRvLUhUVFAiICYmIGNvdW50cnk9IuS4reWbvSI%3D")
        await trigger_source_fetch(source_url, source_type="zoomeye")
        triggered.append({"task": "zoomeye_fetch"})

    # 0.zone 定时扫描
    ozone_scan_cron = get_setting("ozone_scan_cron", "")
    if cron_match(ozone_scan_cron, cron_now) and _should_exec("ozone_scan", now):
        if task_runner.is_idle():
            logger.info(f"⏰ [心跳触发] 0.zone 定时扫描 -> cron: {ozone_scan_cron}")
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id FROM scan_config WHERE dataSource LIKE '%ozone%' AND enabled=1"
                ).fetchall()
            if rows:
                trigger_background_queue([r["id"] for r in rows])
                triggered.append({"task": "ozone_scan", "config_ids": [r["id"] for r in rows]})

    # ZoomEye 定时扫描
    zoomeye_scan_cron = get_setting("zoomeye_scan_cron", "")
    if cron_match(zoomeye_scan_cron, cron_now) and _should_exec("zoomeye_scan", now):
        if task_runner.is_idle():
            logger.info(f"⏰ [心跳触发] ZoomEye 定时扫描 -> cron: {zoomeye_scan_cron}")
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id FROM scan_config WHERE dataSource LIKE '%zoomeye%' AND enabled=1"
                ).fetchall()
            if rows:
                trigger_background_queue([r["id"] for r in rows])
                triggered.append({"task": "zoomeye_scan", "config_ids": [r["id"] for r in rows]})

    # DayDayMap 定时拉取
    daydaymap_fetch_cron = get_setting("daydaymap_fetch_cron", "")
    if cron_match(daydaymap_fetch_cron, cron_now) and _should_exec("daydaymap_fetch", now):
        logger.info(f"⏰ [心跳触发] DayDayMap 定时拉取 -> cron: {daydaymap_fetch_cron}")
        from services.daydaymap import fetch_daydaymap_sources
        sources = await fetch_daydaymap_sources()
        if sources:
            cache_sources("daydaymap", sources)
        triggered.append({"task": "daydaymap_fetch"})

    # DayDayMap 定时扫描
    daydaymap_scan_cron = get_setting("daydaymap_scan_cron", "")
    if cron_match(daydaymap_scan_cron, cron_now) and _should_exec("daydaymap_scan", now):
        if task_runner.is_idle():
            logger.info(f"⏰ [心跳触发] DayDayMap 定时扫描 -> cron: {daydaymap_scan_cron}")
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id FROM scan_config WHERE dataSource LIKE '%daydaymap%' AND enabled=1"
                ).fetchall()
            if rows:
                trigger_background_queue([r["id"] for r in rows])
                triggered.append({"task": "daydaymap_scan", "config_ids": [r["id"] for r in rows]})

    # Hunter 定时拉取
    hunter_fetch_cron = get_setting("hunter_fetch_cron", "")
    if cron_match(hunter_fetch_cron, cron_now) and _should_exec("hunter_fetch", now):
        logger.info(f"⏰ [心跳触发] Hunter 定时拉取 -> cron: {hunter_fetch_cron}")
        from services.hunter import fetch_hunter_sources
        sources = await fetch_hunter_sources()
        if sources:
            cache_sources("hunter", sources)
        triggered.append({"task": "hunter_fetch"})

    # Hunter 定时扫描
    hunter_scan_cron = get_setting("hunter_scan_cron", "")
    if cron_match(hunter_scan_cron, cron_now) and _should_exec("hunter_scan", now):
        if task_runner.is_idle():
            logger.info(f"⏰ [心跳触发] Hunter 定时扫描 -> cron: {hunter_scan_cron}")
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id FROM scan_config WHERE dataSource LIKE '%hunter%' AND enabled=1"
                ).fetchall()
            if rows:
                trigger_background_queue([r["id"] for r in rows])
                triggered.append({"task": "hunter_scan", "config_ids": [r["id"] for r in rows]})

    return triggered
