# -*- coding: utf-8 -*-
"""L2 集成测试：核心逻辑的 DB 端到端流程。

覆盖三条主链路：
1. 保存评估答案 → _recompute 重算分数与就绪度；
2. 创建已利用漏洞 → create_report_deadlines 生成 24h/72h/14d 通报单 → refresh_overdue 标记逾期；
3. 提交 SAMM 评估 → _bridge_samm_to_cra 折算写入 CRA GOV-SAMM 项并触发重算。

只走主路径 + 关键分支，算法边界由 L1 覆盖。
"""
from __future__ import annotations

from datetime import timedelta, timezone

from app.models import AssessmentAnswer, Vulnerability, VulnReport
from app.routers.assess import _recompute, _bridge_samm_to_cra
from app.services.integrations import create_report_deadlines, refresh_overdue


# ────────────────────── 1. 评估打分流程 ──────────────────────

def test_recompute_full_score(cra_setup, db):
    """CRA 评估打满 → score=5, readiness=100。"""
    cra_setup.cra_assess.status = "submitted"
    db.add(AssessmentAnswer(assessment_id=cra_setup.cra_assess.id,
                            item_id=cra_setup.cra_item.id, level=5))
    db.commit()
    _recompute(db, cra_setup.cra_assess)
    assert cra_setup.cra_assess.score == 5.0
    assert cra_setup.cra_assess.readiness == 100.0


def test_recompute_zero_score(cra_setup, db):
    """打 0 分 → score=0, readiness=0。"""
    db.add(AssessmentAnswer(assessment_id=cra_setup.cra_assess.id,
                            item_id=cra_setup.cra_item.id, level=0))
    db.commit()
    _recompute(db, cra_setup.cra_assess)
    assert cra_setup.cra_assess.score == 0.0
    assert cra_setup.cra_assess.readiness == 0.0


def test_recompute_empty_answers(cra_setup, db):
    """无答案 → score=0, readiness=0，不报错。"""
    _recompute(db, cra_setup.cra_assess)
    assert cra_setup.cra_assess.score == 0.0
    assert cra_setup.cra_assess.readiness == 0.0


def test_recompute_updates_after_answer_change(cra_setup, db):
    """修改答案后重算，分数同步变化。"""
    ans = AssessmentAnswer(assessment_id=cra_setup.cra_assess.id,
                           item_id=cra_setup.cra_item.id, level=2)
    db.add(ans); db.commit()
    _recompute(db, cra_setup.cra_assess)
    mid_score = cra_setup.cra_assess.score

    ans.level = 5; db.commit()
    _recompute(db, cra_setup.cra_assess)
    assert cra_setup.cra_assess.score > mid_score
    assert cra_setup.cra_assess.score == 5.0


# ────────────────────── 2. 通报时限流程 ──────────────────────

def test_exploited_vuln_generates_three_reports(cra_setup, db):
    """已利用漏洞 → 生成 3 张通报单，状态 pending，时差正确。"""
    vuln = Vulnerability(node_id=cra_setup.node.id, title="测试漏洞",
                         severity="critical", cvss_score=9.0, exploited=True,
                         source="manual")
    db.add(vuln); db.commit(); db.refresh(vuln)
    reports = create_report_deadlines(db, vuln)
    assert len(reports) == 3
    assert {r.report_type for r in reports} == {"early_24h", "notify_72h", "final_14d"}
    assert all(r.status == "pending" for r in reports)
    # 时差递增
    by_type = {r.report_type: r.due_at for r in reports}
    assert by_type["early_24h"] < by_type["notify_72h"] < by_type["final_14d"]


def test_refresh_overdue_marks_past_pending(cra_setup, db):
    """过期的 pending 通报单被标记 overdue。"""
    from app.models import now as _now
    vuln = Vulnerability(node_id=cra_setup.node.id, title="旧漏洞",
                         severity="high", exploited=True, source="manual",
                         found_at=_now() - timedelta(hours=200))
    db.add(vuln); db.commit(); db.refresh(vuln)
    create_report_deadlines(db, vuln)
    refresh_overdue(db)
    overdue = db.query(VulnReport).filter(VulnReport.vuln_id == vuln.id,
                                           VulnReport.status == "overdue").all()
    # found_at 在 200h 前，24h/72h 均已过期（200>72），14d 未过期
    assert len(overdue) == 2


def test_refresh_overdue_keeps_sent_status(cra_setup, db):
    """已 sent 的通报单即使过期也不被改。"""
    from app.models import now as _now
    vuln = Vulnerability(node_id=cra_setup.node.id, title="已通报漏洞",
                         severity="high", exploited=True, source="manual",
                         found_at=_now() - timedelta(hours=200))
    db.add(vuln); db.commit(); db.refresh(vuln)
    create_report_deadlines(db, vuln)
    # 手动把 24h 那张标记为 sent
    r24 = db.query(VulnReport).filter(VulnReport.vuln_id == vuln.id,
                                      VulnReport.report_type == "early_24h").first()
    r24.status = "sent"; db.commit()
    refresh_overdue(db)
    db.refresh(r24)
    assert r24.status == "sent"  # 未被 refresh_overdue 改动


# ────────────────────── 3. SAMM→CRA 桥接流程 ──────────────────────

def test_bridge_writes_cra_level_and_recomputes(cra_setup, db):
    """提交 SAMM 评估（满级）→ GOV-SAMM 项写入 5，CRA 评估分数变化。"""
    # SAMM 评估打满（level=3, max_level=3 → avg=3 → cra_level=5）
    db.add(AssessmentAnswer(assessment_id=cra_setup.samm_assess.id,
                            item_id=cra_setup.samm_item.id, level=3))
    db.commit()
    # 先记录 CRA 评估原始分数
    _recompute(db, cra_setup.cra_assess)
    score_before = cra_setup.cra_assess.score

    result = _bridge_samm_to_cra(db, cra_setup.samm_assess)
    assert result is not None
    assert result["cra_level"] == 5
    # GOV-SAMM 项被写入
    gov_ans = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.assessment_id == cra_setup.cra_assess.id,
        AssessmentAnswer.item_id == cra_setup.gov_samm.id).first()
    assert gov_ans is not None
    assert gov_ans.level == 5
    # CRA 评估分数已重算（GOV-SAMM weight=2，应拉高分数）
    db.refresh(cra_setup.cra_assess)
    assert cra_setup.cra_assess.score != score_before or cra_setup.cra_assess.score == 5.0


def test_bridge_returns_none_when_no_samm_answers(cra_setup, db):
    """SAMM 评估无答案 → 返回 None。"""
    assert _bridge_samm_to_cra(db, cra_setup.samm_assess) is None


def test_bridge_idempotent_updates_existing(cra_setup, db):
    """重复桥接：更新已有答案而非新增。"""
    db.add(AssessmentAnswer(assessment_id=cra_setup.samm_assess.id,
                            item_id=cra_setup.samm_item.id, level=2))
    db.commit()
    _bridge_samm_to_cra(db, cra_setup.samm_assess)
    count_after_first = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.assessment_id == cra_setup.cra_assess.id,
        AssessmentAnswer.item_id == cra_setup.gov_samm.id).count()
    # 改 SAMM 答案再桥接
    ans = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.assessment_id == cra_setup.samm_assess.id).first()
    ans.level = 3; db.commit()
    _bridge_samm_to_cra(db, cra_setup.samm_assess)
    count_after_second = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.assessment_id == cra_setup.cra_assess.id,
        AssessmentAnswer.item_id == cra_setup.gov_samm.id).count()
    assert count_after_first == 1
    assert count_after_second == 1  # 仍是 1 条，未重复新增
