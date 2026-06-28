# -*- coding: utf-8 -*-
"""安全修复验证测试。

覆盖：
1. JWT 默认密钥启动自检（不安全 secret 默认拒绝，allow_insecure_secret 放行）；
2. CORS 通配源时 credentials 被强制关闭；
3. 演示账号默认不创建（受 allow_demo_accounts 控制）；
4. CRUD 工厂字段污染防护（只读字段黑名单 + 可写白名单）。

隔离策略：
- 纯函数测试（Settings / _filter_writable）直接 import，无副作用；
- 涉及 app.main 启动校验与 seed 的测试用子进程 + 环境变量隔离，避免污染当前进程的模块状态。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings, INSECURE_DEFAULT_SECRETS
from app.crud import _filter_writable, READONLY_FIELDS

BACKEND_DIR = Path(__file__).resolve().parent.parent

# 子进程默认用内存库，避免多个子进程测试竞争同一个 cra.db 文件锁。
# 各测试可在 env 覆盖（如 seed 测试需持久化时指向临时文件）。
_DEFAULT_ENV = {
    "CRA_DATABASE_URL": "sqlite://",
}


def _run_isolated(code: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """在子进程中执行代码，隔离环境变量，避免污染当前 pytest 进程的模块缓存。"""
    full_env = {**os.environ, "PYTHONPATH": str(BACKEND_DIR), **_DEFAULT_ENV, **(env or {})}
    try:
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=full_env, cwd=str(BACKEND_DIR),
            timeout=20,
        )
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            args=e.cmd, returncode=-1, stdout=e.stdout or "", stderr=f"TIMEOUT after {e.timeout}s\n{e.stderr or ''}",
        )


# ────────────────────── 1. JWT 默认密钥启动自检 ──────────────────────

def test_insecure_default_secrets_are_known():
    """代码内占位符都登记在 INSECURE_DEFAULT_SECRETS。"""
    for placeholder in [
        "change-me-in-production-please-use-a-long-random-string",
        "please-change-to-a-long-random-secret-string",
        "change-me-in-production",
        "",
    ]:
        assert placeholder in INSECURE_DEFAULT_SECRETS


@pytest.mark.parametrize("bad_secret", [
    "change-me-in-production-please-use-a-long-random-string",
    "please-change-to-a-long-random-secret-string",
    "change-me-in-production",
    "",
    "   ",  # 纯空白也应视为不安全
])
def test_is_secret_insecure_detects_defaults(bad_secret):
    assert Settings(secret_key=bad_secret).is_secret_insecure() is True


def test_is_secret_insecure_accepts_strong_secret():
    assert Settings(secret_key="a-very-long-random-secret-0123456789abcdef").is_secret_insecure() is False


def test_main_refuses_to_start_with_default_secret():
    """不安全 secret + 未放行 → 导入 app.main 抛 RuntimeError（子进程验证）。"""
    result = _run_isolated("import app.main", env={
        "CRA_SECRET_KEY": "change-me-in-production",
        "CRA_ALLOW_INSECURE_SECRET": "false",
    })
    assert result.returncode != 0
    assert "CRA_SECRET_KEY" in result.stderr
    assert "拒绝启动" in result.stderr


def test_main_starts_with_strong_secret():
    """强随机 secret → 正常导入。"""
    result = _run_isolated("import app.main; print('OK')", env={
        "CRA_SECRET_KEY": "a-very-long-random-secret-0123456789abcdef-WXYZ",
        "CRA_ALLOW_INSECURE_SECRET": "false",
    })
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_main_starts_with_insecure_secret_when_allowed():
    """不安全 secret + 显式放行 → 可正常导入。"""
    result = _run_isolated("import app.main; print('OK')", env={
        "CRA_SECRET_KEY": "change-me-in-production",
        "CRA_ALLOW_INSECURE_SECRET": "true",
    })
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# ────────────────────── 2. CORS 通配源降级 ──────────────────────

def test_cors_wildcard_forces_credentials_off():
    """CRA_CORS_ORIGINS=* 时 allow_credentials 必须为 False。"""
    code = (
        "import app.main as m\n"
        "cors = next(mw for mw in m.app.user_middleware if mw.cls.__name__=='CORSMiddleware')\n"
        "print('ORIGINS=' + str(cors.kwargs['allow_origins']))\n"
        "print('CRED=' + str(cors.kwargs['allow_credentials']))\n"
    )
    result = _run_isolated(code, env={
        "CRA_CORS_ORIGINS": "*",
        "CRA_ALLOW_INSECURE_SECRET": "true",
    })
    assert result.returncode == 0, result.stderr
    assert "ORIGINS=['*']" in result.stdout
    assert "CRED=False" in result.stdout


def test_cors_specific_origin_keeps_credentials():
    """指定具体源时 allow_credentials 保持 True。"""
    code = (
        "import app.main as m\n"
        "cors = next(mw for mw in m.app.user_middleware if mw.cls.__name__=='CORSMiddleware')\n"
        "print('ORIGINS=' + str(cors.kwargs['allow_origins']))\n"
        "print('CRED=' + str(cors.kwargs['allow_credentials']))\n"
    )
    result = _run_isolated(code, env={
        "CRA_CORS_ORIGINS": "https://example.com,https://app.example.com",
        "CRA_ALLOW_INSECURE_SECRET": "true",
    })
    assert result.returncode == 0, result.stderr
    assert "https://example.com" in result.stdout
    assert "CRED=True" in result.stdout


# ────────────────────── 3. 演示账号开关 ──────────────────────

def test_demo_accounts_not_created_by_default(tmp_path):
    """allow_demo_accounts=False 时 seed 不创建演示账号（用临时 DB 文件隔离）。"""
    db_file = tmp_path / "test_seed.db"
    code = (
        "from app.database import SessionLocal\n"
        "from app.models import User\n"
        "from app.seed import seed\n"
        "seed()\n"
        "s = SessionLocal()\n"
        "admin = s.query(User).filter(User.username=='admin').first()\n"
        "print('ADMIN_FOUND=' + str(admin is not None))\n"
        "s.close()\n"
    )
    result = _run_isolated(code, env={
        "CRA_DATABASE_URL": f"sqlite:///{db_file.as_posix()}",
        "CRA_ALLOW_INSECURE_SECRET": "true",
        "CRA_ALLOW_DEMO_ACCOUNTS": "false",
    })
    assert result.returncode == 0, result.stderr
    assert "演示账号未创建" in result.stdout
    assert "ADMIN_FOUND=False" in result.stdout


def test_demo_accounts_created_when_allowed(tmp_path):
    """allow_demo_accounts=True 时 seed 创建演示账号。"""
    db_file = tmp_path / "test_seed.db"
    code = (
        "from app.database import SessionLocal\n"
        "from app.models import User\n"
        "from app.seed import seed\n"
        "seed()\n"
        "s = SessionLocal()\n"
        "admin = s.query(User).filter(User.username=='admin').first()\n"
        "print('ADMIN_FOUND=' + str(admin is not None))\n"
        "print('ROLE=' + str(admin.role) if admin else 'ROLE=none')\n"
        "s.close()\n"
    )
    result = _run_isolated(code, env={
        "CRA_DATABASE_URL": f"sqlite:///{db_file.as_posix()}",
        "CRA_ALLOW_INSECURE_SECRET": "true",
        "CRA_ALLOW_DEMO_ACCOUNTS": "true",
    })
    assert result.returncode == 0, result.stderr
    assert "ADMIN_FOUND=True" in result.stdout
    assert "ROLE=admin" in result.stdout


# ────────────────────── 4. CRUD 字段污染防护 ──────────────────────

def _fake_model_with_columns(*names):
    """造一个带 __table__.columns 的假模型，列名即 names。"""
    cols = [SimpleNamespace(name=n) for n in names]
    return SimpleNamespace(__table__=SimpleNamespace(columns=cols))


def test_readonly_fields_blocked_on_create():
    model = _fake_model_with_columns("id", "title", "created_at", "role", "status")
    payload = {"id": 999, "title": "x", "created_at": "2030-01-01", "role": "admin", "status": "open"}
    data = _filter_writable(payload, model, writable_fields=None)
    assert "id" not in data
    assert "created_at" not in data
    assert "role" not in data
    assert data["title"] == "x"
    assert data["status"] == "open"


def test_unknown_fields_ignored():
    model = _fake_model_with_columns("id", "title")
    payload = {"title": "x", "hacked_field": "evil", "another": 1}
    data = _filter_writable(payload, model, writable_fields=None)
    assert data == {"title": "x"}


def test_writable_whitelist_restricts_further():
    """显式白名单只允许 title，即使模型有 status 列也不能写。"""
    model = _fake_model_with_columns("id", "title", "status", "role")
    payload = {"title": "x", "status": "open", "role": "admin"}
    data = _filter_writable(payload, model, writable_fields=["title"])
    assert data == {"title": "x"}


def test_readonly_fields_list_covers_critical_fields():
    """黑名单必须覆盖密码、角色、启用状态、存储路径等敏感字段。"""
    for field in ("id", "created_at", "hashed_password", "role", "is_active", "sha256", "stored_path"):
        assert field in READONLY_FIELDS


def test_crud_create_rejects_role_escalation():
    """模拟供应商创建请求：role / is_active 等敏感字段应被丢弃。"""
    model = _fake_model_with_columns("id", "name", "role", "is_active", "created_at")
    payload = {"name": "供应商A", "role": "admin", "is_active": False}
    data = _filter_writable(payload, model, writable_fields=None)
    assert data == {"name": "供应商A"}
