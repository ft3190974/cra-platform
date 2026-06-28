# -*- coding: utf-8 -*-
"""pytest 共享 fixtures。

- db: 内存 SQLite session，每用例隔离，建表/销毁自动完成；
- cra_setup: 预置 CRA 控制库 + GOV-SAMM 桥接项 + 产品节点 + CRA 评估，供集成测试复用。
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: F401  确保所有模型注册到 Base.metadata


@pytest.fixture()
def engine():
    """每个测试用一个全新的内存库，互不污染。

    用 StaticPool 让所有 session 共享同一个底层连接——内存 SQLite 默认每连接
    一个独立数据库，TestClient 跨线程请求时会新建连接从而看不到已建的表。
    """
    from sqlalchemy.pool import StaticPool
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    # 内存库随 engine 销毁自动释放，无需 drop_all（避免 users↔org_nodes
    # 循环外键触发 SQLite 排序 warning）
    eng.dispose()


@pytest.fixture()
def db(engine):
    """事务级 session，测试结束自动关闭。"""
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _make_item(db, domain_id, code, *, max_level=5, weight=1.0, remediation=None):
    """快速造一个 ControlItem 并返回。"""
    from app.models import ControlItem
    it = ControlItem(domain_id=domain_id, code=code, title=code, question="q",
                    cra_ref="", guidance="", max_level=max_level, weight=weight,
                    remediation=remediation or [], order=0)
    db.add(it); db.commit(); db.refresh(it)
    return it


@pytest.fixture()
def cra_setup(db):
    """预置：CRA 库(1 域 1 项) + SAMM 库(1 域 1 项) + GOV-SAMM 桥接项
    + 产品节点 + CRA 评估 + SAMM 评估。返回命名空间对象，便于用例取用。
    """
    from types import SimpleNamespace
    from datetime import datetime, timezone
    from app.models import (ControlLibrary, ControlDomain, ControlItem, OrgNode,
                            Assessment, AssessmentAnswer)

    # CRA 库
    cra_lib = ControlLibrary(code="CRA-TEST", name="CRA 测试库",
                             regulation="CRA", framework_type="cra", version="1.0")
    db.add(cra_lib); db.commit(); db.refresh(cra_lib)
    cra_dom = ControlDomain(library_id=cra_lib.id, code="D1", name="域1",
                            samm_function="治理", order=0)
    db.add(cra_dom); db.commit(); db.refresh(cra_dom)
    cra_item = _make_item(db, cra_dom.id, "CRA-1", max_level=5, weight=1.0)
    # GOV-SAMM 桥接项（weight=2，模拟 seed.py）
    gov_samm = _make_item(db, cra_dom.id, "GOV-SAMM", max_level=5, weight=2.0)

    # SAMM 库
    samm_lib = ControlLibrary(code="SAMM-TEST", name="SAMM 测试库",
                              regulation="SAMM", framework_type="samm", version="2.0")
    db.add(samm_lib); db.commit(); db.refresh(samm_lib)
    samm_dom = ControlDomain(library_id=samm_lib.id, code="SD1", name="SAMM域1",
                             samm_function="治理", order=0)
    db.add(samm_dom); db.commit(); db.refresh(samm_dom)
    samm_item = _make_item(db, samm_dom.id, "SAMM-1", max_level=3, weight=1.0)

    # 产品节点
    node = OrgNode(node_type="product", name="测试产品", code="P-TEST",
                   cra_class="important_2")
    db.add(node); db.commit(); db.refresh(node)

    # 两个评估
    cra_assess = Assessment(node_id=node.id, library_id=cra_lib.id,
                            title="CRA 评估", created_by="tester")
    samm_assess = Assessment(node_id=node.id, library_id=samm_lib.id,
                             title="SAMM 评估", created_by="tester")
    db.add_all([cra_assess, samm_assess]); db.commit(); db.refresh(cra_assess); db.refresh(samm_assess)

    return SimpleNamespace(
        cra_lib=cra_lib, cra_dom=cra_dom, cra_item=cra_item, gov_samm=gov_samm,
        samm_lib=samm_lib, samm_dom=samm_dom, samm_item=samm_item,
        node=node, cra_assess=cra_assess, samm_assess=samm_assess,
        make_item=lambda **kw: _make_item(db, cra_dom.id, **kw),
    )
