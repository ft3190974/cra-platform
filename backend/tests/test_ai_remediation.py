# -*- coding: utf-8 -*-
"""AI 差距分析与整改建议联动测试。

守护三个修复点：
1. ai_analyzer 的 remediation 规则匹配（按 level_threshold，不再按索引越界）；
2. ai_analyzer 的差距判定（未达满分即差距，不再只看 level<3）；
3. 整改建议 → Task 转换端点（去重、关联、联动状态）；
4. AI analyses 列表过滤 prompt 敏感字段 + 强制 node_id scope。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models import AssessmentAnswer, Task
from app.routers.ai import list_analyses
from app.routers.assess import remediation, remediation_to_task, RemediationToTaskIn
from app.services.ai_analyzer import _match_remediation_rule, run_gap_analysis


def _fake_user(role="assessor"):
    return SimpleNamespace(id=1, username="u", role=role, is_active=True)


# ────────────────────── 1. remediation 规则匹配 ──────────────────────

def test_match_rule_by_level_threshold(cra_setup, db):
    """level=1 应匹配 level_threshold=2 的规则（而非按索引取 remediation[1]）。"""
    from tests.conftest import _make_item
    item_with_rules = _make_item(db, cra_setup.cra_dom.id, "R-01", max_level=5, weight=1.0,
                                 remediation=[{"level_threshold": 2, "gap_desc": "缺",
                                               "advice": "补", "recommended_tools": ["SAST"]}])
    assert _match_remediation_rule(item_with_rules, level=0) is not None
    assert _match_remediation_rule(item_with_rules, level=1) is not None
    assert _match_remediation_rule(item_with_rules, level=2) is not None
    # level=3 > threshold=2，不匹配
    assert _match_remediation_rule(item_with_rules, level=3) is None


def test_match_rule_returns_none_when_no_rules(cra_setup, db):
    """remediation 为空时返回 None，不报错。"""
    assert _match_remediation_rule(cra_setup.cra_item, level=0) is None


# ────────────────────── 2. 差距判定 ──────────────────────

def test_gap_analysis_includes_non_max_levels(cra_setup, db):
    """level=4（未达满分5）应出现在差距里（原来 level<3 会漏掉）。"""
    db.add(AssessmentAnswer(assessment_id=cra_setup.cra_assess.id,
                            item_id=cra_setup.cra_item.id, level=4))
    db.commit()
    r = run_gap_analysis(db, cra_setup.cra_assess.id)
    assert "当前水平 4/5" in r.result


def test_gap_analysis_excludes_full_score(cra_setup, db):
    """level=5（满分）不应出现在差距里。"""
    db.add(AssessmentAnswer(assessment_id=cra_setup.cra_assess.id,
                            item_id=cra_setup.cra_item.id, level=5))
    db.commit()
    r = run_gap_analysis(db, cra_setup.cra_assess.id)
    assert "当前水平 5/5" not in r.result


def test_gap_analysis_no_IndexError_on_high_level(cra_setup, db):
    """level=1 且 remediation 只有1条规则：不应 IndexError（原来按索引取 [1] 越界）。"""
    from tests.conftest import _make_item
    item = _make_item(db, cra_setup.cra_dom.id, "IDX-01", max_level=5, weight=1.0,
                      remediation=[{"level_threshold": 2, "gap_desc": "缺",
                                    "advice": "补", "recommended_tools": ["SAST"]}])
    db.add(AssessmentAnswer(assessment_id=cra_setup.cra_assess.id, item_id=item.id, level=1))
    db.commit()
    r = run_gap_analysis(db, cra_setup.cra_assess.id)
    # 应包含整改建议（不再为空字符串）
    assert "补" in r.result


def test_gap_analysis_empty_answers(cra_setup, db):
    """无答案时不报错。"""
    r = run_gap_analysis(db, cra_setup.cra_assess.id)
    assert r.status == "done"


# ────────────────────── 3. 整改建议转任务 ──────────────────────

def _ensure_remediation_rule(cra_setup):
    """给 cra_item 补一条 remediation 规则，供需要建议项的测试使用。"""
    if not cra_setup.cra_item.remediation:
        cra_setup.cra_item.remediation = [{"level_threshold": 2, "gap_desc": "缺策略",
                                           "advice": "制定策略", "recommended_tools": ["SAST"]}]
    return cra_setup.cra_item


def test_remediation_lists_gaps_with_task_status(cra_setup, db):
    """remediation 端点返回每条建议的 task_id（初始 None）。"""
    item = _ensure_remediation_rule(cra_setup)
    db.add(AssessmentAnswer(assessment_id=cra_setup.cra_assess.id, item_id=item.id, level=0))
    db.commit()
    rem = remediation(aid=cra_setup.cra_assess.id, db=db, _=_fake_user())
    assert len(rem["items"]) >= 1
    assert all("task_id" in it for it in rem["items"])
    assert all(it["task_id"] is None for it in rem["items"])


def test_remediation_to_task_creates_task(cra_setup, db):
    """转任务端点创建 Task 并关联 node。"""
    body = RemediationToTaskIn(item_code="GOV-01", item_title="安全策略",
                               advice="制定策略", recommended_tools=["SAST"])
    res = remediation_to_task(aid=cra_setup.cra_assess.id, body=body, db=db, user=_fake_user())
    assert res["created"] is True
    t = db.get(Task, res["task_id"])
    assert t is not None
    assert t.source_type == "remediation"
    assert t.source_id == f"aid{cra_setup.cra_assess.id}:GOV-01"
    assert t.node_id == cra_setup.node.id
    assert t.status == "open"


def test_remediation_to_task_idempotent(cra_setup, db):
    """同一条建议重复转任务不重复创建。"""
    body = RemediationToTaskIn(item_code="GOV-01", item_title="安全策略", advice="x")
    r1 = remediation_to_task(aid=cra_setup.cra_assess.id, body=body, db=db, user=_fake_user())
    r2 = remediation_to_task(aid=cra_setup.cra_assess.id, body=body, db=db, user=_fake_user())
    assert r1["created"] is True
    assert r2["created"] is False
    assert r1["task_id"] == r2["task_id"]


def test_remediation_shows_task_id_after_conversion(cra_setup, db):
    """转任务后，remediation 列表该条应显示 task_id。"""
    item = _ensure_remediation_rule(cra_setup)
    db.add(AssessmentAnswer(assessment_id=cra_setup.cra_assess.id, item_id=item.id, level=0))
    db.commit()
    # 转之前 task_id 为 None
    rem1 = remediation(aid=cra_setup.cra_assess.id, db=db, _=_fake_user())
    target = next(it for it in rem1["items"] if it["item_code"] == item.code)
    assert target["task_id"] is None
    # 转任务
    body = RemediationToTaskIn(item_code=item.code, item_title=item.title, advice="x")
    res = remediation_to_task(aid=cra_setup.cra_assess.id, body=body, db=db, user=_fake_user())
    # 转之后应显示 task_id
    rem2 = remediation(aid=cra_setup.cra_assess.id, db=db, _=_fake_user())
    target2 = next(it for it in rem2["items"] if it["item_code"] == item.code)
    assert target2["task_id"] == res["task_id"]


# ────────────────────── 4. AI analyses 列表 ──────────────────────

def test_list_analyses_filters_prompt(cra_setup, db):
    """list_analyses 不应返回 prompt 字段（含评估数据）。"""
    from app.models import AiAnalysis
    db.add(AiAnalysis(node_id=cra_setup.node.id, analysis_type="gap_assessment",
                      prompt="敏感评估数据", result="r", status="done",
                      model="rule-engine", tokens_used=0))
    db.commit()
    out = list_analyses(node_id=cra_setup.node.id, db=db, user=_fake_user())
    assert len(out) == 1
    assert "prompt" not in out[0]
    assert "model" in out[0]
    assert "status" in out[0]


def test_list_analyses_scoped_by_node(cra_setup, db):
    """list_analyses 只返回指定 node 的分析，不跨节点。"""
    from app.models import AiAnalysis, OrgNode
    other_node = OrgNode(node_type="product", name="其他产品", code="P-OTHER", cra_class="default")
    db.add(other_node); db.commit(); db.refresh(other_node)
    db.add_all([
        AiAnalysis(node_id=cra_setup.node.id, analysis_type="gap", prompt="p",
                   result="r", status="done", model="m"),
        AiAnalysis(node_id=other_node.id, analysis_type="gap", prompt="p2",
                   result="r2", status="done", model="m"),
    ])
    db.commit()
    out = list_analyses(node_id=cra_setup.node.id, db=db, user=_fake_user())
    assert all(a["id"] for a in out)
    # 只返回当前 node 的
    assert len(out) == 1
