# -*- coding: utf-8 -*-
"""供应商门户接口契约测试。

重点守护：grant-access 必须接收 JSON body（Pydantic model），
而非 query string —— 否则前端 POST JSON 会 422，令牌生成失败。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import OrgNode, Supplier
from app.routers.supplier_portal import supplier_router


@pytest.fixture()
def client(db, cra_setup):
    """挂载供应商路由，注入测试 session 与 fake 认证。"""
    app = FastAPI()
    app.include_router(supplier_router)

    def get_test_db():
        yield db

    async def fake_user():
        return SimpleNamespace(id=1, username="admin", role="admin", is_active=True)

    from app.auth import get_current_user
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = fake_user
    return TestClient(app)


def _make_supplier(db):
    sup = Supplier(name="测试供应商")
    db.add(sup); db.commit(); db.refresh(sup)
    return sup


def test_grant_access_accepts_json_body(client, db, cra_setup):
    """前端发 JSON body，后端应 200 返回 token + url。"""
    sup = _make_supplier(db)
    r = client.post("/api/supplier-portal/grant-access", json={
        "supplier_id": sup.id,
        "node_id": cra_setup.node.id,
        "days": 30,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and len(data["token"]) >= 20
    assert "url" in data and "token=" in data["url"]
    assert "expires_at" in data


def test_grant_access_missing_fields_returns_422(client, db, cra_setup):
    """缺字段应 422（Pydantic 校验），而非 500。"""
    r = client.post("/api/supplier-portal/grant-access", json={"days": 30})
    assert r.status_code == 422


def test_grant_access_token_is_unique(client, db, cra_setup):
    """连续生成两次，token 互不相同。"""
    sup = _make_supplier(db)
    tokens = []
    for _ in range(2):
        r = client.post("/api/supplier-portal/grant-access", json={
            "supplier_id": sup.id, "node_id": cra_setup.node.id, "days": 30})
        assert r.status_code == 200
        tokens.append(r.json()["token"])
    assert tokens[0] != tokens[1]


def test_grant_access_default_days_30(client, db, cra_setup):
    """不传 days 时默认 30 天。"""
    sup = _make_supplier(db)
    r = client.post("/api/supplier-portal/grant-access", json={
        "supplier_id": sup.id, "node_id": cra_setup.node.id})
    assert r.status_code == 200
    # expires_at 应在 29~31 天后
    from datetime import datetime, timezone, timedelta
    from app.models import now as _now
    expires = datetime.fromisoformat(r.json()["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    delta = expires - _now()
    assert timedelta(days=29) < delta < timedelta(days=31)


def test_submit_with_valid_token_succeeds(client, db, cra_setup):
    """生成令牌后，供应商用该令牌提交材料应成功。"""
    sup = _make_supplier(db)
    r = client.post("/api/supplier-portal/grant-access", json={
        "supplier_id": sup.id, "node_id": cra_setup.node.id, "days": 30})
    token = r.json()["token"]

    # /submit 是外部接口，无需认证（靠 token）
    r2 = client.post("/api/supplier-portal/submit", json={
        "token": token, "form_type": "self_assessment",
        "title": "供应商自评", "content": {"q1": "yes"},
    })
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "submitted"


def test_submit_with_invalid_token_returns_403(client, db):
    """无效 token 提交应 403。"""
    r = client.post("/api/supplier-portal/submit", json={
        "token": "nonexistent-token-xxx", "form_type": "sbom",
        "title": "x", "content": {},
    })
    assert r.status_code == 403
