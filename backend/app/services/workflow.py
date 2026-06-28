"""工作流审批引擎。"""
from sqlalchemy.orm import Session
from ..models import WorkflowInstance, now


def create_workflow(db: Session, ref_type: str, ref_id: int, title: str, submitted_by: str,
                    steps: list = None) -> WorkflowInstance:
    if steps is None:
        steps = [
            {"order": 0, "role": "manager", "assignee": "", "status": "pending", "comment": "", "label": "合规经理审核"},
            {"order": 1, "role": "admin", "assignee": "", "status": "pending", "comment": "", "label": "管理员批准"},
        ]
    wf = WorkflowInstance(ref_type=ref_type, ref_id=ref_id, title=title,
                          submitted_by=submitted_by, steps=steps, status="draft")
    db.add(wf)
    db.commit()
    db.refresh(wf)  # 刷新以填充 id 等自动生成字段，防止序列化时为空
    return wf


def submit_workflow(db: Session, wf_id: int) -> WorkflowInstance:
    wf = db.query(WorkflowInstance).filter_by(id=wf_id).first()
    if not wf:
        raise ValueError("工作流不存在")
    wf.status = "submitted"
    wf.current_step = 0
    if wf.steps:
        wf.steps[0]["status"] = "pending"
    db.commit()
    db.refresh(wf)
    return wf


def approve_step(db: Session, wf_id: int, username: str, comment: str = "") -> WorkflowInstance:
    wf = db.query(WorkflowInstance).filter_by(id=wf_id).first()
    if not wf:
        raise ValueError("工作流不存在")
    steps = list(wf.steps)
    if wf.current_step < len(steps):
        steps[wf.current_step]["status"] = "approved"
        steps[wf.current_step]["assignee"] = username
        steps[wf.current_step]["comment"] = comment
        wf.steps = steps
        wf.current_step += 1
        if wf.current_step >= len(steps):
            wf.status = "approved"
            wf.approved_at = now()
        else:
            steps[wf.current_step]["status"] = "pending"
            wf.steps = steps
    db.commit()
    db.refresh(wf)
    return wf


def reject_step(db: Session, wf_id: int, username: str, comment: str = "") -> WorkflowInstance:
    wf = db.query(WorkflowInstance).filter_by(id=wf_id).first()
    if not wf:
        raise ValueError("工作流不存在")
    steps = list(wf.steps)
    if wf.current_step < len(steps):
        steps[wf.current_step]["status"] = "rejected"
        steps[wf.current_step]["assignee"] = username
        steps[wf.current_step]["comment"] = comment
        wf.steps = steps
    wf.status = "rejected"
    db.commit()
    db.refresh(wf)
    return wf
