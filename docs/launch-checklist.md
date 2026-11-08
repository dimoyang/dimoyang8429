# MediTour 上线前清单

> 核对时间：2026-11-08
> 核对基线：本地 `HEAD 8a4b103`（已推送至 origin/main）
> 核对方式：后端 `pytest`、`verify_api.py`、`alembic check`、`check_query_plans.py --strict` 与前端 `flutter analyze`、`flutter test`、`flutter build web` 均在当前 HEAD 实跑；标 ✅ 的条目都可用文中命令复现。
> 标注约定：**✅ 已完成**（附验证方式）｜**🟡 部分完成**｜**⏳ 待办**｜**❓ 需外部确认**
> 严重度：**S0** = 缺了不能对外提供服务，或有法律/数据风险；**S1** = 可灰度，正式上线前必须补齐；**S2** = 可上线后迭代。

本文按“缺了会怎样”的严重度排序。原始需求 1–10 的对应关系：内容 §5、图片 §6、数据库 §2、部署 §3、HTTPS/客户端 §1、外部服务 §8、账号安全 §7、合规 §4、质量门禁 §9、执行顺序 §10。

## 0. 状态总览

| 序号 | 条目 | 级别 | 当前状态 | 关键缺口 |
| --- | --- | --- | --- | --- |
| 1 | HTTPS、生产 CORS 与客户端联网 | S0 | 🟡 部分完成 | 无生产域名/TLS；Android release 未验证 |
| 2 | 数据库 PostgreSQL、迁移与备份 | S0 | 🟡 部分完成 | Alembic 与备份已完成；PostgreSQL 未实测切换 |
| 3 | 部署与运维 | S0 | 🟡 部分完成 | 无 TLS 反代、staging、监控告警 |
| 4 | 合规：医疗免责、隐私政策、用户协议 | S0 | ⏳ 待办 | 无任何合规页面与同意记录 |
| 5 | 四语言内容与目的地内容 | S1 | 🟡 部分完成 | 机制已完成；缺正式翻译与医学审校 |
| 6 | 图片与静态资源 | S1 | 🟡 部分完成 | 本地上传已完成；缺对象存储/CDN 与存量外链迁移 |
| 7 | 账号与安全 | S1 | 🟡 部分完成 | 闭环已完成；token 仍存 SharedPreferences |
| 8 | 支付与邮件 | S1/S2 | 🟡 部分完成 | 邮件模板与配置已完成；支付未接入 |
| 9 | 质量门禁 | S1 | 🟡 部分完成 | CI 与本地门禁已完成；缺 staging 冒烟与覆盖率阈值 |

> 结论：**本地质量门禁已全绿，可以进入“部署到 staging → 灰度”准备**；但 S0 项（生产域名/TLS、PostgreSQL 决策、合规最低集、运维监控）尚未完成，当前不具备对真实用户开放的条件。

---

## 1. HTTPS、生产 CORS 与客户端联网（S0）

### 已完成 ✅

- CORS 来源改为环境变量 `MEDITOUR_CORS_ORIGINS`（逗号分隔），保留本地默认值；不再硬编码（`backend/app/config.py`）。
- `scripts/prod_check.py` 对通配 `*`、本地地址、非 HTTPS 来源一律报 FAIL，可作发布闸门。
- 前端支持 `--dart-define=API_BASE_URL` 覆盖基址，部署不需要改代码（`lib/core/constants/base_url.dart` 及各平台默认实现）。
- 后端已有健康检查与容器配置，具备接反代的入口（见 §3）。

验证方式：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\prod_check.py --production   # CORS 项应 FAIL，说明闸门生效
```

### 仍待办 ⏳

- 生产域名与证书、TLS 终止（Caddy/Nginx/托管平台），以及证书续期提醒。
- 生产 CORS 白名单只保留真实前端域名。
- Android release 包联网验证；`AndroidManifest.xml` 仍未声明明文 HTTP 例外配置，release 包默认禁止明文，需真机验证。
- Web/Android 构建时注入 HTTPS 基址并用 `verify_api.py --base-url` 对生产域名复跑。

**验收**：release 包能完成注册、登录、`/auth/me`、预约；生产域名预检放行且含 `Authorization`、`Content-Type`。

---

## 2. 数据库 PostgreSQL、迁移与备份（S0）

### 已完成 ✅

- **Alembic 已接管 schema 演进**：启动流程为建库/迁移后播种，不再依赖运行期 `create_all`；当前 head `d4e6f8a2b1c3`（`backend/alembic.ini`、`backend/migrations/`）。
- **迁移一致性**：`alembic check` 实测无 diff。
- **索引实测**：`check_query_plans.py --strict` 实测 0 条全表扫描/临时 B 树排序（订单、审计、套餐、译文、行程、统计、公开列表）。
- **备份与恢复**：在线备份 API + 行数指纹校验；备份完成执行 `wal_checkpoint(TRUNCATE)` 并切回 `journal_mode=DELETE`，不残留 `-wal`/`-shm`；保留策略（按天 7 份、按周 4 份，最新一份永不删）；恢复前自动生成安全副本、默认拒绝覆盖非空库（需 `--force`）。
- **定时执行**：`scripts/run_backup_task.ps1` 作为 Windows 计划任务入口，日志与退出码透传；已有 `schtasks /Run` 演练记录（1 秒内产出备份、退出码 0、旧备份按周策略删除）。
- **SQLite 运行参数**：WAL + `busy_timeout`、连接池按单进程 40 个工作线程配置（`backend/app/database.py`、`config.py`）。
- **数据巡检**：`scripts/check_data_consistency.py` 可核对订单/金额/引用一致性。

验证方式：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe scripts\check_query_plans.py --strict
.\.venv\Scripts\python.exe scripts\check_data_consistency.py
```

### 仍待办 ⏳

- **PostgreSQL 实际切换**：`backend/docker-compose.yml` 与 README 仅提供脚手架，**本机未做构建与运行验证**，不得宣称已支持 PostgreSQL。
- 金额字段仍为 `Float`；切 PostgreSQL 时一并改 `Numeric(12,2)` 或整数分（历史订单价格已是创建时快照，不受改价影响）。
- 生产备份落地到对象存储、开启 PITR/自动备份，并配置失败告警；RPO 目前最坏 24 小时，需业务方确认是否可接受。
- 多实例：SQLite 单写者不支持水平扩展（见 §3）。

**验收**：`alembic upgrade head` 从空库一次成功、`alembic check` 无 diff、备份→删库→恢复数据一致、恢复耗时与 RTO 有记录。

---

## 3. 部署与运维（S0）

### 已完成 ✅

- `GET /api/v1/health`：返回 `status` 与 `database` 连通性，供反代/监控探活（`backend/app/routers/health.py`）。
- 容器化：`backend/Dockerfile`、`backend/docker-compose.yml`。
- 结构化请求日志（含脱敏）与 `X-Request-ID` 透传。
- 安全中间件：全局请求体上限、安全响应头、统一错误兜底（响应体保持 `{"detail": ...}`，生产不返回堆栈）。
- 运行指标 `/metrics`：可开关，支持来源 IP 白名单（默认空表示不限，风险已在 README 标注）。
- 数据保留清理：`scripts/cleanup_data.py` 默认 dry-run，保留期全部配置化；软删除账号保留用户行与订单，仅清理可移除关联数据。
- 上线前配置自检：`scripts/prod_check.py`（开发配置 2 通过/10 警告/0 失败；按生产断言为 1 通过/3 警告/8 失败并退出码 1，属“尚未切生产配置”的真实状态）。
- 本地运维脚本：`scripts/dev_server.ps1 start|stop|restart|status`，含端口占用处理、venv 与密钥自动准备、健康等待。

验证方式：

```powershell
cd backend
.\scripts\dev_server.ps1 status
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
.\.venv\Scripts\python.exe scripts\prod_check.py --production
```

### 仍待办 ⏳

- TLS 反向代理、HSTS、只暴露 443；应用端口不对外。
- 进程守护与自动重启（systemd/容器编排），独立 staging 环境。
- 日志聚合、错误追踪（Sentry 或同类）、5xx/登录失败/备份失败告警、uptime 探活。
- 生产密钥管理（Secret Manager）与轮换流程；`backend/.env` 不入库。
- 运行手册（启动/停止/回滚/恢复/轮换密钥）与回滚演练。
- 多 worker/多实例前：限流改共享存储（Redis），上传存储改对象存储，数据库改 PostgreSQL。

**验收**：staging 可重复部署、部署后自动跑 `verify_api.py` 全绿、备份失败能被发现。

---

## 4. 合规：医疗免责、隐私政策、用户协议与健康数据（S0）

### 现状（事实）

- 医疗服务是隐藏入口（不在主 tab，可从“我的”进入 `/medical`），并非真正下架。
- 前端没有任何隐私政策、用户协议、医疗免责页面或文案，也没有注册/预约的同意勾选与版本记录。
- 预约备注 `notes` 为自由文本，可能包含症状、病史等健康信息；订单仅本人可见，但无字段级加密或保留期限业务决策。
- 账号注销已实现“软删除 + 匿名化”，会保留订单与交易审计（实现层已完成，保留期限仍需业务/法务确认）。

### 仍待办 ⏳

- 四语言（中/英/德/法）隐私政策、用户协议、医疗免责声明，带版本号与生效日期。
- 注册与预约前的必选同意项，记录 `consent_version` / `consent_at`。
- 备注字段最小化提示与长度限制；评估加密存储；管理端访问需授权与审计。
- 数据保留/删除策略（预约、备注、注销后数据）。
- 第三方（邮件、支付、云、CDN）DPA 与隐私披露；应用商店隐私清单/数据安全表单。
- 法务审查：医疗宣传边界、跨境传输（GDPR/PIPL）、退款与取消政策。**❓ 需外部确认**

**验收**：注册与预约能展示并记录同意版本；三类文档四语言可访问；注销/删除有可执行流程与时限。

---

## 5. 内容数据：四语言与目的地内容（S1）

### 已完成 ✅

- **通用翻译表** `content_translations`（实体类型 + 实体键 + 字段 + 语言），不为每种语言平铺列。
- **语言回退**：请求语言 → `en` → `zh`；不传 `lang` 时响应与旧版完全一致（向后兼容）。医院、套餐、目的地均支持 `lang=de|fr`（`backend/app/routers/medical.py`、`destinations.py`）。
- **翻译导入工具**：`scripts/import_translations.py` 支持 CSV、按唯一键幂等更新、非法语言码/空值全量校验后报错退出。
- **种子数据文件化**：`backend/seed/base/`（2 医院 / 2 套餐 / 4 目的地 / 3 条德语示例译文）与 `backend/seed/demo/`（+6 医院 / +20 套餐 / +10 目的地 / de·fr 示例译文），空库首次启动自动播种，重复启动只补缺失行、不重复。
- **演示库实测目录数量**：8 家医院、22 个套餐、14 个目的地。

验证方式：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_api.py            # 第 12 段：多语言与回退
.\.venv\Scripts\python.exe scripts\import_translations.py var\translations.csv
```

### 仍待办 ⏳

- 医院、套餐、目的地的正式德/法内容；医疗相关内容必须母语译员 + 医学背景审校，**不得机翻直接上线**。
- 术语表（医院等级、手术名称、科室、价格说明）与内容 QA（长词布局、截断、四语言一致性）。
- 生产内容发布流程（后台或脚本 + 审核人 + 版本），禁止翻译直接改生产库。

**验收**：四语言逐条核对名称与价格说明；切换语言后缓存键随语言变化，不显示旧内容。

---

## 6. 图片与静态资源（S1）

### 已完成 ✅

- 员工图片上传接口：开发环境按日期分目录存本地文件，随机文件名，校验大小与类型，返回前端可直接使用的 URL（`backend/app/routers/uploads.py`）。
- 前端使用 `CachedNetworkImage`：磁盘缓存、按控件宽度解码（上限 1600px）、加载占位与失败渐变占位。
- 需求文档中的外链图片（套餐、目的地、首页 hero）仍可用，前端有失败兜底。

### 仍待办 ⏳

- 对象存储 + CDN（S3 兼容/OSS/COS/MinIO），多实例共享；当前 `local` 仅单机可用。
- 把存量第三方外链图片转存到自有存储并替换种子与前端样例，避免大面积破图；保留失败兜底。
- 图片元数据（宽高、mime、版权、四语言 alt）与上传/审核/替换/下架流程。
- CDN 4xx/5xx 与源站失联告警；图片版权确认。

**验收**：外链全部替换为自有存储；替换图片后缓存按新 key 刷新；无破图。

---

## 7. 账号与安全（S1）

### 已完成 ✅

- 注册、登录、`/auth/me`；密码 bcrypt；JWT HS256（access 默认 7 天、refresh 默认 30 天）。
- **刷新令牌轮换 + 吊销**：refresh 单次使用、重复使用即拒绝；登出吊销当前会话；支持会话管理与“退出所有设备”（`backend/app/routers/auth.py`、`token_revocations`、`auth_sessions`）。
- **找回密码**：一次性令牌、仅存 SHA-256 摘要、短时效；不同邮箱返回完全相同的 200，防止账号枚举。
- **邮箱验证**：令牌短时效、一次性、仅存摘要；重发按用户维度冷却；是否强制验证由配置开关 `MEDITOUR_REQUIRE_EMAIL_VERIFICATION` 控制（默认关闭，仅影响创建预约）。
- **修改密码 / 注销账号**：改密后旧 access/refresh 立即失效；注销为软删除 + 匿名化，保留订单与交易记录。
- **限流**（进程内）：登录失败按 IP + 账号（5 次/300 秒）、注册按 IP（30 次/1 小时）、找回密码按邮箱（3 封/1 小时）与 IP（30 次/1 小时）、验证邮件重发冷却 60 秒；超限返回 429 + `Retry-After`（找回密码邮箱维度静默 200 防枚举）。
- **数据导出**：仅本人，按令牌用户查询，不含密码哈希与令牌。
- **演示账号可控**：`MEDITOUR_SEED_DEMO_USER` 控制创建，生产默认关闭；凭据见 `backend/.env.example` 与 `backend/README.md`。
- 安全加固：请求体上限、安全响应头、统一错误体、登录 401 与会话过期区分。

验证方式：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_api.py            # 第 2、8、11、13 段
```

### 仍待办 🟡 / ⏳

- **token 仍存 SharedPreferences 明文字段**。暂不迁移 `flutter_secure_storage`：Web 端底层仍是浏览器存储，无实质收益；移动端未发布，迁移有会话丢失风险。**待原生移动端发布或有合规要求时再评估。**
- 生产需要 Redis 等共享限流存储（当前进程内计数，多 worker/多实例各自计数）。
- 生产轮换 JWT 密钥、删除演示账号、关闭演示数据开关。
- 密码强度策略（当前仅最少 6 位）。

**验收**：登录→刷新→登出→改密→找回→注销全链路可用；并发刷新只执行一次，失败完整清除会话。

---

## 8. 支付与邮件（S1/S2）

### 已完成 ✅

- **邮件可插拔**：开发默认 `file`（写入 outbox，不真正发信）；生产 `smtp` 必须显式配置，缺配置直接报错而非假装成功。
- **多语言模板**：重置密码、邮箱验证均为 HTML + 纯文本双版本，语言取用户 `preferred_language`，支持 en/zh/de/fr；完整重置链接不写入模板或常规日志。
- **订单状态流转**：员工可将订单推进为 confirmed/completed/cancelled，越权与非法状态有测试覆盖；订单列表默认裁剪敏感字段，详情访问写审计。

验证方式：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_api.py --mail-outbox var\mail_outbox.log
```

### 仍待办 ⏳

- **支付未接入**（无 Stripe/支付宝/微信代码）；灰度建议人工过渡：文案只说“提交预约意向，客服确认后告知费用”，禁止“支付成功/订单完成”。
- 生产 SMTP 服务、域名 SPF/DKIM/DMARC、失败重试与退信处理；事务邮件与营销邮件分开。
- 订单状态通知邮件；若上线在线收款，需回调验签、幂等、退款与对账。**❓ 商户资质与费率需外部确认**

**验收**：真实 SMTP 能收到重置/验证邮件；未接支付前所有文案不误导付款。

---

## 9. 质量门禁（S1）

### 已完成 ✅

- **CI**：`.github/workflows/backend_ci.yml` 仅在后端变更时跑 pytest；`.github/workflows/flutter_ci.yml` 跑 format/analyze/test/build web。
- **后端本地门禁**（当前 HEAD 实测）：
  - `pytest`：**157 passed**
  - `verify_api.py`（对本地运行中的后端）：**通过 112 / 失败 0**
  - `alembic check`：无 diff
  - `check_query_plans.py --strict`：0 条全表扫描/临时 B 树排序
- **附加脚本**：端到端冒烟 `smoke_journey.py`、数据一致性 `check_data_consistency.py`、并发探测 `concurrency_probe.py`、备份/恢复演练。
- **前端本地门禁**（干净 worktree、当前 HEAD 实测）：`flutter analyze` 无问题；`flutter test` **94 passed**（21 个测试文件）；`flutter build web --no-web-resources-cdn` 构建成功。
- 前端已覆盖窄屏 320dp、1.3 倍字号、错误态、空态、键盘链路、横屏安全区、四语键与占位符完整性、订单状态四语映射、取消订单 404/409 差异化提示、离线回退语义。

验证方式：

```powershell
cd backend; .\.venv\Scripts\python.exe -m pytest -q
flutter analyze
flutter test
flutter build web --no-web-resources-cdn
```

### 仍待办 ⏳

- staging 部署后自动跑 `smoke_journey.py` / `verify_api.py`，失败阻断发布。
- 前端真实后端联调 E2E（登录→预约→订单列表）与四语言切换冒烟。
- 依赖漏洞扫描（`pip-audit`、`pub outdated`/Dependabot）与覆盖率阈值。
- 发布检查单与回滚验证记录。

---

## 10. 建议执行顺序：灰度 → 正式上线

### 阶段 A：对外灰度（邀请制/小流量，可人工兜底）

已完成、可直接依赖的能力：

- [x] Alembic 迁移基线、备份/恢复与保留策略、数据一致性巡检。
- [x] 健康检查、容器化文件、结构化日志、安全中间件、`/metrics` 开关。
- [x] 账号闭环（找回/改密/注销/刷新/吊销/会话管理）与认证限流。
- [x] 邮件模板与可插拔后端（开发 file / 生产 smtp）。
- [x] 四语言界面文案、订单状态四语映射、内容多语言机制与翻译导入。
- [x] 后端与前端本地质量门禁全绿（backend_ci / flutter_ci）。

灰度前仍需补齐：

1. **HTTPS + 生产 CORS + Android release 联网验证**（§1）。
2. **PostgreSQL 实际切换验证**，或由业务方明确接受 SQLite 单实例的边界与 RPO ≤ 24h（§2）。
3. **可重复部署 + staging + 监控告警 + 运行手册**（§3）。
4. **合规最低集**：隐私政策、用户协议、医疗免责声明 + 注册/预约同意记录（§4）。
5. **人工预约流程文案**：诚实的“提交意向/待确认”、客服渠道、状态人工推进（§8）。
6. **生产账号安全**：关闭演示账号/演示数据、轮换密钥、配置 SMTP、限流接共享存储（§7、§3）。
7. **staging 冒烟必过**：`verify_api.py`、`smoke_journey.py` 进入发布闸门（§9）。
8. **图片最低保障**：外链转存或至少失效监控与本地兜底（§6）。

灰度退出标准 **【估算】**：20–50 名真实用户完成注册→预约→客服确认闭环；`verify_api.py` 连续 0 失败；无 S0 故障；备份恢复演练成功并记录耗时；无“已付款但未确认”类投诉；崩溃率/5xx/登录失败率有基线数据（阈值需灰度后校准）。

### 阶段 B：正式上线

1. 四语言正式内容与医学审校（§5）。
2. 对象存储 + CDN + 上传/审核流程，外链全部替换（§6）。
3. `flutter_secure_storage` 迁移评估与实施（移动端发布前）(§7)。
4. 事务邮件域名认证与订单通知（§8）。
5. 在线支付（若商业化）或明确长期人工收款流程（§8）。
6. 监控告警、日志保留、密钥轮换、回滚演练（§3）。
7. 合规完整集：DPA、数据保留/删除、应用商店隐私清单（§4）。
8. E2E、依赖/安全扫描、负载与容量复测（§9）。
9. 发布前检查：演示账号已删除、密钥已轮换、CORS 仅生产域名、HTTPS 强制、备份可用。

### 依赖链

```text
域名/DNS ──> HTTPS/反向代理 ──> 邮件链接、支付回调、生产 CORS、Android 联网
托管平台 ──> PostgreSQL ──> Alembic 迁移演练 ──> 备份/恢复与 PITR
正式翻译/医学审校 ──> 德法内容 ──> 四语言邮件/图片 alt/合规文档
邮件服务 ──> 找回密码/邮箱验证/订单通知闭环
法务与公司主体 ──> 隐私协议/医疗免责/支付与邮件合规
staging + 质量门禁 ──> 灰度与正式发布闸门
```

---

## 附录 A：本次实测记录（2026-11-08，HEAD 8a4b103）

| 项目 | 结果 |
| --- | --- |
| 后端 `pytest` | 157 passed |
| `verify_api.py`（本地 8000） | 通过 112 / 失败 0（员工接口段因未提供凭证跳过） |
| `alembic check` | No new upgrade operations detected |
| `check_query_plans.py --strict` | 0 条全表扫描/临时 B 树排序，退出码 0 |
| `prod_check.py`（开发配置） | 2 通过 / 10 警告 / 0 失败 |
| `prod_check.py --production` | 1 通过 / 3 警告 / 8 失败，退出码 1（符合“未切生产配置”预期） |
| 前端 `flutter analyze`（干净 worktree） | No issues found |
| 前端 `flutter test`（干净 worktree） | 94 passed（21 个测试文件） |
| `flutter build web --no-web-resources-cdn` | 构建成功 |
| 演示库目录数据 | 8 家医院 / 22 个套餐 / 14 个目的地 |

容量与延迟数字（并发 100/150/300 的 p95、统计接口 20 万单延迟、备份/恢复耗时、RTO ≈ 1.3s、RPO ≤ 24h）来自 `backend/README.md`「上线容量与限制总览」的既有实测记录，本次未重跑压测。

## 附录 B：未验证 / 待外部确认 ❓

- PostgreSQL 切换：脚手架存在，但本机未构建/运行验证。
- Android `targetSdk` 具体值与 release 包明文 HTTP 拦截表现。
- 真实 SMTP 送达、SPF/DKIM/DMARC 配置效果。
- 翻译字数、供应商报价与返稿周期；医学审校安排。
- GDPR / PIPL 及跨境传输适用路径，需法务确认；本文不构成法律意见。
- 支付渠道商户资质、费率、结算周期与可用地区。
- 云主机、PostgreSQL、对象存储、CDN、邮件服务的实际报价。
- 灰度真实用户规模与崩溃/5xx 阈值。
- 生产域名、证书与备案要求（视部署地区而定）。
