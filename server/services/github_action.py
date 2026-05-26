# services/github_action.py
"""
HF Spaces 触发 GitHub Action 拉取数据源
配置通过 HF Spaces 环境变量传入
"""
import os
import logging
import aiohttp

logger = logging.getLogger("udpxy_radar")

GITHUB_API = "https://api.github.com"
WORKFLOW_FILE = "source-fetcher.yml"


async def trigger_source_fetch(source_url: str, source_type: str = "zoomeye", hunter_api_key: str = "") -> bool:
    token = os.getenv("GITHUB_ACTION_TOKEN", "")
    owner = os.getenv("GITHUB_ACTION_OWNER", "")
    repo = os.getenv("GITHUB_ACTION_REPO", "")
    callback_token = os.getenv("CALLBACK_TOKEN", "")

    if not token or not owner or not repo:
        logger.warning("🚨 [GitHub Action] 未配置 GITHUB_ACTION_TOKEN/OWNER/REPO 环境变量")
        return False

    hf_url = os.getenv("HF_SPACE_URL", "")
    if not hf_url:
        logger.warning("🚨 [GitHub Action] 未配置 HF_SPACE_URL 环境变量")
        return False

    callback_url = f"{hf_url}/api/source/push"
    logger.info(f"🚀 [触发GitHub Action] source={source_type}")
    logger.info(f"   回调地址: {callback_url}")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    dispatch_payload = {
        "ref": "master",
        "inputs": {
            "source_url": source_url,
            "source_type": source_type,
            "callback_url": callback_url,
            "callback_token": callback_token,
        }
    }
    if hunter_api_key:
        dispatch_payload["inputs"]["hunter_api_key"] = hunter_api_key

    url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=dispatch_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 204:
                    logger.info("✅ [GitHub Action] 触发成功，等待回调...")
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"❌ [GitHub Action] 触发失败: {resp.status} {body[:200]}")
                    return False
    except Exception as e:
        logger.error(f"❌ [GitHub Action] 触发异常: {e}")
        return False
