"""审计工具：写操作留痕。"""
from sqlalchemy.orm import Session

from .models import AuditLog


def log_action(db: Session, user, action: str, resource_type: str,
               resource_id="", detail=None, ip=""):
    entry = AuditLog(
        user_id=getattr(user, "id", None),
        username=getattr(user, "username", "system"),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        detail=detail or {},
        ip=ip,
    )
    db.add(entry)
    db.commit()
    return entry
