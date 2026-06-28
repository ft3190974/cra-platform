"""工作流审批路由。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..services.workflow import create_workflow, submit_workflow, approve_step, reject_step
from ..models import WorkflowInstance, User

wf_router = APIRouter(prefix="/api/workflow", tags=["工作流"])

class WFCreate(BaseModel):
    ref_type: str
    ref_id: int
    title: str
    steps: list = None

class WFStep(BaseModel):
    comment: str = ""


@wf_router.post("/create")
def api_create_wf(body: WFCreate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    wf = create_workflow(db, body.ref_type, body.ref_id, body.title, user.username, body.steps)
    return wf


@wf_router.post("/{wf_id}/submit")
def api_submit_wf(wf_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    return submit_workflow(db, wf_id)


@wf_router.post("/{wf_id}/approve")
def api_approve_step(wf_id: int, body: WFStep, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    return approve_step(db, wf_id, user.username, body.comment)


@wf_router.post("/{wf_id}/reject")
def api_reject_step(wf_id: int, body: WFStep, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    return reject_step(db, wf_id, user.username, body.comment)


@wf_router.get("/list")
def list_workflows(status: str = None, ref_type: str = None,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(WorkflowInstance)
    if status:
        q = q.filter_by(status=status)
    if ref_type:
        q = q.filter_by(ref_type=ref_type)
    return q.order_by(WorkflowInstance.created_at.desc()).limit(50).all()
