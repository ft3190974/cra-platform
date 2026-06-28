"""路由模块包 — 按业务域拆分，main.py 直接从此导入。"""
from .auth import auth_router, users_router
from .nodes import nodes_router
from .assess import assess_router, controls_router
from .vulns import vulns_router
from .docs import templates_router, docs_router, attach_router
from .misc import integ_router, audit_router, dash_router
from .ai import ai_router
from .sbom_router import sbom_router
from .workflow_router import wf_router
from .supplier_portal import supplier_router
from .license_scan import license_router
from .dashboard_v2 import dash2_router

__all__ = [
    "auth_router", "users_router", "nodes_router",
    "assess_router", "controls_router", "vulns_router",
    "templates_router", "docs_router", "attach_router",
    "integ_router", "audit_router", "dash_router",
    "ai_router", "sbom_router", "wf_router",
    "supplier_router", "license_router", "dash2_router",
]
