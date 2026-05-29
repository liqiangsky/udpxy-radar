from fastapi import APIRouter
from services.cron_heartbeat import handle_heartbeat
from services.hf_sync import push_to_hf

router = APIRouter()


@router.post("/cron/heartbeat")
async def api_cron_heartbeat():
    """
    Cloudflare Worker 心跳端点。
    每分钟被 CF Worker ping 一次，检查当前时间是否匹配任何 cron 任务。
    认证由 middleware 统一处理（X-Callback-Token）。
    """
    triggered = await handle_heartbeat()
    return {
        "ok": True,
        "triggered": len(triggered),
        "tasks": triggered
    }


@router.post("/cron/hf-sync")
async def api_cron_hf_sync():
    """
    Cloudflare Worker 触发 HF Datasets 同步端点。
    由 CF Worker 定时调用，将三库同步至 HuggingFace。
    认证由 middleware 统一处理（X-Callback-Token）。
    """
    push_to_hf()
    return {"ok": True}
