"""SBOM 管理路由。"""
import json, os
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..services.sbom_service import import_sbom, export_sbom
from ..models import SbomRecord, User

sbom_router = APIRouter(prefix="/api/sbom", tags=["SBOM"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "sbom")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@sbom_router.post("/upload")
async def upload_sbom_record(
    file: UploadFile = File(...),
    node_id: int = Form(0),
    project_name: str = Form(""),
    version_name: str = Form(""),
    sbom_tool: str = Form("软安SCA"),
    sbom_time: str = Form(""),
    remark: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)):
    # 保存文件
    safe_name = f"{node_id}_{sbom_tool}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    # 创建记录
    record = SbomRecord(
        node_id=node_id, project_name=project_name, version_name=version_name,
        sbom_tool=sbom_tool, sbom_time=sbom_time, filename=file.filename,
        remark=remark, generated_by=user.username
    )
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "filename": record.filename, "project_name": record.project_name}


@sbom_router.get("/records")
def list_sbom(node_id: int = None, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    q = db.query(SbomRecord)
    if node_id:
        q = q.filter_by(node_id=node_id)
    return q.order_by(SbomRecord.created_at.desc()).limit(50).all()
