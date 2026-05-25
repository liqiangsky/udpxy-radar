from fastapi import APIRouter
from db.database import get_db
from db.models import TemplateCreateOrUpdate

router = APIRouter()

@router.get("/templates")
def api_list_templates():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM config_template ORDER BY id DESC").fetchall()]

@router.post("/templates")
def api_create_template(data: TemplateCreateOrUpdate):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO config_template (name, region, operator, targetName, targetAddress) VALUES (?, ?, ?, ?, ?)",
            (data.name, data.region, data.operator, data.targetName, data.targetAddress)
        )
        return dict(conn.execute("SELECT * FROM config_template WHERE id=?", (cur.lastrowid,)).fetchone())

@router.put("/templates/{template_id}")
def api_update_template(template_id: int, data: TemplateCreateOrUpdate):
    with get_db() as conn:
        conn.execute(
            "UPDATE config_template SET name=?, region=?, operator=?, targetName=?, targetAddress=?, updatedAt=datetime('now') WHERE id=?",
            (data.name, data.region, data.operator, data.targetName, data.targetAddress, template_id)
        )
    return {"ok": True}

@router.delete("/templates/{template_id}")
def api_delete_template(template_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM config_template WHERE id=?", (template_id,))
    return {"ok": True}
