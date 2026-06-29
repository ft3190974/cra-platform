# -*- coding: utf-8 -*-
"""初始化数据库并写入种子数据：账号 / CRA 控制库 / 文档模板 / 演示对象树。

运行：python -m app.seed
幂等：已存在的数据跳过，可重复运行增量添加。
"""
from .auth import hash_password
from .cra_content import DOMAINS
from .database import Base, SessionLocal, engine
from .doc_templates import TEMPLATES
from .doc_demos import DEMOS
from .models import (Assessment, Component, ControlDomain, ControlItem, ControlLibrary,
                     DocTemplate, Integration, OrgNode, Policy, SupportLifecycle, User)


def _exists(db, model, **filters):
    return db.query(model).filter_by(**filters).first() is not None


def _get_or_create(db, model, defaults=None, **filters):
    obj = db.query(model).filter_by(**filters).first()
    if obj:
        return obj, False
    kwargs = {**filters, **(defaults or {})}
    obj = model(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj, True


def seed():
    from .config import settings
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    created_count = 0
    try:
        # ── 账号（幂等：按 username 判重）──
        # 演示账号仅当 CRA_ALLOW_DEMO_ACCOUNTS=true 时创建，避免生产环境遗留弱密码账号。
        accounts = [
            ("admin", "admin123", "admin", "系统管理员"),
            ("manager", "manager123", "manager", "合规经理"),
            ("assessor", "assessor123", "assessor", "评估工程师"),
            ("auditor", "auditor123", "auditor", "审计员"),
            ("viewer", "viewer123", "viewer", "只读用户"),
        ]
        if not settings.allow_demo_accounts:
            print("演示账号未创建（CRA_ALLOW_DEMO_ACCOUNTS 未开启）。"
                  "请通过 API 或手动创建管理员账号。")
        else:
            for username, pw, role, name in accounts:
                if not _exists(db, User, username=username):
                    db.add(User(username=username, hashed_password=hash_password(pw),
                                role=role, full_name=name, email=f"{username}@example.com"))
                    created_count += 1
            db.commit()

        # ── CRA 控制库（幂等：按 code 判重）──
        lib, new_lib = _get_or_create(db, ControlLibrary, code="CRA-AnnexI", defaults={
            "name": "CRA 附录 I 合规评估框架",
            "regulation": "EU CRA 2024/2847", "framework_type": "cra", "version": "1.0",
            "description": "融合 OWASP SAMM 五大功能的 CRA 网络安全要求评估模型"})
        if new_lib:
            created_count += 1
            for d in DOMAINS:
                domain = ControlDomain(library_id=lib.id, code=d["code"], name=d["name"],
                                       samm_function=d["samm_function"], order=d["order"])
                db.add(domain); db.commit()
                for idx, it in enumerate(d["items"]):
                    db.add(ControlItem(domain_id=domain.id, code=it["code"], title=it["title"],
                                       question=it["question"], cra_ref=it["cra_ref"],
                                       guidance=it["guidance"], weight=it["weight"],
                                       remediation=it["remediation"], order=idx))
                db.commit()

        # ── SAMM 评估库（幂等：按 code 判重）──
        samm_lib, new_samm = _get_or_create(db, ControlLibrary, code="SAMM-v2", defaults={
            "name": "OWASP SAMM v2 软件安全成熟度评估",
            "regulation": "OWASP SAMM", "framework_type": "samm", "version": "2.0",
            "description": "OWASP SAMM v2：5 大业务功能 × 15 安全实践 × 3 成熟度等级"})
        if new_samm:
            created_count += 1
            import json as _json, os as _os
            samm_path = _os.path.join(_os.path.dirname(__file__), "samm_data.json")
            samm_data = _json.load(open(samm_path, encoding="utf-8"))
            for di, fd in enumerate(samm_data):
                dom = ControlDomain(library_id=samm_lib.id, code=f"SAMM-D{di+1}",
                                    name=fd["function"], samm_function=fd["function"], order=di)
                db.add(dom); db.commit()
                for idx, it in enumerate(fd["items"]):
                    guide = f"实践：{it['practice']}（成熟度等级 L{it['level']}）\n判定指标：\n- " + \
                            "\n- ".join(it.get("indicators", [])[:6])
                    db.add(ControlItem(domain_id=dom.id, code=it["code"],
                                       title=it["title"], question=it["question"],
                                       cra_ref=f"SAMM · {it['practice']} · L{it['level']}",
                                       guidance=guide, max_level=3, weight=1.0,
                                       remediation=[], order=idx))
                db.commit()

        # ── GOV-SAMM 桥接项（幂等：按 code 判重）──
        gov_domain = db.query(ControlDomain).filter(
            ControlDomain.library_id == lib.id, ControlDomain.code == "GOV").first()
        if gov_domain and not _exists(db, ControlItem, domain_id=gov_domain.id, code="GOV-SAMM"):
            db.add(ControlItem(domain_id=gov_domain.id, code="GOV-SAMM",
                               title="软件安全成熟度（SAMM 评估折算）",
                               question="组织的 OWASP SAMM 软件安全成熟度水平（由独立 SAMM 评估自动折算并入）",
                               cra_ref="OWASP SAMM v2 / CRA 附录 I 第一部分(1)",
                               guidance="本项分数由 SAMM 评估页的成熟度自动折算（SAMM 0-3 级 → CRA 0-5 级）",
                               max_level=5, weight=2.0,
                               remediation=[{"level_threshold": 2,
                                             "gap_desc": "软件安全成熟度偏低（SAMM 评估）",
                                             "advice": "依据 SAMM 评估页给出的薄弱实践制定提升路线图",
                                             "recommended_tools": ["SDLC-SER 研发安全生命周期服务"]}],
                               order=99))
            db.commit()
            created_count += 1

        # ── 文档模板（幂等：按 code 判重）──
        for t in TEMPLATES:
            if not _exists(db, DocTemplate, code=t["code"]):
                db.add(DocTemplate(code=t["code"], name=t["name"], doc_type=t["doc_type"],
                                   cra_ref=t["cra_ref"], stage=t["stage"],
                                   body_html=t["body_html"], fields=t["fields"],
                                   demo_html=DEMOS.get(t["code"], "")))
        db.commit()
        # 已有模板补 demo_html（迁移期）
        for t in TEMPLATES:
            existing = db.query(DocTemplate).filter_by(code=t["code"]).first()
            if existing and not existing.demo_html:
                existing.demo_html = DEMOS.get(t["code"], "")
        db.commit()

        # ── 演示对象树（幂等：按 code 判重）──
        if not _exists(db, OrgNode, code="BU-IOT"):
            bu = OrgNode(node_type="business_unit", name="智能终端事业部", code="BU-IOT")
            db.add(bu); db.commit()
            proj = OrgNode(node_type="project", name="车载网关项目", code="PRJ-GW", parent_id=bu.id)
            db.add(proj); db.commit()
            prod = OrgNode(node_type="product", name="车载安全网关 SecGW", code="P-SECGW",
                           parent_id=proj.id, cra_class="important_2",
                           description="面向欧盟市场的车载网关，属 CRA 重要产品 Class II")
            db.add(prod); db.commit()
            ver = OrgNode(node_type="version", name="SecGW v2.1", code="V2.1", parent_id=prod.id,
                          cra_class="important_2")
            db.add(ver); db.commit()
            prod2 = OrgNode(node_type="product", name="OTA 升级服务", code="P-OTA",
                            parent_id=proj.id, cra_class="important_1")
            db.add(prod2); db.commit()

            # 组件
            for c in [("openssl", "3.0.8", "Apache-2.0", "oss"),
                      ("log4j-core", "2.14.1", "Apache-2.0", "oss"),
                      ("zlib", "1.2.13", "Zlib", "oss")]:
                db.add(Component(product_node_id=prod.id, name=c[0], version=c[1],
                                 license=c[2], origin=c[3], purl=f"pkg:generic/{c[0]}@{c[1]}"))
            db.commit()

            # 支持期
            db.add(SupportLifecycle(product_node_id=prod.id, support_start="2026-01-01",
                                    support_end="2031-12-31", eol_date="2032-06-30",
                                    security_update_commitment="支持期内免费提供安全更新（≥5年）"))
            # 集成
            db.add(Integration(node_id=ver.id, kind="sca", name="软安 SCA 检测集成",
                               endpoint="", config={}))
            db.add(Integration(node_id=ver.id, kind="public_disclosure", name="漏洞公开平台同步",
                               endpoint="https://example.org/api/vuln", config={}))
            # CVD 政策
            db.add(Policy(code="POL-CVD", title="协调漏洞披露政策", policy_type="cvd",
                          status="published", body_html="<p>公开的 CVD 政策正文……</p>"))
            # 演示评估
            db.add(Assessment(node_id=ver.id, library_id=lib.id, title="SecGW v2.1 CRA 合规评估",
                              created_by="assessor"))
            db.commit()
            created_count += 1

        if created_count:
            print(f"种子数据写入完成（新增 {created_count} 项）。")
        else:
            print("数据库已是最新，无需新增种子数据。")
        if settings.allow_demo_accounts:
            print("演示账号：admin/admin123, manager/manager123, assessor/assessor123, "
                  "auditor/auditor123, viewer/viewer123（仅演示环境，请及时改密）")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
