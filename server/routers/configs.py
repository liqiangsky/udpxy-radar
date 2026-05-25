import logging
from fastapi import APIRouter, HTTPException, Request
from db.database import get_db, get_setting
from db.models import ConfigCreateOrUpdate
from core.status import task_runner
from core.engine import trigger_background_queue, enqueue_background_queue
import asyncio
import aiohttp

logger = logging.getLogger("udpxy_radar")
router = APIRouter()


def _check_data_source_enabled(ds: str):
    if ds == "github" and get_setting("github_enabled", "1") != "1":
        raise HTTPException(400, "GitHub 数据源未启用")
    if ds == "ozone" and get_setting("ozone_enabled", "0") != "1":
        raise HTTPException(400, "零零信安 数据源未启用")
    if ds == "zoomeye" and get_setting("zoomeye_enabled", "0") != "1":
        raise HTTPException(400, "ZoomEye 数据源未启用")
    if ds not in ("github", "ozone", "zoomeye"):
        raise HTTPException(400, f"不支持的数据源: {ds}")

@router.get("/configs")
def api_list_configs():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM scan_config ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

@router.post("/configs")
def api_create_config(data: ConfigCreateOrUpdate):
    _check_data_source_enabled(data.dataSource)
    with get_db() as conn:
        tpl = conn.execute("SELECT * FROM config_template WHERE id=?", (data.templateId,)).fetchone()
        if not tpl:
            raise HTTPException(400, "模板不存在")

        cur = conn.execute("""
            INSERT INTO scan_config (name, templateId, dataSource,
                                     templateRegion, templateOperator, templateTargetName, templateTargetAddress,
                                     searchDepth, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.name, data.templateId, data.dataSource,
            tpl["region"], tpl["operator"], tpl["targetName"], tpl["targetAddress"],
            data.searchDepth, 1 if data.enabled else 0
        ))
        result = dict(conn.execute("SELECT * FROM scan_config WHERE id=?", (cur.lastrowid,)).fetchone())
    return result

@router.put("/configs/{config_id}")
def api_update_config(config_id: int, data: ConfigCreateOrUpdate):
    _check_data_source_enabled(data.dataSource)
    with get_db() as conn:
        tpl = conn.execute("SELECT * FROM config_template WHERE id=?", (data.templateId,)).fetchone()
        if not tpl:
            raise HTTPException(400, "模板不存在")

        conn.execute("""
            UPDATE scan_config SET name=?, templateId=?, dataSource=?,
                                   templateRegion=?, templateOperator=?, templateTargetName=?, templateTargetAddress=?,
                                   searchDepth=?, enabled=?, updatedAt=datetime('now')
            WHERE id=?
        """, (
            data.name, data.templateId, data.dataSource,
            tpl["region"], tpl["operator"], tpl["targetName"], tpl["targetAddress"],
            data.searchDepth, 1 if data.enabled else 0, config_id
        ))
    return {"ok": True}

@router.delete("/configs/{config_id}")
def api_delete_config(config_id: int):
    with get_db() as conn: conn.execute("DELETE FROM scan_config WHERE id=?", (config_id,))
    return {"ok": True}

@router.post("/configs/{config_id}/run")
def api_trigger_single_config(config_id: int):
    if task_runner.is_idle():
        trigger_background_queue([config_id])
    else:
        enqueue_background_queue(config_id)
    return {"ok": True}

@router.post("/configs/{config_id}/stop")
def api_stop_single_config(config_id: int):
    if task_runner.is_idle(): raise HTTPException(400, "当前无运行中的任务")
    p = task_runner.get_progress()
    if p["config_ids"] and p["current_index"] < len(p["config_ids"]):
        current_running_id = p["config_ids"][p["current_index"]]
        if current_running_id == config_id:
            task_runner.stop_current_and_continue(config_id)
            return {"ok": True}
    if task_runner.remove_from_queue(config_id):
        return {"ok": True}
    raise HTTPException(400, "该配置不在扫描队列中")

@router.post("/configs/run-all")
def api_trigger_run_all():
    if task_runner.is_idle():
        with get_db() as conn: rows = conn.execute("SELECT id FROM scan_config WHERE enabled=1").fetchall()
        if not rows: raise HTTPException(400, "无可用激活配置")
        trigger_background_queue([r["id"] for r in rows], skip_disabled=True)
    else:
        with get_db() as conn: rows = conn.execute("SELECT id FROM scan_config WHERE enabled=1").fetchall()
        if not rows: raise HTTPException(400, "无可用激活配置")
        for r in rows:
            enqueue_background_queue(r["id"])
    return {"ok": True}

@router.get("/configs/progress")
def api_get_progress():
    p = task_runner.get_progress()
    current_id = p["config_ids"][p["current_index"]] if p["config_ids"] and p["current_index"] < len(p["config_ids"]) else None
    queued_ids = p["config_ids"][p["current_index"] + 1:] if p["config_ids"] else []
    return {
        "running": p["running"],
        "currentId": current_id,
        "currentIndex": p["current_index"] if p["running"] else None,
        "total": p["total"],
        "currentName": p["current_config_name"] if p["running"] else None,
        "queuedIds": queued_ids
    }


@router.post("/ozone/fetch")
async def api_manual_ozone_fetch(page: int = 1):
    """
    手动触发 0.zone 源站数据拉取。
    固定查询词: udpxy multicast UDP-to-HTTP
    """
    if get_setting("ozone_enabled", "0") != "1":
        raise HTTPException(400, "零零信安 数据源未启用")

    from services.ozone import fetch_ozone_sources
    from services.source_cache import cache_sources

    sources = await fetch_ozone_sources(page=page)

    if sources:
        cache_sources("ozone", sources)

    return {
        "ok": True,
        "page": page,
        "fetched": len(sources),
        "hosts": [s["host"] for s in sources]
    }


@router.post("/zoomeye/fetch")
async def api_manual_zoomeye_fetch():
    """
    手动触发 zoomeye 数据拉取（通过 GitHub Action）
    """
    from services.github_action import trigger_source_fetch

    source_url = "https://www.zoomeye.ai/api/search?q=YXBwPSJ1ZHB4eSBtdWx0aWNhc3QgVURQLXRvLUhUVFAiICYmIGNvdW50cnk9IuS4reWbvSI%3D"
    ok = await trigger_source_fetch(source_url, source_type="zoomeye")
    if not ok:
        raise HTTPException(500, "GitHub Action 触发失败，请检查配置")

    return {"ok": True, "message": "已触发，等待 Action 回调推送"}


@router.post("/daydaymap/fetch")
async def api_manual_daydaymap_fetch():
    """
    手动触发 DayDayMap 数据拉取
    """
    from services.daydaymap import fetch_daydaymap_sources
    from services.source_cache import cache_sources

    sources = await fetch_daydaymap_sources()
    if sources:
        cache_sources("daydaymap", sources)

    return {
        "ok": True,
        "fetched": len(sources),
        "hosts": [s["host"] for s in sources]
    }


@router.post("/source/push")
async def api_source_push(request: Request):
    """
    GitHub Action 完成数据拉取后，推送清洗后的 host 列表到此接口
    支持任意数据源类型（zoomeye / ozone / custom）
    自动对缺少 geo 信息的 host 进行 geoip 富化
    """
    import aiohttp
    from services.source_cache import cache_sources
    from services.geoip import enrich_geo_batch

    token = request.headers.get("X-Callback-Token", "")
    expected_token = get_setting("callback_token", "")
    if expected_token and token != expected_token:
        raise HTTPException(403, "认证失败")

    body = await request.json()
    source_type = body.get("sourceType", "unknown")
    hosts = body.get("hosts", [])

    logger.info(f"📥 [数据源推送] sourceType={source_type}, hosts={len(hosts)}")

    # geoip 富化
    async with aiohttp.ClientSession() as session:
        enriched = await enrich_geo_batch(session, hosts)

    logger.info(f"📄 [{source_type}] 推送 {len(enriched)} 条数据，已写入 source_cache")

    # 去重后入库
    cache_sources(source_type, enriched)

    return {
        "ok": True,
        "sourceType": source_type,
        "fetched": len(enriched),
        "hosts": [h["host"] for h in enriched]
    }


