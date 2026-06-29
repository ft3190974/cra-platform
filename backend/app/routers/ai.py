"""AI 分析路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..rate_limit import ai_limiter
from ..services.ai_analyzer import run_gap_analysis
from ..models import AiAnalysis, Assessment, AssessmentAnswer, ControlItem, OrgNode, User, ControlLibrary

ai_router = APIRouter(prefix="/api/ai", tags=["AI分析"])


@ai_router.post("/gap-analysis/{assessment_id}")
def trigger_gap_analysis(assessment_id: int, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user),
                         _rate: None = Depends(ai_limiter)):
    result = run_gap_analysis(db, assessment_id)
    return {"id": result.id, "status": result.status, "result": result.result,
            "model": result.model, "tokens_used": result.tokens_used}


@ai_router.get("/analyses")
def list_analyses(node_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """列出指定节点的 AI 分析历史。prompt 含评估数据，不返回。"""
    items = db.query(AiAnalysis).filter(AiAnalysis.node_id == node_id)\
        .order_by(AiAnalysis.created_at.desc()).limit(20).all()
    return [{"id": a.id, "analysis_type": a.analysis_type, "model": a.model,
             "status": a.status, "tokens_used": a.tokens_used,
             "created_at": a.created_at} for a in items]


@ai_router.get("/project-gaps")
def project_gaps(db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """项目级差距分析汇总：每个产品/项目节点的最新评估状态 + 差距项数 + 是否有分析报告。

    返回卡片列表，前端据此渲染项目网格：
    - 未评估：显示"暂无评估"
    - 已评估未分析：显示分数 + "生成差距分析"按钮
    - 已有分析：显示报告摘要 + "查看"/"重新分析"
    """
    # 取所有产品/项目节点
    nodes = db.query(OrgNode).filter(OrgNode.node_type.in_(["product", "project"]))\
        .order_by(OrgNode.id).all()
    out = []
    for node in nodes:
        # 最新 CRA 评估
        cra_lib = db.query(ControlLibrary).filter(ControlLibrary.framework_type == "cra").first()
        latest = None
        if cra_lib:
            latest = db.query(Assessment).filter(
                Assessment.node_id == node.id,
                Assessment.library_id == cra_lib.id
            ).order_by(Assessment.id.desc()).first()

        # 统计差距项（未达满分的答案）
        gap_count = 0
        if latest:
            answers = db.query(AssessmentAnswer).filter(
                AssessmentAnswer.assessment_id == latest.id).all()
            item_ids = [a.item_id for a in answers]
            items_map = {it.id: it for it in db.query(ControlItem).filter(
                ControlItem.id.in_(item_ids)).all()} if item_ids else {}
            for a in answers:
                item = items_map.get(a.item_id)
                if item and a.level < item.max_level:
                    gap_count += 1

        # 最新 AI 分析报告
        latest_ai = db.query(AiAnalysis).filter(
            AiAnalysis.node_id == node.id,
            AiAnalysis.analysis_type == "gap_assessment"
        ).order_by(AiAnalysis.id.desc()).first()

        out.append({
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.node_type,
            "cra_class": node.cra_class,
            "assessment_id": latest.id if latest else None,
            "assessment_status": latest.status if latest else None,
            "score": latest.score if latest else None,
            "readiness": latest.readiness if latest else None,
            "gap_count": gap_count,
            "has_ai_report": latest_ai is not None,
            "ai_report_id": latest_ai.id if latest_ai else None,
            "ai_report_preview": (latest_ai.result[:200] if latest_ai and latest_ai.result else None),
        })
    return out


@ai_router.get("/report/{rid}")
def get_report(rid: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """获取单个 AI 分析报告完整内容。"""
    a = db.get(AiAnalysis, rid)
    if not a:
        from fastapi import HTTPException
        raise HTTPException(404, "报告不存在")
    return {"id": a.id, "result": a.result, "model": a.model,
            "status": a.status, "tokens_used": a.tokens_used,
            "created_at": a.created_at, "node_id": a.node_id}
