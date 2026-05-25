import aiohttp
import logging

logger = logging.getLogger("udpxy_radar")

async def query_geoip(session: aiohttp.ClientSession, ip: str) -> dict:
    url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("status") == "fail":
                    logger.info(f"⚠️ [geoip] {ip} API 失败: {data.get('message', 'unknown')}")
                    return {"region": "", "operator": ""}
                result = {
                    "region": data.get("regionName", "").replace("省", "").replace("市", ""),
                    "operator": data.get("isp", "")
                }
                logger.debug(f"🌍 [geoip] {ip} -> {result}")
                return result
            else:
                logger.debug(f"🌍 [geoip] {ip} HTTP {resp.status}")
                return {"region": "", "operator": ""}
    except Exception as e:
        logger.debug(f"🌍 [geoip] {ip} 异常: {e}")
        return {"region": "", "operator": ""}
