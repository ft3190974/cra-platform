# -*- coding: utf-8 -*-
"""内置样板文档模板（带 {{变量}} 占位符，可一键生成 + 导出）。"""

TEMPLATES = [
    {"code": "DOC-DOC", "name": "欧盟符合性声明 (EU Declaration of Conformity)",
     "doc_type": "DoC", "cra_ref": "CRA 附录 V", "stage": "符合性声明",
     "fields": [{"key": "manufacturer", "label": "制造商名称"},
                {"key": "address", "label": "制造商地址"},
                {"key": "product_name", "label": "产品名称"},
                {"key": "product_model", "label": "型号/版本"},
                {"key": "doc_number", "label": "声明编号"}],
     "body_html": """<h1>欧盟符合性声明 (EU Declaration of Conformity)</h1>
<p>声明编号：{{doc_number}}</p>
<h2>1. 产品</h2>
<p>产品名称：{{product_name}}　型号/版本：{{product_model}}</p>
<p>CRA 产品类别：{{product_class}}</p>
<h2>2. 制造商</h2>
<p>{{manufacturer}}，{{address}}</p>
<h2>3. 声明</h2>
<p>本符合性声明在制造商唯一责任下出具。兹声明上述产品符合 Regulation (EU) 2024/2847
（网络弹性法案）附录 I 规定的基本网络安全要求。</p>
<h2>4. 适用的协调标准/规范</h2>
<p>（列出所采用的协调标准或共同规范）</p>
<h2>5. 公告机构（如适用）</h2>
<p>（公告机构名称、识别号、所执行的合格评定与证书编号）</p>
<h2>6. 附加信息</h2>
<p>签署人：__________　职务：__________　地点：__________　日期：{{date}}</p>"""},

    {"code": "DOC-TECH", "name": "技术文档 (Technical Documentation)",
     "doc_type": "tech_doc", "cra_ref": "CRA 附录 VII", "stage": "技术文档",
     "fields": [{"key": "product_name", "label": "产品名称"},
                {"key": "manufacturer", "label": "制造商"}],
     "body_html": """<h1>技术文档 — {{product_name}}</h1>
<p>制造商：{{manufacturer}}　日期：{{date}}　CRA 类别：{{product_class}}</p>
<h2>1. 产品总体描述</h2>
<p>用途、预期使用环境、关键功能与架构。</p>
<h2>2. 设计与开发信息</h2>
<p>系统架构图、数据流、组件清单(SBOM)、安全设计说明。</p>
<h2>3. 网络安全风险评估</h2>
<p>风险识别、评估方法、风险处置与剩余风险。</p>
<h2>4. 基本要求符合性（附录 I 第一部分）</h2>
<p>逐条说明产品如何满足各项基本网络安全要求。</p>
<h2>5. 漏洞处理（附录 I 第二部分）</h2>
<p>漏洞处理流程、SBOM、协调披露政策、安全更新机制。</p>
<h2>6. 测试与验证</h2>
<p>所执行的安全测试（SAST/SCA/Fuzz/渗透）及结果摘要。</p>
<h2>7. 支持期</h2>
<p>支持期起止、安全更新承诺。</p>"""},

    {"code": "DOC-SBOM", "name": "软件物料清单 (SBOM / CycloneDX)",
     "doc_type": "sbom", "cra_ref": "CRA 附录 I 第二部分(1)", "stage": "成分分析",
     "fields": [],
     "body_html": "<h1>SBOM</h1><p>（生成时自动嵌入该产品组件的 CycloneDX JSON）</p>"},

    {"code": "DOC-RISK", "name": "网络安全风险评估报告",
     "doc_type": "risk", "cra_ref": "CRA 附录 I 第一部分(1)", "stage": "风险评估",
     "fields": [{"key": "product_name", "label": "产品名称"}],
     "body_html": """<h1>网络安全风险评估报告 — {{product_name}}</h1>
<p>日期：{{date}}</p>
<h2>1. 评估范围与方法</h2>
<h2>2. 资产与攻击面识别</h2>
<h2>3. 威胁与脆弱性分析</h2>
<h2>4. 风险评定（固有/剩余）</h2>
<h2>5. 风险处置计划</h2>
<h2>6. 结论</h2>"""},

    {"code": "DOC-CVD", "name": "协调漏洞披露政策 (CVD Policy)",
     "doc_type": "cvd_policy", "cra_ref": "CRA 附录 I 第二部分(5)", "stage": "漏洞处理",
     "fields": [{"key": "manufacturer", "label": "制造商"},
                {"key": "contact", "label": "漏洞报告联系方式"}],
     "body_html": """<h1>协调漏洞披露政策</h1>
<p>{{manufacturer}}　生效日期：{{date}}</p>
<h2>1. 适用范围</h2>
<h2>2. 漏洞报告渠道</h2><p>报告联系方式：{{contact}}</p>
<h2>3. 处理流程与响应时限</h2>
<h2>4. 协调披露时间线</h2>
<h2>5. 安全研究者豁免声明</h2>"""},

    {"code": "DOC-INC24", "name": "漏洞/事件早期预警表单 (24小时)",
     "doc_type": "incident", "cra_ref": "CRA 第14条 (24h 早期预警)", "stage": "通报",
     "fields": [{"key": "product_name", "label": "产品名称"},
                {"key": "incident_summary", "label": "事件摘要"}],
     "body_html": """<h1>早期预警通报（24 小时）</h1>
<p>提交至：ENISA 单一报告平台(SRP) / 主营所在地 CSIRT　日期：{{date}}</p>
<h2>受影响产品</h2><p>{{product_name}}（CRA 类别：{{product_class}}）</p>
<h2>事件/漏洞摘要</h2><p>{{incident_summary}}</p>
<h2>是否已被利用</h2><p>（是/否）</p>
<h2>初步影响评估</h2>
<h2>已采取的初步措施</h2>"""},

    {"code": "DOC-INC72", "name": "漏洞/事件通报表单 (72小时)",
     "doc_type": "incident", "cra_ref": "CRA 第14条 (72h 通报)", "stage": "通报",
     "fields": [{"key": "product_name", "label": "产品名称"}],
     "body_html": """<h1>漏洞/事件通报（72 小时）</h1>
<p>提交至：ENISA SRP / CSIRT　日期：{{date}}</p>
<h2>受影响产品</h2><p>{{product_name}}</p>
<h2>事件性质与严重程度</h2>
<h2>受影响范围与用户数</h2>
<h2>缓解与修复措施</h2>
<h2>暴露指标(IoC)</h2>"""},

    {"code": "DOC-INC14", "name": "最终报告 (14天)",
     "doc_type": "incident", "cra_ref": "CRA 第14条 (最终报告)", "stage": "通报",
     "fields": [{"key": "product_name", "label": "产品名称"}],
     "body_html": """<h1>最终报告</h1>
<p>受影响产品：{{product_name}}　日期：{{date}}</p>
<h2>1. 事件根因分析</h2>
<h2>2. 完整影响评估</h2>
<h2>3. 已实施的修复与缓解</h2>
<h2>4. 预防再发措施</h2>
<h2>5. 经验教训</h2>"""},

    {"code": "DOC-ADV", "name": "安全更新公告 (Security Advisory)",
     "doc_type": "update_notice", "cra_ref": "CRA 附录 I 第二部分(7)(8)", "stage": "安全更新",
     "fields": [{"key": "product_name", "label": "产品名称"},
                {"key": "version", "label": "修复版本"},
                {"key": "cve", "label": "CVE 编号"}],
     "body_html": """<h1>安全更新公告</h1>
<p>产品：{{product_name}}　修复版本：{{version}}　日期：{{date}}</p>
<h2>漏洞概述</h2><p>编号：{{cve}}</p>
<h2>影响版本与严重程度</h2>
<h2>修复方案与升级指引</h2>
<h2>缓解措施（如暂无法升级）</h2>
<h2>致谢</h2>"""},

    {"code": "DOC-USER", "name": "用户安全使用手册",
     "doc_type": "user_manual", "cra_ref": "CRA 附录 II", "stage": "用户信息",
     "fields": [{"key": "product_name", "label": "产品名称"},
                {"key": "manufacturer", "label": "制造商"},
                {"key": "contact", "label": "联系方式"}],
     "body_html": """<h1>用户安全使用手册 — {{product_name}}</h1>
<p>制造商：{{manufacturer}}　联系方式：{{contact}}</p>
<h2>1. 安全配置指引</h2>
<h2>2. 安全功能说明</h2>
<h2>3. 支持期与安全更新</h2>
<h2>4. 已知限制与安全注意事项</h2>
<h2>5. 漏洞报告渠道</h2><p>{{contact}}</p>
<h2>6. 产品停止支持(EoL)安排</h2>"""},
]
