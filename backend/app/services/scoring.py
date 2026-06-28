# -*- coding: utf-8 -*-
"""评估打分与通报时限的纯计算函数。

设计目标：
- 不依赖 DB / settings / 时间源，可独立单测；
- 输入为已查出的 ORM 对象或简单容器，输出为标量；
- 对脏数据（level 越界、max_level=0、weight=0）做防御，避免除零与失真。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from ..models import AssessmentAnswer, ControlItem


# CRA 第14条：已被利用漏洞 / 严重事件的三级通报时限（小时）
# 保留为模块级常量，供 integrations 与测试共用，避免两处定义。
REPORT_STAGES: list[tuple[str, int]] = [
    ("early_24h", 24),
    ("notify_72h", 72),
    ("final_14d", 24 * 14),
]


def compute_score(
    answers: Iterable[AssessmentAnswer],
    items: dict[int, ControlItem],
) -> tuple[float, float]:
    """根据评估答案计算 (成熟度评分 0-5, 合规就绪度 %)。

    - 答案找不到对应控制项时跳过（容错）；
    - level 超过 max_level 时按 max_level 截断（防越界打分）；
    - max_level<=0 或 total_w<=0 时返回 (0, 0)（防除零）。
    """
    answers = list(answers)
    if not answers:
        return 0.0, 0.0

    total_w = 0.0
    got = 0.0
    for a in answers:
        item = items.get(a.item_id)
        if item is None:
            continue
        max_level = item.max_level or 0
        if max_level <= 0:
            # 该控制项分级无效，不计入分母
            continue
        level = min(max(a.level, 0), max_level)  # clamp 到 [0, max_level]
        w = item.weight or 0.0
        total_w += w
        got += (level / max_level) * w

    if total_w <= 0:
        return 0.0, 0.0
    score = round(5 * got / total_w, 2)
    readiness = round(100 * got / total_w, 1)
    return score, readiness


def compute_deadline_stages(
    found_at: datetime | None,
    *,
    now_fn: callable = None,
) -> list[tuple[str, datetime]]:
    """计算 24h/72h/14d 三级通报单的截止时间，不碰 DB。

    - found_at 为空时回退到 now_fn()；
    - now_fn 可注入，默认 None 表示用 datetime.now(timezone.utc)。
    """
    from datetime import timezone
    base = found_at
    if base is None:
        base = (now_fn or (lambda: datetime.now(timezone.utc)))()
    return [(rtype, base + timedelta(hours=hours)) for rtype, hours in REPORT_STAGES]


def samm_avg_to_cra_level(avg: float) -> int:
    """SAMM 平均成熟度（0-3）折算为 CRA 等级（0-5）。

    - 输入先 clamp 到 [0, 3]，防止脏数据导致 cra_level 超过 5；
    - 采用 round 后再 clamp，避免浮点边界（如 2.4999）导致越界。
    """
    avg = max(0.0, min(avg, 3.0))
    level = round(avg / 3 * 5)
    return max(0, min(level, 5))
