# -*- coding: utf-8 -*-
"""文档模板示例 — 基于 CRA 实际要求 + 真实模板结构 (Heimdal/NIST/ISO 27001)。"""

DEMOS = {}
DEMOS["DOC-DOC"] = """<h1>EU Declaration of Conformity（欧盟符合性声明）</h1>
<p><strong>Document No:</strong> EU-DoC-SAFETECH-2026-001 | <strong>Date:</strong> 2026-06-28</p>
<p><strong>Manufacturer:</strong> 软安科技有限公司 | <strong>Address:</strong> 成都市高新区天府大道中段688号</p>
<p><strong>EU Authorised Representative:</strong> SafeTech Europe B.V., Amsterdam, Netherlands</p>
<br>
<h2>1. Product Identification</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Item</th><th>Details</th></tr>
<tr><td>Product Name</td><td>软安安全检测平台 SafeGuard Platform</td></tr>
<tr><td>Product Type</td><td>Software with digital elements — CRA Class I</td></tr>
<tr><td>Version</td><td>V3.0.1 (Build 20260615)</td></tr>
<tr><td>Intended Purpose</td><td>Enterprise software supply chain security: SAST, SCA, binary analysis, fuzz testing</td></tr>
</table>
<br>
<h2>2. Declaration</h2>
<p>This declaration of conformity is issued under the sole responsibility of the manufacturer. The object declared above conforms to:</p>
<ul><li><strong>Regulation (EU) 2024/2847 (Cyber Resilience Act)</strong> — Annex I</li><li><strong>Directive 2014/53/EU (RED)</strong> — Article 3.3(d)(e)(f)</li></ul>
<br>
<h2>3. Harmonised Standards Applied</h2>
<ul><li>EN 18031-1:2025 — Security by Design</li><li>EN 18031-2:2025 — Security by Default</li><li>EN 18031-3:2025 — Vulnerability Handling and Disclosure</li><li>ETSI EN 303 645 V2.1.1 — Consumer IoT Cybersecurity Baseline</li><li>IEC 62443-4-1:2018 — Secure Product Development Lifecycle</li><li>ISO/IEC 27001:2022 — Information Security Management</li></ul>
<br>
<h2>4. Conformity Assessment</h2>
<p><strong>Module:</strong> B+C (EU-type examination + internal production control)</p>
<p><strong>Notified Body:</strong> TUV Rheinland LGA Products GmbH (NB 0197)</p>
<p><strong>Certificate No:</strong> CRA-2026-CN-0312 | <strong>Valid until:</strong> 2031-06-27</p>
<br>
<h2>5. Signing</h2>
<p><strong>Signed by:</strong> Chang Le (常乐), CTO | <strong>Place:</strong> Chengdu, China | <strong>Date:</strong> 2026-06-28</p>
<p style="color:#888;font-size:10px"><em>Issued per CRA Article 10. Retained minimum 10 years after product placed on market.</em></p>"""

DEMOS["DOC-TECH"] = """<h1>Technical Documentation（技术文档）</h1>
<h2>SafeGuard Platform V3.0.1 — CRA Annex VII Compliance</h2>
<p><strong>Doc Ref:</strong> TECH-SAFE-2026 | <strong>Version:</strong> 1.0 | <strong>Date:</strong> 2026-06-28 | <strong>Classification:</strong> Confidential</p>
<br>
<h2>Section 1 — General Product Description</h2>
<p><strong>1.1 Product Identity:</strong> 软安安全检测平台 (SafeGuard Platform) V3.0.1 is a comprehensive software security detection and compliance management platform performing SAST, SCA, binary analysis (BAT), and protocol fuzzing (FUZZ).</p>
<p><strong>1.2 Intended Purpose:</strong> Enterprise software supply chain security management, SBOM generation, vulnerability assessment, and regulatory compliance (CRA, ISO/SAE 21434, GB 44495/44496).</p>
<p><strong>1.3 Software Versions:</strong> V3.0.1 (current, CRA-compliant). Support period: 5 years (until 2031-06-28).</p>
<br>
<h2>Section 2 — System Architecture</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Component</th><th>Technology</th><th>Version</th></tr>
<tr><td>Frontend</td><td>Vue 3 + Tailwind CSS + ECharts</td><td>3.4.0 / 3.4 / 5.5.0</td></tr>
<tr><td>Backend API</td><td>FastAPI (Python 3.11) + SQLAlchemy</td><td>0.115.0 / 2.0.30</td></tr>
<tr><td>Database</td><td>PostgreSQL 16 (prod) / SQLite 3 (demo)</td><td>16.4 / 3.44</td></tr>
<tr><td>Authentication</td><td>JWT (HS256) + bcrypt + RBAC (5 roles)</td><td>python-jose 3.3 / bcrypt 4.1</td></tr>
<tr><td>Web Server</td><td>Uvicorn + Nginx reverse proxy</td><td>0.29.0</td></tr>
<tr><td>Containerisation</td><td>Docker 24 + Docker Compose</td><td>24.0</td></tr>
<tr><td>SBOM Generator</td><td>软安SCA v4.2 (CycloneDX 1.5)</td><td>4.2</td></tr>
</table>
<br>
<h2>Section 3 — Security Controls (CRA Annex I Part I Mapping)</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>CRA Annex I.1 Requirement</th><th>Implementation</th></tr>
<tr><td>Security by Design & Default</td><td>STRIDE threat modeling; CSP headers; password min 8 chars; least privilege</td></tr>
<tr><td>Protection from Unauthorised Access</td><td>JWT + bcrypt + rate limiting + RBAC (5 roles)</td></tr>
<tr><td>Data Confidentiality & Integrity</td><td>TLS 1.3; AES-256 at rest; field-level encryption for secrets</td></tr>
<tr><td>Resilience against DoS</td><td>Rate limiting; connection pooling (20); resource limits</td></tr>
<tr><td>Data Minimisation</td><td>Only essential PII collected; auto-purge after retention</td></tr>
<tr><td>Vulnerability Handling</td><td>CVD policy per ISO/IEC 29147; 24h/72h/14d CRA notification</td></tr>
<tr><td>Secure by Default Configuration</td><td>Least privilege; unused ports closed; firewall deny-all</td></tr>
</table>
<br>
<h2>Section 4 — Support Period</h2>
<p>5 years (2026-2031). Critical patches: 7 days. High: 30 days. Medium: 90 days. OTA updates with Ed25519 signature verification.</p>
<br>
<h2>Section 5 — Test Reports Summary</h2>
<ul><li><strong>SAST Scan:</strong> 软安SAST v3.0 — 0 Critical, 0 High, 2 Medium (resolved)</li><li><strong>SCA Scan:</strong> 软安SCA v4.2 — 247 components, 12 CVEs, all mitigated</li><li><strong>Penetration Test:</strong> SecLab GmbH, June 2026 — No critical exploitable findings</li><li><strong>Fuzz Test:</strong> 软安Fuzz v2.0 — 100,000+ test cases, 0 crashes</li></ul>
<p style="color:#888;font-size:10px"><em>Per CRA Article 31 & Annex VII. Available within 10 days of reasoned request.</em></p>"""

DEMOS["DOC-SBOM"] = """<h1>Software Bill of Materials (SBOM)</h1>
<h2>CycloneDX 1.5 — SafeGuard Platform V3.0.1</h2>
<p><strong>SBOM Ref:</strong> SBOM-SAFEGUARD-20260615 | <strong>Generator:</strong> 软安SCA v4.2 | <strong>Date:</strong> 2026-06-15 14:30 UTC</p>
<br>
<h2>Executive Summary</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Metric</th><th>Value</th></tr>
<tr><td>Total Components</td><td>247</td></tr><tr><td>Open Source</td><td>203 (82.2%)</td></tr><tr><td>Commercial</td><td>44 (17.8%)</td></tr><tr><td>Known CVEs</td><td>12</td></tr><tr><td>Critical CVEs</td><td style="color:red">2</td></tr><tr><td>High CVEs</td><td style="color:orange">5</td></tr><tr><td>Medium CVEs</td><td style="color:gold">3</td></tr><tr><td>Low CVEs</td><td>2</td></tr><tr><td>Unique Licenses (SPDX)</td><td>34</td></tr><tr><td>License Conflicts</td><td style="color:red">1 (GPL-3.0 in proprietary)</td></tr>
</table>
<br>
<h2>Top Components</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Component</th><th>Version</th><th>License</th><th>CVE Count</th><th>Risk</th></tr>
<tr><td>requests</td><td>2.31.0</td><td>Apache-2.0</td><td>1 Critical</td><td style="color:red">Critical</td></tr>
<tr><td>certifi</td><td>2024.7.4</td><td>MPL-2.0</td><td>0</td><td style="color:green">Low</td></tr>
<tr><td>python-jose</td><td>3.3.0</td><td>MIT</td><td>0</td><td style="color:green">Low</td></tr>
<tr><td>bcrypt</td><td>4.1.0</td><td>Apache-2.0</td><td>0</td><td style="color:green">Low</td></tr>
<tr><td>uvicorn</td><td>0.29.0</td><td>BSD-3</td><td>0</td><td style="color:green">Low</td></tr>
<tr><td>fastapi</td><td>0.115.0</td><td>MIT</td><td>0</td><td style="color:green">Low</td></tr>
<tr><td>sqlalchemy</td><td>2.0.30</td><td>MIT</td><td>0</td><td style="color:green">Low</td></tr>
<tr><td>pydantic</td><td>2.7.0</td><td>MIT</td><td>0</td><td style="color:green">Low</td></tr>
<tr><td>httpx</td><td>0.27.0</td><td>BSD-3</td><td>1 High</td><td style="color:orange">High</td></tr>
<tr><td>cryptography</td><td>42.0.0</td><td>Apache-2.0</td><td>0</td><td style="color:green">Low</td></tr>
</table>
<br>
<h2>License Summary</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Category</th><th>Count</th></tr>
<tr><td>Permissive (MIT, Apache-2.0, BSD)</td><td>156</td></tr>
<tr><td>Weak Copyleft (LGPL, MPL)</td><td>18</td></tr>
<tr><td>Strong Copyleft (GPL)</td><td>10</td></tr>
<tr><td>Public Domain / Unlicense</td><td>8</td></tr>
</table>
<p style="color:#888;font-size:10px"><em>Generated by 软安SCA v4.2 per CRA Annex VII.8 & BSI TR-03183-2.</em></p>"""

DEMOS["DOC-RISK"] = """<h1>Cybersecurity Risk Assessment Report（网络安全风险评估报告）</h1>
<h2>SafeGuard Platform V3.0.1 — Pre-Market Security Evaluation</h2>
<p><strong>Report Ref:</strong> RISK-SAFEGUARD-202606 | <strong>Date:</strong> 2026-06-20 | <strong>Methodology:</strong> NIST CSF + STRIDE + CVSS 3.1 + CRA Annex I</p>
<br>
<h2>Section 1: Assessment Overview</h2>
<p><strong>Purpose:</strong> Compliance | Incident Response | InfoSec Program | Development</p>
<p><strong>Scope:</strong> All critical IT infrastructure, applications, and data. Includes network, servers, cloud services, third-party services.</p>
<p><strong>Assessment Team:</strong></p>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Name</th><th>Role</th><th>Department</th></tr>
<tr><td>Chang Le</td><td>Lead Assessor</td><td>Product Security</td></tr>
<tr><td>Li Wei</td><td>Security Engineer</td><td>DevSecOps</td></tr>
<tr><td>Wang Fang</td><td>Compliance Officer</td><td>GRC</td></tr>
</table>
<br>
<h2>Section 2: Asset Inventory</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Asset ID</th><th>Asset Name</th><th>Type</th><th>Owner</th><th>Criticality</th></tr>
<tr><td>A-01</td><td>Auth Service</td><td>Application</td><td>Backend Team</td><td>High</td></tr>
<tr><td>A-02</td><td>API Gateway</td><td>Infrastructure</td><td>DevOps</td><td>High</td></tr>
<tr><td>A-03</td><td>Assessment Database</td><td>Data</td><td>DBA Team</td><td>High</td></tr>
<tr><td>A-04</td><td>SBOM Generator</td><td>Application</td><td>SCA Team</td><td>Medium</td></tr>
<tr><td>A-05</td><td>Admin Dashboard</td><td>Application</td><td>Frontend Team</td><td>High</td></tr>
</table>
<br>
<h2>Section 3: Threat Identification</h2>
<p><strong>Threat Sources:</strong> External (Cybercriminals) | Internal (Employees, Contractors) | Third-Party (Vendors, Partners)</p>
<p><strong>Threat Types:</strong> Malware | Phishing | DDoS | Insider Threat | Ransomware | Supply Chain Attack</p>
<br>
<h2>Section 4: Risk Analysis</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>ID</th><th>Threat</th><th>Vulnerability</th><th>Impact</th><th>Likelihood</th><th>Risk Level</th></tr>
<tr><td>R-01</td><td>SQL Injection</td><td>Unvalidated API query params</td><td>High</td><td>Low</td><td style="color:orange">High (12)</td></tr>
<tr><td>R-02</td><td>XSS Attack</td><td>Rich text fields</td><td>Medium</td><td>Medium</td><td style="color:gold">Medium (8)</td></tr>
<tr><td>R-03</td><td>Credential Brute Force</td><td>Login endpoint</td><td>Medium</td><td>High</td><td style="color:gold">Medium (9)</td></tr>
<tr><td>R-04</td><td>Dependency CVE</td><td>Outdated packages</td><td>High</td><td>Medium</td><td style="color:orange">High (12)</td></tr>
<tr><td>R-05</td><td>JWT Forgery</td><td>Weak secret key</td><td>Critical</td><td>Low</td><td style="color:orange">High (10)</td></tr>
</table>
<br>
<h2>Section 5: Mitigation Actions</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>ID</th><th>Description</th><th>Owner</th><th>Deadline</th><th>Status</th></tr>
<tr><td>M-01</td><td>SQLAlchemy parameterised queries + input validation</td><td>Backend Lead</td><td>2026-07-15</td><td style="color:green">Completed</td></tr>
<tr><td>M-02</td><td>CSP headers + Vue auto-escaping</td><td>Frontend Lead</td><td>2026-07-10</td><td style="color:green">Completed</td></tr>
<tr><td>M-03</td><td>Rate limiting 5 req/min + account lockout</td><td>Security Lead</td><td>2026-07-01</td><td style="color:green">Completed</td></tr>
<tr><td>M-04</td><td>软安SCA automated CI/CD + daily CVE sync</td><td>DevSecOps</td><td>2026-06-30</td><td style="color:green">Completed</td></tr>
<tr><td>M-05</td><td>256-bit secret + 90-day key rotation</td><td>Security Lead</td><td>2026-07-01</td><td style="color:green">Completed</td></tr>
</table>
<br>
<h2>Section 6: Review & Approval</h2>
<p>The assessment identified 5 areas requiring mitigation. All High risks reduced to Low residual through technical controls. Strengths: incident response planning and encryption implementation.</p>
<p><strong>Recommendation:</strong> Proceed with market release under CRA Class I, Module B+C. Continue ongoing vulnerability monitoring per CRA Article 13.</p>
<p><strong>Approver:</strong> CISO | <strong>Date:</strong> 2026-06-25</p>
<p style="color:#888;font-size:10px"><em>Per CRA Article 13. Reviewed annually or upon significant product change.</em></p>"""

DEMOS["DOC-CVD"] = """<h1>Coordinated Vulnerability Disclosure Policy（漏洞协调披露政策）</h1>
<h2>软安科技 — CVD Policy</h2>
<p><strong>Policy Ref:</strong> CVD-POL-2026-v1 | <strong>Effective:</strong> 2026-01-01 | <strong>Version:</strong> 1.0</p>
<br>
<h2>1. Commitment</h2>
<p>软安科技有限公司 is committed to ensuring the security of our products and services. We recognise the valuable role of independent security researchers. This policy establishes our framework per ISO/IEC 29147:2018 and CRA Article 13.</p>
<br>
<h2>2. Scope</h2>
<p>This policy applies to all products: 软安SAST, 软安SCA, 软安BAT, 软安Fuzz, 软安MST, CodingHawk, GuardFox, and SafeGuard Platform.</p>
<br>
<h2>3. How to Report</h2>
<p><strong>Email:</strong> security@softsafe-tech.com</p>
<p><strong>PGP Key:</strong> 8F3C 9A2B D4E6 1F7A 5C8D 9E0B 2A4C 6D8F</p>
<p>Please include: product name/version, vulnerability description, reproduction steps, impact assessment.</p>
<br>
<h2>4. Our Commitments</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Action</th><th>Timeline</th></tr>
<tr><td>Acknowledgment</td><td>Within 72 hours</td></tr><tr><td>Status Updates</td><td>Every 14 days</td></tr>
<tr><td>Critical Fix</td><td>7 days</td></tr><tr><td>High Fix</td><td>30 days</td></tr>
<tr><td>Medium Fix</td><td>90 days</td></tr><tr><td>Public Credit</td><td>Upon mutual agreement</td></tr>
</table>
<br>
<h2>5. Safe Harbor</h2>
<p>We will not pursue legal action for good-faith security research conducted per this policy. We support responsible disclosure and coordinated publication timelines.</p>
<br>
<h2>6. CRA Article 14 Notifications</h2>
<p>Actively exploited critical vulnerabilities trigger: <strong>24h</strong> early warning to ENISA SRP → <strong>72h</strong> detailed notification → <strong>14d</strong> final report with root cause and preventive measures.</p>
<p style="color:#888;font-size:10px"><em>Per ISO/IEC 29147:2018. Last reviewed: 2026-06-28.</em></p>"""

DEMOS["DOC-INC24"] = """<h1>Early Warning Notification（漏洞早期预警 — 24小时）</h1>
<h2>CRA Article 14(1) — 脆弱性/事件早期预警通知</h2>
<p><strong>Notification Ref:</strong> INC-2026-003-EARLY | <strong>Date:</strong> 2026-06-28 08:00 UTC</p>
<p><strong>To:</strong> ENISA Single Reporting Platform (SRP) | <strong>From:</strong> 软安科技有限公司 (MFG-CN-2024-01234)</p>
<br>
<h2>1. Incident Summary</h2>
<p>A critical vulnerability has been identified in SafeGuard Platform V3.0.1. Submitted within 24 hours per CRA Article 14(1).</p>
<br>
<h2>2. Product Affected</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Item</th><th>Details</th></tr>
<tr><td>Product</td><td>SafeGuard Platform V3.0.1</td></tr>
<tr><td>Component</td><td>Requests library 2.31.0 — SSRF via HTTP redirect</td></tr>
<tr><td>CVE ID</td><td>CVE-2026-12345 (reserved)</td></tr>
<tr><td>CVSS 3.1</td><td><span style="color:red;font-weight:bold">9.8 (Critical)</span> — AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H</td></tr>
<tr><td>Exploitation</td><td><span style="color:red;font-weight:bold">ACTIVELY EXPLOITED</span> — 3 customer sites confirmed</td></tr>
<tr><td>Attack Vector</td><td>Remote, unauthenticated — crafted HTTP redirect to internal services</td></tr>
</table>
<br>
<h2>3. Affected Installations</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Region</th><th>Devices</th><th>Notified</th></tr>
<tr><td>EU/EEA</td><td>1,200</td><td>ENISA SRP</td></tr>
<tr><td>Asia-Pacific</td><td>2,500</td><td>Direct customer notification</td></tr>
<tr><td>Americas</td><td>500</td><td>Direct customer notification</td></tr>
<tr><td><strong>Total</strong></td><td><strong>4,200</strong></td><td></td></tr>
</table>
<br>
<h2>4. Immediate Mitigation</h2>
<ol><li><strong>Critical:</strong> Apply hotfix V3.0.2 (upgrades requests to >= 2.32.0)</li><li><strong>Workaround:</strong> Disable HTTP redirect following; restrict outbound HTTP to trusted hosts</li><li><strong>Monitor:</strong> Check logs for unusual outbound HTTP patterns to internal IP ranges</li></ol>
<br>
<h2>5. Next Steps</h2>
<ul><li>72h detailed notification by 2026-06-30</li><li>Final 14d report by 2026-07-10</li></ul>
<p><strong>24/7 Contact:</strong> security@softsafe-tech.com | <strong>Hotline:</strong> +86-400-857-0808</p>"""

DEMOS["DOC-INC72"] = """<h1>Vulnerability/Incident Notification（漏洞/事件通报 — 72小时）</h1>
<h2>CRA Article 14(2) — 72-Hour Detailed Notification</h2>
<p><strong>Notification Ref:</strong> INC-2026-003-NOTIFY | <strong>Date:</strong> 2026-06-30 14:00 UTC</p>
<p><strong>To:</strong> ENISA SRP | <strong>Follow-up to:</strong> INC-2026-003-EARLY (24h)</p>
<br>
<h2>1. Root Cause Analysis</h2>
<p>The vulnerability originates from insufficient validation of HTTP redirect targets in the Python requests library v2.31.0. The SSRF vulnerability allows an attacker to craft a malicious HTTP response with a Location header pointing to internal network resources (e.g., 169.254.169.254, 10.0.0.0/8, 127.0.0.1), causing the server to make unintended requests to internal services.</p>
<p><strong>Affected Code:</strong> requests/adapters.py — HTTPAdapter.send() redirect resolution</p>
<p><strong>Discovery:</strong> Zhang Wei (Tsinghua University) on 2026-06-26 via CVD channel</p>
<br>
<h2>2. Impact Assessment</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Dimension</th><th>Assessment</th></tr>
<tr><td>Confidentiality</td><td style="color:orange">High — Internal service data exposure</td></tr>
<tr><td>Integrity</td><td style="color:gold">Medium — Request manipulation possible</td></tr>
<tr><td>Availability</td><td style="color:green">Low — No DoS impact</td></tr>
<tr><td>Exploitability</td><td style="color:orange">High — Remote, unauthenticated</td></tr>
</table>
<br>
<h2>3. Corrective Actions</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Action</th><th>Status</th><th>Timeline</th></tr>
<tr><td>Patch V3.0.2: Upgrade requests to >= 2.32.0</td><td style="color:green">Deployed</td><td>2026-06-28</td></tr>
<tr><td>OTA update campaign</td><td style="color:green">In Progress</td><td>67.9% complete</td></tr>
<tr><td>WAF SSRF detection rules</td><td style="color:green">Deployed</td><td>2026-06-29</td></tr>
<tr><td>CI/CD SCA scan gate</td><td style="color:green">Deployed</td><td>2026-06-29</td></tr>
</table>
<br>
<h2>4. Affected Versions</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Version</th><th>Status</th></tr>
<tr><td>V3.0.1</td><td style="color:red">Vulnerable — Update immediately</td></tr>
<tr><td>V3.0.0 and earlier</td><td style="color:green">Not Affected</td></tr>
<tr><td>V3.0.2</td><td style="color:green">Fixed</td></tr>
</table>
<p><strong>Next:</strong> Final 14d report by 2026-07-10.</p>"""

DEMOS["DOC-INC14"] = """<h1>Final Incident Report（最终报告 — 14天）</h1>
<h2>CRA Article 14(3) — 14-Day Final Report</h2>
<p><strong>Report Ref:</strong> INC-2026-003-FINAL | <strong>Date:</strong> 2026-07-10 | <strong>Classification:</strong> Confidential</p>
<br>
<h2>1. Executive Summary</h2>
<p>Final report for CVE-2026-12345 (CVSS 9.8, SSRF). Discovered 2026-06-26, early warning within 24h, detailed notification within 72h. All 4,200 devices patched (100%). No data breach. Zero downtime.</p>
<br>
<h2>2. Complete Timeline</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Date</th><th>Event</th></tr>
<tr><td>2026-06-26 10:30</td><td>Reported via CVD channel</td></tr>
<tr><td>2026-06-26 14:00</td><td>Triaged Critical (CVSS 9.8)</td></tr>
<tr><td>2026-06-27 08:00</td><td>24h early warning to ENISA SRP</td></tr>
<tr><td>2026-06-28 16:00</td><td>Patch V3.0.2 released</td></tr>
<tr><td>2026-06-30 14:00</td><td>72h notification submitted</td></tr>
<tr><td>2026-07-05 12:00</td><td>100% remediation (4,200 devices)</td></tr>
<tr><td>2026-07-10 09:00</td><td>Final report submitted</td></tr>
</table>
<br>
<h2>3. Lessons Learned & Preventive Measures</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Finding</th><th>Measure</th><th>Status</th></tr>
<tr><td>Manual dependency check (weekly)</td><td>Automated daily SBOM monitoring</td><td style="color:green">Implemented</td></tr>
<tr><td>No SSRF WAF rules</td><td>SSRF detection signatures deployed</td><td style="color:green">Implemented</td></tr>
<tr><td>CI/CD lacked scan gate</td><td>SCA scan gate blocks Critical CVE</td><td style="color:green">Implemented</td></tr>
<tr><td>Incomplete network segmentation</td><td>Internal services isolated; metadata restricted</td><td style="color:green">Implemented</td></tr>
</table>
<br>
<h2>4. Customer Impact</h2>
<p>4,200 devices. 100% patched. 3 exploit attempts (contained). No data breach. Zero downtime. Time to patch: 48 hours.</p>
<p><strong>Prepared by:</strong> PSIRT | <strong>Approved by:</strong> CISO | <strong>Date:</strong> 2026-07-10</p>"""

DEMOS["DOC-ADV"] = """<h1>Security Advisory（安全更新公告）</h1>
<h2>SAFETECH-SA-2026-003 — CVE-2026-12345</h2>
<p><strong>Advisory ID:</strong> SAFETECH-SA-2026-003 | <strong>Published:</strong> 2026-06-29 | <strong>Updated:</strong> 2026-07-05</p>
<p><strong>Severity:</strong> <span style="color:red;font-weight:bold">CRITICAL — CVSS 9.8</span></p>
<br>
<h2>1. Summary</h2>
<p>A critical SSRF vulnerability in SafeGuard Platform V3.0.1 allows remote attackers to force the server to make unintended HTTP requests to internal services via crafted redirects (CVE-2026-12345).</p>
<br>
<h2>2. Vulnerability Details</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Attribute</th><th>Value</th></tr>
<tr><td>CVE ID</td><td>CVE-2026-12345</td></tr>
<tr><td>CVSS 3.1</td><td>9.8 (Critical) — AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H</td></tr>
<tr><td>CWE</td><td>CWE-918: Server-Side Request Forgery (SSRF)</td></tr>
<tr><td>Component</td><td>Python requests library v2.31.0</td></tr>
<tr><td>Discovery</td><td>Zhang Wei, Tsinghua University</td></tr>
</table>
<br>
<h2>3. Affected Products</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Product</th><th>Version</th><th>Status</th></tr>
<tr><td>SafeGuard Platform</td><td>V3.0.1</td><td style="color:red">Vulnerable — Update NOW</td></tr>
<tr><td>SafeGuard Platform</td><td>V3.0.0 and earlier</td><td style="color:green">Not Affected</td></tr>
<tr><td>SafeGuard Platform</td><td>V3.0.2</td><td style="color:green">Fixed</td></tr>
</table>
<br>
<h2>4. Resolution</h2>
<p><strong>Update to V3.0.2 immediately.</strong> OTA: Settings > System > Check for Updates. Manual: support.softsafe-tech.com/firmware/v3.0.2</p>
<br>
<h2>5. Workarounds</h2>
<ol><li>Disable HTTP redirect following</li><li>Configure outbound firewall: allow only known hosts</li><li>Block internal IP ranges at application network level</li><li>Monitor logs for requests to internal IPs</li></ol>
<br>
<h2>6. Acknowledgments</h2>
<p>Zhang Wei, Tsinghua University Network Security Lab — responsible disclosure via CVD program.</p>
<p style="color:#888;font-size:10px"><em>Per CRA Article 13 & ISO/IEC 29147:2018.</em></p>"""

DEMOS["DOC-USER"] = """<h1>Product Security User Manual（产品安全使用手册）</h1>
<h2>SafeGuard Platform V3.0 — 安全配置与运维指南</h2>
<p><strong>Doc Ref:</strong> USER-SEC-SAFEGUARD-2026 | <strong>Audience:</strong> System Administrators, Security Teams</p>
<br>
<h2>1. Initial Setup & Hardening</h2>
<h3>1.1 First Login</h3>
<ol><li>Access https://[host]:443</li><li>Default: admin / [printed on license certificate]</li><li>You must change password on first login</li><li>Password: min 12 chars, mixed case + digits + special</li><li>Enable MFA (TOTP) — strongly recommended</li></ol>
<h3>1.2 Hardening Checklist</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>#</th><th>Action</th><th>Priority</th></tr>
<tr><td>1</td><td>Change default admin password (min 12 chars)</td><td style="color:red">Critical</td></tr>
<tr><td>2</td><td>Enable MFA for all admin accounts</td><td style="color:red">Critical</td></tr>
<tr><td>3</td><td>Install valid TLS certificate (no self-signed)</td><td style="color:orange">High</td></tr>
<tr><td>4</td><td>Restrict database access to app server only</td><td style="color:orange">High</td></tr>
<tr><td>5</td><td>Enable audit logging + SIEM forwarding (syslog/TLS)</td><td style="color:orange">High</td></tr>
<tr><td>6</td><td>Configure encrypted daily backups</td><td style="color:orange">High</td></tr>
<tr><td>7</td><td>Enable automatic security update checks</td><td style="color:orange">High</td></tr>
<tr><td>8</td><td>Set up email/SMS alerting for security events</td><td style="color:gold">Medium</td></tr>
<tr><td>9</td><td>Review and remove default service accounts</td><td style="color:gold">Medium</td></tr>
<tr><td>10</td><td>Configure rate limiting and account lockout</td><td style="color:orange">High</td></tr>
</table>
<br>
<h2>2. Regular Maintenance</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1a3a5c;color:#fff"><th>Frequency</th><th>Task</th></tr>
<tr><td>Daily</td><td>Review security dashboard and alerts; verify backups</td></tr>
<tr><td>Weekly</td><td>Check for software updates; review new CVE advisories</td></tr>
<tr><td>Monthly</td><td>Review user access; audit admin actions; rotate API keys</td></tr>
<tr><td>Quarterly</td><td>Vulnerability scan; firewall rule review; incident response drill</td></tr>
<tr><td>Annually</td><td>Penetration test; disaster recovery drill; compliance audit</td></tr>
</table>
<br>
<h2>3. Incident Response</h2>
<p>If you suspect a security incident:</p>
<ol><li>Do NOT reboot — preserve volatile memory for forensics</li><li>Disconnect from network immediately</li><li>Export all logs: Settings > Diagnostics > Export All Logs</li><li>Document all actions (who, what, when)</li><li>Contact PSIRT: security@softsafe-tech.com | +86-400-857-0808 (24/7)</li></ol>
<br>
<h2>4. End-of-Life Disposal</h2>
<ol><li>Export all data for archival</li><li>Secure Erase: Settings > System > Factory Reset > Secure Erase (DoD 3-pass)</li><li>Delete all cryptographic material and uploaded files</li><li>Revoke all API tokens</li><li>Document decommissioning date and data destruction method</li></ol>
<p style="color:#888;font-size:10px"><em>Latest version: support.softsafe-tech.com/docs | Document v1.0, 2026-06-28.</em></p>""",
