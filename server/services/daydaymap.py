"""DayDayMap 数据源拉取服务"""
import aiohttp
import base64
import logging
from typing import List
from db.database import get_db, get_setting
from services.geoip import enrich_geo_batch

logger = logging.getLogger("udpxy_radar")

DAYDAYMAP_API_URL = "https://www.daydaymap.com/api/v1/raymap/search/asset/query"
# 固定搜索词：product="Udpxy Web Module"
DAYDAYMAP_KEYWORD = base64.b64encode('product="Udpxy Web Module"'.encode()).decode()


async def fetch_daydaymap_sources() -> List[dict]:
    """
    请求 DayDayMap API 拉取 udpxy 设备数据（未登录只能查看第一页，固定10条），
    解析 ip+port 为 host，geo 信息全部走 geoip 查询。
    """
    page = 1
    page_size = 10
    logger.info(f"📡 [DayDayMap] 拉取第 1 页...")

    payload = {
        "page": 1,
        "page_size": page_size,
        "keyword": DAYDAYMAP_KEYWORD,
        "scan_time": [],
        "asset_tag": "",
        "asset_type": "",
        "data_filter": []
    }

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.daydaymap.com",
        "Referer": f"https://www.daydaymap.com/searchResult?page=1&pageSize={page_size}&value=&rawValue=&assetType=&assetTag=&scanTime=&dataFilter=&showType=card&keyword={DAYDAYMAP_KEYWORD}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                DAYDAYMAP_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ [DayDayMap] 请求失败，状态码: {resp.status}")
                    return []

                result = await resp.json()

            if result.get("code") != 200:
                logger.warning(f"⚠️ [DayDayMap] 返回错误: {result.get('msg', 'unknown')}")
                return []

            data_list = result.get("data", {}).get("list", [])
            raw_sources = []

            for item in data_list:
                ip = item.get("ip", "")
                port = item.get("port", "")
                if ip and port:
                    raw_sources.append({"host": f"{ip}:{port}"})

            # 全部走 geoip 查询
            enriched = await enrich_geo_batch(session, raw_sources)

            total = result.get("data", {}).get("total", 0)
            logger.info(f"📄 [DayDayMap] 第 1 页 -> {len(enriched)} 条 (总计 {total})")
            return enriched

    except Exception as e:
        logger.error(f"❌ [DayDayMap] 请求异常: {e}")
        return []
