# -*- coding: utf-8 -*-
"""L1 单元测试：通报时限纯函数 compute_deadline_stages。

覆盖：基本生成、found_at 为空回退 now、各阶段时差、时间注入。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.scoring import compute_deadline_stages, REPORT_STAGES


def _t(year=2026, month=6, day=1, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_three_stages_generated():
    found = _t()
    stages = compute_deadline_stages(found)
    assert len(stages) == 3
    assert [s[0] for s in stages] == ["early_24h", "notify_72h", "final_14d"]


def test_stage_offsets_correct():
    found = _t()
    stages = dict(compute_deadline_stages(found))
    assert stages["early_24h"] == found + timedelta(hours=24)
    assert stages["notify_72h"] == found + timedelta(hours=72)
    assert stages["final_14d"] == found + timedelta(hours=24 * 14)


def test_found_at_none_falls_back_to_now():
    """found_at=None 时用 now_fn 注入的当前时间。"""
    fake_now = _t(day=15, hour=12)
    stages = compute_deadline_stages(None, now_fn=lambda: fake_now)
    assert dict(stages)["early_24h"] == fake_now + timedelta(hours=24)


def test_found_at_none_uses_real_now_when_not_injected():
    """不注入 now_fn 时应取真实当前时间，且在合理窗口内。"""
    before = datetime.now(timezone.utc)
    stages = compute_deadline_stages(None)
    after = datetime.now(timezone.utc)
    early = dict(stages)["early_24h"]
    # early 应在 [before+24h, after+24h] 之间
    assert before + timedelta(hours=24) <= early <= after + timedelta(hours=24)


def test_stages_consistent_with_report_stages_constant():
    """函数行为与模块常量 REPORT_STAGES 一致。"""
    found = _t()
    stages = compute_deadline_stages(found)
    for (rtype, hours), (got_rtype, got_due) in zip(REPORT_STAGES, stages):
        assert rtype == got_rtype
        assert got_due == found + timedelta(hours=hours)


def test_past_found_at_still_computes_future_deadlines():
    """发现时间在很久以前：截止时间仍按 found_at 推算（可能已逾期，由 refresh_overdue 处理）。"""
    old = _t(year=2020)
    stages = dict(compute_deadline_stages(old))
    assert stages["final_14d"] == old + timedelta(hours=336)
