"""漏洞通报时限服务（CRA 第14条）与集成 adapter。"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..models import Vulnerability, VulnReport, Component, now
from .scoring import REPORT_STAGES, compute_deadline_stages


def create_report_deadlines(db: Session, vuln: Vulnerability, target="ENISA_SRP"):
    """为一个（已被利用）漏洞生成 24h/72h/14d 三张通报单与到期时间。"""
    created = []
    for rtype, due_at in compute_deadline_stages(vuln.found_at):
        r = VulnReport(
            vuln_id=vuln.id, report_type=rtype, target=target,
            status="pending", due_at=due_at,
            content={"vuln": vuln.title, "cve": vuln.cve_id},
        )
        db.add(r)
        created.append(r)
    db.commit()
    return created


def refresh_overdue(db: Session):
    """批量 UPDATE 把已过期未提交的通报单标记 overdue（一次 SQL，无 N+1）。"""
    n = now()
    db.execute(
        update(VulnReport)
        .where(VulnReport.status == "pending", VulnReport.due_at < n)
        .values(status="overdue")
    )
    db.commit()


# ───── 集成 adapter：mock + 真实 HTTP 拉取骨架 ─────
def sync_integration(db: Session, integration) -> dict:
    """根据 kind 拉取漏洞/成分数据。检测工具用 mock 样例，
    public_disclosure 预留真实 HTTP 拉取骨架。"""
    kind = integration.kind
    summary = ""
    imported = 0

    if kind in ("sast", "sca", "bat", "fuzz"):
        samples = _mock_tool_findings(kind)
        for s in samples:
            db.add(Vulnerability(
                node_id=integration.node_id, source=kind, title=s["title"],
                severity=s["severity"], cvss_score=s["cvss"], cwe=s.get("cwe", ""),
                component=s.get("component", ""), status="open",
            ))
            imported += 1
        summary = f"从 {kind.upper()} 导入 {imported} 条漏洞（mock）"

    elif kind == "public_disclosure":
        summary = _fetch_public_disclosure_skeleton(integration)
    else:
        summary = "未知集成类型"

    integration.last_sync_at = now()
    db.commit()
    return {"imported": imported, "summary": summary}


def _mock_tool_findings(kind: str):
    table = {
        "sast": [
            {"title": "缓冲区溢出（栈）", "severity": "high", "cvss": 8.1, "cwe": "CWE-121", "component": "core/parser.c"},
            {"title": "格式化字符串漏洞", "severity": "medium", "cvss": 5.3, "cwe": "CWE-134", "component": "log/fmt.c"},
        ],
        "sca": [
            {"title": "log4j 远程代码执行 (CVE-2021-44228)", "severity": "critical", "cvss": 10.0, "cwe": "CWE-502", "component": "log4j-core@2.14.1"},
        ],
        "bat": [
            {"title": "固件中硬编码密钥", "severity": "high", "cvss": 7.5, "cwe": "CWE-798", "component": "firmware.bin"},
        ],
        "fuzz": [
            {"title": "协议解析空指针解引用", "severity": "medium", "cvss": 6.5, "cwe": "CWE-476", "component": "proto/can.c"},
        ],
    }
    return table.get(kind, [])


def _fetch_public_disclosure_skeleton(integration) -> str:
    """真实对接示例（默认不发起网络请求，避免演示环境失败）。
    生产启用：解开下面注释并按目标平台 API 调整字段映射。
    """
    endpoint = integration.endpoint
    if not endpoint:
        return "未配置 endpoint，跳过（骨架）"
    return f"已连接 {endpoint}（真实拉取骨架，待按平台字段映射启用）"
