"""AI 差距分析服务 — 评估打分后自动生成整改报告。"""
import os, json
from sqlalchemy.orm import Session
from ..models import Assessment, AssessmentAnswer, ControlItem, AiAnalysis, OrgNode, now


def _match_remediation_rule(item: ControlItem, level: int) -> dict | None:
    """按 level_threshold 匹配整改规则，与 build_remediation_report 逻辑一致。

    规则列表每项含 level_threshold：当 level <= threshold 时该规则适用。
    取第一条匹配的规则（按列表顺序即优先级）。
    """
    for rule in (item.remediation or []):
        if level <= rule.get("level_threshold", 2):
            return rule
    return None


def run_gap_analysis(db: Session, assessment_id: int) -> AiAnalysis:
    """基于评估结果运行 AI 差距分析。优先用 ANTHROPIC_API_KEY，否则用规则引擎。"""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise ValueError("评估不存在")
    node = db.query(OrgNode).filter_by(id=assessment.node_id).first()
    answers = db.query(AssessmentAnswer).filter_by(assessment_id=assessment_id).all()

    # 批量预加载 ControlItem，避免 N+1
    item_ids = [a.item_id for a in answers]
    items_map = {it.id: it for it in db.query(ControlItem).filter(ControlItem.id.in_(item_ids)).all()} if item_ids else {}

    gaps = []
    for a in answers:
        item = items_map.get(a.item_id)
        if not item:
            continue
        # 差距判定：未达满分即算差距（原来是 level<3，会漏掉 level=4/5 的情况）
        if a.level < item.max_level:
            rule = _match_remediation_rule(item, a.level)
            gaps.append({
                "domain": item.domain_id, "code": item.code,
                "title": item.title, "level": a.level, "max": item.max_level,
                "gap_desc": rule.get("gap_desc", "") if rule else "未达满分，需进一步提升",
                "advice": rule.get("advice", "参考 CRA Annex I 相关条款制定整改计划") if rule else "",
                "recommended_tools": rule.get("recommended_tools", []) if rule else [],
            })

    total = len(answers)
    low = sum(1 for a in answers if items_map.get(a.item_id) and a.level < 2)
    mid = sum(1 for a in answers if items_map.get(a.item_id) and 2 <= a.level < 4)
    high = sum(1 for a in answers if items_map.get(a.item_id) and a.level >= 4)

    context = {
        "node_name": node.name if node else "", "node_type": node.node_type if node else "",
        "score": round(assessment.score, 1), "readiness": round(assessment.readiness, 1),
        "total_items": total, "gaps_count": len(gaps),
        "level_dist": {"low": low, "mid": mid, "high": high},
        "top_gaps": gaps[:10]
    }

    prompt = f"""你是 CRA《欧盟网络弹性法案》合规专家。基于以下评估数据生成差距分析报告：

产品: {context['node_name']} ({context['node_type']})
合规就绪度: {context['readiness']}% | 评估得分: {context['score']}/{total}
差距项: {len(gaps)}/{total}

前10项差距:
{json.dumps(context['top_gaps'], ensure_ascii=False, indent=2)}

请用中文输出：
1. 总体评估（2-3句）
2. 三大关键差距
3. 整改路线图（按优先级排序）
4. 推荐软安工具（SAST/SCA/BAT/FUZZ/CodingHawk/GuardFox）
"""

    ai_record = AiAnalysis(node_id=assessment.node_id, analysis_type="gap_assessment",
                           prompt=prompt, status="running", model="rule-engine")
    db.add(ai_record)
    db.commit()

    # 规则引擎生成（AI API 可选调用）
    result = _rule_based_gap_report(context, gaps, db)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000,
                system="你是CRA合规专家，回答简洁专业。",
                messages=[{"role": "user", "content": prompt}])
            result = resp.content[0].text
            ai_record.model = "claude-sonnet-4-6"
            ai_record.tokens_used = resp.usage.output_tokens if hasattr(resp, 'usage') else 0
        except Exception:
            pass

    ai_record.result = result
    ai_record.status = "done"
    db.commit()
    return ai_record


def _rule_based_gap_report(context, gaps, db):
    lines = [
        "## CRA 合规差距分析报告",
        "",
        f"**产品**: {context['node_name']} | **合规就绪度**: {context['readiness']}%",
        "",
        "### 总体评估",
        f"当前产品CRA合规就绪度为 {context['readiness']}%，",
    ]
    if context['readiness'] < 30:
        lines.append("处于合规建设早期阶段，建议从基本安全要求和漏洞处理流程入手，优先补齐关键控制项。")
    elif context['readiness'] < 60:
        lines.append("已建立基础安全能力，仍需加强漏洞通报机制和供应商安全管理。")
    elif context['readiness'] < 85:
        lines.append("合规体系较为完善，重点优化文档化水平和持续监控能力。")
    else:
        lines.append("合规就绪度良好，可按计划推进符合性评估和CE标志申请。")

    lines.extend(["", "### 三大关键差距", ""])
    for i, g in enumerate(gaps[:3], 1):
        lines.append(f"**{i}. {g['title']}** — 当前水平 {g['level']}/{g['max']}")
        lines.append(f"差距: {g['gap_desc']}")
        lines.append(f"建议: {g['advice']}")
        if g.get("recommended_tools"):
            lines.append(f"推荐工具: {'、'.join(g['recommended_tools'])}")
        lines.append("")

    lines.extend(["### 整改路线图", "",
        "| 优先级 | 整改项 | 建议工具 | 预计周期 |",
        "|--------|--------|----------|----------|"])

    for i, g in enumerate(gaps[:5]):
        tools = "、".join(g.get("recommended_tools") or ["软安综合方案"])
        # 优先级按差距程度排：level 越低越紧急
        weeks = 2 + i * 2
        lines.append(f"| P{i+1} | {g['title'][:30]} | {tools} | {weeks}-{weeks+2}周 |")

    lines.extend(["", "### 推荐软安工具矩阵",
        "| 产品 | 角色 | CRA 覆盖条款 |",
        "|------|------|-------------|",
        "| SAST 静兮 | 代码安全检测 | Annex I §2 安全设计与开发 |",
        "| SCA 源兮 | 成分分析 & SBOM | Annex I §2(7) SBOM |",
        "| BAT 固兮 | 二进制安全 | Annex I §4 供应链安全 |",
        "| FUZZ 侦兮 | 协议模糊测试 | Annex I §2 安全验证 |",
        "| CodingHawk | AI 代码审计 | Annex I §2 安全审计 |",
        "| GuardFox 洞兮 | 漏洞验证 | Annex I §5 漏洞处理 |",
        "", "---", "*由 CRA 合规平台（华南Test）AI 引擎自动生成*"])
    return "\n".join(lines)
