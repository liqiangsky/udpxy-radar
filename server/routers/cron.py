from fastapi import APIRouter, HTTPException
from fastapi import Request
from db.database import get_setting
from services.cron_heartbeat import handle_heartbeat

router = APIRouter()


@router.post("/cron/heartbeat")
async def api_cron_heartbeat(request: Request):
    """
    Cloudflare Worker 心跳端点。
    每分钟被 CF Worker ping 一次，检查当前时间是否匹配任何 cron 任务。
    """
    # 简单认证：通过 callback_token 验证
    token = get_setting("callback_token", "")
    if token:
        auth_header = request.headers.get("X-Cron-Token", "")
        if auth_header != token:
            raise HTTPException(403, "认证失败")

    triggered = await handle_heartbeat()
    return {
        "ok": True,
        "triggered": len(triggered),
        "tasks": triggered
    }
