"""供应商合规门户路由 — 外部访问 + 内部管理。"""
import secrets
from datetime import timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..models import Supplier, SupplierAccess, SupplierSubmission, OrgNode, User, now

supplier_router = APIRouter(prefix="/api/supplier-portal", tags=["供应商门户"])


def _is_expired(access: SupplierAccess) -> bool:
    """判断令牌是否过期。SQLite 读出的 datetime 可能无 tzinfo，统一补 UTC。"""
    exp = access.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < now()

# ── 内部管理 ──
class GrantAccessIn(BaseModel):
    supplier_id: int
    node_id: int
    days: int = 30


@supplier_router.post("/grant-access")
def grant_access(body: GrantAccessIn,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    token = secrets.token_urlsafe(32)
    access = SupplierAccess(supplier_id=body.supplier_id, node_id=body.node_id,
                            token=token, expires_at=now() + timedelta(days=body.days))
    db.add(access)
    db.commit()
    return {"token": token, "expires_at": access.expires_at.isoformat(),
            "url": f"/supplier/submit?token={token}"}


@supplier_router.get("/access-list")
def list_accesses(supplier_id: int = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = db.query(SupplierAccess)
    if supplier_id:
        q = q.filter_by(supplier_id=supplier_id)
    return q.order_by(SupplierAccess.created_at.desc()).all()


@supplier_router.post("/revoke-access/{access_id}")
def revoke_access(access_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    access = db.query(SupplierAccess).filter_by(id=access_id).first()
    if not access:
        raise HTTPException(404, "访问令牌不存在")
    access.is_active = False
    db.commit()
    return {"ok": True}


# ── 供应商提交审查 ──
@supplier_router.get("/submissions")
def list_submissions(supplier_id: int = None, status: str = None,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(SupplierSubmission)
    if supplier_id:
        q = q.filter_by(supplier_id=supplier_id)
    if status:
        q = q.filter_by(status=status)
    return q.order_by(SupplierSubmission.created_at.desc()).limit(50).all()


class ReviewSubmission(BaseModel):
    status: str  # approved / rejected
    note: str = ""


@supplier_router.post("/submissions/{sub_id}/review")
def review_submission(sub_id: int, body: ReviewSubmission,
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sub = db.query(SupplierSubmission).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(404, "提交不存在")
    sub.status = body.status
    sub.reviewed_by = user.username
    sub.review_note = body.note
    db.commit()
    return {"ok": True}


# ── 外部供应商接口 (token 验证) ──
class SupplierSubmit(BaseModel):
    token: str
    form_type: str  # self_assessment/sbom/evidence
    title: str
    content: dict


@supplier_router.post("/submit")
def supplier_submit(body: SupplierSubmit, db: Session = Depends(get_db)):
    access = db.query(SupplierAccess).filter_by(token=body.token, is_active=True).first()
    if not access or _is_expired(access):
        raise HTTPException(403, "访问令牌无效或已过期")
    sub = SupplierSubmission(access_id=access.id, supplier_id=access.supplier_id,
                             form_type=body.form_type, title=body.title, content=body.content)
    db.add(sub)
    db.commit()
    return {"id": sub.id, "status": "submitted"}


@supplier_router.get("/access-info")
def access_info(token: str, db: Session = Depends(get_db)):
    access = db.query(SupplierAccess).filter_by(token=token, is_active=True).first()
    if not access or _is_expired(access):
        raise HTTPException(403, "令牌无效或已过期")
    supplier = db.query(Supplier).filter_by(id=access.supplier_id).first()
    node = db.query(OrgNode).filter_by(id=access.node_id).first()
    return {"supplier_name": supplier.name if supplier else "", "node_name": node.name if node else "",
            "expires_at": access.expires_at.isoformat()}
