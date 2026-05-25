# services/validator.py
import aiohttp
import time
from typing import Optional

async def verify_single_host(session: aiohttp.ClientSession, host: str, target_addr: str, timeout_sec: float, should_stop_func) -> Optional[dict]:
    for proto in ["rtp", "udp"]:
        if should_stop_func(): return None
        test_url = f"http://{host}/{proto}/{target_addr}"
        try:
            start_time = time.time()
            async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=timeout_sec)) as resp:
                if resp.status == 200:
                    chunk = await resp.content.read(512)
                    if chunk:
                        return {"url": test_url, "protocol": proto, "delay": int((time.time() - start_time) * 1000)}
        except Exception: continue
    return None
