# CRA 合规平台（华南Test）

面向企业用户的 **欧盟《网络弹性法案》(EU Cyber Resilience Act, Regulation (EU) 2024/2847)** 产品合规管理平台。单客户私有部署，作为软件安全检测工具的附属交付平台。

## 核心能力

| 模块 | 说明 |
|------|------|
| 🌲 合规对象树 | 事业部 → 项目 → 产品 → 版本 四层结构，每个对象独立合规页面与 CRA 产品分类、符合性路径引导 |
| ✅ CRA 成熟度评估 | 内置 CRA 附录 I（基本要求+漏洞处理）27 条评估条目，融合 OWASP SAMM 五大功能，0-5 级打分、雷达图、合规就绪度 |
| 🧭 整改建议 | 基于知识库按打分自动生成差距分析 + 整改方向 + 推荐软安检测工具（SAST/SCA/BAT/FUZZ/MST…） |
| ⚠️ 风险登记册 | 固有/剩余风险评分、处置计划 |
| 🐞 漏洞管理 | CVSS 定级、状态流转、检测工具导入；**CRA 第14条 24h/72h/14d 通报时限看板**（已被利用漏洞自动生成通报单） |
| 📄 文档与模板 | 内置 10 类样板文档（DoC/技术文档/SBOM/风险报告/CVD政策/24h-72h-14d通报/安全公告/用户手册），**一键生成 + 导出 Word/JSON** |
| 📎 通用附件 | 任意业务对象（节点/评估/漏洞/文档…）均可上传/下载合规证据文件 |
| 🔌 工具集成 | 检测工具(SAST/SCA/BAT/FUZZ) mock 同步 + 漏洞公开平台真实 HTTP 拉取骨架 |
| 📜 日志审计 | 全量写操作留痕，按用户/资源/时间筛选 |
| 📊 合规仪表盘 | 产品就绪度、漏洞分布、通报时限告警全局态势 |

## 技术栈

- 后端：FastAPI + SQLAlchemy 2.0 + Pydantic v2 + SQLite（可换 PostgreSQL）
- 认证：JWT + bcrypt + 基于角色 RBAC（admin/manager/assessor/auditor/viewer）
- 前端：Vue 3 + Tailwind CSS + ECharts（单文件 SPA，CDN 引入，无需构建）
- 文档导出：python-docx（Word）、CycloneDX（SBOM）

## 快速开始

### 方式一：本地运行

```bash
cd backend
pip install -r requirements.txt
python -m app.seed              # 初始化数据库 + 种子数据（幂等）
python -m uvicorn app.main:app --reload --port 8000
```

> 若提示 `uvicorn: command not found`，用 `python -m uvicorn ...`（Python 脚本目录未加入 PATH 时）。

浏览器打开 **http://localhost:8000** （后端已静态托管前端）。
API 文档：http://localhost:8000/docs

### 方式二：Docker

```bash
docker-compose up --build
# 打开 http://localhost:8000
```

## 演示账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员（全部权限） |
| manager | manager123 | 合规经理（建对象树/集成） |
| assessor | assessor123 | 评估员（评估/漏洞/文档） |
| auditor | auditor123 | 审计员（可看审计日志） |
| viewer | viewer123 | 只读 |

## 端到端演示路径

1. 用 `admin` 登录 → **合规对象树**：已预置「智能终端事业部 → 车载网关项目 → 车载安全网关 SecGW(重要产品ClassII) → SecGW v2.1」
2. 选中版本节点 → **CRA 评估** → 打开预置评估，逐条打分 → 右侧雷达图与就绪度实时更新 → 「生成整改建议」看推荐工具
3. **漏洞管理** → 录入一条漏洞并设「已被利用=是」→ 「通报时限看板」自动出现 24h/72h/14d 通报单与倒计时
4. **文档与模板** → 点「欧盟符合性声明」→ 填字段一键生成 → 「导出 Word」
5. **工具集成** → 对「软安 SCA 检测集成」点「立即同步」→ 漏洞列表出现导入数据
6. **审计日志** → 查看以上全部操作留痕

## 生产部署要点

### 安全配置（务必）

- **设置强随机 `CRA_SECRET_KEY`**（如 `openssl rand -hex 32`）。启动时会自检：空值或命中已知默认占位符且 `CRA_ALLOW_INSECURE_SECRET=false` 时**拒绝启动**。
- **保持 `CRA_ALLOW_INSECURE_SECRET=false`**（默认），仅测试/本地演示设 true。
- **保持 `CRA_ALLOW_DEMO_ACCOUNTS=false`**（默认），避免生产环境出现 admin/admin123 等弱密码账号。演示账号仅上述两开关为 true 时由 `seed` 创建。
- **收紧 `CRA_CORS_ORIGINS`** 为具体域名（如 `https://your-domain.com`）。设为 `*` 时系统会自动关闭 `credentials` 以符合浏览器规范。
- 通过环境变量或 `.env` 注入配置，参考 `.env.example`。

### 数据库与部署

- 切换 PostgreSQL：设 `CRA_DATABASE_URL=postgresql+psycopg://...`
- 生产前置 nginx 反代 + HTTPS，uvicorn 去掉 `--reload`
- 多进程部署（如 gunicorn -w N）下，内存限流每进程独立计数，强限流场景建议接 Redis 后端

### 业务对接

- 漏洞公开平台真实对接：见 `backend/app/services/integrations.py` 的 `_fetch_public_disclosure_skeleton`，按目标平台 API 字段映射启用
- 检测工具集成：当前为 mock 样例，替换 `_mock_tool_findings` 为真实工具结果拉取
- AI 差距分析：配置 `CRA_ANTHROPIC_API_KEY` 后用 Claude 生成报告，否则走内置规则引擎

## 目录结构

```
cra-platform/
├── backend/app/
│   ├── main.py            # 入口、路由挂载、CORS、静态托管
│   ├── models.py          # 全部 ORM 模型
│   ├── auth.py            # JWT + RBAC
│   ├── routers.py         # 核心业务路由
│   ├── crud.py            # 通用 CRUD 路由工厂
│   ├── cra_content.py     # CRA 评估控制库内容
│   ├── doc_templates.py   # 10 类样板文档模板
│   ├── seed.py            # 种子数据
│   └── services/          # 文档生成/SBOM/通报时限/集成
├── frontend/index.html    # 单文件 SPA
├── docker-compose.yml
└── .env.example
```
