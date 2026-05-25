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


async def enrich_geo_batch(session: aiohttp.ClientSession, sources: list[dict]) -> list[dict]:
    """批量富化 geo 信息：对缺少 geoRegion/geoOperator 的 host 条目进行 geoip 查询
    保留原始字段（如 delay、protocol 等），只追加 geo 信息
    """
    enriched = []
    for item in sources:
        host = item.get("host", "")
        if not item.get("geoRegion") and not item.get("geoOperator"):
            ip_part = host.rsplit(":", 1)[0] if ":" in host else host
            geo = await query_geoip(session, ip_part)
            region_val = geo.get("region", "")
            operator_val = geo.get("operator", "")
            logger.info(f"🌍 [geoip] {host} -> region={region_val!r}, operator={operator_val!r}")
            enriched.append({
                **item,
                "geoRegion": region_val,
                "geoOperator": operator_val
            })
        else:
            enriched.append(item)
    return enriched
