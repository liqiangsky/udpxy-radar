import asyncio
import aiohttp
import threading
import time
import logging

from typing import List

from db.database import get_db, get_setting
from core.status import task_runner
from services.github import search_github_sources
from services.ozone import fetch_ozone_sources
from services.source_cache import get_cached_hosts, cache_sources
from services.validator import verify_single_host
from services.geoip import enrich_geo_batch
from services.hf_sync import push_to_hf

logger = logging.getLogger("udpxy_radar")

# SQLite 写锁：序列化所有并发写入，防止 database is locked
_db_write_lock = threading.Lock()


async def execute_scan_queue(config_ids: List[int], skip_disabled: bool = False):

    logger.info(f"🚀 [扫描开始] 配置队列: {config_ids}")

    global_config_delay = int(get_setting("config_delay", "3"))
    global_concurrency = int(get_setting("concurrency", "64"))
    global_timeout_ms = int(get_setting("timeout", "2000"))

    timeout = aiohttp.ClientTimeout(total=global_timeout_ms / 1000.0 * 2)

    connector = aiohttp.TCPConnector(
        limit=512,
        ssl=False,
        ttl_dns_cache=300
    )

    total_valid = 0

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector
    ) as session:

        for index, cfg_id in enumerate(config_ids):

            # 全局停止信号
            if task_runner.should_stop():
                logger.info(f"⛔ [停止扫描] 配置 {config['name']} 被用户停止")
                break

            with get_db() as conn:
                row_data = conn.execute(
                    "SELECT * FROM scan_config WHERE id=?",
                    (cfg_id,)
                ).fetchone()

            if not row_data:
                logger.warning(f"⚠️ [配置不存在] id={cfg_id}，跳过")
                continue

            config = dict(row_data)

            if skip_disabled and not config["enabled"]:
                logger.warning(f"⚠️ [配置已停用] {config['name']}，跳过")
                continue

            task_runner.update_progress(
                index,
                config["name"]
            )

            with get_db() as conn:
                conn.execute(
                    "UPDATE scan_config SET updatedAt=datetime('now') WHERE id=?",
                    (cfg_id,)
                )

            logger.info(f"🚀 [开始扫描] {config['name']}")

            try:
                # 根据 dataSource 路由
                data_source = config.get("dataSource", "github")
                source_type = data_source
                source_name_map = {"github": "GitHub", "ozone": "零零信安", "zoomeye": "ZoomEye"}
                source_name = source_name_map.get(data_source, data_source)

                if data_source == "ozone":
                    region = config.get("templateRegion", "")
                    candidate_hosts = get_cached_hosts("ozone", region)
                    logger.info(f"📡 [ozone] 从 source_cache 读取, region='{region}', 匹配到 {len(candidate_hosts)} 个 host")
                elif data_source == "zoomeye":
                    region = config.get("templateRegion", "")
                    candidate_hosts = get_cached_hosts("zoomeye", region)
                    logger.info(f"📡 [zoomeye] 从 source_cache 读取, region='{region}', 匹配到 {len(candidate_hosts)} 个 host")
                else:
                    # GitHub 实时搜索
                    candidate_hosts = await search_github_sources(
                        session,
                        config["templateTargetAddress"],
                        config["searchDepth"],
                        task_runner.should_stop
                    )

                if not candidate_hosts:
                    logger.warning(f"⚠️ [无候选源] {config['name']} 未搜索到任何候选 host")
                else:

                    run_concurrency = global_concurrency

                    logger.info(f"⚡ [验证中] {len(candidate_hosts)} 个候选，并发数={run_concurrency}")

                    valid_count = 0
                    _valid_lock = threading.Lock()
                    _valid_hosts = []  # 收集验证通过的 host

                    sem = asyncio.Semaphore(run_concurrency)

                    async def worker(host_item):

                        if task_runner.should_stop():
                            return

                        async with sem:

                            try:
                                #
                                # 去重检查：如果 host 已在 iptv_list 中则跳过
                                #
                                with get_db() as conn:
                                    existing = conn.execute(
                                        "SELECT 1 FROM iptv_list WHERE host=?",
                                        (host_item,)
                                    ).fetchone()
                                if existing:
                                    logger.debug(f"⏭️ [去重跳过] {host_item} 已存在于 iptv_list")
                                    return

                                res = await verify_single_host(
                                    session,
                                    host_item,
                                    config["templateTargetAddress"],
                                    global_timeout_ms / 1000.0,
                                    task_runner.should_stop
                                )

                                if not res:
                                    return

                                # 收集验证通过的结果
                                with _valid_lock:
                                    _valid_hosts.append({
                                        "host": host_item,
                                        "delay": res["delay"],
                                        "protocol": res["protocol"]
                                    })

                            except Exception as e:
                                logger.error(f"❌ [验证异常] {host_item} -> {e}")

                        return

                    await asyncio.gather(
                        *(worker(h) for h in candidate_hosts)
                    )

                    if _valid_hosts:
                        # 统一 geoip 富化
                        enriched = await enrich_geo_batch(session, _valid_hosts)

                        now_stamp = int(time.time() * 1000)

                        # 入 iptv_list 活源池
                        _db_write_lock.acquire()
                        try:
                            with get_db() as conn:
                                for item in enriched:
                                    host_item = item["host"]
                                    if ":" in host_item:
                                        ip_val, port_val = host_item.rsplit(":", 1)
                                    else:
                                        ip_val, port_val = host_item, 80

                                    conn.execute("""
                                        INSERT INTO iptv_list (
                                            host, ip, port,
                                            sourceType, sourceName,
                                            region, operator,
                                            geoRegion, geoOperator,
                                            delay, protocol,
                                            target, channelName,
                                            createTime, updateTime
                                        ) VALUES (
                                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                                        )
                                        ON CONFLICT(host, target, channelName)
                                        DO UPDATE SET
                                            delay = excluded.delay,
                                            updateTime = excluded.updateTime,
                                            geoRegion = excluded.geoRegion,
                                            geoOperator = excluded.geoOperator
                                    """, (
                                        host_item, ip_val, int(port_val),
                                        source_type, source_name,
                                        config.get("templateRegion", ""),
                                        config.get("templateOperator", ""),
                                        item["geoRegion"], item["geoOperator"],
                                        item["delay"], item["protocol"],
                                        config["templateTargetAddress"],
                                        config["templateTargetName"],
                                        now_stamp, now_stamp
                                    ))
                        finally:
                            _db_write_lock.release()

                        valid_count = len(enriched)

                    logger.info(f"✅ [扫描完成] {config['name']} -> {valid_count}/{len(candidate_hosts)} 个有效")
                    total_valid += valid_count

            except Exception as e:
                logger.error(f"❌ [扫描异常] {config['name']} -> {e}")

            finally:
                with get_db() as conn:
                    conn.execute(
                        "UPDATE scan_config SET updatedAt=datetime('now') WHERE id=?",
                        (cfg_id,)
                    )

            # 配置间延迟
            if index < len(config_ids) - 1 and not task_runner.should_stop():
                logger.info(f"⏳ [等待延迟] {global_config_delay}s 后进入下一个配置")
                await asyncio.sleep(global_config_delay)

        task_runner.finish()

        if total_valid > 0:
            push_to_hf()
            logger.info(f"✅ [扫描完成] 共发现 {total_valid} 个有效源，已同步云端")
        else:
            logger.info("📭 [扫描完成] 本次扫描未产生新活源")

        # 自动续跑：用户停止当前配置后，用剩余配置继续执行
        skipped_ids = task_runner.pop_skipped_configs()
        if skipped_ids:
            progress = task_runner.get_progress()
            next_index = progress["current_index"] + 1
            remaining = [cid for cid in progress["config_ids"][next_index:] if cid not in skipped_ids]

            if remaining:
                logger.info(f"⏭️ [自动续跑] 用剩余 {len(remaining)} 个配置继续: {remaining}")
                await asyncio.sleep(1)
                threading.Thread(
                    target=auto_restart_with_remaining,
                    args=(list(remaining), False),
                    daemon=True
                ).start()


def auto_restart_with_remaining(config_ids: List[int], skip_disabled: bool = False):
    """自动重启：重置所有中断标记，确保新配置干净启动"""
    # 强制重置所有停止标记，防止旧信号污染新线程
    with task_runner._lock:
        task_runner._should_stop = False
        task_runner._scanning_config_id = None
        task_runner._skip_config_ids.clear()
    task_runner.start(len(config_ids), config_ids)
    asyncio.run(execute_scan_queue(config_ids, skip_disabled))


def trigger_background_queue(config_ids: List[int], skip_disabled: bool = False):

    shared_queue = list(config_ids)
    logger.info(f"▶️ [任务队列] 共 {len(shared_queue)} 个配置: {shared_queue}")

    task_runner.start(len(shared_queue), shared_queue)

    threading.Thread(
        target=lambda: asyncio.run(
            execute_scan_queue(shared_queue, skip_disabled)
        ),
        daemon=True
    ).start()


def enqueue_background_queue(config_id: int):

    if task_runner.is_idle():
        return False

    task_runner.enqueue([config_id])
    logger.info(f"📋 [加入队列] 配置 id={config_id}")
    return True


class ActiveSourceJanitor:

    def __init__(self):
        self._thread = None
        self._running = False
        self._stop_event = threading.Event()

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._thread = None

    def _loop(self):
        import datetime
        import threading
        import asyncio
        import aiohttp
        last_scan_exec = ""
        last_janitor_exec = ""
        last_ozone_fetch_exec = ""
        last_zoomeye_fetch_exec = ""
        last_ozone_scan_exec = ""
        last_zoomeye_scan_exec = ""

        # HF 自动同步定时器（每分钟一次）
        last_hf_sync = time.time()

        while self._running:
            scan_cron = get_setting("scan_cron", "")
            janitor_cron = get_setting("janitor_cron", "")

            now = datetime.datetime.now()
            cron_now = f"{now.minute} {now.hour} {now.day} {now.month} {now.weekday()+1}"

            def cron_match(cron_expr: str, cron_str: str) -> bool:
                """匹配 cron 表达式，返回是否匹配"""
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

            def cron_field_match(pattern: str, value: str) -> bool:
                """匹配单个 cron 字段：支持 */N, *, N, N-M, N,M"""
                if pattern == "*":
                    return True
                if "/" in pattern:
                    base, step = pattern.split("/", 1)
                    v = int(value)
                    s = int(step)
                    if base == "*":
                        return v % s == 0
                    return v >= int(base) and (v - int(base)) % s == 0
                if "-" in pattern:
                    start, end = pattern.split("-", 1)
                    return int(start) <= int(value) <= int(end)
                if "," in pattern:
                    return value in pattern.split(",")
                return pattern == value

            try:
                # HF 自动同步（每分钟一次）
                now_t = time.time()
                if now_t - last_hf_sync >= 60:
                    last_hf_sync = now_t
                    push_to_hf()

                # 扫描任务触发
                if scan_cron and cron_match(scan_cron, cron_now):
                    exec_key = now.strftime("%Y-%m-%d %H:%M")
                    if exec_key != last_scan_exec and task_runner.is_idle():
                        last_scan_exec = exec_key
                        logger.info(f"⏰ [Cron触发] 定时扫描 -> cron: {scan_cron}")
                        with get_db() as conn:
                            rows = conn.execute("SELECT id FROM scan_config WHERE enabled=1").fetchall()
                        if rows:
                            ids = [r["id"] for r in rows]
                            trigger_background_queue(ids, skip_disabled=True)
                        else:
                            logger.warning("⚠️ [Cron触发] 无可用激活配置")

                # 复测任务触发
                if janitor_cron and cron_match(janitor_cron, cron_now):
                    exec_key = now.strftime("%Y-%m-%d %H:%M")
                    if exec_key != last_janitor_exec and task_runner.is_idle():
                        last_janitor_exec = exec_key
                        logger.info(f"⏰ [Cron触发] 定时复测 -> cron: {janitor_cron}")
                        with get_db() as conn:
                            active_sources = conn.execute("SELECT * FROM iptv_list").fetchall()

                        logger.info(f"🧹 [定时复测] 开始复测 {len(active_sources)} 个活源")

                        if active_sources:
                            timeout_sec = int(get_setting("timeout", "2000")) / 1000.0
                            concurrency = int(get_setting("concurrency", "64"))
                            sem = asyncio.Semaphore(concurrency)

                            task_runner.set_rechecking()
                            try:
                                async def recheck_all():
                                    timeout = aiohttp.ClientTimeout(total=timeout_sec)
                                    connector = aiohttp.TCPConnector(limit=256, ssl=False)

                                    async with aiohttp.ClientSession(
                                        timeout=timeout,
                                        connector=connector
                                    ) as session:

                                        async def recheck_worker(source):

                                            async with sem:

                                                # 检查是否被扫描任务要求暂停
                                                if task_runner.should_pause_recheck():
                                                    logger.info(f"⏸️ [复测暂停] 等待扫描完成: {source['host']}")
                                                    while task_runner.should_pause_recheck():
                                                        await asyncio.sleep(2)
                                                    logger.info(f"▶️ [复测恢复] 继续处理: {source['host']}")

                                                host_val = source["host"]
                                                target_val = source["target"]
                                                proto = (source["protocol"] or "rtp").lower().strip()

                                                if not host_val.startswith("http"):
                                                    host_val = f"http://{host_val}"
                                                host_val = host_val.rstrip("/")

                                                try:
                                                    start_t = time.time()
                                                    test_url = f"{host_val}/{proto}/{target_val}"
                                                    async with session.get(
                                                        test_url,
                                                        timeout=aiohttp.ClientTimeout(total=timeout_sec),
                                                        headers={"User-Agent": "Mozilla/5.0"}
                                                    ) as r:
                                                        if (
                                                            r.status in [200, 206]
                                                            and await r.content.read(512)
                                                        ):
                                                            delay = int((time.time() - start_t) * 1000)
                                                            with get_db() as conn:
                                                                conn.execute("""
                                                                    UPDATE iptv_list
                                                                    SET delay=?, updateTime=?, protocol=?
                                                                    WHERE id=?
                                                                """, (
                                                                    delay,
                                                                    int(time.time() * 1000),
                                                                    proto,
                                                                    source["id"]
                                                                ))
                                                            return
                                                except Exception:
                                                    pass

                                                logger.warning(f"🗑️ [老化淘汰] {source['host']}")
                                                with get_db() as conn:
                                                    conn.execute(
                                                        "DELETE FROM iptv_list WHERE id=?",
                                                        (source["id"],)
                                                    )

                                        await asyncio.gather(
                                            *(recheck_worker(s) for s in active_sources)
                                        )

                                asyncio.run(recheck_all())
                                logger.info("🧹 [复测完成] 将在下一分钟自动同步云端")
                            finally:
                                task_runner.clear_rechecking()

                # 0.zone 定时拉取
                ozone_fetch_cron = get_setting("ozone_fetch_cron", "")
                if ozone_fetch_cron and cron_match(ozone_fetch_cron, cron_now):
                    exec_key = now.strftime("%Y-%m-%d %H:%M")
                    if exec_key != last_ozone_fetch_exec:
                        last_ozone_fetch_exec = exec_key
                        logger.info(f"⏰ [Cron触发] 0.zone 定时拉取 -> cron: {ozone_fetch_cron}")
                        async def _fetch_loop():
                            from services.ozone import fetch_ozone_sources
                            from services.source_cache import cache_sources
                            sources = await fetch_ozone_sources(page=1)
                            if sources:
                                cache_sources("ozone", sources)
                        asyncio.run(_fetch_loop())

                # zoomeye 定时拉取（通过 GitHub Action）
                zoomeye_fetch_cron = get_setting("zoomeye_fetch_cron", "")
                if zoomeye_fetch_cron and cron_match(zoomeye_fetch_cron, cron_now):
                    exec_key = now.strftime("%Y-%m-%d %H:%M")
                    if exec_key != last_zoomeye_fetch_exec:
                        last_zoomeye_fetch_exec = exec_key
                        logger.info(f"⏰ [Cron触发] zoomeye 定时拉取 -> cron: {zoomeye_fetch_cron}")
                        source_url = get_setting("zoomeye_source_url", "https://www.zoomeye.ai/api/search?q=YXBwPSJ1ZHB4eSBtdWx0aWNhc3QgVURQLXRvLUhUVFAiICYmIGNvdW50cnk9IuS4reWbvSI%3D")
                        async def _trigger_ze():
                            from services.github_action import trigger_source_fetch
                            await trigger_source_fetch(
                            source_url,
                            source_type="zoomeye"
                        )
                        asyncio.run(_trigger_ze())

                # 0.zone 定时扫描
                ozone_scan_cron = get_setting("ozone_scan_cron", "")
                if ozone_scan_cron and cron_match(ozone_scan_cron, cron_now):
                    exec_key = now.strftime("%Y-%m-%d %H:%M")
                    if exec_key != last_ozone_scan_exec and task_runner.is_idle():
                        last_ozone_scan_exec = exec_key
                        logger.info(f"⏰ [Cron触发] 0.zone 定时扫描 -> cron: {ozone_scan_cron}")
                        with get_db() as conn:
                            rows = conn.execute(
                                "SELECT id FROM scan_config WHERE dataSource='ozone' AND enabled=1"
                            ).fetchall()
                        if rows:
                            trigger_background_queue([r["id"] for r in rows])
                        else:
                            logger.info("📡 [0.zone] 无启用的 ozone 扫描配置")

                # ZoomEye 定时扫描
                zoomeye_scan_cron = get_setting("zoomeye_scan_cron", "")
                if zoomeye_scan_cron and cron_match(zoomeye_scan_cron, cron_now):
                    exec_key = now.strftime("%Y-%m-%d %H:%M")
                    if exec_key != last_zoomeye_scan_exec and task_runner.is_idle():
                        last_zoomeye_scan_exec = exec_key
                        logger.info(f"⏰ [Cron触发] ZoomEye 定时扫描 -> cron: {zoomeye_scan_cron}")
                        with get_db() as conn:
                            rows = conn.execute(
                                "SELECT id FROM scan_config WHERE dataSource='zoomeye' AND enabled=1"
                            ).fetchall()
                        if rows:
                            trigger_background_queue([r["id"] for r in rows])
                        else:
                            logger.info("📡 [ZoomEye] 无启用的 zoomeye 扫描配置")

            except Exception as e:
                logger.error(f"❌ [复测异常] 老化器心跳内爆: {e}")

            # 每分钟检查一次
            self._stop_event.wait(timeout=30)


# 🛠️ 全局唯一实例化对象，供 main.py 正常引入
janitor = ActiveSourceJanitor()
