"""Hunter (奇安信) 数据源拉取服务"""
import aiohttp
import logging
from typing import List
from datetime import date
from db.database import get_db, get_setting

logger = logging.getLogger("udpxy_radar")

HUNTER_API_URL = "https://hunter.qianxin.com/openApi/search"
# 固定搜索词: header="Server: udpxy"&&ip.country=="中国"
HUNTER_QUERY = 'aGVhZGVyPSJTZXJ2ZXI6IHVkcHh5IiYmaXAuY291bnRyeT09IuS4reWbvSI'


async def fetch_hunter_sources(page: int = 1, page_size: int = 100) -> List[dict]:
    """
    请求 Hunter API 拉取 udpxy 设备数据，
    解析 ip+port 为 host，geo 信息全部走 geoip 查询。
    """
    api_key = get_setting("hunter_api_key", "")
    if not api_key:
        logger.warning("⚠️ [Hunter] API Key 未配置")
        return []

    today = date.today().isoformat()

    params = {
        "api-key": api_key,
        "search": HUNTER_QUERY,
        "page": page,
        "page_size": page_size,
        "is_web": 1,
        "start_time": today,
        "end_time": today
    }

    logger.info(f"📡 [Hunter] 拉取第 {page} 页...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                HUNTER_API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ [Hunter] 请求失败，状态码: {resp.status}")
                    return []

                result = await resp.json()

            if result.get("code") != 200:
                logger.warning(f"⚠️ [Hunter] 返回错误: {result.get('message', 'unknown')}")
                return []

            data = result.get("data", {})
            arr = data.get("arr", [])
            raw_sources = []

            for item in arr:
                ip = item.get("ip", "")
                port = item.get("port", "")
                if ip and port:
                    raw_sources.append({"host": f"{ip}:{port}"})

            # 全部走 geoip 查询
            from services.geoip import enrich_geo_batch
            enriched = await enrich_geo_batch(session, raw_sources)

            total = data.get("total", 0)
            rest_quota = data.get("rest_quota", "")
            logger.info(f"📄 [Hunter] 第 {page} 页 -> {len(enriched)} 条 (总计 {total}), {rest_quota}")
            return enriched

    except Exception as e:
        logger.error(f"❌ [Hunter] 请求异常: {e}")
        return []
