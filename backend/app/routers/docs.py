"""文档模板、文档生成/导出、附件上传/下载路由。"""
import hashlib
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_role
from ..config import settings
from ..database import get_db
from ..models import Attachment, DocTemplate, Document, OrgNode, User, now
from ..rate_limit import upload_limiter
from ..schemas import DocUpdate, DocumentGenerate
from ..services.documents import (generate_sbom, html_to_docx_bytes, render_template)
from ..services.security import (can_access_owner, safe_join, sanitize_download_filename,
                                 sanitize_stored_filename)

templates_router = APIRouter(prefix="/api/templates", tags=["templates"])
docs_router = APIRouter(prefix="/api/documents", tags=["documents"])
attach_router = APIRouter(prefix="/api/attachments", tags=["attachments"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB


# ── 模板 ──
@templates_router.get("")
def list_templates(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [{"id": t.id, "code": t.code, "name": t.name, "doc_type": t.doc_type,
             "cra_ref": t.cra_ref, "stage": t.stage, "fields": t.fields}
            for t in db.query(DocTemplate).all()]


@templates_router.get("/{tid}")
def get_template(tid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    t = db.get(DocTemplate, tid)
    if not t:
        raise HTTPException(404, "未找到模板")
    return {"id": t.id, "code": t.code, "name": t.name, "doc_type": t.doc_type,
            "cra_ref": t.cra_ref, "body_html": t.body_html, "fields": t.fields,
            "demo_html": t.demo_html or ""}


@templates_router.get("/{tid}/demo")
def get_template_demo(tid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """获取文档模板的最佳实践示例。"""
    t = db.get(DocTemplate, tid)
    if not t:
        raise HTTPException(404, "未找到模板")
    return {"demo_html": t.demo_html or "", "name": t.name}

@templates_router.get("/{tid}/demo/export")
def export_template_demo(tid: int, fmt: str = "docx", db: Session = Depends(get_db)):
    """下载模板示例为 Word 文档"""
    from fastapi.responses import Response
    t = db.get(DocTemplate, tid)
    if not t or not t.demo_html:
        raise HTTPException(404, "该模板暂无示例")
    data = html_to_docx_bytes(t.name, t.demo_html)
    fname = (t.name or "template") + ".docx"
    safe_name = fname.encode("ascii", "ignore").decode() or "document.docx"
    return Response(content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"})


@templates_router.post("/upload")
async def upload_template(
    name: str = Form(...), cra_ref: str = Form(""), placeholders: str = Form(""),
    file: UploadFile = File(...), db: Session = Depends(get_db),
    user: User = Depends(require_role("manager"))):
    """上传模板文件(.docx/.html)，自动提取占位符"""
    import os as _os
    upload_dir = _os.path.join(_os.path.dirname(__file__), "..", "..", "uploads", "templates")
    _os.makedirs(upload_dir, exist_ok=True)
    # Save file
    safe_name = f"{file.filename}"
    file_path = _os.path.join(upload_dir, safe_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    # Generate code from name
    code = "DOC-" + name[:20].upper().replace(" ", "_").replace("/", "_")
    # Extract placeholders
    ph_list = [p.strip() for p in placeholders.replace("{{", "").replace("}}", "").split(",") if p.strip()]
    if not ph_list:
        ph_list = ["product_name", "version", "company_name", "date"]
    # Create template record
    t = DocTemplate(code=code, name=name, doc_type="uploaded", cra_ref=cra_ref, stage="",
                    body_html="", fields=[{"key": p, "label": p} for p in ph_list],
                    template_file=safe_name)
    db.add(t); db.commit(); db.refresh(t)
    return {"id": t.id, "name": t.name, "code": t.code, "template_file": safe_name}


# ── 文档 ──
@docs_router.get("")
def list_docs(node_id: int | None = None, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    q = db.query(Document)
    if node_id is not None:
        q = q.filter(Document.node_id == node_id)
    return [{"id": d.id, "node_id": d.node_id, "title": d.title, "doc_type": d.doc_type,
             "status": d.status, "version": d.version, "created_by": d.created_by,
             "created_at": d.created_at} for d in q.order_by(Document.id.desc()).all()]


@docs_router.post("/generate")
def generate_doc(payload: DocumentGenerate, db: Session = Depends(get_db),
                 user: User = Depends(require_role("assessor"))):
    t = db.get(DocTemplate, payload.template_id)
    node = db.get(OrgNode, payload.node_id)
    if not t or not node:
        raise HTTPException(400, "模板或节点不存在")
    fields = dict(payload.fields)
    fields.setdefault("product_name", node.name)
    fields.setdefault("product_class", node.cra_class)
    fields.setdefault("date", now().strftime("%Y-%m-%d"))
    fields.setdefault("manufacturer", fields.get("manufacturer", "（制造商名称）"))
    if t.doc_type == "sbom":
        sbom = generate_sbom(db, node.id)
        content = "<pre>" + json.dumps(sbom, ensure_ascii=False, indent=2) + "</pre>"
    else:
        content = render_template(t.body_html, fields)
    d = Document(node_id=node.id, template_id=t.id, title=payload.title or t.name,
                 doc_type=t.doc_type, content_html=content, fields=fields,
                 created_by=user.username, status="draft")
    db.add(d); db.commit(); db.refresh(d)
    log_action(db, user, "CREATE", "document", d.id, {"doc_type": d.doc_type})
    return {"id": d.id, "content_html": content}


@docs_router.get("/{did}")
def get_doc(did: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    d = db.get(Document, did)
    if not d:
        raise HTTPException(404, "未找到文档")
    return {"id": d.id, "node_id": d.node_id, "title": d.title, "doc_type": d.doc_type,
            "status": d.status, "content_html": d.content_html, "fields": d.fields,
            "version": d.version}


@docs_router.put("/{did}")
def update_doc(did: int, payload: DocUpdate, db: Session = Depends(get_db),
               user: User = Depends(require_role("assessor"))):
    d = db.get(Document, did)
    if not d:
        raise HTTPException(404, "未找到文档")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    log_action(db, user, "UPDATE", "document", did, {})
    return {"ok": True}


@docs_router.get("/{did}/export")
def export_doc(did: int, fmt: str = "docx", db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    d = db.get(Document, did)
    if not d:
        raise HTTPException(404, "未找到文档")
    log_action(db, user, "EXPORT", "document", did, {"fmt": fmt})
    if fmt == "json":
        return Response(json.dumps({"title": d.title, "content_html": d.content_html,
                                    "fields": d.fields}, ensure_ascii=False, indent=2),
                        media_type="application/json")
    data = html_to_docx_bytes(d.title, d.content_html)
    d.status = "exported"; db.commit()
    fname = f"{d.title}.docx".encode("ascii", "ignore").decode() or "document.docx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=document.docx; filename*=UTF-8''{fname}"})


# ── 附件 ──
@attach_router.get("")
def list_attachments(owner_type: str, owner_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    if not can_access_owner(db, user, owner_type, owner_id):
        raise HTTPException(403, "无权访问该对象的附件")
    items = db.query(Attachment).filter(Attachment.owner_type == owner_type,
                                        Attachment.owner_id == owner_id).all()
    return [{"id": a.id, "filename": a.filename, "size": a.size, "mime": a.mime,
             "doc_category": a.doc_category, "uploaded_by": a.uploaded_by,
             "created_at": a.created_at} for a in items]


@attach_router.post("")
def upload_attachment(owner_type: str = Form(...), owner_id: int = Form(...),
                      doc_category: str = Form(""), file: UploadFile = File(...),
                      db: Session = Depends(get_db),
                      user: User = Depends(require_role("assessor")),
                      _rate: None = Depends(upload_limiter)):
    if not can_access_owner(db, user, owner_type, owner_id):
        raise HTTPException(403, "无权向该对象上传附件")
    os.makedirs(settings.upload_dir, exist_ok=True)
    # 流式读取 + 大小限制
    chunks = []
    total = 0
    while True:
        chunk = file.file.read(8192)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "文件过大，单文件上限 50MB")
        chunks.append(chunk)
    raw = b"".join(chunks)
    sha = hashlib.sha256(raw).hexdigest()
    # 存储文件名：纯 sha + 白名单后缀，丢弃用户原始路径，防穿越
    safe_name = sanitize_stored_filename(file.filename or "upload", sha[:32])
    path = safe_join(settings.upload_dir, safe_name)
    with open(path, "wb") as f:
        f.write(raw)
    a = Attachment(owner_type=owner_type, owner_id=owner_id,
                   filename=sanitize_download_filename(file.filename or "upload"),
                   stored_path=path, mime=file.content_type or "", size=len(raw), sha256=sha,
                   doc_category=doc_category, uploaded_by=user.username)
    db.add(a); db.commit(); db.refresh(a)
    log_action(db, user, "CREATE", "attachment", a.id,
               {"owner": f"{owner_type}:{owner_id}", "file": a.filename})
    return {"id": a.id, "filename": a.filename, "size": a.size}


@attach_router.get("/{aid}/download")
def download_attachment(aid: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    a = db.get(Attachment, aid)
    if not a:
        raise HTTPException(404, "文件不存在")
    if not can_access_owner(db, user, a.owner_type, a.owner_id):
        raise HTTPException(403, "无权下载该附件")
    # 二次校验：stored_path 必须仍在 upload_dir 之内，防篡改
    try:
        expected = safe_join(settings.upload_dir, os.path.basename(a.stored_path))
    except ValueError:
        raise HTTPException(403, "附件路径不安全")
    if not os.path.exists(expected):
        raise HTTPException(404, "文件不存在")
    with open(expected, "rb") as f:
        data = f.read()
    log_action(db, user, "EXPORT", "attachment", aid, {})
    fname = sanitize_download_filename(a.filename)
    return StreamingResponse(
        iter([data]), media_type=a.mime or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"file\"; filename*=UTF-8''{fname}"})


@attach_router.delete("/{aid}")
def delete_attachment(aid: int, db: Session = Depends(get_db),
                      user: User = Depends(require_role("assessor"))):
    a = db.get(Attachment, aid)
    if not a:
        raise HTTPException(404, "未找到")
    if not can_access_owner(db, user, a.owner_type, a.owner_id):
        raise HTTPException(403, "无权删除该附件")
    try:
        # 删除前同样校验路径未越界
        target = safe_join(settings.upload_dir, os.path.basename(a.stored_path))
        if os.path.exists(target):
            os.remove(target)
    except (OSError, ValueError):
        pass
    db.delete(a); db.commit()
    log_action(db, user, "DELETE", "attachment", aid, {})
    return {"ok": True}
