"""SBOM 管理路由。"""
import json
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..services.sbom_service import import_sbom, export_sbom
from ..models import SbomRecord, User

sbom_router = APIRouter(prefix="/api/sbom", tags=["SBOM"])


@sbom_router.post("/import")
async def upload_sbom(node_id: int, file: UploadFile = File(...),
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    content = json.loads(await file.read())
    record = import_sbom(db, node_id, content, filename=file.filename, generated_by=user.username)
    return {"id": record.id, "component_count": record.component_count,
            "vuln_matched": record.vuln_matched_count, "format": record.format}


@sbom_router.get("/export/{node_id}")
def download_sbom(node_id: int, fmt: str = "CycloneDX",
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return export_sbom(db, node_id, fmt)


@sbom_router.get("/records")
def list_sbom(node_id: int = None, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    q = db.query(SbomRecord)
    if node_id:
        q = q.filter_by(node_id=node_id)
    return q.order_by(SbomRecord.created_at.desc()).limit(50).all()
