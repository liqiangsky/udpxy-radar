import aiohttp
import re
import logging
import asyncio
from typing import List, Optional
from db.database import get_setting

logger = logging.getLogger("CastScout_V3")

async def search_github_sources(session: aiohttp.ClientSession, target_addr: str, config_max_pages: Optional[int], should_stop_func) -> List[str]:
    multicast_heads = set()

    # 1. 🔑 Token 安全加载与基础配置
    token = get_setting("github_token", "")
    max_pages = config_max_pages if config_max_pages and config_max_pages > 0 else 5

    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "CastScout/3.0"}
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
                # 🛡️ 翻页呼吸器（避免频繁请求触发 GitHub 403）
                await asyncio.sleep(2.5)

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
