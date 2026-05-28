# services/cron_heartbeat.py
"""
Cloudflare Worker 心跳端点服务
CF Worker 每分钟 ping 此接口，HF 内部检查当前时间是否匹配任何 cron 任务
"""
import datetime
import asyncio
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
            # */n 表示从 0 开始每 n 步（0/n, n, 2n, 3n...）
            # 但 day-of-month 从 1 开始，需要特殊处理
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

    # 通用扫描 cron（所有数据源统一走这一个入口）
    scan_cron = get_setting("scan_cron", "")
    if cron_match(scan_cron, cron_now) and _should_exec("scan", now):
        with get_db() as conn:
            rows = conn.execute("SELECT id FROM scan_config WHERE enabled=1").fetchall()
        if rows:
            ids = [r["id"] for r in rows]
            trigger_background_queue(ids, skip_disabled=True)
            triggered.append({"task": "scan", "config_ids": ids})

    # 复测任务触发
    janitor_cron = get_setting("janitor_cron", "")
    if cron_match(janitor_cron, cron_now) and _should_exec("janitor", now):
        if task_runner.is_idle():
            logger.info(f"⏰ [心跳触发] 定时复测 -> cron: {janitor_cron}")
            from db.database import get_cache_db
            import aiohttp
            timeout_sec = int(get_setting("timeout", "2000")) / 1000.0
            concurrency = int(get_setting("concurrency", "64"))
            sem = asyncio.Semaphore(concurrency)

            task_runner.set_rechecking()
            try:
                with get_cache_db() as conn:
                    active_sources = conn.execute("SELECT * FROM iptv_list").fetchall()

                logger.info(f"🧹 [心跳复测] 开始复测 {len(active_sources)} 个活源")

                if active_sources:
                    async def recheck_all():
                        timeout = aiohttp.ClientTimeout(total=timeout_sec)
                        connector = aiohttp.TCPConnector(limit=256, ssl=False)

                        async with aiohttp.ClientSession(
                            timeout=timeout,
                            connector=connector
                        ) as session:

                            async def recheck_worker(source):
                                async with sem:
                                    if task_runner.should_pause_recheck():
                                        while task_runner.should_pause_recheck():
                                            await asyncio.sleep(2)

                                    host_val = source["host"]
                                    target_val = source["target"]
                                    proto = (source["protocol"] or "rtp").lower().strip()

                                    if not host_val.startswith("http"):
                                        host_val = f"http://{host_val}"
                                    host_val = host_val.rstrip("/")

                                    try:
                                        start_t = __import__("time").time()
                                        test_url = f"{host_val}/{proto}/{target_val}"
                                        async with session.get(
                                            test_url,
                                            timeout=aiohttp.ClientTimeout(total=timeout_sec),
                                            headers={"User-Agent": "Mozilla/5.0"}
                                        ) as r:
                                            if r.status in [200, 206] and await r.content.read(512):
                                                delay = int((__import__("time").time() - start_t) * 1000)
                                                with get_cache_db() as conn:
                                                    conn.execute(
                                                        "UPDATE iptv_list SET delay=?, updateTime=?, protocol=? WHERE id=?",
                                                        (delay, int(__import__("time").time() * 1000), proto, source["id"])
                                                    )
                                                return
                                    except Exception:
                                        pass

                                    logger.warning(f"🗑️ [老化淘汰] {source['host']}")
                                    with get_cache_db() as conn:
                                        conn.execute("DELETE FROM iptv_list WHERE id=?", (source["id"],))
                                        conn.execute("DELETE FROM source_cache WHERE host=?", (source["host"],))

                            await asyncio.gather(
                                *(recheck_worker(s) for s in active_sources)
                            )
                            logger.info(f"🧹 [心跳复测完成] {len(active_sources)} 个活源复测完毕")

                await recheck_all()
                triggered.append({"task": "recheck", "count": len(active_sources)})
            finally:
                task_runner.clear_rechecking()

    # 0.zone 定时拉取
    ozone_fetch_cron = get_setting("ozone_fetch_cron", "")
    if cron_match(ozone_fetch_cron, cron_now) and _should_exec("ozone_fetch", now) and get_setting("ozone_enabled", "0") == "1":
        logger.info(f"⏰ [心跳触发] 0.zone 定时拉取 -> cron: {ozone_fetch_cron}")
        from services.ozone import fetch_ozone_sources
        sources = await fetch_ozone_sources(page=1)
        if sources:
            cache_sources("ozone", sources)
        triggered.append({"task": "ozone_fetch"})

    # zoomeye 定时拉取（通过 GitHub Action）
    zoomeye_fetch_cron = get_setting("zoomeye_fetch_cron", "")
    if cron_match(zoomeye_fetch_cron, cron_now) and _should_exec("zoomeye_fetch", now) and get_setting("zoomeye_enabled", "0") == "1":
        logger.info(f"⏰ [心跳触发] zoomeye 定时拉取 -> cron: {zoomeye_fetch_cron}")
        from services.github_action import trigger_source_fetch
        source_url = get_setting("zoomeye_source_url", "https://www.zoomeye.ai/api/search?q=YXBwPSJ1ZHB4eSBtdWx0aWNhc3QgVURQLXRvLUhUVFAiICYmIGNvdW50cnk9IuS4reWbvSI%3D")
        await trigger_source_fetch(source_url, source_type="zoomeye")
        triggered.append({"task": "zoomeye_fetch"})

    # 0.zone 定时拉取
    daydaymap_fetch_cron = get_setting("daydaymap_fetch_cron", "")
    if cron_match(daydaymap_fetch_cron, cron_now) and _should_exec("daydaymap_fetch", now) and get_setting("daydaymap_enabled", "0") == "1":
        logger.info(f"⏰ [心跳触发] DayDayMap 定时拉取 -> cron: {daydaymap_fetch_cron}")
        from services.daydaymap import fetch_daydaymap_sources
        sources = await fetch_daydaymap_sources()
        if sources:
            cache_sources("daydaymap", sources)
        triggered.append({"task": "daydaymap_fetch"})

    # Hunter 定时拉取
    hunter_fetch_cron = get_setting("hunter_fetch_cron", "")
    if cron_match(hunter_fetch_cron, cron_now) and _should_exec("hunter_fetch", now) and get_setting("hunter_enabled", "0") == "1":
        logger.info(f"⏰ [心跳触发] Hunter 定时拉取 -> cron: {hunter_fetch_cron}")
        from services.hunter import fetch_hunter_sources
        sources = await fetch_hunter_sources()
        if sources:
            cache_sources("hunter", sources)
        triggered.append({"task": "hunter_fetch"})

    return triggered
