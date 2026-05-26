import asyncio
import aiohttp
import threading
import time
import logging

from typing import List

from db.database import get_db, get_cache_db, get_setting
from core.status import task_runner
from services.github import search_github_sources
from services.ozone import fetch_ozone_sources
from services.source_cache import get_cached_hosts, cache_sources, get_cached_geo, cache_host_geo
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
                # 根据 dataSource 路由（空 = 全部启用源，逗号分隔 = 指定源）
                raw_ds = config.get("dataSource", "").strip()
                if raw_ds:
                    data_sources = [s.strip() for s in raw_ds.split(',') if s.strip()]
                else:
                    data_sources = []
                    for ds_name in ("github", "ozone", "zoomeye", "daydaymap", "hunter"):
                        setting_key = f"{ds_name}_enabled"
                        if get_setting(setting_key, "0" if ds_name != "github" else "1") == "1":
                            data_sources.append(ds_name)

                source_name_map = {"github": "GitHub", "ozone": "零零信安", "zoomeye": "ZoomEye", "daydaymap": "DayDayMap", "hunter": "Hunter"}

                candidate_hosts = []  # list of (host, source_type, source_name)
                for ds in data_sources:
                    ds_name = source_name_map.get(ds, ds)
                    if ds == "ozone":
                        region = config.get("templateRegion", "")
                        hosts = get_cached_hosts("ozone", region)
                        logger.info(f"📡 [ozone] 从 source_cache 读取, region='{region}', 匹配到 {len(hosts)} 个 host")
                        candidate_hosts.extend((h, ds, ds_name) for h in hosts)
                    elif ds == "zoomeye":
                        region = config.get("templateRegion", "")
                        hosts = get_cached_hosts("zoomeye", region)
                        logger.info(f"📡 [zoomeye] 从 source_cache 读取, region='{region}', 匹配到 {len(hosts)} 个 host")
                        candidate_hosts.extend((h, ds, ds_name) for h in hosts)
                    elif ds == "daydaymap":
                        region = config.get("templateRegion", "")
                        hosts = get_cached_hosts("daydaymap", region)
                        logger.info(f"📡 [daydaymap] 从 source_cache 读取, region='{region}', 匹配到 {len(hosts)} 个 host")
                        candidate_hosts.extend((h, ds, ds_name) for h in hosts)
                    elif ds == "hunter":
                        region = config.get("templateRegion", "")
                        hosts = get_cached_hosts("hunter", region)
                        logger.info(f"📡 [hunter] 从 source_cache 读取, region='{region}', 匹配到 {len(hosts)} 个 host")
                        candidate_hosts.extend((h, ds, ds_name) for h in hosts)
                    elif ds == "github":
                        hosts = await search_github_sources(
                            session,
                            config["templateTargetAddress"],
                            config["searchDepth"],
                            task_runner.should_stop
                        )
                        candidate_hosts.extend((h, "github", "GitHub") for h in hosts)

                if not candidate_hosts:
                    logger.warning(f"⚠️ [无候选源] {config['name']} 未搜索到任何候选 host")
                else:

                    run_concurrency = global_concurrency

                    logger.info(f"⚡ [验证中] {len(candidate_hosts)} 个候选，并发数={run_concurrency}")

                    valid_count = 0
                    _valid_lock = threading.Lock()
                    _valid_hosts = []  # 收集验证通过的 host

                    sem = asyncio.Semaphore(run_concurrency)

                    async def worker(host_entry):
                        host_item, host_source_type, host_source_name = host_entry

                        if task_runner.should_stop():
                            return

                        async with sem:

                            try:
                                #
                                # 去重检查：如果 host 已在 iptv_list 中则跳过
                                #
                                with get_cache_db() as conn:
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

                                # 收集验证通过的结果（携带来源标签）
                                with _valid_lock:
                                    _valid_hosts.append({
                                        "host": host_item,
                                        "delay": res["delay"],
                                        "protocol": res["protocol"],
                                        "sourceType": host_source_type,
                                        "sourceName": host_source_name
                                    })

                            except Exception as e:
                                logger.error(f"❌ [验证异常] {host_item} -> {e}")

                        return

                    await asyncio.gather(
                        *(worker(h) for h in candidate_hosts)
                    )

                    if _valid_hosts:
                        # 预填充已有 geo 缓存，跳过重复查询
                        for host_item in _valid_hosts:
                            cached = get_cached_geo(host_item["host"])
                            if cached:
                                host_item.update(cached)

                        # 统一 geoip 富化（已有 geo 的会自动跳过）
                        enriched = await enrich_geo_batch(session, _valid_hosts)

                        # 新 geo 回写 source_cache
                        new_geo_count = 0
                        for item in enriched:
                            if item.get("geoRegion") or item.get("geoOperator"):
                                cache_host_geo(item["sourceType"], item["host"], item.get("geoRegion", ""), item.get("geoOperator", ""))
                                new_geo_count += 1

                        if new_geo_count:
                            logger.info(f"💾 [geo缓存] {new_geo_count} 条新 geo 信息已写入 source_cache")

                        now_stamp = int(time.time() * 1000)

                        # 入 iptv_list 活源池
                        _db_write_lock.acquire()
                        try:
                            with get_cache_db() as conn:
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
                                        item["sourceType"], item["sourceName"],
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
        # HF 自动同步定时器（每分钟一次）
        last_hf_sync = time.time()

        while self._running:
            try:
                # HF 自动同步（每分钟一次）
                now_t = time.time()
                if now_t - last_hf_sync >= 60:
                    last_hf_sync = now_t
                    push_to_hf()

                # 所有数据源 cron 任务已迁移到 /api/cron/heartbeat 端点，
                # 由 Cloudflare Worker 每分钟触发一次。
                # 这里只保留 HF 同步和基础心跳。

            except Exception as e:
                logger.error(f"❌ [复测异常] 老化器心跳内爆: {e}")

            except Exception as e:
                logger.error(f"❌ [复测异常] 老化器心跳内爆: {e}")

            # 每分钟检查一次
            self._stop_event.wait(timeout=30)


# 🛠️ 全局唯一实例化对象，供 main.py 正常引入
janitor = ActiveSourceJanitor()
