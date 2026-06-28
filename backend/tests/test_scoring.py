# -*- coding: utf-8 -*-
"""L1 单元测试：评估打分纯函数 compute_score。

覆盖：空集、上下界、加权、clamp 越界、除零防御、容错。
"""
from __future__ import annotations

from types import SimpleNamespace

from app.services.scoring import compute_score


def _ans(item_id, level):
    """轻量造一个 AssessmentAnswer-like 对象（避免依赖 DB）。"""
    return SimpleNamespace(item_id=item_id, level=level)


def _item(item_id, *, max_level=5, weight=1.0):
    """轻量造一个 ControlItem-like 对象。"""
    return SimpleNamespace(id=item_id, max_level=max_level, weight=weight)


def test_empty_answers_returns_zero():
    assert compute_score([], {}) == (0.0, 0.0)


def test_all_max_level_full_score():
    items = {1: _item(1, max_level=5, weight=1.0)}
    answers = [_ans(1, 5)]
    score, readiness = compute_score(answers, items)
    assert score == 5.0
    assert readiness == 100.0


def test_all_zero_level_zero_score():
    items = {1: _item(1, max_level=5, weight=1.0)}
    answers = [_ans(1, 0)]
    score, readiness = compute_score(answers, items)
    assert score == 0.0
    assert readiness == 0.0


def test_weight_affects_score():
    # A: weight=2, level=max → 贡献 2
    # B: weight=1, level=0   → 贡献 0
    # 总权重 3，got=2 → score=5*2/3, readiness=100*2/3
    items = {1: _item(1, max_level=5, weight=2.0), 2: _item(2, max_level=5, weight=1.0)}
    answers = [_ans(1, 5), _ans(2, 0)]
    score, readiness = compute_score(answers, items)
    assert score == round(5 * 2 / 3, 2)
    assert readiness == round(100 * 2 / 3, 1)


def test_level_above_max_is_clamped():
    """level=6 但 max_level=5：应按 5 算，而非让分数超过 5。"""
    items = {1: _item(1, max_level=5, weight=1.0)}
    answers = [_ans(1, 6)]
    score, readiness = compute_score(answers, items)
    assert score == 5.0
    assert readiness == 100.0


def test_negative_level_clamped_to_zero():
    items = {1: _item(1, max_level=5, weight=1.0)}
    answers = [_ans(1, -3)]
    score, readiness = compute_score(answers, items)
    assert score == 0.0
    assert readiness == 0.0


def test_max_level_zero_does_not_crash():
    """max_level=0 的控制项：不应除零，应跳过。"""
    items = {1: _item(1, max_level=0, weight=1.0)}
    answers = [_ans(1, 3)]
    # 全部 item 都无效 → total_w=0 → (0, 0)
    score, readiness = compute_score(answers, items)
    assert score == 0.0
    assert readiness == 0.0


def test_all_weights_zero_returns_zero():
    items = {1: _item(1, max_level=5, weight=0.0), 2: _item(2, max_level=5, weight=0.0)}
    answers = [_ans(1, 5), _ans(2, 5)]
    score, readiness = compute_score(answers, items)
    assert score == 0.0
    assert readiness == 0.0


def test_answer_without_matching_item_is_skipped():
    """答案指向已删除的 item：跳过，不影响其余打分。"""
    items = {1: _item(1, max_level=5, weight=1.0)}
    answers = [_ans(1, 5), _ans(999, 5)]  # 999 不在 items
    score, readiness = compute_score(answers, items)
    assert score == 5.0
    assert readiness == 100.0


def test_mixed_levels_partial_score():
    # 三项等权，level 分别 5/3/0（满 5）→ got = 1+0.6+0 = 1.6, total_w=3
    items = {
        1: _item(1, max_level=5, weight=1.0),
        2: _item(2, max_level=5, weight=1.0),
        3: _item(3, max_level=5, weight=1.0),
    }
    answers = [_ans(1, 5), _ans(2, 3), _ans(3, 0)]
    score, readiness = compute_score(answers, items)
    got = 1.0 + 0.6 + 0.0
    assert score == round(5 * got / 3, 2)
    assert readiness == round(100 * got / 3, 1)
