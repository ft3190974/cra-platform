"""通用 CRUD 路由工厂 — 为简单实体快速生成 list/get/create/update/delete。

安全设计：
- 全局只读字段黑名单：id / created_at / 外键这类系统字段，无论 create/update 均不可被请求体污染；
- 调用方可通过 writable_fields 显式指定白名单，进一步收紧（推荐）。
"""
from typing import Iterable, Type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .auth import get_current_user, require_role
from .audit import log_action
from .database import get_db
from .models import User

# 全局只读字段：任何模型都不应通过 CRUD 工厂被请求体写入。
# 涵盖主键、审计时间戳、密码哈希、角色等敏感字段。
READONLY_FIELDS = frozenset({
    "id", "created_at", "updated_at",
    "hashed_password",  # User 表密码字段（即使有 User CRUD 也不可直改）
    "role", "is_active",  # 角色与启用状态需走专用接口，不走通用 CRUD
    "sha256", "stored_path",  # 附件的存储路径与哈希由系统计算
})


def _filter_writable(payload: dict, model: Type, writable_fields: Iterable[str] | None = None) -> dict:
    """按黑名单 + 可选白名单过滤可写字段。"""
    cols = {c.name for c in model.__table__.columns}
    forbidden = READONLY_FIELDS
    allowed = set(writable_fields) if writable_fields else cols
    out = {}
    for k, v in payload.items():
        if k == "id" or k in forbidden:
            continue
        if k not in cols or k not in allowed:
            continue
        out[k] = v
    return out


def make_crud_router(model: Type, name: str, write_role="assessor",
                     filter_fields=None, writable_fields=None) -> APIRouter:
    r = APIRouter(prefix=f"/api/{name}", tags=[name])
    filter_fields = filter_fields or []

    def serialize(obj):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    @r.get("")
    def list_items(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                   node_id: int | None = None):
        q = db.query(model)
        if node_id is not None and hasattr(model, "node_id"):
            q = q.filter(model.node_id == node_id)
        items = q.order_by(model.id.desc()).limit(1000).all()
        return [serialize(i) for i in items]

    @r.get("/{item_id}")
    def get_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, "未找到")
        return serialize(obj)

    @r.post("")
    def create_item(payload: dict, db: Session = Depends(get_db),
                    user: User = Depends(require_role(write_role))):
        data = _filter_writable(payload, model, writable_fields)
        obj = model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        log_action(db, user, "CREATE", name, obj.id, {"name": payload.get("name") or payload.get("title")})
        return serialize(obj)

    @r.put("/{item_id}")
    def update_item(item_id: int, payload: dict, db: Session = Depends(get_db),
                    user: User = Depends(require_role(write_role))):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, "未找到")
        data = _filter_writable(payload, model, writable_fields)
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        log_action(db, user, "UPDATE", name, item_id, {})
        return serialize(obj)

    @r.delete("/{item_id}")
    def delete_item(item_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_role("manager"))):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, "未找到")
        db.delete(obj)
        db.commit()
        log_action(db, user, "DELETE", name, item_id, {})
        return {"ok": True}

    return r
