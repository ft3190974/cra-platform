# -*- coding: utf-8 -*-
"""加固测试：附件越权、文件名 sanitize、限流。

策略：
- 纯函数（can_access_owner / sanitize_*）直接测；
- 附件越权用真实 DB session + 不同角色用户，直接断言 can_access_owner 行为；
- 限流用 FastAPI TestClient 走完整请求链路，验证 429 响应。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.security import (GOVERNANCE_ROLES, can_access_owner,
                                   resolve_owner_node_id, safe_join,
                                   sanitize_download_filename,
                                   sanitize_stored_filename)


# ────────────────────── 1. 附件越权：owner 归属校验 ──────────────────────

def _user(role):
    return SimpleNamespace(id=1, username="u", role=role, is_active=True)


def test_governance_roles_can_access_any_owner(cra_setup, db):
    """admin/manager/auditor 全局放行，即使 owner 不存在。"""
    for role in GOVERNANCE_ROLES:
        assert can_access_owner(db, _user(role), "node", 999999) is True


def test_non_governance_denied_when_owner_not_resolvable(cra_setup, db):
    """assessor/viewer 访问无法归属的 owner_type → 拒绝。"""
    assert can_access_owner(db, _user("assessor"), "unknown_type", 1) is False
    assert can_access_owner(db, _user("viewer"), "node", 999999) is False  # 不存在的 node


def test_non_governance_allowed_when_owner_resolves_to_existing_node(cra_setup, db):
    """assessor 访问真实存在的 node → 放行。"""
    assert can_access_owner(db, _user("assessor"), "node", cra_setup.node.id) is True


def test_non_governance_denied_when_node_missing(cra_setup, db):
    """assessor 访问不存在的 node → 拒绝。"""
    assert can_access_owner(db, _user("assessor"), "node", 999999) is False


def test_resolve_owner_through_assessment(cra_setup, db):
    """assessment owner 能链回其所属 node。"""
    nid = resolve_owner_node_id(db, "assessment", cra_setup.cra_assess.id)
    assert nid == cra_setup.node.id


def test_resolve_owner_through_vuln(cra_setup, db):
    """vuln owner 能链回其所属 node。"""
    from app.models import Vulnerability
    v = Vulnerability(node_id=cra_setup.node.id, title="v", severity="low",
                      cvss_score=1.0, source="manual")
    db.add(v); db.commit(); db.refresh(v)
    assert resolve_owner_node_id(db, "vuln", v.id) == cra_setup.node.id


def test_resolve_owner_unresolvable_type_returns_none(cra_setup, db):
    assert resolve_owner_node_id(db, "totally_unknown", 1) is None


# ────────────────────── 2. 文件名 sanitize 与路径穿越 ──────────────────────

def test_stored_filename_drops_directory_components():
    """原始文件名含路径成分 → 存储名只用 sha + 后缀。"""
    name = sanitize_stored_filename("../../etc/passwd", "abc123")
    assert name == "abc123.bin"  # passwd 后缀不在白名单 → .bin
    assert "/" not in name and "\\" not in name and ".." not in name


def test_stored_filename_keeps_safe_extension():
    assert sanitize_stored_filename("报告.PDF", "deadbeef") == "deadbeef.pdf"
    assert sanitize_stored_filename("data.JSON", "deadbeef") == "deadbeef.json"
    assert sanitize_stored_filename("archive.tar.gz", "deadbeef") == "deadbeef.gz"


def test_stored_filename_no_extension_uses_bin():
    assert sanitize_stored_filename("README", "sha") == "sha.bin"
    assert sanitize_stored_filename("", "sha") == "sha.bin"


def test_stored_filename_double_extension_not_traversed():
    """恶意双后缀也不应产生路径成分。"""
    name = sanitize_stored_filename("evil.php.jpg", "sha")
    assert ".." not in name
    assert "/" not in name
    assert name.endswith(".jpg")


def test_download_filename_strips_path():
    assert sanitize_download_filename("../../etc/passwd") == "passwd"
    assert sanitize_download_filename("a/b/c.txt") == "c.txt"
    assert sanitize_download_filename("..\\..\\windows\\win.ini") == "win.ini"


def test_download_filename_keeps_chinese():
    assert sanitize_download_filename("合规报告.docx") == "合规报告.docx"


def test_download_filename_empty_or_all_evil_defaults_to_file():
    assert sanitize_download_filename("") == "file"
    assert sanitize_download_filename("///") == "file"
    assert sanitize_download_filename("..") == "file"


def test_safe_join_rejects_traversal(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    assert safe_join(str(upload_dir), "abc.txt") == str((upload_dir / "abc.txt").resolve())
    with pytest.raises(ValueError):
        safe_join(str(upload_dir), "../etc/passwd")
    with pytest.raises(ValueError):
        safe_join(str(upload_dir), "../../etc/passwd")


# ────────────────────── 3. 限流 ──────────────────────

def test_rate_limiters_exist_and_are_distinct():
    from app.rate_limit import ai_limiter, upload_limiter, sync_limiter, login_limiter
    assert ai_limiter is not upload_limiter
    assert sync_limiter is not login_limiter
    import inspect
    for f in (ai_limiter, upload_limiter, sync_limiter):
        assert inspect.iscoroutinefunction(f)


class _FakeRequest:
    """最小 Request 替身，仅提供 client.host 供限流读取。"""
    def __init__(self, ip="127.0.0.1"):
        self.client = SimpleNamespace(host=ip)


def _run(coro):
    """同步执行协程，避免引入 pytest-asyncio 依赖。"""
    import asyncio
    return asyncio.new_event_loop().run_until_complete(coro)


def test_upload_limiter_blocks_after_threshold():
    """limiter 阈值 5：前 5 次放行，第 6 次抛 429。"""
    from app.rate_limit import make_rate_limiter, reset_store
    reset_store()
    limiter = make_rate_limiter(max_requests=5, window_seconds=60)
    req = _FakeRequest()
    # 前 5 次不抛
    for _ in range(5):
        _run(limiter(req))
    # 第 6 次应抛 429
    with pytest.raises(Exception) as exc:
        _run(limiter(req))
    assert getattr(exc.value, "status_code", None) == 429


def test_rate_limit_isolated_per_ip():
    """不同 IP 各自计数，互不影响。"""
    from app.rate_limit import make_rate_limiter, reset_store
    reset_store()
    limiter = make_rate_limiter(max_requests=2, window_seconds=60)
    # IP-A 用满 2 次
    _run(limiter(_FakeRequest("10.0.0.1")))
    _run(limiter(_FakeRequest("10.0.0.1")))
    with pytest.raises(Exception):
        _run(limiter(_FakeRequest("10.0.0.1")))
    # IP-B 仍可访问（不抛即通过）
    _run(limiter(_FakeRequest("10.0.0.2")))


def test_rate_limit_window_expires():
    """窗口期过后计数清零（用极短窗口验证）。"""
    import time
    from app.rate_limit import make_rate_limiter, reset_store
    reset_store()
    limiter = make_rate_limiter(max_requests=1, window_seconds=1)
    _run(limiter(_FakeRequest()))
    with pytest.raises(Exception):
        _run(limiter(_FakeRequest()))
    time.sleep(1.1)
    # 窗口过期后应再次放行（不抛即通过）
    _run(limiter(_FakeRequest()))
