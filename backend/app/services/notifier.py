"""通知中心 — 应用内 + 邮件 + 飞书多渠道推送。"""
import os, json
from datetime import timedelta
from sqlalchemy.orm import Session
from ..models import Notification, NotificationRule, VulnReport, Vulnerability, WorkflowInstance, now


def send_notification(db: Session, user_id: int, kind: str, title: str, body: str = "",
                      link: str = "", severity: str = "info"):
    n = Notification(user_id=user_id, kind=kind, title=title, body=body, link=link, severity=severity)
    db.add(n)
    db.commit()

    # 检查用户通知规则
    rules = db.query(NotificationRule).filter_by(user_id=user_id, is_enabled=True).all()
    for rule in rules:
        if rule.rule_type == kind or rule.rule_type == "all":
            if rule.channel == "email":
                _send_email(user_id, title, body)
            elif rule.channel == "feishu":
                _send_feishu(user_id, title, body)

    return n


def check_vuln_deadlines(db: Session):
    """检查漏洞通报时限，过期/即将过期发送通知。"""
    now_ts = now()
    reports = db.query(VulnReport).filter(VulnReport.status == "pending").all()
    for r in reports:
        hours_left = (r.due_at - now_ts).total_seconds() / 3600
        vuln = db.query(Vulnerability).filter_by(id=r.vuln_id).first()
        vuln_title = vuln.title if vuln else "未知漏洞"
        if hours_left <= 0:
            r.status = "overdue"
            db.commit()
            send_notification(db, 0, "vuln_deadline",
                f"通报时限已过期: {vuln_title}",
                f"漏洞 '{vuln_title}' 的 {r.report_type} 通报时限已过期，请立即处理！",
                link=f"/vulns/{r.vuln_id}", severity="critical")
        elif hours_left <= 24:
            send_notification(db, 0, "vuln_deadline",
                f"通报时限即将到期: {vuln_title}",
                f"漏洞 '{vuln_title}' 的 {r.report_type} 通报还剩 {int(hours_left)} 小时。",
                link=f"/vulns/{r.vuln_id}", severity="warning")


def check_workflow_reminders(db: Session):
    """检查待审批工作流，72小时未处理发送提醒。"""
    now_ts = now()
    wfs = db.query(WorkflowInstance).filter(WorkflowInstance.status == "submitted").all()
    for w in wfs:
        hours_pending = (now_ts - w.created_at).total_seconds() / 3600
        if hours_pending > 72:
            send_notification(db, 0, "workflow_remind",
                f"审批提醒: {w.title}",
                f"工作流已等待 {int(hours_pending)} 小时，请尽快处理。",
                link=f"/workflow/{w.id}", severity="warning")


def _send_email(user_id: int, title: str, body: str):
    """邮件发送骨架 (SMTP)。"""
    pass  # 生产环境配置 SMTP


def _send_feishu(user_id: int, title: str, body: str):
    """飞书 webhook 发送。"""
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if not webhook:
        return
    try:
        import httpx
        httpx.post(webhook, json={"msg_type": "interactive", "card": {
            "header": {"title": {"content": title, "tag": "plain_text"}},
            "elements": [{"tag": "div", "text": {"content": body, "tag": "lark_md"}}]
        }}, timeout=5)
    except Exception:
        pass


def init_default_rules(db: Session, user_id: int):
    """为新用户初始化默认通知规则。"""
    defaults = [
        ("vuln_deadline", "in_app", 24),
        ("workflow_remind", "in_app", 72),
    ]
    for rt, ch, th in defaults:
        if not db.query(NotificationRule).filter_by(user_id=user_id, rule_type=rt).first():
            db.add(NotificationRule(user_id=user_id, rule_type=rt, channel=ch, threshold_hours=th))
    db.commit()
