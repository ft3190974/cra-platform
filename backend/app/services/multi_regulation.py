"""多法规框架支持 — ISO 21434, GBT 44495/96。"""
from sqlalchemy.orm import Session
from ..models import RegulationFramework, ControlLibrary, ControlDomain, ControlItem, now

# 预定义法规框架
FRAMEWORKS = {
    "ISO21434": {
        "name": "ISO 21434", "full_name": "ISO/SAE 21434:2021 道路车辆—网络安全工程",
        "domains": [
            {"code": "ORG", "name": "组织级网络安全管理", "items": [
                ("ORG-01", "网络安全治理", "是否建立了网络安全治理框架？", "§5"),
                ("ORG-02", "网络安全文化", "是否建立了网络安全文化？", "§5"),
                ("ORG-03", "信息共享", "是否有网络安全信息共享机制？", "§5"),
                ("ORG-04", "供应商管理", "是否对供应商进行网络安全要求管理？", "§5"),
            ]},
            {"code": "PROJ", "name": "项目级网络安全管理", "items": [
                ("PROJ-01", "网络安全计划", "是否制定了项目网络安全计划？", "§6"),
                ("PROJ-02", "TARA 分析", "是否进行了威胁分析与风险评估(TARA)？", "§8"),
                ("PROJ-03", "安全概念", "是否制定了网络安全概念？", "§9"),
            ]},
            {"code": "DEV", "name": "网络安全开发", "items": [
                ("DEV-01", "安全设计", "是否将安全要求融入设计？", "§10"),
                ("DEV-02", "安全编码", "是否有安全编码规范？", "§10"),
                ("DEV-03", "安全测试", "是否进行了网络安全测试？", "§11"),
            ]},
            {"code": "OPS", "name": "网络安全运维", "items": [
                ("OPS-01", "漏洞管理", "是否建立了漏洞管理流程？", "§13"),
                ("OPS-02", "事件响应", "是否有网络安全事件响应流程？", "§13"),
                ("OPS-03", "持续监控", "是否对车辆网络安全进行持续监控？", "§13"),
            ]},
        ]
    },
    "GBT44495": {
        "name": "GB/T 44495/96", "full_name": "GB/T 44495-2024/44496-2024 汽车信息安全",
        "domains": [
            {"code": "GEN", "name": "通用要求", "items": [
                ("GEN-01", "信息安全策略", "是否制定了汽车信息安全策略？", "§4"),
                ("GEN-02", "资产管理", "是否建立了车辆信息资产管理机制？", "§5"),
            ]},
            {"code": "DESIGN", "name": "安全设计", "items": [
                ("DES-01", "安全架构", "是否设计了分层安全架构？", "§6"),
                ("DES-02", "访问控制", "是否实现了最小权限访问控制？", "§7"),
                ("DES-03", "密码应用", "是否合规使用密码技术？", "§8"),
            ]},
            {"code": "TEST", "name": "安全测试", "items": [
                ("TST-01", "渗透测试", "是否进行了渗透测试？", "§9"),
                ("TST-02", "模糊测试", "是否进行了协议模糊测试？", "§9"),
            ]},
        ]
    }
}


def seed_frameworks(db: Session):
    """初始化多法规框架（幂等）。"""
    for code, fw in FRAMEWORKS.items():
        reg = db.query(RegulationFramework).filter_by(code=code).first()
        if not reg:
            reg = RegulationFramework(code=code, name=fw["name"], full_name=fw["full_name"],
                                      domain_count=len(fw["domains"]),
                                      item_count=sum(len(d["items"]) for d in fw["domains"]))
            db.add(reg)
            db.flush()

            lib = ControlLibrary(code=f"CTRL_{code}", name=f"{fw['name']} 控制库",
                                 regulation=code, framework_type=code.lower())
            db.add(lib)
            db.flush()

            for di, dom in enumerate(fw["domains"]):
                cd = ControlDomain(library_id=lib.id, code=dom["code"],
                                   name=dom["name"], order=di)
                db.add(cd)
                db.flush()
                for ii, (code, title, question, ref) in enumerate(dom["items"]):
                    db.add(ControlItem(domain_id=cd.id, code=code, title=title,
                                       question=question, cra_ref=ref, order=ii,
                                       max_level=5, weight=1.0,
                                       remediation=[
                                           "建立基础流程，制定初步制度文件",
                                           "完善管理流程，配置责任人",
                                           "建立度量体系，定期审查改进",
                                           "自动化监控，量化评估",
                                           "持续优化，行业最佳实践"
                                       ]))
    db.commit()
