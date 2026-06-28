# -*- coding: utf-8 -*-
"""安全工具：owner 归属解析、文件名 sanitize。

供附件/文档等路由复用，集中维护越权与路径穿越防护逻辑。
"""
from __future__ import annotations

import os
import re
from typing import Any

from sqlalchemy.orm import Session

from ..models import (Assessment, AssessmentAnswer, Document, OrgNode,
                      User, Vulnerability)

# 治理角色：全局可访问，不受 owner 归属限制
GOVERNANCE_ROLES = frozenset({"admin", "manager", "auditor"})

# 允许的附件后缀白名单（小写、不含点）。未命中则统一存为 .bin
SAFE_EXTENSIONS = frozenset({
    "txt", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "png", "jpg", "jpeg", "gif", "webp",
    "json", "xml", "csv", "md", "log", "yml", "yaml",
    "zip", "tar", "gz",
})

def _node_id_of(db: Session, model: Any, oid: int) -> int | None:
    obj = db.get(model, oid)
    return getattr(obj, "node_id", None) if obj else None


def _resolve_answer_node(db: Session, answer_id: int) -> int | None:
    """评估步骤附件：answer → assessment → node。"""
    ans = db.get(AssessmentAnswer, answer_id)
    if not ans:
        return None
    a = db.get(Assessment, ans.assessment_id)
    return a.node_id if a else None


# owner_type → 如何从 owner_id 找到对应 org_node_id 的映射
# 未列出的类型视为「无法归属到组织节点」，非治理角色将被拒绝访问。
# 放在 resolver 函数定义之后，避免前向引用。
_OWNER_NODE_RESOLVERS: dict[str, Any] = {
    "node": lambda db, oid: oid,
    "assessment": lambda db, oid: _node_id_of(db, Assessment, oid),
    "vuln": lambda db, oid: _node_id_of(db, Vulnerability, oid),
    "document": lambda db, oid: _node_id_of(db, Document, oid),
    "assessment_answer": _resolve_answer_node,
}


def resolve_owner_node_id(db: Session, owner_type: str, owner_id: int) -> int | None:
    """把任意 owner 链回 org_node_id。无法归属返回 None。"""
    resolver = _OWNER_NODE_RESOLVERS.get(owner_type)
    if not resolver:
        return None
    try:
        return resolver(db, owner_id)
    except Exception:
        return None


def can_access_owner(db: Session, user: User, owner_type: str, owner_id: int) -> bool:
    """判断用户能否访问指定 owner 的资源。

    - 治理角色（admin/manager/auditor）全局放行；
    - 其他角色要求 owner 能链回一个真实存在的 org_node；
    - 未来可在此扩展「用户 → 可访问节点集合」的细粒度 ACL。
    """
    if user.role in GOVERNANCE_ROLES:
        return True
    node_id = resolve_owner_node_id(db, owner_type, owner_id)
    if node_id is None:
        return False
    return db.get(OrgNode, node_id) is not None


def sanitize_stored_filename(original: str, sha_prefix: str) -> str:
    """生成安全的磁盘存储文件名：<sha前缀>.<白名单后缀>。

    - 完全丢弃用户原始路径，只用后缀；
    - 后缀不在白名单则用 .bin；
    - 结果仅含 [a-z0-9.]，杜绝路径穿越与特殊字符。
    """
    ext = ""
    if "." in original:
        raw_ext = original.rsplit(".", 1)[-1].lower()
        # 只保留字母数字，长度<=8
        cleaned = re.sub(r"[^a-z0-9]", "", raw_ext)[:8]
        ext = cleaned if cleaned in SAFE_EXTENSIONS else ""
    if not ext:
        ext = "bin"
    return f"{sha_prefix}.{ext}"


def sanitize_download_filename(original: str) -> str:
    """生成安全的下载文件名（用于 Content-Disposition）。

    - 剥除目录成分（..  / \\）；
    - 仅保留字母数字、点、下划线、连字符、中文；
    - 空或全非法 → 'file'。
    """
    if not original:
        return "file"
    # 只取 basename，剥除任何路径成分
    base = re.split(r"[\\/]", original)[-1]
    # 保留常见安全字符（含中文 \u4e00-\u9fff）
    cleaned = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", base).strip("._")
    return cleaned or "file"


def safe_join(upload_dir: str, filename: str) -> str:
    """安全拼接上传目录与文件名，确保结果仍在 upload_dir 之内。"""
    base = os.path.abspath(upload_dir)
    target = os.path.abspath(os.path.join(base, filename))
    if not target.startswith(base + os.sep) and target != base:
        raise ValueError("不安全的文件路径")
    return target
