"""License Copilot 集成路由。"""
import subprocess, json, os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..models import LicenseScan, User, now

license_router = APIRouter(prefix="/api/license-scan", tags=["许可证扫描"])

LICENSE_COPILOT_DIR = r"C:\Users\常乐\Desktop\license-copilot"


@license_router.post("/scan")
def run_license_scan(node_id: int = None, deep: bool = False,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scan_type = "deep" if deep else "quick"
    try:
        result = subprocess.run(
            ["python", "-c", f"from license_copilot.cli import main; main()",
             "scan", "--json"],
            capture_output=True, text=True, cwd=LICENSE_COPILOT_DIR, timeout=60,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except Exception as e:
        data = {"error": str(e)}

    stats = data.get("stats", {})
    record = LicenseScan(node_id=node_id or 0, scan_type=scan_type,
                         total_deps=stats.get("total_deps", 0),
                         risk_level=data.get("risk_summary", {}).get("overall_risk", "low"),
                         conflicts_error=stats.get("conflicts_error", 0),
                         conflicts_warning=stats.get("conflicts_warning", 0),
                         result_json=data, scanned_by=user.username)
    db.add(record)
    db.commit()
    return {"id": record.id, "risk_level": record.risk_level,
            "total_deps": record.total_deps, "conflicts": record.conflicts_error + record.conflicts_warning,
            "result": data}


@license_router.get("/scans")
def list_scans(node_id: int = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    q = db.query(LicenseScan)
    if node_id:
        q = q.filter_by(node_id=node_id)
    return q.order_by(LicenseScan.created_at.desc()).limit(30).all()
