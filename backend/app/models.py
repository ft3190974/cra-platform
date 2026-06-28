"""全部 ORM 模型 — CRA 合规平台（华南Test）。

对象层级：BusinessUnit → Project → Product → Version（OrgNode 自引用）。
GRC 治理层 + CRA 法定流程对象一并建模。
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ───────────────────────── 用户 / 审计 ─────────────────────────
class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), default="")
    full_name: Mapped[str] = mapped_column(String(64), default="")
    hashed_password: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="viewer")  # admin/manager/assessor/auditor/viewer
    dept_id: Mapped[int | None] = mapped_column(ForeignKey("org_nodes.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(16))  # CREATE/UPDATE/DELETE/LOGIN/EXPORT/SYNC
    resource_type: Mapped[str] = mapped_column(String(48))
    resource_id: Mapped[str] = mapped_column(String(48), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str] = mapped_column(String(64), default="")


# ───────────────────────── 合规对象树 ─────────────────────────
class OrgNode(Base, TimestampMixin):
    __tablename__ = "org_nodes"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("org_nodes.id"), nullable=True, index=True)
    node_type: Mapped[str] = mapped_column(String(24))  # business_unit/project/product/version
    name: Mapped[str] = mapped_column(String(128))
    code: Mapped[str] = mapped_column(String(64), default="")
    cra_class: Mapped[str] = mapped_column(String(24), default="default")  # default/important_1/important_2/critical
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    children: Mapped[list["OrgNode"]] = relationship(
        backref="parent", remote_side=[id], uselist=True,
        primaryjoin="OrgNode.parent_id==OrgNode.id", viewonly=True,
    )


class VersionIteration(Base, TimestampMixin):
    __tablename__ = "version_iterations"
    id: Mapped[int] = mapped_column(primary_key=True)
    version_node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    iteration_no: Mapped[str] = mapped_column(String(32))
    change_type: Mapped[str] = mapped_column(String(16), default="feature")  # feature/security/bugfix
    summary: Mapped[str] = mapped_column(String(256), default="")
    changelog: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_by: Mapped[str] = mapped_column(String(64), default="")


class SupportLifecycle(Base, TimestampMixin):
    __tablename__ = "support_lifecycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    support_start: Mapped[str] = mapped_column(String(32), default="")
    support_end: Mapped[str] = mapped_column(String(32), default="")
    eol_date: Mapped[str] = mapped_column(String(32), default="")
    security_update_commitment: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="active")


# ───────────────────────── 评估引擎 / 控制库 ─────────────────────────
class ControlLibrary(Base, TimestampMixin):
    __tablename__ = "control_libraries"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(48), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    regulation: Mapped[str] = mapped_column(String(64), default="CRA")
    framework_type: Mapped[str] = mapped_column(String(16), default="cra")  # cra/samm
    version: Mapped[str] = mapped_column(String(24), default="1.0")
    description: Mapped[str] = mapped_column(Text, default="")


class ControlDomain(Base):
    __tablename__ = "control_domains"
    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey("control_libraries.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128))
    samm_function: Mapped[str] = mapped_column(String(48), default="")  # 治理/设计/实施/验证/运维
    order: Mapped[int] = mapped_column(Integer, default=0)


class ControlItem(Base):
    __tablename__ = "control_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("control_domains.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(256))
    question: Mapped[str] = mapped_column(Text)
    cra_ref: Mapped[str] = mapped_column(String(128), default="")
    guidance: Mapped[str] = mapped_column(Text, default="")
    max_level: Mapped[int] = mapped_column(Integer, default=5)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    # 整改建议（知识库驱动）：按等级阈值给差距/建议/推荐工具
    remediation: Mapped[list] = mapped_column(JSON, default=list)
    order: Mapped[int] = mapped_column(Integer, default=0)


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    library_id: Mapped[int] = mapped_column(ForeignKey("control_libraries.id"))
    title: Mapped[str] = mapped_column(String(128), default="CRA 合规评估")
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft/submitted/approved
    score: Mapped[float] = mapped_column(Float, default=0.0)
    readiness: Mapped[float] = mapped_column(Float, default=0.0)  # 合规就绪度 %
    created_by: Mapped[str] = mapped_column(String(64), default="")


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("control_items.id"))
    level: Mapped[int] = mapped_column(Integer, default=0)
    evidence_text: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")


# ───────────────────────── 风险登记册 ─────────────────────────
class Risk(Base, TimestampMixin):
    __tablename__ = "risks"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(48), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    inherent_score: Mapped[int] = mapped_column(Integer, default=0)   # 1-25
    residual_score: Mapped[int] = mapped_column(Integer, default=0)
    treatment: Mapped[str] = mapped_column(String(16), default="mitigate")  # accept/mitigate/transfer/avoid
    owner: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    linked_vuln_ids: Mapped[list] = mapped_column(JSON, default=list)


# ───────────────────────── 漏洞管理 + 通报 ─────────────────────────
class Vulnerability(Base, TimestampMixin):
    __tablename__ = "vulnerabilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual/sast/sca/bat/fuzz/import/public
    cve_id: Mapped[str] = mapped_column(String(32), default="")
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # critical/high/medium/low
    cvss_score: Mapped[float] = mapped_column(Float, default=0.0)
    cwe: Mapped[str] = mapped_column(String(32), default="")
    component: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open/triaged/fixing/fixed/disclosed/reported
    exploited: Mapped[bool] = mapped_column(Boolean, default=False)
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VulnReport(Base, TimestampMixin):
    __tablename__ = "vuln_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    vuln_id: Mapped[int] = mapped_column(ForeignKey("vulnerabilities.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(16))  # early_24h/notify_72h/final_14d
    target: Mapped[str] = mapped_column(String(16), default="ENISA_SRP")  # ENISA_SRP/CSIRT/AR
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/sent/overdue
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)


# ───────────────────────── 文档 / 模板 / 附件 / 政策 ─────────────────────────
class DocTemplate(Base, TimestampMixin):
    __tablename__ = "doc_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(48), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    doc_type: Mapped[str] = mapped_column(String(32))
    cra_ref: Mapped[str] = mapped_column(String(128), default="")
    stage: Mapped[str] = mapped_column(String(48), default="")
    body_html: Mapped[str] = mapped_column(Text, default="")
    fields: Mapped[list] = mapped_column(JSON, default=list)  # [{key,label,default}]


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("doc_templates.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    doc_type: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft/review/approved/exported
    content_html: Mapped[str] = mapped_column(Text, default="")
    fields: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[str] = mapped_column(String(24), default="1.0")
    created_by: Mapped[str] = mapped_column(String(64), default="")


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(32), index=True)  # node/assessment/vuln/document/...
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    filename: Mapped[str] = mapped_column(String(256))
    stored_path: Mapped[str] = mapped_column(String(512))
    mime: Mapped[str] = mapped_column(String(128), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    doc_category: Mapped[str] = mapped_column(String(48), default="")
    uploaded_by: Mapped[str] = mapped_column(String(64), default="")


class Policy(Base, TimestampMixin):
    __tablename__ = "policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(48), default="")
    title: Mapped[str] = mapped_column(String(128))
    policy_type: Mapped[str] = mapped_column(String(24), default="security")  # security/cvd/support/update
    body_html: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(24), default="1.0")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    owner: Mapped[str] = mapped_column(String(64), default="")


# ───────────────────────── 任务 / 通知 / CAPA ─────────────────────────
class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("org_nodes.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    task_type: Mapped[str] = mapped_column(String(32), default="general")
    assignee: Mapped[str] = mapped_column(String(64), default="")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open/in_progress/done
    source_type: Mapped[str] = mapped_column(String(32), default="")
    source_id: Mapped[str] = mapped_column(String(32), default="")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), default="info")
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(256), default="")
    severity: Mapped[str] = mapped_column(String(16), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class CAPA(Base, TimestampMixin):
    __tablename__ = "capas"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("org_nodes.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(24), default="assessment")
    finding: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text, default="")
    corrective_action: Mapped[str] = mapped_column(Text, default="")
    preventive_action: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(64), default="")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")
    verified_by: Mapped[str] = mapped_column(String(64), default="")


# ───────────────────────── 供应商 / 组件 ─────────────────────────
class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    contact: Mapped[str] = mapped_column(String(128), default="")
    type: Mapped[str] = mapped_column(String(24), default="commercial")  # oss_steward/commercial
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    note: Mapped[str] = mapped_column(Text, default="")


class Component(Base, TimestampMixin):
    __tablename__ = "components"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(48), default="")
    purl: Mapped[str] = mapped_column(String(256), default="")
    license: Mapped[str] = mapped_column(String(64), default="")
    supplier: Mapped[str] = mapped_column(String(128), default="")
    origin: Mapped[str] = mapped_column(String(16), default="oss")  # oss/commercial
    known_vuln_count: Mapped[int] = mapped_column(Integer, default=0)


# ───────────────────────── CRA 法定流程对象 ─────────────────────────
class CraClassification(Base, TimestampMixin):
    __tablename__ = "cra_classifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    product_class: Mapped[str] = mapped_column(String(24), default="default")
    rationale: Mapped[str] = mapped_column(Text, default="")
    conformity_module: Mapped[str] = mapped_column(String(16), default="A")  # A / B+C / H
    notified_body_required: Mapped[bool] = mapped_column(Boolean, default=False)
    determined_by: Mapped[str] = mapped_column(String(64), default="")


class ConformityAssessment(Base, TimestampMixin):
    __tablename__ = "conformity_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    module: Mapped[str] = mapped_column(String(16), default="A")
    status: Mapped[str] = mapped_column(String(16), default="not_started")
    notified_body: Mapped[str] = mapped_column(String(128), default="")
    certificate_ref: Mapped[str] = mapped_column(String(128), default="")


class DeclarationOfConformity(Base, TimestampMixin):
    __tablename__ = "declarations_of_conformity"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    doc_number: Mapped[str] = mapped_column(String(64), default="")
    signed_by: Mapped[str] = mapped_column(String(64), default="")
    signed_at: Mapped[str] = mapped_column(String(32), default="")
    retention_until: Mapped[str] = mapped_column(String(32), default="")
    ce_marking: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="draft")


# ───────────────────────── 外部集成 ─────────────────────────
class Integration(Base, TimestampMixin):
    __tablename__ = "integrations"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("org_nodes.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(24))  # public_disclosure/sast/sca/bat/fuzz
    name: Mapped[str] = mapped_column(String(128))
    endpoint: Mapped[str] = mapped_column(String(256), default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationLog(Base, TimestampMixin):
    __tablename__ = "integration_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int] = mapped_column(ForeignKey("integrations.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    summary: Mapped[str] = mapped_column(String(256), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


# ═══════════════════ 工作流审批引擎 ═══════════════════
class WorkflowInstance(Base, TimestampMixin):
    __tablename__ = "workflow_instances"
    id: Mapped[int] = mapped_column(primary_key=True)
    ref_type: Mapped[str] = mapped_column(String(32), index=True)  # assessment/document/policy/remediation
    ref_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft/submitted/approved/rejected
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[list] = mapped_column(JSON, default=list)  # [{order,role,assignee,status,comment}]
    submitted_by: Mapped[str] = mapped_column(String(64), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ═══════════════════ 供应商合规门户 ═══════════════════
class SupplierAccess(Base, TimestampMixin):
    __tablename__ = "supplier_accesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SupplierSubmission(Base, TimestampMixin):
    __tablename__ = "supplier_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    access_id: Mapped[int] = mapped_column(ForeignKey("supplier_accesses.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    form_type: Mapped[str] = mapped_column(String(32))  # self_assessment/sbom/evidence
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="submitted")  # submitted/reviewed/approved/rejected
    reviewed_by: Mapped[str] = mapped_column(String(64), default="")
    review_note: Mapped[str] = mapped_column(Text, default="")


# ═══════════════════ SBOM 管理 ═══════════════════
class SbomRecord(Base, TimestampMixin):
    __tablename__ = "sbom_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    format: Mapped[str] = mapped_column(String(16), default="CycloneDX")  # CycloneDX/SPDX
    version: Mapped[str] = mapped_column(String(24), default="1.5")
    filename: Mapped[str] = mapped_column(String(256))
    component_count: Mapped[int] = mapped_column(Integer, default=0)
    vuln_matched_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_by: Mapped[str] = mapped_column(String(64), default="")


# ═══════════════════ 多法规框架 ═══════════════════
class RegulationFramework(Base, TimestampMixin):
    __tablename__ = "regulation_frameworks"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # CRA / ISO21434 / GBT44495
    name: Mapped[str] = mapped_column(String(128))
    full_name: Mapped[str] = mapped_column(String(256), default="")
    version: Mapped[str] = mapped_column(String(24), default="1.0")
    domain_count: Mapped[int] = mapped_column(Integer, default=0)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ═══════════════════ AI 分析 ═══════════════════
class AiAnalysis(Base, TimestampMixin):
    __tablename__ = "ai_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    analysis_type: Mapped[str] = mapped_column(String(32))  # gap_assessment/vuln_priority/license_risk/remediation
    prompt: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/running/done/error


# ═══════════════════ 通知规则 ═══════════════════
class NotificationRule(Base, TimestampMixin):
    __tablename__ = "notification_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(32))  # vuln_deadline/assessment_due/workflow_remind
    channel: Mapped[str] = mapped_column(String(16), default="in_app")  # in_app/email/feishu
    threshold_hours: Mapped[int] = mapped_column(Integer, default=24)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


# ═══════════════════ 许可证扫描结果 ═══════════════════
class LicenseScan(Base, TimestampMixin):
    __tablename__ = "license_scans"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("org_nodes.id"), index=True)
    scan_type: Mapped[str] = mapped_column(String(16), default="quick")  # quick/deep/audit
    total_deps: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    conflicts_error: Mapped[int] = mapped_column(Integer, default=0)
    conflicts_warning: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scanned_by: Mapped[str] = mapped_column(String(64), default="")
