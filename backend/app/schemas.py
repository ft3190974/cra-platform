"""Pydantic schemas — 全量写操作模型（杜绝 dict 裸收，防 SQL 注入/字段污染）。"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── 认证 ──
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    username: str
    email: str = ""
    full_name: str = ""
    role: str
    dept_id: int | None = None
    is_active: bool


class UserCreate(BaseModel):
    username: str
    password: str
    email: str = ""
    full_name: str = ""
    role: str = "viewer"
    dept_id: int | None = None


# ── 对象树 ──
class NodeCreate(BaseModel):
    parent_id: int | None = None
    node_type: str
    name: str
    code: str = ""
    cra_class: str = "default"
    description: str = ""
    meta: dict = {}


class NodeUpdate(BaseModel):
    """仅允许更新名称/编码/分类/描述/meta，防止篡改 node_type/parent_id。"""
    name: str | None = None
    code: str | None = None
    cra_class: str | None = None
    description: str | None = None
    meta: dict | None = None


class NodeOut(ORM):
    id: int
    parent_id: int | None = None
    node_type: str
    name: str
    code: str = ""
    cra_class: str
    description: str = ""
    meta: dict = {}
    created_at: datetime | None = None


# ── 评估 ──
class AnswerIn(BaseModel):
    item_id: int
    level: int = 0
    evidence_text: str = ""
    note: str = ""


class AssessmentCreate(BaseModel):
    node_id: int
    library_id: int
    title: str = "CRA 合规评估"


# ── 漏洞（严格校验，防止字段污染） ──
class VulnCreate(BaseModel):
    node_id: int
    source: str = "manual"
    cve_id: str = ""
    title: str
    description: str = ""
    severity: str = "medium"
    cvss_score: float = 0.0
    cwe: str = ""
    component: str = ""
    exploited: bool = False


class VulnUpdate(BaseModel):
    status: str | None = None
    exploited: bool | None = None
    severity: str | None = None
    cvss_score: float | None = None
    title: str | None = None
    description: str | None = None
    cve_id: str | None = None
    cwe: str | None = None
    component: str | None = None
    fixed_at: datetime | None = None


# ── 风险 ──
class RiskCreate(BaseModel):
    node_id: int
    title: str
    category: str = ""
    description: str = ""
    inherent_score: int = Field(default=0, ge=0, le=25)
    residual_score: int = Field(default=0, ge=0, le=25)
    treatment: str = "mitigate"
    owner: str = ""
    status: str = "open"


# ── 文档 ──
class DocumentGenerate(BaseModel):
    template_id: int
    node_id: int
    title: str = ""
    fields: dict = {}


class DocUpdate(BaseModel):
    title: str | None = None
    content_html: str | None = None
    status: str | None = None
    version: str | None = None


# ── 集成 ──
class IntegrationCreate(BaseModel):
    node_id: int | None = None
    kind: str
    name: str
    endpoint: str = ""
    config: dict = {}
