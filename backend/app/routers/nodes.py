"""合规对象树路由：事业部→项目→产品→版本 四层结构。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_role
from ..database import get_db
from ..models import Assessment, OrgNode, User, Vulnerability
from ..schemas import NodeCreate, NodeOut, NodeUpdate

nodes_router = APIRouter(prefix="/api/nodes", tags=["nodes"])

_CHILD_TYPE = {"business_unit": "project", "project": "product", "product": "version", "version": None}
_CONFORMITY = {
    "default": {"module": "A", "notified_body": False, "path": "内部控制（自评，Module A）"},
    "important_1": {"module": "A/B+C", "notified_body": False, "path": "可自评或采用协调标准（重要产品 Class I）"},
    "important_2": {"module": "B+C/H", "notified_body": True, "path": "需第三方公告机构（重要产品 Class II）"},
    "critical": {"module": "H + 强制认证", "notified_body": True, "path": "需欧盟网络安全认证（关键产品）"},
}


def _node_dict(n: OrgNode) -> dict:
    return {"id": n.id, "parent_id": n.parent_id, "node_type": n.node_type, "name": n.name,
            "code": n.code, "cra_class": n.cra_class, "description": n.description, "meta": n.meta}


@nodes_router.get("/tree")
def get_tree(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    nodes = db.query(OrgNode).all()
    by_id = {n.id: {**_node_dict(n), "children": []} for n in nodes}
    roots = []
    for n in nodes:
        if n.parent_id and n.parent_id in by_id:
            by_id[n.parent_id]["children"].append(by_id[n.id])
        else:
            roots.append(by_id[n.id])
    return roots


@nodes_router.get("/projects")
def list_projects(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """返回所有项目(project)级别节点及其聚合统计，用于项目详情卡片页。"""
    projects = db.query(OrgNode).filter(OrgNode.node_type == "project").all()
    result = []
    for p in projects:
        assessments = db.query(Assessment).filter(Assessment.node_id == p.id).all()
        vulns = db.query(Vulnerability).filter(Vulnerability.node_id == p.id).all()
        latest = max(assessments, key=lambda a: a.id, default=None)
        # 子节点(产品)的漏洞
        child_ids = [c.id for c in db.query(OrgNode).filter(OrgNode.parent_id == p.id).all()]
        child_vulns = db.query(Vulnerability).filter(Vulnerability.node_id.in_(child_ids)).all() if child_ids else []
        all_vulns = vulns + child_vulns
        result.append({
            "id": p.id, "parent_id": p.parent_id, "name": p.name, "code": p.code,
            "cra_class": p.cra_class, "description": p.description,
            "assessment_count": len(assessments),
            "latest_score": round(latest.score, 1) if latest else None,
            "latest_readiness": round(latest.readiness, 1) if latest else None,
            "vuln_total": len(all_vulns),
            "vuln_open": sum(1 for v in all_vulns if v.status in ("open", "triaged", "fixing")),
            "vuln_critical": sum(1 for v in all_vulns if v.severity == "critical"),
            "child_count": len(child_ids),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return result


@nodes_router.get("/{node_id}/overview")
def node_overview(node_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    node = db.get(OrgNode, node_id)
    if not node:
        raise HTTPException(404, "未找到节点")
    assessments = db.query(Assessment).filter(Assessment.node_id == node_id).all()
    vulns = db.query(Vulnerability).filter(Vulnerability.node_id == node_id).all()
    latest = max(assessments, key=lambda a: a.id, default=None)
    return {
        "node": _node_dict(node),
        "conformity": _CONFORMITY.get(node.cra_class, _CONFORMITY["default"]),
        "assessment_count": len(assessments),
        "latest_score": round(latest.score, 1) if latest else None,
        "latest_readiness": round(latest.readiness, 1) if latest else None,
        "vuln_total": len(vulns),
        "vuln_open": sum(1 for v in vulns if v.status in ("open", "triaged", "fixing")),
        "vuln_critical": sum(1 for v in vulns if v.severity == "critical"),
    }


@nodes_router.post("", response_model=NodeOut)
def create_node(payload: NodeCreate, db: Session = Depends(get_db),
                user: User = Depends(require_role("manager"))):
    if payload.parent_id:
        parent = db.get(OrgNode, payload.parent_id)
        if not parent:
            raise HTTPException(400, "父节点不存在")
        expected = _CHILD_TYPE.get(parent.node_type)
        if expected and payload.node_type != expected:
            raise HTTPException(400, f"{parent.node_type} 的子节点应为 {expected}")
    n = OrgNode(**payload.model_dump())
    db.add(n); db.commit(); db.refresh(n)
    log_action(db, user, "CREATE", "node", n.id, {"name": n.name, "type": n.node_type})
    return n


@nodes_router.put("/{node_id}", response_model=NodeOut)
def update_node(node_id: int, payload: NodeUpdate, db: Session = Depends(get_db),
                user: User = Depends(require_role("manager"))):
    n = db.get(OrgNode, node_id)
    if not n:
        raise HTTPException(404, "未找到节点")
    # 仅更新显式传入的非空字段
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(n, k, v)
    db.commit()
    log_action(db, user, "UPDATE", "node", node_id, {})
    return n


@nodes_router.delete("/{node_id}")
def delete_node(node_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_role("manager"))):
    n = db.get(OrgNode, node_id)
    if not n:
        raise HTTPException(404, "未找到节点")
    if db.query(OrgNode).filter(OrgNode.parent_id == node_id).first():
        raise HTTPException(400, "请先删除子节点")
    db.delete(n); db.commit()
    log_action(db, user, "DELETE", "node", node_id, {})
    return {"ok": True}
