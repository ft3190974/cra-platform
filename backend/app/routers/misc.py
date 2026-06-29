"""集成、审计、仪表盘路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_role
from ..database import get_db
from ..models import (Assessment, AuditLog, ControlLibrary, Document, Integration,
                     IntegrationLog, OrgNode, User, VulnReport, Vulnerability)
from ..rate_limit import sync_limiter
from ..schemas import IntegrationCreate
from ..services.integrations import refresh_overdue, sync_integration

integ_router = APIRouter(prefix="/api/integrations", tags=["integrations"])
audit_router = APIRouter(prefix="/api/audit", tags=["audit"])
dash_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ───────────────────────── 集成 ─────────────────────────
@integ_router.get("")
def list_integrations(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [{"id": i.id, "node_id": i.node_id, "kind": i.kind, "name": i.name,
             "endpoint": i.endpoint, "enabled": i.enabled, "last_sync_at": i.last_sync_at}
            for i in db.query(Integration).all()]


@integ_router.post("")
def create_integration(payload: IntegrationCreate, db: Session = Depends(get_db),
                       user: User = Depends(require_role("manager"))):
    i = Integration(**payload.model_dump())
    db.add(i); db.commit(); db.refresh(i)
    log_action(db, user, "CREATE", "integration", i.id, {"kind": i.kind})
    return {"id": i.id}


@integ_router.post("/{iid}/sync")
def sync(iid: int, db: Session = Depends(get_db),
         user: User = Depends(require_role("assessor")),
         _rate: None = Depends(sync_limiter)):
    i = db.get(Integration, iid)
    if not i:
        raise HTTPException(404, "未找到集成")
    result = sync_integration(db, i)
    db.add(IntegrationLog(integration_id=iid, status="ok",
                          summary=result["summary"], payload=result))
    db.commit()
    log_action(db, user, "SYNC", "integration", iid, result)
    return result


@integ_router.get("/{iid}/logs")
def integ_logs(iid: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    logs = db.query(IntegrationLog).filter(
        IntegrationLog.integration_id == iid).order_by(IntegrationLog.id.desc()).all()
    return [{"id": l.id, "status": l.status, "summary": l.summary,
             "created_at": l.created_at} for l in logs]


# ───────────────────────── 审计 ─────────────────────────
@audit_router.get("")
def list_audit(resource_type: str | None = None, action: str | None = None,
               limit: int = 200, db: Session = Depends(get_db),
               _: User = Depends(require_role("auditor"))):
    q = db.query(AuditLog)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if action:
        q = q.filter(AuditLog.action == action)
    return [{"id": a.id, "username": a.username, "action": a.action,
             "resource_type": a.resource_type, "resource_id": a.resource_id,
             "detail": a.detail, "created_at": a.created_at}
            for a in q.order_by(AuditLog.id.desc()).limit(limit).all()]


# ───────────────────────── 仪表盘 ─────────────────────────
@dash_router.get("")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """全局合规态势 — 批量查询优化，无 N+1。"""
    refresh_overdue(db)
    nodes = db.query(OrgNode).all()
    vulns = db.query(Vulnerability).all()
    projects = [n for n in nodes if n.node_type == "project"]
    products = [n for n in nodes if n.node_type == "product"]
    versions = [n for n in nodes if n.node_type == "version"]
    reports = db.query(VulnReport).all()
    cra_lib = db.query(ControlLibrary).filter(ControlLibrary.framework_type == "cra").first()

    sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for v in vulns:
        sev[v.severity] = sev.get(v.severity, 0) + 1

    # 合规逾期项目数
    from ..models import now as model_now
    now_ts = model_now()
    compliance_overdue = sum(1 for n in nodes if n.compliance_deadline and n.compliance_deadline < now_ts)

    # 供应商数量
    from ..models import Supplier
    supplier_count = db.query(Supplier).count()

    # 批量加载所有产品的评估（一次查询代替 N 次）
    product_ids = [p.id for p in products]
    all_assessments = {}
    if product_ids and cra_lib:
        q = db.query(Assessment).filter(
            Assessment.node_id.in_(product_ids),
            Assessment.library_id == cra_lib.id
        ).order_by(Assessment.id.desc()).all()
        for a in q:
            if a.node_id not in all_assessments:
                all_assessments[a.node_id] = a  # 最新的排前面
    elif cra_lib:
        pass

    passed = 0
    not_passed = 0
    readiness = []
    for p in products:
        a = all_assessments.get(p.id)
        is_passed = bool(a and a.status == "approved")
        if is_passed:
            passed += 1
        else:
            not_passed += 1
        readiness.append({
            "product": p.name, "readiness": a.readiness if a else 0,
            "cra_class": p.cra_class,
            "compliance_status": "passed" if is_passed else ("assessing" if a else "not_started")
        })

    total_projects = len(products)
    pass_rate = round(100 * passed / total_projects, 1) if total_projects else 0.0
    vulns_unfixed = sum(1 for v in vulns if v.status in ("open", "triaged", "fixing"))
    vulns_unfixed_total = sum(1 for v in vulns if v.status in ("open", "triaged", "fixing"))

    return {
        "products_count": len(versions),
        "critical_vulns": vulns_unfixed_total,
        "compliance_overdue": compliance_overdue,
        "supplier_count": supplier_count,
        "overdue_reports": compliance_overdue,
        "avg_readiness": supplier_count,
        "counts": {
            "compliance_projects_total": total_projects,
            "projects_not_passed": not_passed,
            "vulns_unfixed": vulns_unfixed,
            "pass_rate": pass_rate,
            "projects_passed": passed,
            "business_units": sum(1 for n in nodes if n.node_type == "business_unit"),
            "projects": sum(1 for n in nodes if n.node_type == "project"),
            "products": len(products),
            "versions": sum(1 for n in nodes if n.node_type == "version"),
            "vulns_total": len(vulns),
            "vulns_open": vulns_unfixed,
            "assessments": db.query(Assessment).count(),
            "documents": db.query(Document).count(),
        },
        "severity": sev,
        "readiness": readiness,
        "report_alerts": [
            {"type": r.report_type, "target": r.target, "status": r.status, "due_at": r.due_at}
            for r in reports if r.status in ("pending", "overdue")
        ],
    }
