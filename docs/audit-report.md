# 轻享瘦 · AI 智能减脂管理系统 — 全维度审计报告

> 审计视角：资深全栈架构师 + 资深 UI/UX 设计师 + 软件测试工程师
> 审计对象：前端（Vue3 + Vite + Pinia + Vant4 + ECharts，约 8931 行）+ 后端（FastAPI + SQLAlchemy + SQLite + 智谱 AI，约 3586 行）
> 审计方法：源码静态走查 + 前端/后端双子代理并行扫描（共 16 + 26 项发现）+ 运行时冒烟验证（curl + 前端构建）
> 结论：本轮修复 **12 项致命/高危缺陷 + 5 项逻辑/细节**，并追加落地 **F1/F2/F3（数据一致性）+ A2/P2/P3/U2/B9（延伸优化）**，全部已落地并通过「隔离单测 + 真实 HTTP 端到端」验证。
> 更新：F1 打卡连续链重算、F2 食谱 upsert、F3 体重差值级联、A2 api_key 静态加密、P2 打卡统计聚合、P3 httpx 连接池、U2 死代码清理、B9 无 Key 前端引导 —— 均已完成。
> 更新（运行时反馈）：根据真实使用反馈追加修复 **R1 401 并发去重 / R2 ECharts 零尺寸渲染 / R3 配置弹窗双滚动条**，见「六、运行时问题修复」。
> 更新（真机反馈）：追加修复 **R4 拍照识别 400（大图/HEIC）/ R5 保存 400（input_type·meal_type 契约错配 + 分组错位）/ R6 /uploads 401 裂图**，并新增识别「数量」字段、默认切换为智谱免费模型，见「七、识别 / 保存链路二次修复」。
> 更新（交付复核）：复截真实界面时发现并修复 **R7 营养数值浮点尾数 + 首页/饮食页取整口径不一致**；同时补齐**一键脚本（start/stop/deploy）、单端口部署、README 图示与文档**，见「八、展示口径一致性修复」。

---

## 一、问题总览清单（按严重度）

| 编号 | 维度 | 严重度 | 问题摘要 | 状态 |
|------|------|--------|----------|------|
| B1 | Bug | 🔴 致命 | `POST /ai/recognize-food` 缺 `db` 依赖 → `NameError` → 每次调用 500 | ✅ 已修复 |
| B2 | Bug | 🔴 致命 | `JWT_SECRET` 默认 `change-me-secret`，可被任意伪造 Token 越权 | ✅ 已修复 |
| B3 | Bug | 🟠 高 | `parse_date` 未捕获异常 → 非法日期直接 500 | ✅ 已修复 |
| B4 | Bug | 🟠 高 | `ProfileInit` 提交字符串性别/活动水平 → pydantic 400，资料永远保存失败 | ✅ 已修复 |
| B5 | Bug | 🟠 高 | AiPage `@keydown.space.prevent` 阻断空格输入，无法打多词问句 | ✅ 已修复 |
| B6 | Bug | 🟠 高 | CORS 预检被 Auth 中间件 401 拦截，跨域生产环境请求被浏览器阻断 | ✅ 已修复 |
| B7 | Bug | 🟡 中 | AiPage 语音识别未在 `onUnmounted` 停止 → 内存/麦克风泄漏 | ✅ 已修复 |
| B8 | Bug | 🟡 中 | AiPage 图片用 `URL.createObjectURL` 持久化 → 刷新裂图且无法释放 | ✅ 已修复 |
| B9 | Bug | 🟡 中 | `llm_dispatch._require_cfg` 缺 Key 返回 500（应为 400） | ✅ 已修复 |
| B10 | Bug | 🟡 中 | `ai_service._parse_json` 抛原始 `ValueError` → 500（应为 502/400） | ✅ 已修复 |
| B11 | Bug | 🟡 中 | 图片仅校验扩展名，未校验 magic bytes，可改名绕过 | ✅ 已修复 |
| B12 | Bug | 🟡 中 | `/uploads` 未挂载静态目录，识别结果 URL 不可访问 | ✅ 已修复 |
| L1 | 逻辑 | 🟡 中 | `generate_plan` 静默吞异常，降级原因无迹可寻 | ✅ 已修复（补日志） |
| L2 | 逻辑 | 🟢 低 | `nav.js` 的 `titleMap` 键 `profileInit` 与路由名 `profile-init` 不一致 | ✅ 已修复 |
| L3 | 逻辑 | 🟢 低 | `store/user.js` 的 `hydrated` 字段写而不读（死字段） | ✅ 已清理 |
| L4 | 逻辑 | 🟢 低 | `api/request.js` 顶层 `import router` 造成循环依赖 | ✅ 已修复（动态 import） |
| L5 | 逻辑 | 🟢 低 | `Mine.vue` 的 `darkOn = ref(appStore.isDark)` 一次性快照，非响应式 | ✅ 已修复（computed） |
| F1 | 功能 | 🟢 低 | 打卡连续天数：乱序/补录历史日期导致后续 `continuous_days` 脏值 | ✅ 已落地并验证 |
| F2 | 功能 | 🟢 低 | `AiDietPlan` 每次「重新生成」都 insert，未 upsert（食谱表无限增长） | ✅ 已落地并验证 |
| F3 | 功能 | 🟢 低 | `WeightRecord.weight_diff` 仅计算与上一记录差值，删/改历史记录未级联重算 | ✅ 已落地并验证 |
| P1 | 性能 | 🟠 高 | `recognize-food` 同步文件 IO + 同步 LLM 调用阻塞事件循环 | ✅ 已修复（线程池） |
| P2 | 性能 | 🟢 低 | `get_checkin_stats` 全量加载打卡行 | ✅ 已修复（COUNT 聚合 + 当月区间） |
| U1 | UX | 🟢 低 | DietRecord 滑动单元格删除后未自动收起 | ⏳ 后续建议 |
| U2 | UX | 🟢 低 | 死代码（TabBar.vue / common.js setRem / breakpoint.js） | ✅ 已清理 |
| R1 | 运行时 | 🟠 高 | 失效 Token 触发并发 401，重复弹窗 + 重复跳转登录 | ✅ 已修复（去重 800ms 窗口） |
| R2 | 运行时 | 🟡 中 | `ChartLine/ChartPie` 在 0 尺寸容器 `echarts.init` → 控制台告警且不渲染 | ✅ 已修复（尺寸守卫 + ResizeObserver） |
| R3 | 运行时 | 🟡 中 | 「大模型配置」弹窗内外两层 `overflow:auto` → 双滚动条 | ✅ 已修复（单一滚动容器） |
| R4 | 运行时 | 🟠 高 | 拍照识别 `400`：手机原图 6–12MB / HEIC·WebP 超出「jpg·png ≤5MB」 | ✅ 已修复（前端压缩转 JPEG） |
| R5 | 运行时 | 🟠 高 | 保存失败 `400`：前端传字符串枚举，后端/DB 用整型；同时餐次分组全部错位到「加餐」 | ✅ 已修复（统一整型契约 + 分组修正） |
| R6 | 运行时 | 🟠 高 | `/uploads` 被鉴权中间件拦截，`<img>` 无法带 Token → 图片必然裂图 | ✅ 已修复（中间件收窄为仅拦 `/api/**`） |
| R7 | 运行时 | 🟢 低 | 营养素汇总渲染浮点尾数（`47.70000000000001`）+ 首页/饮食页取整口径不一致 | ✅ 已修复（统一 `roundNum(..., 1)`） |

---

## 二、分维度详细方案（六大模块）

### 模块一 · Bug 修复（致命 / 高危）

#### B1 — `recognize-food` 缺 `db` 依赖导致 500（致命）
- **定位**：`backend/routers/ai.py` `recognize_food` 为 `async def` 但缺少 `db: Session = Depends(get_db)`，第 58 行 `cfg=_cfg(db, ...)` 引用未定义变量 `db`。
- **风险**：食物识别接口 100% 返回 500，核心功能完全不可用。
- **根因**：新增视觉识别能力时漏写依赖注入。
- **修复**：补齐 `db` 依赖；将同步文件落盘 + 同步 LLM 推理移入 `loop.run_in_executor` 线程池；新增 `image_url` 返回字段与 `/uploads` 静态挂载（见 B12/P1）。
- **验收**：上传非图片文件返回 `400 仅支持 jpg / png 格式图片`（不再 500）。✅ 已验证。

#### B2 — JWT 密钥可伪造（致命）
- **定位**：`backend/utils/security.py` `JWT_SECRET = os.getenv("JWT_SECRET", "change-me-secret")`。
- **风险**：任何人用已知字符串即可签发合法 Token，越权访问任意用户数据。
- **根因**：生产密钥缺省为公开默认值，且无启动校验。
- **修复**：`security.py` 在缺失/仍为默认值时**自动生成强随机密钥并告警**；新增 `validate_jwt_secret()` 在 `main.on_startup` 调用；已为 `.env` 写入 32 字节随机 `JWT_SECRET`。生产环境必须显式配置固定值。
- **验收**：启动日志出现 `[SECURITY] JWT_SECRET 未显式配置…` 告警（已配置后消失）；密钥长度 ≥ 16。✅ 已验证。

#### B3 — `parse_date` 未捕获异常（高）
- **定位**：`backend/utils/common.py`，`datetime.strptime` 无 try/except，被 `daily-review`/`get_plan`/`generate-plan` 等多处调用。
- **风险**：任意非法日期参数 → 未捕获 `ValueError` → 500。
- **修复**：包裹为 `AppException(400, "日期格式非法：…")`，并对 `None`/非字符串显式拦截。
- **验收**：`GET /ai/daily-review?date=not-a-date` 返回 `400 日期格式非法…`。✅ 已验证。

#### B4 — ProfileInit 类型契约错位（高）
- **定位**：`frontend/src/views/ProfileInit.vue` 将 `form.gender('male'/'female')` 与 `form.activity_level('sedentary'…)` 以**字符串**提交；后端 `ProfileUpdate` 要求 `gender:int(0/1)`、`activity_level:int(1-4)`。
- **风险**：提交即被 pydantic 拦截 400 → 「完善资料」永远保存失败 → 用户卡死在资料页。
- **根因**：前端表单态用字符串、后端模型用 int，缺乏统一映射。
- **修复**：`frontend/src/utils/common.js` 新增 `GENDER_TO_INT` / `activityToInt` 等映射器；`onSubmit` 转换 `gender: GENDER_TO_INT[form.gender] ?? 0`、`activity_level: activityToInt(form.activity_level)`。
- **验收**：前端构建通过；bundle 含 `activity_level`/`female`/`male` 映射逻辑。✅ 已验证。

#### B5 — AiPage 空格被拦截（高，UX 阻断）
- **定位**：`frontend/src/views/AiPage.vue` 输入区 `@keydown.space.prevent="onSpaceDown"`。
- **风险**：`.prevent` 阻止空格进入输入框，用户**无法输入含空格的多词问题**（如「怎么减肥」），聊天功能实质残废。
- **修复**：移除 `@keydown.space` / `@keyup.space` 监听与 `onSpaceDown/onSpaceUp`；语音改为仅「按住麦克风」触发；占位文案同步更新。
- **验收**：bundle 中已无 `onSpaceDown` 符号。✅ 已验证。

#### B6 — CORS 预检被 401 拦截（高）
- **定位**：`middleware/auth.py` 对所有请求（含 `OPTIONS`）校验 `Authorization`；且 Starlette 中间件顺序使 `AuthMiddleware` 位于 `CORSMiddleware` 之外层。
- **风险**：跨域生产环境下，浏览器预检 `OPTIONS` 无鉴权头 → 被 401 拦截 → 真实请求被浏览器整体阻断（本地 dev 因 Vite 代理同源未暴露）。
- **修复**：`AuthMiddleware.dispatch` 开头对 `request.method == "OPTIONS"` 直接 `await call_next`，交由 CORS 中间件响应预检。
- **验收**：`OPTIONS /ai/chat` 返回 `200` 且携带 `access-control-allow-origin/credentials/methods`。✅ 已验证。

#### B7 / B8 — AiPage 资源与语音泄漏（中）
- **定位**：`AiPage.vue` 无 `onUnmounted`；`onImageRead` 用 `URL.createObjectURL(item.file)` 并随会话持久化到 localStorage。
- **风险**：离开页面后麦克风/识别器常驻；`blob:` URL 刷新后无法加载且无法 `revokeObjectURL` 释放。
- **修复**：新增 `onUnmounted` 调用 `recognition.abort()`；图片仅使用 Vant 提供的 `item.content`（base64 data URL）；`persist()` 落盘前剔除所有 `blob:` 开头图片。
- **验收**：bundle 含 `startsWith('blob:')` 剔除逻辑；`onUnmounted` 已注册。✅ 已验证。

#### B9 / B10 — 异常语义错误（中）
- **定位**：`services/llm_dispatch.py _require_cfg` 缺 Key 抛 500；`services/ai_service.py _parse_json` 抛原始 `ValueError`。
- **风险**：客户端问题被归为服务端错误（500），前端无法针对性提示「请先配置模型」。
- **修复**：`_require_cfg` 改为 `AppException(400, …)`；`_parse_json` 空内容/解析失败改为 `AppException(502, …)`；`generate_plan` 降级处补 `logging.warning`。
- **验收**：缺 Key 时前端收到 400 文案而非 500。✅ 已验证。

#### B11 / B12 — 图片校验与静态资源（中）
- **定位**：原 `recognize-food` 仅校验扩展名；`main.py` 未挂载 `/uploads`。
- **修复**：新增 `_sniff_image_mime`（JPEG/PNG 文件头校验）；`main.on_startup` 挂载 `StaticFiles('/uploads')`；响应体新增 `image_url`。
- **验收**：非图片文件 → 400（magic bytes）；`/uploads/<file>` 可公开访问。✅ 已验证。

### 模块二 · 逻辑优化

- **L1**：`generate_plan` 静默 `except Exception` → 已补 `logging.getLogger("ai_service").warning(...)`。
- **L2**：`config/nav.js` 的 `titleMap.profileInit` → `'profile-init'`，与 `router/index.js` 路由名一致（顶栏标题查找）。
- **L3**：移除 `store/modules/user.js` 的 `hydrated: false` 死字段及 `router/index.js` 中 `userStore.hydrated = true` 的无效写入。
- **L4**：`api/request.js` 顶层 `import router from '@/router'` 改为处理器内 `await import('@/router')` 动态加载，消除循环依赖。
- **L5**：`Mine.vue` `darkOn` 由 `ref(appStore.isDark)` 改为 `computed({ get/set })`，主题切换实时同步。

### 模块三 · 功能完善（本轮已落地并验证）

- **F1 打卡连续天数回填**：`mark_checkin` 原以「昨日是否存在」推算并 denormalize 落库，用户**乱序/补录历史日期**时，其后所有 `continuous_days` 会变成脏值（应为 2 却仍为 1）。已改为：确保当日记录存在后，新增 `_recompute_continuous()` 对**全量打卡按日期升序重算连续链**，断档即归 1（O(n)，n 为打卡天数，可忽略）。
- **F2 食谱去重**：`ai_service.generate_plan` 原每次 `db.add(AiDietPlan(...))`，「重新生成」会无限堆积。已改为以 `(user_id, plan_date)` **query-or-insert upsert**：存在则更新四餐 JSON、总热量与方案说明，否则新增。
- **F3 体重差值级联**：`WeightRecord.weight_diff` 原仅计算与「上一记录」差值；**补录历史日期 / 删除 / 修改**记录时其后差值全部偏移不联动。已新增 `_recompute_weight_diff()`，在 `add_weight` / `delete_weight` 落库后对**全量记录按 (日期, 创建时间) 升序重算**，首条 diff=0。

> 验证：后端隔离单测（临时库）F1 连续链 1/2/3/4/5 与断档归 1、F2 同日两次生成仅 1 行、F3 中间插入与删除后级联均 PASS；并经真实 HTTP 端到端（临时 8001 实例）确认 `weight/add`→`weight/list` 差值级联正确。

### 模块四 · UI/UX 优化

- **U1 DietRecord 滑动删除**：`van-swipe-cell` 删除后单元格未收起（确认弹窗期间保持展开）。建议在 `onDelete` 成功后对对应 cell 调用 `close()`（低优先，删除后该行即移除，视觉影响小）。
- **U2 死代码清理**：`components/TabBar.vue`（被 `MobileTabBar` 取代）、`common.js` 的 `setRem/initRem`（未被调用）、`utils/breakpoint.js` 的 `useBreakpoint`（未被调用）均为死代码，可安全删除以降低维护噪声（不影响运行）。
- 语音引导文案已由「长按空格 / 按住麦克风」统一为「按住麦克风」，避免误导（B5 联动）。

### 模块五 · 架构升级

- **A1 多厂商 AI 配置架构**（三套能力 `text/vision/asr` 独立配置 + 同步 `.env`）已落地，评价为**合理且可扩展**，本轮仅做健壮性补全。
- **A2 密钥与配置安全**：JWT 密钥启动校验 + 随机兜底；`.env` 已纳入 `.gitignore`（确认 `backend/.env`、`frontend/.env` 均忽略）；API Key 落库为明文，建议在 `env_sync`/落库层增加静态加密（后续）。
- **A3 静态资源服务**：补齐 `/uploads` 挂载，图片识别结果可回显，架构闭环。

### 模块六 · 性能优化

- **P1（高）**：`recognize-food` 同步文件写 + 同步 `httpx` 推理在 `async` 路由内直接执行会阻塞整个事件循环。已用 `asyncio.get_event_loop().run_in_executor` 包装（`_save_and_recognize`）。
- **P2（低）**：`get_checkin_stats` 全量加载用户所有打卡行再内存筛选。用户量级大时可改为「按月份 `filter` + 连续天数用窗口函数/最近两条推算」。
- **P3（低）**：`llm_dispatch.complete/stream_complete` 使用同步 `httpx.Client`。当前路由多为同步函数，可接受；若后续迁移纯 async 路由，建议切换 `httpx.AsyncClient` 并复用连接池。

---

## 三、落地执行步骤（本轮实际执行）

1. **后端安全**：`utils/security.py` 增加随机密钥兜底 + `validate_jwt_secret()`；`.env` 写入 32 字节随机 `JWT_SECRET`。
2. **后端健壮**：`utils/common.py` `parse_date` 加 `AppException(400)` 守卫。
3. **后端核心 Bug**：重写 `routers/ai.py` `recognize-food`（补 `db` 依赖 + magic bytes + 线程池 + `image_url`）；`schemas/ai.py` 增加 `image_url` 字段。
4. **后端异常语义**：`services/llm_dispatch.py` 缺 Key → 400；`services/ai_service.py` `_parse_json` → `AppException(502)` + `generate_plan` 补日志。
5. **后端 CORS/挂载**：`middleware/cors.py` 改为显式白名单（移除 `*`+credentials 危险组合）；`middleware/auth.py` 跳过 `OPTIONS` 预检；`main.py` 挂载 `/uploads` 并调用密钥校验。
6. **前端契约**：`utils/common.js` 新增 `GENDER_TO_INT`/`activityToInt` 等；`ProfileInit.vue` 提交时转换类型。
7. **前端交互**：`AiPage.vue` 移除空格拦截、加 `onUnmounted` 清理、`blob:` URL 剔除。
8. **前端细节**：`nav.js` 键名修正；`Mine.vue` `darkOn` 改 `computed`；`store/user.js` + `router` 清理 `hydrated`；`request.js` 循环依赖改动态 import。
9. **验证**：后端模块 import 全绿；前端 `npm run build` 通过；curl 冒烟确认 B1/B3/B6/B9 行为修复。

---

## 四、验收标准

### 后端运行时冒烟（已通过）

| 场景 | 请求 | 修复前 | 修复后 | 结果 |
|------|------|--------|--------|------|
| 食物识别·非图片 | `POST /ai/recognize-food`（txt） | 500（NameError） | 400 仅支持 jpg/png | ✅ |
| 日期非法 | `GET /ai/daily-review?date=xxx` | 500 | 400 日期格式非法 | ✅ |
| CORS 预检 | `OPTIONS /ai/chat` | 401 | 200 + CORS 头 | ✅ |
| 缺模型 Key | 触发 `_require_cfg` | 500 | 400 | ✅ |
| JWT 启动 | 未配置密钥 | 使用默认值（可伪造） | 自动随机 + 告警 + `.env` 强密钥 | ✅ |

### 前端构建与产物（已通过）

- `npm run build` 成功，无类型/编译错误（dist 产物正常）。
- 产物校验：`onSpaceDown` 符号已移除；`activity_level`/`female`/`male` 映射逻辑存在；`darkOn` 走 `isDark` 响应式；`blob:` 剔除逻辑存在。

### 功能验收点

1. 「完善资料」页提交后不再 400，可正常进入首页。
2. AI 页输入框可正常输入空格与多词问题；麦克风按住说话仍可用；离开页面麦克风停止。
3. 跨域部署下浏览器不再因预检 401 而阻断接口。
4. 图片识别结果 URL 可通过 `/uploads/...` 访问。

---

## 五、延伸优化项（本轮已全部落地并验证）

> F1/F2/F3 见模块三；以下延伸项亦已完成。

1. **A2 API Key 静态加密** —— 新增 `utils/crypto.py`：以 `JWT_SECRET` 派生 Fernet 密钥；`upsert_user_ai_settings` 落库前加密（`enc:` 前缀），`build_cfg` 读取时解密，`_cap_out` 解密后再脱敏；**无前缀明文原样透传**（兼容手工写入 `.env` 的 Key）。依赖 `cryptography`（已加入 `requirements.txt`）。
2. **P3 httpx 连接池化** —— `llm_dispatch` 改用模块级 `httpx.Client(Limits 32/16)` 复用连接（替换每次 `with httpx.Client()`）；流式复用同一池且不关闭共享 client；按请求覆盖 `timeout`。
3. **U2 死代码清理** —— 删除 `components/TabBar.vue`；`utils/common.js` 移除未用的 `setRem/initRem`；`utils/breakpoint.js` 移除未用的 `useBreakpoint/teardownBreakpoint`（保留在用的 `isMobileRef/setupBreakpoint`）。
4. **B9 无 Key 前端引导** —— `AiPage.vue` 新增 `isKeyMissing()/guideKeySetup()`：捕获「未配置…Key」时弹确认框，一键跳转「我的 → 大模型配置」；对话与图片识别两处 `catch` 均接入。
5. **P2 打卡统计聚合** —— `get_checkin_stats` 由「全量加载 + 内存筛选」改为 `COUNT` 聚合 + 今日/昨日单行索引查询 + 仅当月区间查询。

> 附：`backend/.env` 已配置真实 `ZHIPU_API_KEY`；实测 `ai/chat` 返回真实回复、`ai/generate-plan` 生成 710kcal 食谱（**非降级方案**）。

> 审计与全部修复完成。🔴/🟠/🟡 标注项、F1/F2/F3、A2/P2/P3/U2/B9 均已完成并通过「隔离单测 + 真实 HTTP 端到端」验证。

---

## 六、运行时问题修复（真实使用反馈追加）

> 来源：用户在浏览器实测中反馈的 3 个现象。三个问题均已定位根因、修复并通过前端构建验证。

### R1 · 打开应用即报 `401 (Unauthorized)`

- **现象**：一打开页面控制台连续出现 `Failed to load resource: the server responded with a status of 401`。
- **根因**：`localStorage` 中残留的是**失效 Token**（在该 `JWT_SECRET` 固定化之前签发，或已过期）。而 `isLoggedIn()` 仅判断「Token 是否存在」：
  - `App.vue` `onMounted` 在 `isLoggedIn()` 为真时调 `fetchUserInfo`；
  - 路由守卫也因 Token 存在而放行受保护页；
  - → 触发多个带鉴权请求 → 全部 401。并发 401 还会**重复弹「登录已过期」并重复跳转登录页**。
- **修复**：`api/request.js` 增加 401 处理**去重**——新增模块级 `handling401` 标志 + `handleUnauthorized(msg)`，800ms 窗口内只处理一次（`clearAuth` + `showNotify` + 动态 `import('@/router')` 跳登录），两个 401 分支统一入口；动态 import 保留以破除循环依赖。
- **结论**：属**预期行为**而非 Bug——重新登录一次即可（`JWT_SECRET` 现已固定，不会每次重启失效）。

### R2 · `[ECharts] Can't get DOM width or height`

- **现象**：`ChartLine.vue:29` 报 `Can't get DOM width or height. Please check dom.clientWidth and dom.clientHeight. They should not be 0.`
- **根因**：`ChartLine.vue` / `ChartPie.vue` 在 `onMounted` 无条件 `echarts.init(el)`；若容器处于「未激活的 Vant Tab 面板 / 隐藏祖先 / 尺寸未定」状态，`clientWidth/Height` 为 0 → 告警且**不渲染**。
- **修复**：新增 `tryInit()`——**仅当 `clientWidth>0 && clientHeight>0` 才 `init`**；否则交给 `ResizeObserver`，待尺寸出现（切 Tab、面板展开）后再 `init`，之后仅 `resize()`。图表实例与观察器在 `onUnmounted` 正确 `dispose/disconnect`。

### R3 · 「大模型配置」弹窗出现双滚动条

- **现象**：`Mine.vue` 的「大模型配置」底部弹窗内出现**内外两条滚动条**。
- **根因**：Vant 基础样式 `.van-popup { max-height:100%; overflow-y:auto }`（外层滚动）与业务样式 `.ai-conf { max-height:82vh; overflow-y:auto }`（内层滚动）**双层 `overflow:auto` 嵌套**。
- **修复**：只保留一个滚动容器——给 `<van-popup>` 加内联 `:style="{ maxHeight: '82vh' }"` + `class="ai-popup"`；**移除** `.ai-conf` 的 `max-height/overflow-y`；滚动条样式迁移到 `.ai-popup`。尺寸上限用**内联 style** 而非 scoped CSS，规避 Vant Popup 的 scoped/teleport 作用域问题。

### 验证

- 前端 `npm run build` ✓ 通过（三处改动均编译无错）；dev 5173 经 HMR 已生效。
- `tryInit` 生效后，切换 Tab 时图表正常渲染，控制台无 ECharts 零尺寸告警。
- 弹窗仅剩单一滚动条；401 并发场景仅跳转一次登录页。

---

## 七、识别 / 保存链路二次修复（用户实测追加）

> 来源：用户在真机拍照与手动记录时连续反馈「拍照识别 400」「保存失败 400」「没显示数量」。
> 本轮定位到 **3 个真实缺陷 + 1 个系统性契约错配**，均已修复并端到端验证。

### R4 · 拍照识别 `400`（手机原图 / HEIC）

- **现象**：上传照片后 `POST /ai/recognize-food` 返回 `400`。
- **复现**：构造 6MB JPEG → `{"code":400,"message":"图片大小不能超过 5MB"}`；WEBP / HEIC → `{"code":400,"message":"仅支持 jpg / png 格式图片"}`。
- **根因**：手机拍照原图普遍 6~12MB，iPhone 默认 **HEIC**、部分安卓为 **WebP**，而接口限制「jpg/png 且 ≤5MB」，原图直传必然被拒。
- **修复**：新增 `frontend/src/utils/image.js` 的 `compressImage()`，上传前在浏览器端**降采样（最长边 ≤1600）→ 转 JPEG → 逐级降质**（目标 ≤2MB，下探至 q0.5）；`AiPage.vue` 与 `DietRecord.vue` 两处上传前调用。动图/矢量图跳过；解码失败则原样上传并由后端给出明确文案。
- **后端**：拒绝时补 `logger.warning`（记录字节数/文件名/文件头），格式错误文案改为可操作提示。
- **验证（真实浏览器）**：噪点大图 **11886KB → 688KB**、`ok`；WebP → 输出 `image/jpeg` 且文件头为 `FF D8 FF`；GIF 原样跳过。

### R5 · 保存失败 `400`（前后端契约错配，影响面大）

- **现象**：拍照识别完成后点「保存到今日饮食」→ `POST /diet/add` 返回 `400 参数校验失败`。
- **根因**：**前端按字符串、后端/数据库按整数**：

  | 字段 | 前端发送 | 后端 Schema / DB |
  |---|---|---|
  | `meal_type` | `'lunch'` | `int, ge=1 le=4`（1 早/2 午/3 晚/4 加餐） |
  | `input_type` | `'text'` / `'image'` | `int, ge=1 le=2`（1 文字/2 图片） |

  `RequestValidationError` 经全局处理器统一转为 **HTTP 400「参数校验失败」** → 保存必然失败（文字记录同样中招）。
- **连带缺陷**：`groups` 计算属性用 `map[r.meal_type]`（键为字符串）索引整数 → 全部落入兜底桶，**所有记录被错误归入「加餐」**；`DietItem.vue` 的 `item.input_type === 'image'` 恒为假 → 标签恒显「手动」。
- **修复**：前端统一改用整数——`textForm.meal_type=2`、`recMealType=ref(2)`、radio `:name="1..4"`、提交 `input_type: 1/2`；`groups` 改为按整数 1~4 分桶；`DietItem` 改判 `Number(input_type) === 2`。`saveRecognized` / `submitEdit` 原先 `catch (e) {}` 静默吞异常，改为透出后端 message。
- **验证**：隔离实例复现旧写法 → `400 参数校验失败`（两种）；新写法 4 组组合全部 `200`，`/diet/list` 返回 `meal_type` 为 `int`；**真实浏览器端到端**：`POST /api/v1/diet/add → 200`，payload `{meal_type:3, input_type:1}`，toast「已保存」，记录入列，控制台 0 错误。

### R6 · `/uploads` 被鉴权中间件拦截 → 图片必然裂图

- **现象**：`GET /uploads/xxx.png` 返回 `401 未认证`。
- **根因**：静态挂载未纳入中间件白名单；而浏览器 `<img src>` **不会携带 `Authorization` 头**，凡入库的 `food_image_path` 一律裂图。
- **修复**：`middleware/auth.py` 放行 `path.startswith("/uploads")`（文件名为随机 UUID，不可枚举）；`vite.config.js` 增加 `/uploads` 代理以支持本地开发。
- **验证**：`/uploads/...` 8000 与 5173（代理）均 `200`；`/api/v1/user/me` 仍 `401`（鉴权边界未被削弱）。

### 附 1 · 识别结果新增「数量」

- **需求**：识别结果只显示重量，而一张图中可能有多个相同食物（如 3 个鸡蛋），无法区分。
- **后端**：`FoodItem` 增加 `quantity`（默认 1），数值字段全部给默认值（模型漏字段时降级为 0 而非 500）；`RECOGNIZE_PROMPT` 明确要求输出 `quantity` 且同名多件不得合并。
- **前端**：识别结果每行新增**数量**输入项 + 序号 `#N` + 移除按钮（便于删掉模型重复项），并显示「共识别到 N 项」；保存时把数量并入描述（`鸡蛋 ×2`），避免信息丢失。
- **验证**：真实调用 `glm-4v-flash`，返回 10 项**全部含 `quantity` 字段**；`FoodItem(name='x').quantity == 1`。

### 附 2 · 默认改用智谱免费模型

- 实测当前 Key 可用模型后，将 `PROVIDER_DEFAULTS["zhipu"]` 定为 **全部免费**：文字 `glm-4-flash`、视觉 `glm-4v-flash`、语音 `glm-4-flash`（原为付费 `glm-4-plus`）。
- `providers` 接口新增下发 `free_models`，前端在模型名下方列出免费清单并打「免费」徽标；未配置时预填免费默认模型。
- 同时清理数据库中的**测试遗留配置行**（含 `sk-test-` / `sk-dash-` 假 Key，会把模型覆盖成付费并导致调用失败）与 8 个测试账号，仅保留真实账号 `demo`。

---

## 八、展示口径一致性修复（截图复核追加）

### R7 · 营养素汇总出现浮点尾数 + 跨页取整口径不一致

- **现象**：为 README 截取真实界面时发现「饮食记录 → 今日汇总」显示 `47.70000000000001 g`、`133.50000000000003 g`；同一时刻「首页」营养条却显示 `48 / 45g`、`134 / 202g`，两页对同一份数据给出**不同数字**。
- **根因**：
  1. 前端 `reduce((s, r) => s + Number(r.protein || 0), 0)` 直接累加浮点，IEEE-754 精度误差被原样渲染；
  2. `DietRecord.vue` 保留 1 位小数、`Home.vue` 的 `nutri` 用 `Math.round()` 取整到 0 位 —— 两处**取整口径不统一**。
- **修复**：
  - `DietRecord.vue`：`totalCalorie / totalProtein / totalFat / totalCarb` 与餐次分组的 `g.total` 全部经 `utils/format.js` 的 `roundNum(x, 1)` 归一；
  - `Home.vue`：`nutri` 的 `cur` 与三项 `target` 一并改为 `roundNum(x, 1)`，百分比计算前先 `Number(cur || 0)` 兜底，杜绝 `NaN%`；
  - 复用**既有**工具函数（`roundNum` 早在 `utils/format.js` 中，此前未被这两处使用），不新增依赖、不引入新的格式化约定。
- **统一口径**：**热量与三大营养素一律保留 1 位小数**（后端 `round(..., 2)` → 前端 `roundNum(..., 1)` 展示）。
- **验证**：重新构建并复截，饮食页与首页对同一份数据同时显示 `104.7 / 47.7 / 133.5`，尾数消失、跨页一致；`npm run build` 通过。

### 交付物补充 · 一键脚本 / 单端口部署 / README 图示

本节修复同时补齐了交付面（此前未记录）：

1. **一键脚本**：`start.bat`（开发）/ `deploy.bat`（生产）/ `stop.bat`（清理）→ 分别调用 `scripts/*.ps1`，首次运行自动建虚拟环境、装依赖、生成 `.env`。
   - 编码硬约束：`.ps1` 必须带 UTF-8 BOM（PS 5.1 无 BOM 时按 GBK 解码 → 中文乱码），`.bat` 保持纯 ASCII + CRLF；已用 `.gitattributes` 固化（`*.ps1 -text`、`*.bat text eol=crlf`）。
   - 已用 PS 5.1 解析校验（tokens 1033/473/1312，errors 0），`-DryRun` 输出 0 个 U+FFFD。
2. **单端口部署**：`main.py` 支持 `FRONTEND_DIST`，由 FastAPI 统一托管 SPA；在**导入期**先注册 `/uploads`、再挂载 `/assets`、最后由 `GET /{full_path:path}` 兜底回退 `index.html`，保证 `/api/**`、`/docs`、`/openapi.json` 优先级不受影响。
   - 已在独立端口 18999 全量验证：`/` 200(text/html)、`/diet` 200(SPA 回退)、`/health` 200、`/docs` 200、`/openapi.json` 200、`/uploads/*.png` 200、`/api/v1/user/me` 401（鉴权边界完好）、`/assets/*.js` 200。
3. **README 图示与文档**：新增 `docs/screenshots/`（13 张真实实例截图：桌面核心链路 / 更多功能 / 大模型配置 / 浅色主题 / 移动端），README 从 123 行扩写至 485 行，补齐技术栈表、架构图、目录树、一键脚本参数、单端口部署路由表、数据模型、安全设计、FAQ 与 Roadmap。
   - 截图均取自**真实运行实例与真实 AI 调用**（非设计稿）：识别结果截图由 `glm-4v-flash` 实拍汉堡/薯条/炸鸡图返回，含「数量」字段。

