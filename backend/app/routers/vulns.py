"""漏洞管理 + CRA 第14条通报路由。"""
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_role
from ..database import get_db
from ..models import User, Vulnerability, VulnReport, now
from ..schemas import VulnCreate, VulnUpdate
from ..services.integrations import create_report_deadlines, refresh_overdue

vulns_router = APIRouter(prefix="/api/vulns", tags=["vulns"])


@vulns_router.get("")
def list_vulns(node_id: int | None = None, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    q = db.query(Vulnerability)
    if node_id is not None:
        q = q.filter(Vulnerability.node_id == node_id)
    return [{"id": v.id, "node_id": v.node_id, "source": v.source, "cve_id": v.cve_id,
             "title": v.title, "severity": v.severity, "cvss_score": v.cvss_score,
             "cwe": v.cwe, "component": v.component, "status": v.status,
             "exploited": v.exploited, "found_at": v.found_at}
            for v in q.order_by(Vulnerability.id.desc()).all()]


@vulns_router.post("")
def create_vuln(payload: VulnCreate, db: Session = Depends(get_db),
                user: User = Depends(require_role("assessor"))):
    v = Vulnerability(**payload.model_dump())
    db.add(v); db.commit(); db.refresh(v)
    if v.exploited:
        create_report_deadlines(db, v)
    log_action(db, user, "CREATE", "vuln", v.id, {"title": v.title, "exploited": v.exploited})
    return {"id": v.id}


@vulns_router.put("/{vid}")
def update_vuln(vid: int, payload: VulnUpdate, db: Session = Depends(get_db),
                user: User = Depends(require_role("assessor"))):
    v = db.get(Vulnerability, vid)
    if not v:
        raise HTTPException(404, "未找到漏洞")
    was_exploited = v.exploited
    for k, val in payload.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    db.commit()
    if v.exploited and not was_exploited:
        create_report_deadlines(db, v)
    log_action(db, user, "UPDATE", "vuln", vid, {})
    return {"ok": True}


@vulns_router.get("/reports/board")
def reports_board(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """CRA 第14条通报时限看板 — 批量预加载漏洞避免 N+1。"""
    refresh_overdue(db)
    reports = db.query(VulnReport).order_by(VulnReport.due_at).all()
    # 批量加载关联漏洞
    vuln_ids = list({r.vuln_id for r in reports})
    vulns_map = {v.id: v for v in db.query(Vulnerability).filter(Vulnerability.id.in_(vuln_ids)).all()} if vuln_ids else {}
    out = []
    for r in reports:
        v = vulns_map.get(r.vuln_id)
        due = r.due_at
        if due and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        remaining = (due - now()).total_seconds() / 3600 if due else None
        out.append({"id": r.id, "vuln": v.title if v else "", "cve": v.cve_id if v else "",
                    "report_type": r.report_type, "target": r.target, "status": r.status,
                    "due_at": r.due_at, "hours_remaining": round(remaining, 1) if remaining is not None else None})
    return out


@vulns_router.post("/reports/{rid}/send")
def send_report(rid: int, db: Session = Depends(get_db),
                user: User = Depends(require_role("manager"))):
    r = db.get(VulnReport, rid)
    if not r:
        raise HTTPException(404, "未找到通报单")
    r.status = "sent"; r.sent_at = now(); db.commit()
    log_action(db, user, "UPDATE", "vuln_report", rid, {"action": "send", "target": r.target})
    return {"ok": True}
