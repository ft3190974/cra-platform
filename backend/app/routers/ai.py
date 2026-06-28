"""AI 分析路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..rate_limit import ai_limiter
from ..services.ai_analyzer import run_gap_analysis
from ..models import AiAnalysis, User

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
