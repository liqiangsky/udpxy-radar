from fastapi import APIRouter
from services.cron_heartbeat import handle_heartbeat

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
