"""增强仪表盘路由 — 多产品线合规态势 + 通报时限告警 + 许可证风险。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..models import (OrgNode, Assessment, Vulnerability, VulnReport, Risk, LicenseScan,
                       Supplier, SupplierSubmission, WorkflowInstance, Notification, User, now)

dash2_router = APIRouter(prefix="/api/dashboard-v2", tags=["仪表盘V2"])


@dash2_router.get("/overview")
def get_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """高管视角：全局合规态势概览。"""
    nodes = db.query(OrgNode).all()
    products = [n for n in nodes if n.node_type == "product"]
    versions = [n for n in nodes if n.node_type == "version"]

    assessments = db.query(Assessment).all()
    avg_readiness = round(sum(a.readiness for a in assessments) / len(assessments), 1) if assessments else 0

    vulns = db.query(Vulnerability).all()
    open_vulns = [v for v in vulns if v.status in ("open", "triaged")]
    critical_vulns = [v for v in open_vulns if v.severity == "critical"]

    overdue_reports = db.query(VulnReport).filter(VulnReport.status == "overdue").count()

    risks = db.query(Risk).filter(Risk.status == "open").all()

    latest_scan = db.query(LicenseScan).order_by(LicenseScan.created_at.desc()).first()

    pending_subs = db.query(SupplierSubmission).filter(SupplierSubmission.status == "submitted").count()
    pending_wfs = db.query(WorkflowInstance).filter(WorkflowInstance.status == "submitted").count()

    return {
        "products_count": len(products),
        "versions_count": len(versions),
        "avg_readiness": avg_readiness,
        "open_vulns": len(open_vulns),
        "critical_vulns": len(critical_vulns),
        "overdue_reports": overdue_reports,
        "open_risks": len(risks),
        "license_risk": latest_scan.risk_level if latest_scan else "n/a",
        "pending_submissions": pending_subs,
        "pending_workflows": pending_wfs,
        "vuln_by_severity": {
            "critical": len([v for v in open_vulns if v.severity == "critical"]),
            "high": len([v for v in open_vulns if v.severity == "high"]),
            "medium": len([v for v in open_vulns if v.severity == "medium"]),
            "low": len([v for v in open_vulns if v.severity == "low"]),
        },
        "readiness_distribution": _readiness_dist(assessments),
    }


def _readiness_dist(assessments):
    dist = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    for a in assessments:
        if a.readiness < 25:
            dist["0-25"] += 1
        elif a.readiness < 50:
            dist["25-50"] += 1
        elif a.readiness < 75:
            dist["50-75"] += 1
        else:
            dist["75-100"] += 1
    return dist


@dash2_router.get("/product-readiness")
def product_readiness(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """各产品线合规就绪度排行。"""
    nodes = db.query(OrgNode).filter(OrgNode.node_type.in_(["product", "version"])).all()
    result = []
    for n in nodes:
        assessments = db.query(Assessment).filter_by(node_id=n.id).all()
        max_r = max((a.readiness for a in assessments), default=0)
        result.append({"id": n.id, "name": n.name, "type": n.node_type,
                       "cra_class": n.cra_class, "readiness": max_r})
    return sorted(result, key=lambda x: x["readiness"], reverse=True)


@dash2_router.get("/alerts")
def get_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """实时告警汇总。"""
    overdue = db.query(VulnReport).filter(VulnReport.status == "overdue").all()
    critical_vulns = db.query(Vulnerability).filter(
        Vulnerability.severity == "critical", Vulnerability.status.in_(["open", "triaged"])
    ).all()
    pending_wfs = db.query(WorkflowInstance).filter(WorkflowInstance.status == "submitted").all()

    alerts = []
    for r in overdue:
        alerts.append({"type": "vuln_overdue", "message": f"通报时限已过期: {r.report_type}", "id": r.id})
    for v in critical_vulns[:5]:
        alerts.append({"type": "critical_vuln", "message": f"严重漏洞: {v.title}", "id": v.id})
    for w in pending_wfs:
        alerts.append({"type": "pending_approval", "message": f"待审批: {w.title}", "id": w.id})

    return {"total": len(alerts), "items": alerts[:20]}
