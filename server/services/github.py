"""GitHub 数据源服务：Code Search + UserResult 文件解析"""
import aiohttp
import re
import logging
import asyncio
import random
from typing import List, Optional, Dict
from db.database import get_setting

logger = logging.getLogger("udpxy_radar")

# ===== GitHub Code Search =====

async def search_github_sources(session: aiohttp.ClientSession, target_addr: str, config_max_pages: Optional[int], should_stop_func) -> List[str]:
    multicast_heads = set()

    # 1. 🔑 Token 安全加载与基础配置
    token = get_setting("github_token", "")
    max_pages = config_max_pages if config_max_pages and config_max_pages > 0 else 5

    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "udpxy-radar/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
        logger.info(f"🔑 [Token] 已加载，最大挖掘深度: {max_pages} 页")
    else:
        logger.warning("🔑 [Token] 未配置，降级为 1 页模式")
        max_pages = 1

    # 🛠️ 【修复点 1】必须在函数头部对输入的 target_addr 进行拆解，否则后续会报 NameError
    if ":" in target_addr:
        ip, port = target_addr.rsplit(":", 1)
    else:
        ip, port = target_addr, ""

    target_extensions = ["m3u", "txt"]

    # 3. 🔄 专项格式轮询检索
    for ext in target_extensions:
        if should_stop_func(): break

        # 🎯 完美复刻旧版逻辑：通过标准空格传递给 params
        # aiohttp 会在底层自动将空格转为官方合规的 %20，100% 触发 GitHub 的紧密相关性邻近搜索！
        if port:
            query_str = f"{ip} {port} extension:{ext}"
        else:
            query_str = f"{ip} extension:{ext}"

        params = {
            "q": query_str,
            "per_page": "30"
        }

        logger.info(f"🔍 [GitHub搜索] .{ext} -> {query_str}")

        for page in range(1, max_pages + 1):
            if should_stop_func(): break

            params["page"] = str(page)
            api_url = "https://api.github.com/search/code"

            try:
                # 🛡️ 翻页呼吸器（避免频繁请求触发 GitHub 403），随机 3-5s
                await asyncio.sleep(random.uniform(3, 5))

                async with session.get(api_url, headers=headers, params=params, timeout=15) as resp:
                    if resp.status == 403:
                        logger.warning(f"⚠️ [GitHub频控] .{ext} 第 {page} 页遭遇微限流，保护性休眠 8 秒...")
                        await asyncio.sleep(8.0)
                        continue

                    if resp.status != 200:
                        logger.warning(f"⚠️ [GitHub异常] .{ext} 第 {page} 页请求失败，状态码: {resp.status}")
                        continue

                    data = await resp.json()
                    items = data.get("items", [])

                    if not items:
                        break

                    logger.info(f"📄 [GitHub] .{ext} 第 {page} 页 -> {len(items)} 个文件")

                    # 4. 🚀 纯正则榨取文本内容中的 HOST 部分
                    for item in items:
                        if should_stop_func(): break
                        raw_url = item["html_url"].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                        file_name = item.get("name", f"未知.{ext}")

                        try:
                            async with session.get(raw_url, timeout=8) as r_resp:
                                if r_resp.status != 200: continue
                                content = await r_resp.text()

                                # 🛠️ 【修复点 2】转义整个 target_addr（包含端口），保障只有命中特定频道的 Host 才会被提取
                                escaped_addr = re.escape(target_addr)
                                matches = re.findall(rf"https?://([^/\s]+)/(?:rtp|udp)/{escaped_addr}", content, re.IGNORECASE)

                                for m in matches:
                                    host_clean = m.strip()
                                    host_lower = host_clean.lower()

                                    # 阻击内网死源
                                    if (
                                        "127.0.0.1" in host_lower or
                                        "localhost" in host_lower or
                                        "192.168." in host_lower or
                                        host_lower.startswith("10.")
                                    ):
                                        continue

                                    if host_clean not in multicast_heads:
                                        multicast_heads.add(host_clean)
                        except Exception:
                            continue

            except Exception as e:
                logger.error(f"❌ [GitHub搜索] 检索 .{ext} 第 {page} 页遭遇未知异常: {e}")
                continue

    logger.info(f"✅ [GitHub收网] {target_addr} -> {len(multicast_heads)} 个候选 HOST")
    return list(multicast_heads)


# ===== GitHub UserResult 全网文件解析 =====

_URL_PATTERN = re.compile(
    r'https?://([^/\s]+)/(rtp|udp)/([^\s"\']+)',
    re.IGNORECASE
)

_PRIVATE_PATTERNS = [
    "127.0.0.1", "localhost", "0.0.0.0",
    "::1", "[::1]"
]


def _is_private(host_lower: str) -> bool:
    if any(p in host_lower for p in _PRIVATE_PATTERNS):
        return True
    if host_lower.startswith("192.168."):
        return True
    if host_lower.startswith("10."):
        return True
    if host_lower.startswith("172."):
        parts = host_lower.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
                if 16 <= second <= 31:
                    return True
            except ValueError:
                pass
    return False


async def fetch_github_user_result_sources(
    session: aiohttp.ClientSession,
    timeout_sec: float = 5.0
) -> List[Dict]:
    """
    通过 GitHub Code Search API 搜索全网文件，或直接下载指定 URL 列表，
    解析 /rtp/ 或 /udp/ 直播源 URL。
    按 HOST 去重，保留第一个完整 URL，测试可用性（512字节），返回可用源列表。
    """
    if not get_setting("github_enabled", "1") == "1":
        logger.info("📡 [GitHub UserResult] GitHub 未启用，跳过拉取")
        return []

    token = get_setting("github_token", "")

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "udpxy-radar/1.0"
    }
    if token:
        headers["Authorization"] = f"token {token}"
        logger.info(f"🔑 [GitHub UserResult] Token 已加载，持续翻页直到无新结果")
    else:
        logger.warning("🔑 [GitHub UserResult] Token 未配置，降级为 1 页模式")

    # 优先使用 URL 列表（一行一个）
    urls_text = get_setting("github_user_result_urls", "").strip()
    custom_urls = [u.strip() for u in urls_text.split("\n") if u.strip().startswith("https://")] if urls_text else []

    # 搜索关键词（可配置）
    search_query = get_setting("github_user_result_query", "filename:result.txt path:output/ipv4")

    file_items = []

    if custom_urls:
        # 使用自定义 URL 列表直接下载
        logger.info(f"📄 [GitHub UserResult] 使用自定义 URL 列表: {len(custom_urls)} 个")
        for url in custom_urls:
            file_items.append({"html_url": url.replace("raw.githubusercontent.com", "github.com").replace("/raw/", "/blob/")})
    elif search_query.startswith("https://"):
        # 搜索关键词是完整 URL，直接下载
        logger.info(f"📄 [GitHub UserResult] 直接使用 URL: {search_query}")
        file_items = [{"html_url": search_query.replace("raw.githubusercontent.com", "github.com").replace("/raw/", "/blob/")}]
    else:
        # Step 1: 搜索文件
        params = {"q": search_query, "per_page": "30", "sort": "updated", "order": "desc"}

        page = 1
        while True:
            params["page"] = str(page)
            try:
                async with session.get(
                    "https://api.github.com/search/code",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 403:
                        logger.warning("⚠️ [GitHub UserResult] 微限流，休眠 8s")
                        await asyncio.sleep(8)
                        continue
                    if resp.status != 200:
                        logger.warning(f"⚠️ [GitHub UserResult] 搜索失败: {resp.status}")
                        break
                    data = await resp.json()
                    items = data.get("items", [])
                    if not items:
                        break
                    file_items.extend(items)
                    total = data.get("total_count", 0)
                    logger.info(f"📄 [GitHub UserResult] 第 {page} 页 -> {len(items)} 个文件 (共 {total} 个)")
                    await asyncio.sleep(random.uniform(3, 5))
                    page += 1
            except Exception as e:
                logger.error(f"❌ [GitHub UserResult] 搜索异常: {e}")
                break

    if not file_items:
        logger.info("📭 [GitHub UserResult] 未搜索到任何文件")
        return []

    # Step 2: 解析文件内容，提取 URL，按 HOST 去重
    host_map = {}

    for item in file_items:
        try:
            raw_url = (
                item["html_url"]
                .replace("github.com", "raw.githubusercontent.com")
                .replace("/blob/", "/")
            )
            async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    continue
                content = await resp.text()

                for match in _URL_PATTERN.finditer(content):
                    host_raw = match.group(1)
                    protocol = match.group(2).lower()
                    target = match.group(3)

                    host_lower = host_raw.lower()
                    if _is_private(host_lower):
                        continue

                    # 按 HOST 去重，保留第一个
                    if host_lower not in host_map:
                        host_map[host_lower] = {
                            "host": host_raw,
                            "protocol": protocol,
                            "target": target,
                        }
        except Exception as e:
            logger.debug(f"⚠️ [GitHub UserResult] 解析文件失败: {item.get('html_url', '?')} -> {e}")

    logger.info(f"✅ [GitHub UserResult] 解析完成，去重后 {len(host_map)} 个唯一 HOST")

    if not host_map:
        return []

    # Step 3: 验证可用性（512字节测试）
    timeout = int(get_setting("timeout", "2000")) / 1000.0
    concurrency = int(get_setting("concurrency", "64"))

    sem = asyncio.Semaphore(concurrency)

    async def verify_entry(entry):
        async with sem:
            h = entry["host"]
            test_url = f"http://{h}/{entry['protocol']}/{entry['target']}"
            try:
                start = asyncio.get_event_loop().time()
                async with session.get(
                    test_url,
                    timeout=aiohttp.ClientTimeout(total=timeout * 2),
                    headers={"User-Agent": "udpxy-radar/1.0"}
                ) as r:
                    if r.status in (200, 206):
                        chunk = await r.content.read(512)
                        if chunk:
                            delay = int((asyncio.get_event_loop().time() - start) * 1000)
                            return {
                                "host": h,
                                "sourceType": "github_user_result",
                                "sourceName": "GitHub",
                                "delay": delay,
                                "protocol": entry["protocol"],
                                "geoRegion": "",
                                "geoOperator": "",
                            }
            except Exception:
                pass
            return None

    tasks = [verify_entry(v) for v in host_map.values()]
    results = await asyncio.gather(*tasks)

    valid_hosts = [r for r in results if r is not None]
    logger.info(f"✅ [GitHub UserResult] 验证完成，{len(valid_hosts)}/{len(host_map)} 个可用")

    return valid_hosts
