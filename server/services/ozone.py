from urllib.parse import urlparse
import aiohttp
import hashlib
import random
import logging
from typing import List
from db.database import get_db, get_setting
from services.geoip import query_geoip

logger = logging.getLogger("udpxy_radar")

OZONE_API_URL = "https://0.zone/api/home/search/"
OZONE_QUERY = "udpxy multicast UDP-to-HTTP"


def _generate_sign():
    """生成 0.zone 的随机 ns 和对应的 sign 签名"""
    ns = str(random.randint(10**15, 10**16 - 1))
    raw_string = f"0.zone.{ns}"
    sign = hashlib.md5(raw_string.encode()).hexdigest()
    return ns, sign


async def fetch_ozone_sources(page: int = 1) -> List[dict]:
    """
    请求 0.zone 搜索接口（固定搜索词: udpxy multicast UDP-to-HTTP），
    对每个 host 查 geoip 获取 geoRegion/geoOperator。
    """
    if not get_setting("ozone_enabled", "0") == "1":
        logger.warning("📡 [0.zone] 数据源未启用，跳过拉取")
        return []

    ns, sign = _generate_sign()

    form_data = (
        f"page={page}&pagesize=10&title={OZONE_QUERY}"
        f"&title_type=site&ns={ns}&sign={sign}&sort=explore_timestamp"
    )

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://0.zone",
        "Referer": f"https://0.zone/search_home?title_type=site&title={OZONE_QUERY}&page={page}&pagesize=10",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # TODO: CSRFToken 需要定期更新或从配置读取
    csrf = get_setting("ozone_csrf_token", "")
    if csrf:
        headers["X-CSRFToken"] = csrf

    logger.info(f"📡 [0.zone] 拉取第 {page} 页")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OZONE_API_URL,
                data=form_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ [0.zone] 请求失败，状态码: {resp.status}")
                    return []

                result = await resp.json()

            if result.get("code") != 0:
                logger.warning(f"⚠️ [0.zone] 返回错误: {result.get('message', 'unknown')}")
                return []

            data_list = result.get("data", {}).get("data_list", [])
            sources = []

            for item in data_list:
                src = item.get("_source", {})
                redirect_url = src.get("redirect_url", "")
                if not redirect_url:
                    continue

                # 从 redirect_url 解析 host（可能是 IP 或域名）
                try:
                    parsed = urlparse(redirect_url)
                    hostname = parsed.hostname
                    port = parsed.port or "4022"
                    if not hostname:
                        continue
                except Exception:
                    continue

                host = f"{hostname}:{port}"

                # geoip 查询（IP 和域名都支持）
                try:
                    geo_info = await query_geoip(session, hostname)
                except Exception:
                    geo_info = {"region": "", "operator": ""}

                region_val = geo_info.get("region", "")
                operator_val = geo_info.get("operator", "")

                logger.info(f"🌍 [geoip] {host} -> region={region_val!r}, operator={operator_val!r}")

                sources.append({
                    "host": host,
                    "geoRegion": region_val,
                    "geoOperator": operator_val
                })

            logger.info(f"📄 [0.zone] 第 {page} 页 -> {len(sources)} 条数据")
            return sources

    except Exception as e:
        logger.error(f"❌ [0.zone] 请求异常: {e}")
        return []
