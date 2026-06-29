# CRA 合规平台 — 开发规范

## 核心原则（每次改代码前必读）
1. **改函数前先 grep 全量引用**：删除/重命名任何函数，必须先 `grep -n` 查看所有引用点，同步更新
2. **改完用 node --check 验证 JS 语法**：每次修改 `frontend/index.html` 后必须验证
3. **Python 后端修改后用 TestClient 验证**：改完 `backend/app/` 后必须跑 API 测试
4. **不累积死代码**：删除的功能必须清理所有残留引用（函数、变量、return语句、模板HTML）

## 项目结构
```
cra-platform/
├── frontend/index.html     # 单文件 Vue 3 SPA（所有前端代码）
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── models.py       # SQLAlchemy ORM 模型
│   │   ├── schemas.py      # Pydantic 请求/响应模型
│   │   ├── auth.py         # JWT认证 + RBAC权限
│   │   ├── database.py     # SQLite 连接
│   │   ├── crud.py         # 通用CRUD路由工厂
│   │   ├── seed.py         # 数据库初始化种子
│   │   ├── routers/        # 业务路由
│   │   │   ├── auth.py     # 登录 + 用户管理CRUD
│   │   │   ├── nodes.py    # 合规对象树
│   │   │   ├── assess.py   # CRA/SAMM 评估
│   │   │   ├── vulns.py    # 漏洞管理
│   │   │   ├── docs.py     # 文档模板 + 附件
│   │   │   ├── workflow_router.py  # 工作流审批
│   │   │   ├── dashboard_v2.py     # 高管态势
│   │   │   ├── sbom_router.py      # SBOM管理
│   │   │   ├── supplier_portal.py  # 供应商门户
│   │   │   └── misc.py    # 仪表盘 + 集成 + 审计
│   │   └── services/      # 业务服务层
│   ├── cra.db             # SQLite 数据库文件
│   └── uploads/           # 上传文件目录
└── docs/                  # GitHub Pages 部署目录（=frontend/ 副本）
```

## 数据库
- **文件**：`backend/cra.db`（SQLite）
- **修改ORM模型后必须手动ALTER TABLE**：`Base.metadata.create_all()` 只建表不更新列
- **迁移命令**：`sqlite3 backend/cra.db "ALTER TABLE xxx ADD COLUMN yyy TYPE"`

## 启动命令
```bash
cd backend && CRA_ALLOW_INSECURE_SECRET=true python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```
- 默认账号：`admin / admin123`
- 环境变量 `CRA_ALLOW_INSECURE_SECRET=true` 跳过弱密钥检查（仅本地开发）

## 前端架构
- 单文件 `frontend/index.html`：Vue 3 CDN + Tailwind CSS
- `createApp({ setup() { ... } }).mount('#app')` 模式
- 全局状态：`ref()` / `reactive()` 定义在 `setup()` 内
- 页面路由：`view.value` 切换，无 vue-router
- API 调用：`async function api(method, url, body, isForm)` 封装 fetch
- 认证：JWT token 存在 `token.value`，每次请求带 `Authorization: Bearer`

## 常见错误清单

### 1. 引用死代码
**症状**：页面空白（运行时 ReferenceError）
**原因**：删除了函数定义但模板/其他函数仍引用它
**修复**：`grep -n "函数名" frontend/index.html` 找所有引用，逐一清理

### 2. SQLAlchemy commit 后未 refresh  
**症状**：API 返回 `id: null` 或字段为空
**原因**：`db.commit()` 后对象 expired，FastAPI 序列化时读取不到属性
**修复**：每个 `db.commit()` 后加 `db.refresh(obj)`

### 3. 日期字符串转 datetime
**症状**：SQLite DateTime 类型报错
**原因**：前端 `<input type="date">` 传 `"2026-12-31"` 字符串，不能直接写入 DateTime 列
**修复**：后端用 `datetime.fromisoformat(str)` 转换

### 4. 转义字符错误
**症状**：JS 语法错误，`node --check` 报 Invalid token
**原因**：在 JS 单引号字符串内使用 `\'` 时多了一层转义
**修复**：避免深层转义，用简单字符串拼接

### 5. 函数未暴露到 return
**症状**：模板中 `@click="fn"` 不工作，控制台报 undefined
**原因**：在 setup() 内定义了函数但没加入 return 对象
**修复**：检查 `return { ... }` 是否包含该函数

### 6. 复制前端到 docs/ 
**修改 frontend/index.html 后**：`cp -r frontend/* docs/` 同步 GitHub Pages

## 已验证的函数引用完整性检查命令
```bash
cd frontend
# 检查某个函数的所有引用
grep -n "函数名" index.html
# JS语法验证
python -c "import re;c=open('index.html',encoding='utf-8').read();s=re.findall(r'<script>(.*?)</script>',c,re.DOTALL);open('/tmp/check.js','w').write(s[0])" && node --check /tmp/check.js
```
