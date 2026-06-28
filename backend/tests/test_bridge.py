# -*- coding: utf-8 -*-
"""L1 单元测试：SAMM→CRA 折算纯函数 samm_avg_to_cra_level。

覆盖：上下界、中间值、银行家舍入策略、脏数据 clamp。
"""
from __future__ import annotations

import pytest

from app.services.scoring import samm_avg_to_cra_level


def test_full_score_maps_to_five():
    assert samm_avg_to_cra_level(3.0) == 5


def test_zero_maps_to_zero():
    assert samm_avg_to_cra_level(0.0) == 0


@pytest.mark.parametrize("avg,expected", [
    (0.0, 0),
    (0.6, 1),    # 0.6/3*5 = 1.0
    (1.2, 2),    # 1.2/3*5 = 2.0
    (1.8, 3),    # 1.8/3*5 = 3.0
    (2.4, 4),    # 2.4/3*5 = 4.0
    (3.0, 5),
])
def test_linear_mapping(avg, expected):
    assert samm_avg_to_cra_level(avg) == expected


def test_dirty_avg_above_three_is_clamped():
    """SAMM level 越界导致 avg>3：cra_level 不应超过 5。"""
    assert samm_avg_to_cra_level(10.0) == 5
    assert samm_avg_to_cra_level(3.5) == 5


def test_negative_avg_clamped_to_zero():
    assert samm_avg_to_cra_level(-1.0) == 0


def test_rounding_strategy_is_documented():
    """明确取整策略：Python round 为银行家舍入。
    avg=1.5 → 1.5/3*5 = 2.5 → round(2.5)=2（向偶数取整）。
    若未来改为常规四舍五入，此用例需同步更新。
    """
    assert samm_avg_to_cra_level(1.5) == 2


def test_avg_just_below_threshold():
    """avg=0.59 → 0.59/3*5 = 0.983 → round = 1。"""
    assert samm_avg_to_cra_level(0.59) == 1


def test_avg_just_above_threshold():
    """avg=0.61 → 0.61/3*5 = 1.017 → round = 1。"""
    assert samm_avg_to_cra_level(0.61) == 1
