"""Hunter (奇安信) 数据源拉取服务"""
import aiohttp
import logging
from typing import List
from datetime import date
from db.database import get_setting

logger = logging.getLogger("udpxy_radar")

HUNTER_API_URL = "https://hunter.qianxin.com/openApi/search"
# 固定搜索词: header="Server: udpxy"&&ip.country=="中国"
HUNTER_QUERY = 'aGVhZGVyPSJTZXJ2ZXI6IHVkcHh5IiYmaXAuY291bnRyeT09IuS4reWbvSI'
HUNTER_PAGE_SIZE = 10  # 每次 10 条（1 条 1 积分）


async def fetch_hunter_sources() -> List[dict]:
    """
    循环分页请求 Hunter API，每次 10 条，直到积分用完或无数据。
    解析 ip+port 为 host，geo 信息全部走 geoip 查询。
    """
    api_key = get_setting("hunter_api_key", "")
    if not api_key:
        logger.warning("⚠️ [Hunter] API Key 未配置")
        return []

    today = date.today().isoformat()
    all_sources = []
    page = 1

    async with aiohttp.ClientSession() as session:
        while True:
            params = {
                "api-key": api_key,
                "search": HUNTER_QUERY,
                "page": page,
                "page_size": HUNTER_PAGE_SIZE,
                "is_web": 1,
                "start_time": today,
                "end_time": today
            }

            logger.info(f"📡 [Hunter] 拉取第 {page} 页...")

            # 打印完整请求信息（调试用）
            logger.info(f"🔍 [Hunter] 请求 URL: {HUNTER_API_URL}")
            logger.info(f"🔍 [Hunter] 请求参数: api-key={api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '(too short)'}, page={page}, page_size={HUNTER_PAGE_SIZE}, start_time={today}, end_time={today}")

            try:
                async with session.get(
                    HUNTER_API_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Encoding": "identity"
                    }
                ) as resp:
                    # 打印响应信息（调试用）
                    logger.info(f"🔍 [Hunter] 响应状态码: {resp.status}")
                    logger.info(f"🔍 [Hunter] 响应头: {dict(resp.headers)}")
                    logger.info(f"🔍 [Hunter] 实际请求 URL: {resp.url}")

                    if resp.status != 200:
                        # 打印响应体（调试用）
                        raw_text = await resp.text()
                        logger.warning(f"⚠️ [Hunter] 请求失败，状态码: {resp.status}, 响应体: {raw_text[:500]}")
                        break

                    result = await resp.json()
                    # 打印完整响应（调试用）
                    logger.info(f"🔍 [Hunter] 完整响应: {result}")

                if result.get("code") != 200:
                    logger.warning(f"⚠️ [Hunter] 返回错误: {result.get('message', 'unknown')}")
                    break

                data = result.get("data", {})
                arr = data.get("arr", [])
                rest_quota = data.get("rest_quota", "")
                total = data.get("total", 0)

                if not arr:
                    logger.info(f"📄 [Hunter] 第 {page} 页无数据，停止翻页")
                    break

                for item in arr:
                    ip = item.get("ip", "")
                    port = item.get("port", "")
                    if ip and port:
                        all_sources.append({"host": f"{ip}:{port}"})

                logger.info(f"📄 [Hunter] 第 {page} 页 -> {len(arr)} 条 (累计 {len(all_sources)}/{total}), {rest_quota}")

                # 判断积分是否用完
                if "0" in rest_quota:
                    logger.info(f"📄 [Hunter] 积分已用完，停止翻页")
                    break

                page += 1

            except Exception as e:
                logger.error(f"❌ [Hunter] 第 {page} 页请求异常: {e}")
                break

        # 全部走 geoip 查询
        if all_sources:
            from services.geoip import enrich_geo_batch
            enriched = await enrich_geo_batch(session, all_sources)
            logger.info(f"📄 [Hunter] 总计获取 {len(enriched)} 条数据")
            return enriched
        return []
