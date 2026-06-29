"""FastAPI 应用入口 — CRA 合规平台（华南Test）。"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .crud import make_crud_router
from .database import Base, engine
from . import models  # noqa: F401  确保模型注册
from .models import (CAPA, Component, ConformityAssessment, CraClassification,
                     DeclarationOfConformity, Notification, Policy, Risk, Supplier,
                     SupportLifecycle, Task, VersionIteration,
                     LicenseScan, SupplierSubmission, SbomRecord, WorkflowInstance,
                     AiAnalysis, NotificationRule, RegulationFramework)
from .routers import (assess_router, attach_router, audit_router, auth_router,
                      controls_router, dash_router, docs_router, integ_router,
                      nodes_router, templates_router, users_router, vulns_router,
                      ai_router, sbom_router, wf_router, supplier_router,
                      license_router, dash2_router)
from .services.multi_regulation import seed_frameworks
from .services.notifier import init_default_rules

Base.metadata.create_all(bind=engine)

# ── 启动期安全自检：不安全 secret 默认拒绝启动 ──
# 生产必须配置强随机 CRA_SECRET_KEY；测试/本地演示可设 CRA_ALLOW_INSECURE_SECRET=true 放行。
if settings.is_secret_insecure() and not settings.allow_insecure_secret:
    raise RuntimeError(
        "拒绝启动：CRA_SECRET_KEY 为空或命中已知默认占位符。"
        "请设置一个强随机的 CRA_SECRET_KEY（例如 openssl rand -hex 32）。"
        "仅测试/本地演示可设 CRA_ALLOW_INSECURE_SECRET=true 临时放行。"
    )


# ── lifespan：替代已废弃的 on_event('startup') ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化多法规框架等基础数据。"""
    from .database import SessionLocal
    db = SessionLocal()
    try:
        # 轻量迁移：为 vulnerabilities 加列（SQLite 不支持 IF NOT EXISTS，用 inspect 判断）
        from sqlalchemy import inspect, text
        inspector = inspect(db.bind)
        cols = {c["name"] for c in inspector.get_columns("vulnerabilities")}
        for col, ddl in [("first_seen_at", "TEXT"), ("note", "TEXT DEFAULT ''")]:
            if col not in cols:
                db.execute(text(f"ALTER TABLE vulnerabilities ADD COLUMN {col} {ddl}"))
                db.commit()
        # DocTemplate 加 demo_html 列
        doc_cols = {c["name"] for c in inspector.get_columns("doc_templates")}
        if "demo_html" not in doc_cols:
            db.execute(text("ALTER TABLE doc_templates ADD COLUMN demo_html TEXT DEFAULT ''"))
            db.commit()
        seed_frameworks(db)
    finally:
        db.close()
    yield
    # 关闭期无资源需释放，预留扩展位


app = FastAPI(title=settings.app_name, version="2.0.0",
              description="CRA《欧盟网络弹性法案》产品合规平台（华南Test）— 单客户私有部署",
              lifespan=lifespan)

# ── CORS：通配源 + credentials 是危险组合（浏览器规范亦禁止），强制降级 ──
_cors_list = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
_cors_is_wildcard = settings.cors_origins.strip() == "*" or "*" in _cors_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors_is_wildcard else _cors_list,
    # 通配源时必须关 credentials，否则浏览器会拒绝；指定具体源时才允许携带
    allow_credentials=(not _cors_is_wildcard),
    allow_methods=["*"], allow_headers=["*"],
)

MAX_BODY_BYTES = 60 * 1024 * 1024

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "请求体过大，上限 60MB"}, status_code=413)
    return await call_next(request)


# ── 业务路由 ──
for r in (auth_router, users_router, nodes_router, controls_router, assess_router,
          vulns_router, templates_router, docs_router, attach_router, integ_router,
          audit_router, dash_router, ai_router, sbom_router, wf_router,
          supplier_router, license_router, dash2_router):
    app.include_router(r)

# 通用 CRUD 路由
app.include_router(make_crud_router(Risk, "risks"))
app.include_router(make_crud_router(Task, "tasks"))
app.include_router(make_crud_router(Notification, "notifications", write_role="viewer"))
app.include_router(make_crud_router(CAPA, "capa"))
app.include_router(make_crud_router(Component, "components"))
app.include_router(make_crud_router(Supplier, "suppliers"))
app.include_router(make_crud_router(Policy, "policies"))
app.include_router(make_crud_router(VersionIteration, "iterations"))
app.include_router(make_crud_router(SupportLifecycle, "lifecycles"))
app.include_router(make_crud_router(CraClassification, "classifications"))
app.include_router(make_crud_router(ConformityAssessment, "conformity"))
app.include_router(make_crud_router(DeclarationOfConformity, "doc"))
app.include_router(make_crud_router(WorkflowInstance, "workflows"))
app.include_router(make_crud_router(LicenseScan, "license-scans"))
app.include_router(make_crud_router(SupplierSubmission, "supplier-submissions"))
app.include_router(make_crud_router(SbomRecord, "sbom-records"))
app.include_router(make_crud_router(AiAnalysis, "ai-analyses"))
app.include_router(make_crud_router(NotificationRule, "notification-rules"))
app.include_router(make_crud_router(RegulationFramework, "regulation-frameworks"))


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": "2.0.0"}


# 静态托管前端
_frontend = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_frontend):
    @app.get("/")
    def index():
        return FileResponse(os.path.join(_frontend, "index.html"))
    app.mount("/static", StaticFiles(directory=_frontend), name="static")
