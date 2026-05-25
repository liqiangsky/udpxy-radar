# services/source_cache.py
"""
公共缓存表 source_cache 读写工具
所有低频定时数据源（0.zone、zoomeye 等）共用
"""
import logging
from typing import List
from db.database import get_db

logger = logging.getLogger("udpxy_radar")


def cache_sources(source_type: str, sources: List[dict]):
    """
    将数据写入 source_cache 公共表。
    每个 source dict 至少包含 "host"，可选 "geoRegion", "geoOperator"
    """
    if not sources:
        return

    with get_db() as conn:
        seen = set()
        rows = []
        for s in sources:
            if s["host"] in seen:
                continue
            seen.add(s["host"])
            rows.append((source_type, s["host"], s.get("geoRegion", ""), s.get("geoOperator", "")))

        if rows:
            conn.executemany(
                "INSERT OR IGNORE INTO source_cache (sourceType, host, geoRegion, geoOperator) VALUES (?, ?, ?, ?)",
                rows
            )
            regions = set(r[2] for r in rows)
            logger.info(f"💾 [source_cache] {source_type} 写入 {len(rows)} 条, 地区分布: {regions}")


def get_cached_hosts(source_type: str, region: str = "") -> List[str]:
    """
    从 source_cache 读取缓存 host 列表，按 geoRegion 过滤。
    """
    with get_db() as conn:
        if region:
            rows = conn.execute(
                "SELECT DISTINCT host FROM source_cache WHERE sourceType=? AND geoRegion=?",
                (source_type, region)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT host FROM source_cache WHERE sourceType=?",
                (source_type,)
            ).fetchall()
        return [r["host"] for r in rows]
