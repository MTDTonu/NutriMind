# 知食 NutriMind · 看懂你怎么吃

> 面向普通减重人群的 AI 饮食教练：**15 秒记完一餐 → 自适应代谢校准目标 → 把记录翻译成每天一条可执行建议**。
> 内置 220 条中餐食物库，前后端一体、纯本地即可运行，**默认走智谱永久免费模型**，开箱零成本。
>
> 品牌标识与全站文案集中在 `frontend/src/config/brand.js`，改名只需动这一处。

![Vue](https://img.shields.io/badge/Vue-3.4-42b883?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5.4-646cff?logo=vite&logoColor=white)
![Vant](https://img.shields.io/badge/Vant-4.9-1989fa)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003b57?logo=sqlite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 界面预览

> 截图均来自真实运行实例（设计系统「温润生机 · Warm Humanist」，暖白底 + 青柠 `#c6f24e` 唯一强调色）。
> 注：桌面端与移动端主要页面为当前版本实拍；「拍照识别结果」与「大模型配置」两张拍摄于改版之前，需配置视觉模型 Key 才能复现。

### 桌面端 · 核心链路

<table>
  <tr>
    <td width="50%">
      <img src="docs/screenshots/home.png" alt="首页总览">
      <br><sub><b>首页工作台</b> · 今日能量环、三大营养素进度、AI 一日食谱、快捷入口</sub>
    </td>
    <td width="50%">
      <img src="docs/screenshots/diet.png" alt="饮食记录">
      <br><sub><b>饮食记录</b> · 按早/午/晚/加餐分组，缩略图 + <code>识别</code>/<code>手动</code> 来源标记</sub>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="docs/screenshots/diet-recognize.png" alt="拍照识别结果">
      <br><sub><b>拍照识别结果</b> · 逐项可改，「共识别到 N 项」+ <b>数量</b>字段（同名多件不合并）</sub>
    </td>
    <td width="50%">
      <img src="docs/screenshots/stats.png" alt="数据统计">
      <br><sub><b>数据统计</b> · 结论先行（下降 X kg / 每周 Y kg / 还需 N 天）+ 体重曲线与目标线 + 三图并列 + 可排序每日明细表</sub>
    </td>
  </tr>
</table>

### 桌面端 · 更多功能

<table>
  <tr>
    <td width="50%">
      <img src="docs/screenshots/diet-text.png" alt="文字记录">
      <br><sub><b>文字输入</b> · 与拍照识别互补的第二条录入通道（双模态）</sub>
    </td>
    <td width="50%">
      <img src="docs/screenshots/exercise.png" alt="运动与饮水">
      <br><sub><b>运动 + 饮水</b> · 32 项运动库（6 分类 + MET）+ 时长档位实时预估 + 本周小结，饮水目标 = 体重 × 35ml</sub>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="docs/screenshots/ai.png" alt="AI 助手">
      <br><sub><b>AI 助手</b> · 顶部「今日画像」（目标 / 已摄入 / 剩余 / 蛋白 / 运动 / 体重）+ 按处境生成的提问建议 + 流式输出 + 长期记忆</sub>
    </td>
    <td width="50%">
      <img src="docs/screenshots/mine.png" alt="我的">
      <br><sub><b>我的</b> · 智能目标（按速度 / 按缺口 + 校准证据）、提醒设置、数据导入导出、大模型配置</sub>
    </td>
  </tr>
</table>

### 配置面板 & 双主题

<table>
  <tr>
    <td width="50%">
      <img src="docs/screenshots/ai-settings.png" alt="大模型配置">
      <br><sub><b>大模型配置</b> · 文字/视觉/语音三套独立可混搭，实时列出厂商<b>免费模型清单</b></sub>
    </td>
    <td width="50%">
      <img src="docs/screenshots/home-dark.png" alt="深色皮肤">
      <br><sub><b>深色皮肤</b> · 与暖白默认主题共用同一套 CSS 变量 token，一键切换</sub>
    </td>
  </tr>
</table>

### 移动端

<table>
  <tr>
    <td width="33%"><img src="docs/screenshots/mobile-home.png" alt="移动端首页"><br><sub>首页</sub></td>
    <td width="33%"><img src="docs/screenshots/mobile-diet.png" alt="移动端饮食记录"><br><sub>饮食记录</sub></td>
    <td width="33%"><img src="docs/screenshots/mobile-stats.png" alt="移动端数据统计"><br><sub>数据统计</sub></td>
  </tr>
</table>

---

## 核心特性

| 能力 | 说明 |
| --- | --- |
| **拍照识别饮食** | 上传食物照片 → 视觉大模型识别 → **逐项可编辑**（名称 / **数量** / 重量 / 热量 / 蛋白 / 脂肪 / 碳水）→ 确认后落库。同名多件<u>不合并</u>，按「数量 × 单份」计 |
| **文字快速记录** | 餐次 + 描述 + 营养数值，秒级录入 |
| **前端图片压缩** | 手机原图常 6–12MB 或为 HEIC/WebP，前端先 canvas 压到 1600px / ≤2MB 并统一转 JPEG 再上传，规避「超出 5MB」与「格式不支持」两类失败 |
| **AI 一日食谱** | 结合 BMI / 推荐热量 / 饮食偏好与忌口生成早午晚三餐并落库；无 Key 时自动降级为本地通用方案 |
| **多轮营养对话** | SSE 流式输出 + Markdown 渲染 + 多会话管理 + 长期记忆（可开关） |
| **每日复盘** | 每日 ≤300 字饮食运动小结 |
| **数据看板** | 体重趋势（日/周/月 + 目标线）、营养分析（柱状 + 供能比饼图）、周度报告；首屏直接给**结论**（下降 X kg，平均每周 Y kg，照此速度还需 N 天） |
| **全维度记录** | 体重 / 运动（32 项运动库 + MET 估算 + 周小结）/ 饮水（体重 × 35ml）/ 连续打卡 / 成就徽章 |
| **内置食物库** | 220 条中餐食物（11 分类）：每 100g 营养 + 份量单位 + 来源 + 置信度，热量由 Atwater 反算保证自洽；搜索按「收藏 → 命中位置 → 使用频次」重排 |
| **食量换算入库** | 选食物 → 选份量（碗/个/份/克）→ 即时换算热量与三大营养素 → 一次点击落库，不用手算 |
| **自适应代谢校准** | 用体重曲线做最小二乘拟合反推真实 TDEE（7700 kcal/kg），数据不足明确拒绝；BMR 1.1~2.5 倍夹逼、缺口 ≤25% TDEE、周降 ≤1.0kg；目标支持「按速度 / 按缺口」双模式 |
| **提醒触达** | 三餐 / 称重 / 饮水 / 免打扰设置 → 到点弹**系统通知 + 应用内提示条**（未授权也不丢提示），每条当天只响一次 |
| **数据导入导出** | 导出 CSV / JSON（UTF-8 BOM，Excel 直接打开）；导入体重 / 饮食**幂等**（同日更新不重复），脏行返回具体行号与原因 |
| **后台提醒（Web Push）** | 除页面内的前台提醒外，服务端按提醒设置经 VAPID 加密推送到设备通知中心——**关掉浏览器也会响**；当天每槽位只推一次、免打扰跳过、失效订阅自动清理 |
| **离线可用** | 断网时写请求（记一餐 / 记体重 / 记饮水 / 记运动）进 IndexedDB 队列，联网自动补发；关键读数接口有 12 小时缓存兜底，页面顶部状态条显示待同步条数 |
| **PWA** | 可安装到桌面 / 手机主屏，Service Worker 缓存应用壳支持断网打开 |
| **运行时配 Key** | 「我的 → 大模型配置」在线填 Key，保存即写库（**加密存储**）并同步 `.env`，无需手改文件、无需重启 |
| **双皮肤** | 暖白默认皮肤 / 深色皮肤一键切换，共用同一套 CSS 变量 token |
| **移动优先** | 320–768px 自适应，REM + 断点方案，Vant 组件体系 |

---

## 技术栈

| 层 | 选型 |
| --- | --- |
| 前端 | Vue 3.4 · Vite 5.4 · Pinia 2 · Vue Router 4 · Vant 4.9 · ECharts 5 · Axios · Less · markdown-it |
| 后端 | Python 3.10+ · FastAPI 0.115 · Uvicorn 0.30 · SQLAlchemy 2.0 · Pydantic 2.9 · PyJWT · passlib(bcrypt) · httpx |
| 数据 | SQLite 3（零运维，首次启动自动建表；14 张表）；设 `DATABASE_URL` 即切 PostgreSQL，配套 `scripts/migrate_to_pg.py` 一键搬迁 |
| AI | 智谱开放平台 `zhipuai` SDK；默认 `glm-4-flash`（文字）/ `glm-4v-flash`（视觉），**均为永久免费**；可选阿里云百炼 / 字节豆包 / 百度文心 / 任意 OpenAI 兼容端点 |
| 安全 | bcrypt 密码哈希 · JWT 鉴权中间件 · 静态加密的 API Key · 上传文件 magic-bytes 校验 |
| 部署 | 开发：Vite dev server + `--reload`；生产：**单端口**由 FastAPI 统一托管前端构建产物 |
| 推送 | VAPID（Web Push）· `pywebpush` · Service Worker `push` / `notificationclick` / `pushsubscriptionchange` |

---

## 系统架构

```
┌──────────────────────── 浏览器（移动优先 / 桌面自适应） ─────────────────────────┐
│  Vue 3 + Vant 4 + Pinia + Vue Router                                             │
│    views/  Login · Register · ProfileInit · Home · DietRecord · Exercise          │
│            Stats · AiPage · Mine                                                  │
│    api/    request.js（拦截器：注入 JWT / 统一拆包 / 401 跳登录）                  │
└───────────────────────────────────┬──────────────────────────────────────────────┘
                                    │  /api/v1/**   （开发：Vite proxy；生产：同源）
                                    ▼
┌──────────────────────────── FastAPI 应用 ────────────────────────────────────────┐
│  middleware/auth.py   JWT 鉴权（仅拦截 /api/**，OPTIONS 预检放行）                │
│  middleware/cors.py   CORS 白名单                                                 │
│  routers/  auth · user · diet · weight · exercise · water · stats · ai             │
│  services/ 业务逻辑（auth / user / diet / stats / calc / ai）                     │
│  schemas/  Pydantic v2 请求 & 响应模型（全局 RequestValidationError → 400）        │
└───────────────┬──────────────────────────────────┬───────────────────────────────┘
                │                                  │
                ▼                                  ▼
        SQLite  diet.db                    智谱 / 兼容 OpenAI 大模型
        8 张业务表                          · recognize-food（视觉）
        （首次启动自动建表）                 · generate-plan / chat / stream（文字）
                                           · 用户自带 Key（Fernet 加密落库）
```

**单端口部署模式**：`FRONTEND_DIST` 指向 `frontend/dist` 时，后端在**导入期**先注册 `/uploads` 静态目录，再挂载 SPA，最后用 `GET /{full_path:path}` 兜底回退到 `index.html`；`/api/**` 与 `/docs`、`/openapi.json` 优先级更高，互不干扰。一个进程、一个端口、无跨域。

---

## 目录结构

```
JianFeiWeb/
├── start.bat / stop.bat / deploy.bat   # 一键脚本入口（双击即可，调用 scripts/*.ps1）
├── scripts/                            # 一键脚本实现（PowerShell，UTF-8 BOM）
│   ├── start.ps1                       # 开发模式：后端 8000 + 前端 5173
│   ├── deploy.ps1                      # 生产模式：构建 + 单端口托管
│   ├── stop.ps1                        # 按端口/进程名清理残留进程
│   ├── gen_icons.py                    # 由 favicon 图形生成 PWA 图标（Pillow）
│   └── migrate_to_pg.py                # SQLite → PostgreSQL 搬迁（干跑 / 校验 / 重置序列）
├── docs/
│   ├── audit-report.md                 # 全量审计报告与逐条修复记录
│   ├── 升级方案.md
│   └── screenshots/                    # README 演示截图
├── backend/
│   ├── main.py                         # 入口：CORS → 鉴权 → 路由 → 静态/SPA → 全局异常
│   ├── .env.example                    # 环境变量模板（复制为 .env）
│   ├── requirements.txt
│   ├── database/    db.py（引擎/会话，支持 DATABASE_URL 切 PG）· models.py（14 张表）
│   ├── data/        foods_seed.py（220 条内置食物库）
│   ├── routers/     auth · user · diet · weight · exercise · water · stats · ai · food · energy · data · push
│   ├── services/    auth · user · diet · stats · calc · ai · food · energy · data（导出导入）
│   │                brief（今日画像）· push（VAPID/Web Push）· reminder_scheduler（服务端调度）
│   ├── schemas/     auth · user · diet · stats · ai · ai_settings · food · energy · data · push
│   ├── middleware/  auth.py（JWT）· cors.py
│   ├── utils/       security.py · common.py · exceptions.py
│   └── uploads/     # 图片存储（自动创建，UUID 重命名）
│   └── seed_demo.py # 演示数据（默认 14 天，幂等可重复执行）
└── frontend/
    ├── index.html / package.json / vite.config.js / public/（favicon · manifest · sw.js · icons/）
    ├── .env.development / .env.production
    └── src/
        ├── main.js · App.vue · router/ · store/modules（app · user）
        ├── api/         request.js（含离线拦截）+ 业务模块（food · energy · data · push · ai）
        ├── views/       9 个页面（Home · DietRecord · Exercise · Stats · AiPage · Mine …）
        ├── components/  FoodPicker · StatsPanel · TargetPanel · ReminderPanel · DataManagePanel
        │                OfflineBar（离线/待同步状态条）
        │                （+ layout/：AppSidebar · AppTopbar · MobileTabBar · CommandPalette）
        ├── config/      brand.js（品牌文案）· exercises.js（运动库）· nav.js
        ├── utils/       auth · credentials · session · reminder（前台提醒调度）· push（订阅）
        │                offline（IndexedDB 写队列 + 读数缓存）· format · image · breakpoint · common
        └── styles/      Less 设计系统「温润生机 · Warm Humanist」
```

---

## 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.10+ | 后端运行 |
| Node.js | 18+ | 前端构建 |
| 浏览器 | 现代浏览器 | 语音输入依赖内置 Web Speech API（Chrome / Edge） |

### 方式一：一键脚本（推荐）

Windows 下双击根目录脚本即可：

```text
start.bat     # 开发模式：一键起后端 + 前端，自动装依赖 / 生成 .env / 开浏览器
deploy.bat    # 生产模式：一键构建前端 + 单端口托管（一个进程、一个端口）
stop.bat      # 一键停止：按端口与进程名清理残留
```

首次运行会自动完成：创建 `.venv`、装后端依赖、从 `.env.example` 生成 `.env`、装前端依赖。

支持的参数（`.bat` 会把参数原样透传给 `scripts/*.ps1`）：

| 脚本 | 参数 | 默认 | 说明 |
| --- | --- | --- | --- |
| `start.ps1` | `-BackendPort` | `8000` | 后端端口 |
| | `-FrontendPort` | `5173` | 前端端口 |
| | `-NoBrowser` | — | 不自动打开浏览器 |
| | `-DryRun` | — | 只做环境体检，不启动任何进程 |
| `deploy.ps1` | `-Port` | `8000` | 单端口对外端口 |
| | `-SkipBuild` | — | 跳过 `npm run build`，用已有 `dist` 直接启动 |
| | `-NoBrowser` / `-Foreground` | — | 不自动开浏览器 / 前台阻塞运行 |
| `stop.ps1` | `-Ports` | `8000,5173,4173` | 要清理的端口列表 |

示例：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -Port 8080
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -DryRun
```

### 方式二：手动启动（开发）

**后端**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows；Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt   # 国内加速：-i https://pypi.tuna.tsinghua.edu.cn/simple
cp .env.example .env              # 需要 AI 时填入 ZHIPU_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger 文档：<http://localhost:8000/docs>
- 数据库 `diet.db` 在**首次启动时自动创建**，无需手动建表。
- `--reload` 只监听 `.py` 文件；**改动 `.env` 后需重启后端**。

**前端**

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

- 开发期 Vite 已把 `/api` 与 `/uploads` 代理到 `http://localhost:8000`，无跨域问题。
- 手机调试：手机与电脑同一局域网，浏览器打开 `http://<电脑IP>:5173` 即可。

---

## 部署（单端口）

生产/演示推荐用单端口模式：**FastAPI 同时提供 API 与前端静态资源**，只有一个进程、一个端口，天然无跨域。

```bash
cd frontend && npm run build      # 产物 → frontend/dist
cd ../backend
# Linux/macOS
FRONTEND_DIST=../frontend/dist uvicorn main:app --host 0.0.0.0 --port 8000
# Windows PowerShell
$env:FRONTEND_DIST="../frontend/dist"; uvicorn main:app --host 0.0.0.0 --port 8000
```

或直接 `deploy.bat`（自动生成 `JWT_SECRET`、构建、启动、打印局域网访问地址）。

启动后路由行为：

| 路径 | 行为 |
| --- | --- |
| `/` | 返回 `frontend/dist/index.html` |
| `/diet`、`/stats` … | SPA 前端路由，回退到 `index.html`（刷新不 404） |
| `/assets/*` | 前端构建产物（带长缓存哈希） |
| `/uploads/*` | 用户上传图片（静态目录） |
| `/api/v1/**` | 业务接口（JWT 鉴权） |
| `/docs`、`/openapi.json` | Swagger 与 OpenAPI 描述 |

若 `FRONTEND_DIST` 未设置或 `index.html` 不存在，后端自动退回「纯 API 模式」，`GET /` 返回服务信息，方便前端独立开发。

---

## 配置大模型

### 方式 A：改 `.env`（简单）

1. 到 <https://open.bigmodel.cn> 注册并获取 API Key。
2. 编辑 `backend/.env`：

   ```ini
   ZHIPU_API_KEY=你的key
   ```

3. 重启后端。之后「拍照识别 / 生成食谱 / AI 对话 / 每日复盘」即可使用。

### 方式 B：「我的 → 大模型配置」（推荐，运行时生效）

- **三套能力各自独立**：文字生成（对话 / 食谱 / 复盘）、视觉理解（识别食物）、语言转文字。厂商可任意混搭。
- 可选厂商：智谱 GLM、阿里云百炼、字节豆包、百度文心，或「自定义（OpenAI 兼容）」填 `base_url`。
- 保存即**加密写库**并同步 `.env`，无需手改文件、无需重启。
- 模型名下方会**实时列出该厂商的免费模型清单**并打「免费」徽标。

### 默认模型（全部永久免费）

| 能力 | 默认模型 |
| --- | --- |
| 文字生成（对话 / 食谱 / 复盘） | `glm-4-flash` |
| 视觉理解（拍照识别） | `glm-4v-flash` |
| 语言转文字 | `glm-4-flash` |

免费清单：`glm-4-flash`、`glm-4-flash-250414`、`glm-4.7-flash`、`glm-4v-flash`、`glm-4.6v-flash`、`glm-4.1v-thinking-flash`。需要更强效果时再手动改成付费模型即可。

> 语音识别走浏览器内置 Web Speech API，**不需要任何 Key**。

**未配置 Key 时的行为**（保证不 500）：

- `ai/chat`、`ai/recognize-food`、`ai/chat/stream` → 返回**友好业务提示**（HTTP 400 / SSE error），例如「未配置「文字」模型的 Key，请到「我的」页配置（国内大模型均可）」。
- `ai/generate-plan` → **自动降级**为本地通用食谱，仍返回 200 且可直接使用。
- 注册 / 登录 / 记录 / 统计等核心功能**完全不受影响**。

---

## 功能清单

- **账号**：注册 / 登录 / JWT 鉴权（默认 30 天，本机 `.env` 设 365 天）+ 记住凭据静默续期 / 首次信息采集（BMI · 推荐热量 · 预计达成时间**实时预览**）
- **饮食**：文字 + 拍照双模态；按早/午/晚/加餐分组；左滑删除、点击编辑；AI 识别结果**必须用户确认后**才保存；拍照原图前端自动压缩转 JPEG
- **体重**：记录 / 趋势；同日重复记录自动覆盖并计算差值
- **运动**：类型 + 时长，按 MET 自动估算消耗
- **饮水**：每日目标 = 体重 × 35ml，一键 +200 / +500ml
- **AI**：图片识食物（含数量）、生成一日减脂食谱（落库）、多轮营养对话（SSE 流式 + Markdown）、每日 ≤300 字复盘；对话区顶部常驻**今日画像**（目标 / 已摄入 / 剩余 / 蛋白 / 运动 / 体重），画像同时注入系统提示词，回答基于真实记录；推荐问题按当下处境生成
- **统计**：体重趋势（日/周/月，标注目标线）、营养分析（柱状图 + 供能比饼图）、周度报告；桌面端附**每日明细表**（点击表头排序，点击热量曲线某天即交叉筛选该天）
- **打卡**：连续打卡按昨日状态递增 / 重置；成就徽章（初次打卡、连续 7 天、减重 5kg、达成目标…）
- **提醒**：三餐 / 称重 / 饮水 / 免打扰可配置；页面开着走前台调度器（系统通知 + 应用内提示条），页面关着走**服务端 Web Push**，两条链路共用同一套计划算法，当天每槽位只响一次、免打扰跳过
- **数据**：CSV / JSON 导出（Excel 兼容）、体重与饮食幂等导入（脏行报行号）；**离线写队列**（IndexedDB，联网自动补发，4xx 丢弃、5xx 重试至多 5 次）+ 关键读数 12 小时缓存兜底
- **体验**：温润生机浅色主题（青柠 `#c6f24e` 唯一强调色）+ 暖性深褐深色皮肤、桌面端侧栏与 ⌘K 命令面板、移动端底部 Tab、PWA 可安装、Toast / Notify、空状态与骨架屏

---

## 接口一览

统一前缀 `/api/v1`，统一响应体 `{"code":200,"message":"success","data":{}}`，错误码 `200 / 400 / 401 / 403 / 500`。

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 认证 | POST | `/auth/register` | 注册 |
| | POST | `/auth/login` | 登录，返回 token |
| | GET | `/auth/info` | 当前用户信息 |
| 用户 | PUT | `/user/profile` | 更新身高/体重/目标等资料 |
| | PUT | `/user/preference` | 饮食偏好与忌口 |
| | GET | `/user/metrics` | BMR / TDEE / BMI / 推荐热量 |
| | GET | `/user/checkin` | 打卡记录与连续天数 |
| | GET | `/user/ai-settings/providers` | 可选厂商与**免费模型清单** |
| | GET / PUT | `/user/ai-settings` | 读取（脱敏）/ 保存三套模型配置 |
| 饮食 | POST | `/diet/add` | 新增记录 |
| | GET | `/diet/list` | 按日期查询 |
| | PUT / DELETE | `/diet/{id}` | 更新 / 删除 |
| | GET | `/diet/today` | 当日汇总（热量 + 三大营养素） |
| 体重 | POST / GET / DELETE | `/weight/add` · `/weight/list` · `/weight/{id}` | 记录 / 列表 / 删除 |
| 运动 | POST / GET / DELETE | `/exercise/add` · `/exercise/list` · `/exercise/{id}` | 记录 / 列表 / 删除 |
| 饮水 | POST / GET | `/water/add` · `/water/today` | 累加 / 当日进度 |
| AI | POST | `/ai/recognize-food` | 图片识别食物（返回 food_list，含 quantity） |
| | POST | `/ai/generate-plan` | 生成一日食谱 |
| | GET | `/ai/plan` | 查询已生成的食谱 |
| | POST | `/ai/chat` | 多轮对话（自动注入今日实况） |
| | POST | `/ai/chat/stream` | 流式对话（SSE） |
| | GET | `/ai/brief` | 今日画像（目标 / 摄入 / 营养素 / 运动 / 饮水 / 体重 / 打卡） |
| | GET | `/ai/daily-review` | 每日复盘 |
| 统计 | GET | `/stats/daily` · `/weekly` · `/weight-trend` · `/nutrient-trend` | 各项统计（营养页用 `nutrient-trend` 展开每日明细表） |
| 食物库 | GET | `/foods/search` | 搜索（收藏 → 命中位置 → 频次重排） |
| | GET | `/foods/{id}` | 详情（含份量单位） |
| | POST / DELETE | `/foods/favorite/{id}` | 收藏 / 取消收藏 |
| | POST | `/foods/custom` · `/foods/quick-add` | 自定义食物 / 按份量换算后直接入库 |
| 能量 | GET | `/energy/target` | 目标热量（双模式）+ 校准证据 |
| | POST | `/energy/calibrate` | 用体重曲线反推自适应 TDEE |
| 数据 | GET | `/data/export` | 导出 CSV / JSON（可选时间范围） |
| | POST | `/data/import` | 导入体重 / 饮食（幂等，返回脏行行号） |
| | GET / PUT | `/data/reminders` | 提醒设置（HH:MM 校验、间隔 1~6 小时，局部更新） |
| 推送 | GET | `/push/public-key` | VAPID 公钥（订阅用） |
| | GET | `/push/status` | 调度器状态 + 当天到期计划表 |
| | POST | `/push/subscribe` | 订阅（幂等，单用户上限 10 台设备） |
| | DELETE | `/push/unsubscribe` | 取消订阅 |
| | POST | `/push/test` | 发一条测试推送，验证链路 |

**契约要点**（前端与数据库统一使用整型枚举，避免参数校验 400）：

- `meal_type`：`1` 早 / `2` 午 / `3` 晚 / `4` 加餐
- `input_type`：`1` 文字 / `2` 图片
- 日期字段统一 `YYYY-MM-DD`

---

## 数据模型

SQLite / PostgreSQL 同构，14 张业务表（`database/models.py`）：

| 表 | 关键字段 | 说明 |
| --- | --- | --- |
| `user` | username(uniq) · password_hash · gender · age · height · current_weight · target_weight · activity_level · bmr · tdee · recommend_calorie · diet_preference · diet_avoid | 用户与代谢档案 |
| `diet_record` | record_date · meal_type · food_desc · food_image_path · input_type · calorie · protein · fat · carbohydrate · sugar · fiber · sodium | 饮食记录 |
| `weight_record` | record_date · weight · body_fat · waist · weight_diff · remark | 体重记录 |
| `ai_diet_plan` | plan_date · breakfast · lunch · dinner · total_calorie · adapt_desc | AI 食谱（JSON 文本） |
| `exercise_record` | record_date · exercise_type · duration · calorie_burn | 运动记录 |
| `water_record` | record_date(uniq) · total_amount · target_amount | 饮水（当日单行累加） |
| `user_checkin` | checkin_date · continuous_days · status | 打卡 |
| `user_ai_settings` | text/vision/asr 各自的 provider · api_key · model · base_url | 三套模型配置（**api_key 加密**） |
| `food` | name · category · calorie/protein/fat/carbs/fiber/sodium(每 100g) · source · confidence · use_count | 内置 + 自定义食物库 |
| `food_portion` | food_id · unit_name · gram | 份量单位（碗 / 个 / 份 …）与克重 |
| `food_favorite` | user_id · food_id | 用户收藏（影响搜索排序） |
| `reminder_setting` | user_id(uniq) · meal/weigh/water/quiet 的时间与开关 | 提醒配置（时间存 HH:MM 字符串） |
| `push_subscription` | user_id · endpoint(uniq) · p256dh · auth · enabled · fail_count | Web Push 订阅（连续失败 20 次自动停用） |
| `reminder_log` | user_id · fire_date · slot_key · channel（三者唯一） | 提醒触发记录，服务端去重依据（保留 30 天） |

---

## 安全设计

- **密码**：bcrypt 加盐哈希存储，绝不落明文。
- **鉴权**：JWT 中间件只拦截 `/api/**`，仅 `register` / `login` 公开；`OPTIONS` 预检放行；`/uploads`、静态资源与 SPA 路由不参与鉴权（`<img>` 无法携带 Authorization 头）。
- **API Key 静态加密**：由 `JWT_SECRET` 派生 Fernet 密钥，落库加密、读取时解密，接口仅回显**末 4 位**。
- **JWT_SECRET 自愈**：缺省或仍为 `change-me-secret` / 长度不足时，启动自动生成随机密钥并打印告警；`deploy.ps1` 会生成 64 位十六进制密钥写入 `.env`，避免每次重启 Token 失效。
- **上传校验**：magic-bytes 真实类型校验（jpg / png）+ 大小限制（≤5MB）+ UUID 重命名，不信任扩展名与 `Content-Type`。
- **CORS**：白名单可配（`CORS_ORIGINS`）；生产单端口模式下同源，无跨域面。
- **参数校验**：Pydantic v2 校验失败统一转 **400「参数校验失败」**，不泄漏堆栈。
- **错误处理**：全局异常处理器统一包装响应；第三方/未配置 Key 场景返回业务提示而非 500。

---

## 设计系统 · 温润生机 · Warm Humanist

- **主色** 青柠 `#c6f24e`，**仅用于填充**（主按钮、进度、达标态）；出现在文字上时改用可读的深橄榄 `#567013`。
- **语义辅色**：橄榄 `#4f6b2a`（正向）/ 陶土 `#c97a45`（提醒）/ 天蓝 `#4a8fa8`（数据）。
- **底色**：暖白纸感 `#fbf7f0`，卡片纯白；默认浅色，深色为可切换的「暖性深褐」第二皮肤。
- **表达原则**：先给结论再给数字；去掉工业字库、英文装饰标签、网格肌理与噪点——层级由字号与留白建立，而非描边与发光。
- **色板全部走 CSS 变量**（`styles/variable.less`），两套主题共享同一套 token，组件零硬编码颜色。
- **栅格与断点**：移动优先 320–1023px，桌面 1024px 起切换侧栏 + ⌘K 命令面板；`utils/breakpoint.js` 统一判定。
- **图表**：ECharts 统一封装（`ChartLine` / `ChartPie`），参与主题切换自动重绘。

---

## 常见问题（FAQ）

**Q1. 拍照识别报 400？**
多半是原图超限或格式不支持。前端已内置压缩：>1600px 或 >2MB 会自动缩放并转 JPEG（HEIC/WebP 一并转换）。若仍失败，请确认图片为 **JPG/PNG**，且服务端返回的提示是「图片格式不支持…」还是「参数校验失败」，二者定位不同。

**Q2. 识别完成后保存失败（400）？**
历史版本前端曾传字符串枚举（`'lunch'` / `'image'`），与后端整型契约不符。现已统一为整型（见「契约要点」）。升级后如有缓存，请强制刷新一次页面。

**Q3. `/uploads/xxx.png` 返回 401？**
`<img>` 标签无法携带 `Authorization` 头。鉴权中间件已收窄为只拦截 `/api/**`，其余路径放行。若自行改造过中间件，请保留该放行规则。

**Q4. 改了 `.env` 为什么不生效？**
`--reload` 只监听 `.py`。改 `.env` 后**必须重启后端**。

**Q5. 重启后老 Token 全部失效？**
说明 `JWT_SECRET` 是自动生成的随机值（每次重启都变）。请显式配置固定的 `JWT_SECRET`，或直接运行 `deploy.bat` 自动生成并落盘。

**Q6. 首页与饮食页的营养素数值差 0.1？**
已统一取整口径为**保留 1 位小数**（`utils/format.js` 的 `roundNum`）。浮点累加（如 `47.70000000000001`）在后端 `round(...,2)` 与前端渲染时统一收敛。

**Q7. 手机访问需要额外配置吗？**
局域网内直接用 `http://<电脑IP>:5173`（开发）或 `http://<电脑IP>:8000`（单端口部署）。注意放通防火墙对应端口。

**Q8. 提醒设置好了却不弹通知？**
先看是哪条链路：

- **页面开着**：「我的 → 提醒」通道卡点「开启」授权；若显示「已拦截」，点地址栏左侧图标 → 网站设置 → 通知 → 允许后刷新。
- **页面关着**：需要 Web Push。装成 App 或在同一页面点「开启后台提醒」，确认 `/push/status` 里 `subscriptions` 不为 0；可点「发测试推送」验证链路。

两者的硬前提都是 **HTTPS 或 localhost**——局域网 IP 上的 `http://` 浏览器不会授权通知，也不会给 Push 订阅。后台推送还依赖设备能访问推送服务商通道（Google / Mozilla），纯内网环境收不到。

**Q9. 怎么装成 App / 断网能用吗？**
生产模式下（`deploy.bat`）浏览器地址栏会出现安装图标，装到桌面/主屏后以独立窗口运行。

断网时：界面能打开（Service Worker 缓存应用壳）；读数展示上次缓存（12 小时内，页面顶部会标注）；**记录可以照常提交**——写请求进 IndexedDB 队列，顶部状态条显示「N 条待同步」，联网后自动补发，也可点「立即同步」。

**Q10. 怎么从 SQLite 迁到 PostgreSQL？**
```bash
# 1) 目标库先建好空库，然后干跑看行数
python scripts/migrate_to_pg.py --to postgresql+psycopg://user:pwd@host:5432/nutrimind --dry-run
# 2) 确认无误后正式搬迁（含建表、批量搬数据、重置自增序列、逐表校验）
python scripts/migrate_to_pg.py --to postgresql+psycopg://user:pwd@host:5432/nutrimind
# 3) 把连接串写进 backend/.env 后重启
DATABASE_URL=postgresql+psycopg://user:pwd@host:5432/nutrimind
```
连接池可用 `PG_POOL_SIZE` / `PG_MAX_OVERFLOW` / `PG_POOL_RECYCLE` / `PG_POOL_TIMEOUT` / `PG_POOL_PRE_PING` 调。

---

## 文档

| 文档 | 内容 |
| --- | --- |
| [`docs/audit-report.md`](docs/audit-report.md) | 全量审计报告：12 项高危 + 逻辑缺陷逐条修复、运行时问题 R1–R6、识别/保存链路二次修复 |
| [`docs/升级方案.md`](docs/升级方案.md) | 后续功能升级规划 |

---

## 开发进度 / Roadmap

- [x] 核心闭环：账号 → 资料 → 记录 → 统计 → AI
- [x] 拍照识别（含数量字段、逐项可编辑）
- [x] 单端口部署 + 一键启动 / 部署 / 停止脚本
- [x] 默认免费模型 + 运行时配 Key + 免费清单提示
- [x] 双主题（深色 / 浅色）
- [x] 品牌与视觉改版：知食 NutriMind ·「温润生机」设计系统
- [x] 内置食物库 + 份量换算入库
- [x] 自适应代谢校准 + 目标双模式 + 校准证据面板
- [x] 数据导出 / 导入（CSV · JSON，幂等）
- [x] 提醒触达（系统通知 + 应用内提示）
- [x] PWA：可安装 + 离线应用壳
- [x] 提醒的后台推送（Web Push + 服务端调度器）
- [x] AI 页信息架构重做（今日画像 + 处境化提问）
- [x] 离线写队列与读数缓存（IndexedDB）
- [x] SQLite → PostgreSQL 迁移脚本与连接池
- [ ] 图片报告 / 微信小程序端 / 多用户社交
- [ ] AI 会话历史服务端化（现仍存 localStorage）

---

## 备注

- 所有日期默认取**服务端日期**，避免客户端时间误差。
- 业务规则：每日热量缺口 300–500 kcal；体重同日仅保留最新；连续打卡按昨日状态递增/重置；AI 结果必须经用户确认。
- 数据全部本地存储（SQLite + `backend/uploads/`），不上传任何第三方（除你自行配置的大模型调用）。

## License

MIT
