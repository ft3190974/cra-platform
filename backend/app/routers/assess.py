"""评估引擎路由：CRA/SAMM 评估、控制库、整改建议、雷达图。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_role
from ..database import get_db
from ..models import (Assessment, AssessmentAnswer, ControlDomain, ControlItem,
                     ControlLibrary, Task, User)
from ..schemas import AnswerIn, AssessmentCreate
from ..services.documents import build_remediation_report
from ..services.scoring import compute_score, samm_avg_to_cra_level
from pydantic import BaseModel

assess_router = APIRouter(prefix="/api/assessments", tags=["assessments"])
controls_router = APIRouter(prefix="/api/controls", tags=["controls"])


@controls_router.get("/libraries")
def list_libraries(framework_type: str | None = None, db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    q = db.query(ControlLibrary)
    if framework_type:
        q = q.filter(ControlLibrary.framework_type == framework_type)
    return [{"id": l.id, "code": l.code, "name": l.name, "regulation": l.regulation,
             "framework_type": l.framework_type, "version": l.version} for l in q.all()]


@controls_router.get("/libraries/{lib_id}/items")
def library_items(lib_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    domains = db.query(ControlDomain).filter(ControlDomain.library_id == lib_id).order_by(ControlDomain.order).all()
    out = []
    for d in domains:
        items = db.query(ControlItem).filter(ControlItem.domain_id == d.id).order_by(ControlItem.order).all()
        out.append({"domain": {"id": d.id, "code": d.code, "name": d.name, "samm_function": d.samm_function},
                    "items": [{"id": i.id, "code": i.code, "title": i.title, "question": i.question,
                               "cra_ref": i.cra_ref, "guidance": i.guidance, "max_level": i.max_level,
                               "weight": i.weight} for i in items]})
    return out


def _recompute(db: Session, assessment: Assessment):
    """重算评估分与就绪度 — 批量预加载 ControlItem 避免 N+1。"""
    answers = db.query(AssessmentAnswer).filter(AssessmentAnswer.assessment_id == assessment.id).all()
    if not answers:
        assessment.score = 0
        assessment.readiness = 0
        db.commit()
        return
    # 批量加载所有相关 ControlItem
    item_ids = [a.item_id for a in answers]
    items_map = {it.id: it for it in db.query(ControlItem).filter(ControlItem.id.in_(item_ids)).all()}
    # 纯函数计算，DB 只负责落库
    assessment.score, assessment.readiness = compute_score(answers, items_map)
    db.commit()


# 预加载库缓存（避免每个评估一条查询）
def _lib_cache(db: Session):
    return {l.id: l for l in db.query(ControlLibrary).all()}


@assess_router.get("")
def list_assessments(node_id: int | None = None, framework_type: str | None = None,
                     db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = db.query(Assessment)
    if node_id is not None:
        q = q.filter(Assessment.node_id == node_id)
    rows = q.order_by(Assessment.id.desc()).all()
    libs = _lib_cache(db)  # 一次查询代替 N 次
    out = []
    for a in rows:
        lib = libs.get(a.library_id)
        ft = lib.framework_type if lib else "cra"
        if framework_type and ft != framework_type:
            continue
        out.append({"id": a.id, "node_id": a.node_id, "title": a.title, "status": a.status,
                    "score": a.score, "readiness": a.readiness, "created_by": a.created_by,
                    "library_id": a.library_id, "framework_type": ft, "created_at": a.created_at})
    return out


@assess_router.post("")
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_role("assessor"))):
    a = Assessment(node_id=payload.node_id, library_id=payload.library_id,
                   title=payload.title, created_by=user.username)
    db.add(a); db.commit(); db.refresh(a)
    log_action(db, user, "CREATE", "assessment", a.id, {"node_id": a.node_id})
    return {"id": a.id}


@assess_router.get("/{aid}")
def get_assessment(aid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    a = db.get(Assessment, aid)
    if not a:
        raise HTTPException(404, "未找到评估")
    lib = db.get(ControlLibrary, a.library_id)
    answers = {x.item_id: x for x in db.query(AssessmentAnswer).filter(AssessmentAnswer.assessment_id == aid)}
    return {"id": a.id, "node_id": a.node_id, "library_id": a.library_id,
            "framework_type": lib.framework_type if lib else "cra", "title": a.title,
            "status": a.status, "score": a.score, "readiness": a.readiness,
            "answers": {iid: {"answer_id": x.id, "level": x.level,
                              "evidence_text": x.evidence_text, "note": x.note}
                        for iid, x in answers.items()}}


@assess_router.post("/{aid}/answer")
def save_answer(aid: int, payload: AnswerIn, db: Session = Depends(get_db),
                user: User = Depends(require_role("assessor"))):
    a = db.get(Assessment, aid)
    if not a:
        raise HTTPException(404, "未找到评估")
    ans = db.query(AssessmentAnswer).filter(AssessmentAnswer.assessment_id == aid,
                                            AssessmentAnswer.item_id == payload.item_id).first()
    if ans:
        ans.level = payload.level; ans.evidence_text = payload.evidence_text; ans.note = payload.note
    else:
        ans = AssessmentAnswer(assessment_id=aid, **payload.model_dump())
        db.add(ans)
    db.commit(); db.refresh(ans)
    _recompute(db, a)
    return {"ok": True, "score": a.score, "readiness": a.readiness, "answer_id": ans.id}


@assess_router.post("/{aid}/approve")
def approve_assessment(aid: int, db: Session = Depends(get_db),
                       user: User = Depends(require_role("manager"))):
    a = db.get(Assessment, aid)
    if not a:
        raise HTTPException(404, "未找到评估")
    a.status = "approved"; db.commit()
    log_action(db, user, "UPDATE", "assessment", aid, {"action": "approve"})
    return {"ok": True}


@assess_router.post("/{aid}/submit")
def submit_assessment(aid: int, db: Session = Depends(get_db),
                      user: User = Depends(require_role("assessor"))):
    a = db.get(Assessment, aid)
    if not a:
        raise HTTPException(404, "未找到评估")
    a.status = "submitted"; db.commit()
    lib = db.get(ControlLibrary, a.library_id)
    bridged = None
    if lib and lib.framework_type == "samm":
        bridged = _bridge_samm_to_cra(db, a)
    log_action(db, user, "UPDATE", "assessment", aid, {"action": "submit"})
    return {"ok": True, "bridged_to_cra": bridged}


def _bridge_samm_to_cra(db: Session, samm_assess: Assessment):
    """SAMM 评估提交后：把 SAMM 成熟度（0-3）折算为 CRA 0-5 分。"""
    answers = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.assessment_id == samm_assess.id).all()
    if not answers:
        return None
    avg = sum(x.level for x in answers) / len(answers)
    cra_level = samm_avg_to_cra_level(avg)
    cra_lib = db.query(ControlLibrary).filter(ControlLibrary.framework_type == "cra").first()
    if not cra_lib:
        return None
    cra_assess = db.query(Assessment).filter(
        Assessment.node_id == samm_assess.node_id,
        Assessment.library_id == cra_lib.id).order_by(Assessment.id.desc()).first()
    if not cra_assess:
        return None
    bridge_item = db.query(ControlItem).filter(ControlItem.code == "GOV-SAMM").first()
    if not bridge_item:
        return None
    ans = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.assessment_id == cra_assess.id,
        AssessmentAnswer.item_id == bridge_item.id).first()
    note = f"由 SAMM 评估 #{samm_assess.id} 自动折算（SAMM 平均 {avg:.2f}/3 → CRA {cra_level}/5）"
    if ans:
        ans.level = cra_level; ans.note = note
    else:
        db.add(AssessmentAnswer(assessment_id=cra_assess.id, item_id=bridge_item.id,
                                level=cra_level, note=note))
    db.commit()
    _recompute(db, cra_assess)
    return {"cra_assessment_id": cra_assess.id, "samm_avg": round(avg, 2), "cra_level": cra_level}


@assess_router.get("/{aid}/remediation")
def remediation(aid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    a = db.get(Assessment, aid)
    if not a:
        raise HTTPException(404, "未找到评估")
    items = build_remediation_report(db, aid)
    # 标注每条建议是否已转成任务（前端据此显示按钮状态）
    existing = {t.source_id: t.id for t in db.query(Task).filter(
        Task.source_type == "remediation",
        Task.source_id.like(f"aid{aid}:%")).all()}
    for it in items:
        key = f"aid{aid}:{it['item_code']}"
        it["task_id"] = existing.get(key)
    return {"assessment_id": aid, "readiness": a.readiness, "score": a.score,
            "items": items}


class RemediationToTaskIn(BaseModel):
    item_code: str
    item_title: str
    advice: str = ""
    recommended_tools: list[str] = []
    priority: str = "medium"  # high/medium/low
    assignee: str = ""
    due_days: int = 30


@assess_router.post("/{aid}/remediation/to-task")
def remediation_to_task(aid: int, body: RemediationToTaskIn,
                        db: Session = Depends(get_db),
                        user: User = Depends(require_role("assessor"))):
    """把一条整改建议转为整改任务（Task），联动 Task 模块。

    - source_type='remediation'，source_id='aid{aid}:{item_code}' 用于去重与追溯；
    - 同一条建议重复转任务返回已有的 task_id，不重复创建；
    - 任务自动关联到评估所属的 org_node。
    """
    a = db.get(Assessment, aid)
    if not a:
        raise HTTPException(404, "未找到评估")
    source_id = f"aid{aid}:{body.item_code}"
    # 去重：已存在则返回
    exist = db.query(Task).filter(Task.source_type == "remediation",
                                  Task.source_id == source_id).first()
    if exist:
        return {"task_id": exist.id, "created": False, "msg": "该建议已转任务"}
    from datetime import timedelta
    from ..models import now
    title = f"[整改]{body.item_code} {body.item_title}"
    desc = body.advice
    if body.recommended_tools:
        desc += f"\n推荐工具：{'、'.join(body.recommended_tools)}"
    t = Task(node_id=a.node_id, title=title, task_type="remediation",
             assignee=body.assignee, priority=body.priority, status="open",
             source_type="remediation", source_id=source_id,
             due_at=now() + timedelta(days=body.due_days))
    db.add(t); db.commit(); db.refresh(t)
    log_action(db, user, "CREATE", "task", t.id,
               {"from": "remediation", "item_code": body.item_code})
    return {"task_id": t.id, "created": True}


@assess_router.get("/{aid}/radar")
def radar(aid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    a = db.get(Assessment, aid)
    if not a:
        raise HTTPException(404, "未找到评估")
    answers = {x.item_id: x.level for x in db.query(AssessmentAnswer).filter(AssessmentAnswer.assessment_id == aid)}
    domains = db.query(ControlDomain).filter(ControlDomain.library_id == a.library_id).order_by(ControlDomain.order).all()
    result = []
    for d in domains:
        items = db.query(ControlItem).filter(ControlItem.domain_id == d.id).all()
        levels = [answers.get(i.id, 0) for i in items]
        avg = round(sum(levels) / len(levels), 2) if levels else 0
        result.append({"domain": d.name, "value": avg, "max": 5})
    return result
