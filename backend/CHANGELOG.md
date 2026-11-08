# 后端变更记录

记录 `backend/` 对外接口、响应字段、行为规则与数据库迁移的变化，供后续接手人快速了解“现在为什么是这样”。

- 接口前缀统一为 `/api/v1`；未特别说明时错误体为 `{"detail": ...}`。
- 按时间倒序排列；同一天按提交顺序倒序。日期为提交日期（Asia/Shanghai）。
- 当前 Alembic head：`d4e6f8a2b1c3`（2026-11-08）。

---

## 2026-11-08 — 种子数据文件化与首次启动自动播种（本批）

### 数据与启动行为

- 种子内容从 Python 代码搬到 `backend/seed/` 下的 JSON，非程序员可直接编辑：
  - `seed/base/`：2 医院 / 2 套餐 / 4 目的地 / 3 条德语示例译文，任何环境可用；
  - `seed/demo/`：+6 医院 / +20 套餐 / +10 目的地 / 64 条 de/fr 译文，仅本地演示与联调用。
  - 合计 8 家医院、22 个套餐、14 个目的地、67 条译文；套餐覆盖 12 个分类、价格 300–45000。
- **空库首次启动自动播种**：应用启动在建库/迁移之后调用 `seed_data()`，无需手工执行脚本；
  已有数据时只补缺失行，不覆盖、不重复。
- 写入按自然键判断存在性：医院/套餐用 `name_en`，目的地用 `id`，译文用
  `(entity_type, entity_key, lang, field)`。默认 insert-only；`--sync` 才更新已有行，
  且永远不删除数据库中多出来的记录。
- 新增 `python -m app.seed` 命令行：`--base` / `--demo` 选择目录，`--sync` 增量更新。
  JSON 格式错误、`name_en` 重复、译文引用不存在实体会报出文件名和行号并中止启动。
- 套餐 `image_url` 在种子文件中可选；`--sync` 不会用空值覆盖后台上传的图片。

### 配置

- 新增 `MEDITOUR_AUTO_SEED`：开发默认开、生产默认关。关闭后启动不写任何数据。
- `MEDITOUR_SEED_DEMO_DATA` 默认值改为随环境：开发开、生产关（原默认关闭）；
  `.env.example` 本地模板显式设为 `1`，保证克隆后启动即有完整演示数据。
- `scripts/prod_check.py` 的“演示开关”检查纳入 `AUTO_SEED`：生产环境三项
  （演示账号 / 自动播种 / demo 数据）任一开启即 FAIL，并提示改用
  `python -m app.seed --base` 显式初始化。

### 接口

- 无接口路径或响应字段变化；`/api/v1/destinations` 的 `lang=de|fr` 现在能命中
  种子中的目的地译文（此前演示译文只覆盖套餐与医院）。

---

## 2026-11-08 — 上线前最后一公里：生产自检、防滥用限流、定时备份（本批）

### 新增脚本

- `scripts/prod_check.py`：上线前配置自检，逐项输出 PASS/WARN/FAIL 与修复建议。
  - `--production` 存在 FAIL 时退出码 1，可直接作为发布流水线关口。
  - 覆盖：密钥强度/占位值、文档与 OpenAPI、CORS 通配与本地地址、`/metrics` 白名单、
    演示账号/数据开关、强制邮箱验证、SQLite、进程内限流、HTTPS、file 邮件后端、
    本地上传存储。
  - 进程内限流与本地存储在单实例下可用，只报 WARN；其余生产风险报 FAIL。

### 接口行为变化

- 新增配置 `MEDITOUR_DOCS_ENABLED`：生产环境默认关闭 `/docs`、`/redoc`、`/openapi.json`
  （开发默认仍开启）。显式环境变量优先。
- **注册**新增按来源 IP 限流：默认 1 小时 30 次，超限返回 `429 + Retry-After`，
  且在写库前拦截。粒度只能是 IP（注册前没有可信账号标识）；代价是同一 NAT/办公室
  共享额度，因此阈值取得较宽，可用 `MEDITOUR_REGISTER_LIMIT_PER_IP` 调整。
- **找回密码**新增双维度限流：
  - 邮箱维度默认 1 小时 3 封；超限时静默返回同样的 200、不发信——若返回 429 会泄露
    “该邮箱已注册”。
  - IP 维度默认 1 小时 30 次；超限返回 `429 + Retry-After`，对所有邮箱一致。
  - 未注册邮箱不占用邮箱额度，避免被用来探测账号。
- **重发验证邮件**新增用户维度冷却（默认 60 秒）：冷却内返回同样的 200，不签发新令牌、
  不发信；可通过 `MEDITOUR_VERIFICATION_RESEND_COOLDOWN_SECONDS` 调整。
- 限流仍为进程内计数（多 worker/多实例各自计数），本次未改变这一点，但已在自检中
  标为生产 WARN。

### 备份与恢复

- 备份文件完成后执行 `wal_checkpoint(TRUNCATE)` 并切回 `journal_mode=DELETE`，
  备份目录不再残留 `-wal`/`-shm`；此前演练发现残留边车文件，单独拷 `.db` 恢复有丢页风险。
- 删除旧备份时一并清理同名 `-wal`/`-shm`。
- 执行 `--force` 恢复前先对目标库做 WAL checkpoint 再生成安全副本；覆盖后删除目标库
  遗留的 `-wal`/`-shm`，防止旧日志页叠加到恢复数据上。
- 新增 `scripts/run_backup_task.ps1` 作为 Windows 计划任务入口：追加日志到
  `var/logs/backup.log`，透传退出码。README 补计划任务创建/立即触发/查询/删除命令。
- 计划任务真实演练：`schtasks /Run` 后 1 秒内产出 278,528 bytes 备份，退出码 0；
  预置的 2024 年旧备份被按周策略删除，最新备份保留。

### 文档

- README 新增「上线前配置自检」与「上线容量与限制总览」：汇总并发 100/150/300 的
  p95、统计接口在 40 单与 20 万单下的延迟、备份/恢复耗时、RTO ≈ 1.3s、RPO ≤ 24h、
  SQLite 单写者与多实例边界，给出“能否上线”的直接判断。

---

## 2026-11-08 — 索引实测、员工统计、备份保留、目的地多语言

### 新增接口

- `GET /staff/stats/overview`（仅 `staff`）
  - 全量：`total_bookings`、`status_counts`（pending / confirmed / completed / cancelled，缺失状态补 0）。
  - 日期范围：`date_from` / `date_to`（含边界，按 UTC 日期解释），默认最近 14 天，最长 90 天；范围颠倒或超限返回 422。
  - 成交金额 `revenue` 按币种分组，完成时间取 `completed_at`；迁移前 `completed_at` 为空的历史订单回退 `created_at`，且先探测是否存在，避免每次空扫。
  - `trend` 按日返回 `created` / `completed` / `revenue`，日期范围与成交金额一致。

### 接口变化

- `GET /destinations` 与 `GET /destinations/{slug}` 新增可选 `lang=zh|en|de|fr`。
  - 不传 `lang` 时响应与旧版本完全一致；前端现有调用不需要改。
  - 只翻译标量字段 `name` / `tagline` / `intro` / `best_season` / `suggest_days`，
    回退顺序与医疗套餐一致（请求语言 → en → zh）。
  - 数组字段 `search_terms` / `experiences` / `tips` 不翻译，类型与主数据保持一致。
  - `id` 仍是 slug 字符串；非法 `lang` 返回 422（大小写不敏感），未知 slug 仍返回 404。
  - 列表关键词 `query` 仍只匹配主数据列，不搜索译文。

### 数据库

- 新迁移 `c2d4e6f8a1b3`，依据 `EXPLAIN QUERY PLAN` 实测补齐索引：
  - `bookings(user_id, id)`：用户订单列表按 `id` 倒序不再建临时 B 树。
  - `bookings(status, completed_at, currency, total_price)`：统计成交金额的覆盖索引，避免按日汇总逐行回表；替代原 `(status, completed_at)`。
  - `medical_packages(is_active, id)`：在售列表过滤 + 排序，消除全表扫描与临时排序。
  - `audit_logs(actor_user_id, created_at)`：替代单列 `actor_user_id` 索引。
- 分类过滤目前由前端本地完成，服务端没有 `category` 查询，因此不建分类索引。
- 新迁移 `d4e6f8a2b1c3`：`content_translations.entity_id` 由整数改为 `String(64)`。
  - 原因：目的地主键是 slug，旧的整数列无法存目的地译文，这一冲突来自此前未提交的
    `destinations.py` 改动——它声明了 `lang` 参数却没有可用的译文存储。
  - 套餐/医院继续存整数主键的文本形式，唯一约束 `(entity_type, entity_id, lang, field)` 不变。
  - SQLite 通过批量重建表转换类型，已有整数值按文本保留；降级前删除目的地译文后恢复整数。

### 运维

- `scripts/check_query_plans.py`：对列表/过滤/统计查询跑 `EXPLAIN QUERY PLAN`，报告全表扫描与临时 B 树排序；`--strict` 有疑点时退出码 1。
- `scripts/backup_db.py` 增加保留策略：最近 N 天每天保留最新一份（默认 7），更早的每个 ISO 周保留最新一份、最多 M 周（默认 4）；最新一份永不删除；只清理 `meditour-YYYYMMDD-HHMMSS.db`。
- `--no-retention` 可只备份不清理；`--daily-keep` / `--weekly-keep` 调整策略。
- 恢复演练（225 KB / 40 单演示库）：备份 298 ms，恢复 270 ms，`alembic upgrade head` 空跑 1031 ms，**实测 RTO ≈ 1.3 s**。

---

## 2026-11-08 — `b403ae0` 订单状态机与审计扩展

### 行为变化（重要）

- 订单状态机锁死：`pending → confirmed|cancelled`、`confirmed → completed|cancelled`。
  - `completed` / `cancelled` 为终态，再流转一律 **409**。
  - 把 `completed` 退回 `pending` 不是合法目标值，返回 **422**（`status` 只接受 confirmed / completed / cancelled）。
  - 用户只能自助取消 `pending`；取消 `confirmed` 订单返回 **409**，提示联系员工。
  - 状态流转改为条件更新（`WHERE id=? AND status=<旧状态>`），并发操作只有一个成功，其余 409。
- `DELETE /auth/account` 注销账号时吊销该用户的全部有效会话（此前只做软删除与匿名化，残留会话仍可用）。
- 审计写入与业务写入同事务；审计写入失败时不返回敏感详情。
- 员工订单详情、状态流转、改价/删除内容、用户取消、用户导出均写审计。
- `audit_logs.entity_id` 统一为字符串，兼容整数主键与目的地 slug；新增 `details` JSON 保存 `before` / `after` 快照。

### 字段新增

- `bookings.confirmed_at`、`cancelled_at`、`completed_at`（迁移 `a7c2e9f4b6d1`）。
  迁移前历史订单为 NULL，无法回溯真实时刻；巡检脚本单独列出。
- 员工订单详情/列表响应包含状态时间戳。
- `audit_logs.details`（JSON）、`entity_id` 改为 `String(64)`。

### 新增接口

- `GET /staff/audit-logs`：按 `action`（精确）、`entity_type`、`entity_id`、`actor_user_id`、`created_from` / `created_to` 过滤，按时间倒序分页；`created_from > created_to` 返回 422。

### 审计事件

| `action` | 触发者 | 说明 |
| --- | --- | --- |
| `booking.view` | 员工 | 查看订单详情（列表不记） |
| `booking.status_change` | 员工 | 状态流转，含前后状态 |
| `booking.cancel` | 用户 | 自助取消 pending |
| `package.update` | 员工 | 仅记录实际变化字段 |
| `package.delete` / `hospital.delete` / `destination.delete` | 员工 | 删除前快照 |
| `user.export` | 用户 | 导出本人数据 |

### 运维

- `scripts/check_data_consistency.py`：输出“确定异常 / 需人工判断”两类巡检结果。
- `scripts/dev_server.ps1`：PowerShell 一键 start / stop / restart / status，处理端口占用、虚拟环境缺失、密钥未设置。

---

## 2026-11-08 — `2f00399` 连接池与 SQLite 写入并发

- 连接池参数可配置：`MEDITOUR_DB_POOL_SIZE`（默认 20）、`MEDITOUR_DB_MAX_OVERFLOW`（默认 20）、`MEDITOUR_DB_POOL_TIMEOUT`（默认 10 秒）。
- 文件型 SQLite 默认开启 WAL（`MEDITOUR_DB_SQLITE_WAL=true`），写锁等待 `MEDITOUR_DB_SQLITE_BUSY_TIMEOUT_MS`（默认 15000），`synchronous=NORMAL`。
- 写冲突改为排队等待，而不是立刻 `database is locked`；池耗尽时明确报 `QueuePool limit ... timed out`。

---

## 2026-11-08 — `8aaa11f` 契约检查、演示数据与探针

- 增加契约检查与演示数据种子：
  - `MEDITOUR_SEED_DEMO_USER=1`：创建演示账号 `demo@meditour.com / Demo123456`。
  - `MEDITOUR_SEED_DEMO_DATA=1`：增量写入联调目录（+6 医院 / +20 套餐 / +10 目的地 / 40 条 de·fr 译文），只插入不修改，生产环境不要开启。
- 增加查询/并发探针脚本，并补充对应索引迁移 `e3f5a7c9b1d2`。

---

## 2026-11-08 — `f6ed771` 冒烟、验证/指标开关与数据保留

- 新增端到端冒烟流程与验证开关：
  - `MEDITOUR_REQUIRE_EMAIL_VERIFICATION`：开启后未验证邮箱创建预约返回 403；登录不受影响。
  - `MEDITOUR_METRICS_ENABLED` / `MEDITOUR_METRICS_ALLOWED_IPS`：控制 `/metrics` 与来源白名单。
- 新增数据保留清理（`scripts/cleanup_data.py`）：
  - `MEDITOUR_TOKEN_RETENTION_DAYS`（默认 30）
  - `MEDITOUR_AUDIT_LOG_RETENTION_DAYS`（默认 365）
  - `MEDITOUR_SOFT_DELETED_ACCOUNT_RETENTION_DAYS`（默认 30）
  - `MEDITOUR_MAIL_PREVIEW_RETENTION_DAYS`（默认 14）
  - `MEDITOUR_UPLOAD_TEMP_RETENTION_DAYS`（默认 1）

---

## 2026-11-08 — `4dda7f0` 邮箱验证、会话管理与指标

### 新增接口

- `POST /auth/email-verification/request`：重新发送验证邮件。
- `POST /auth/email-verification/confirm`：用一次性令牌验证邮箱。
- `GET /auth/sessions`：列出当前账号的设备会话。
- `DELETE /auth/sessions/{session_id}`：吊销指定设备会话。
- `POST /auth/sessions/revoke-all`：退出所有设备。
- `GET /metrics`：轻量运行指标（生产默认关闭，见上）。

### 字段新增

- `users.email_verified_at`；`UserResponse.email_verified` 派生字段。
- 新表 `auth_sessions`：登录设备会话，refresh token 轮换沿用同一行。
- 迁移 `d1a4b7c9e2f3`。

---

## 2026-11-08 — `a39631c` / `371f15c` 原子限流与取消并发

- 登录限流改为先原子占用槽位再校验凭据，避免并发请求同时穿透。
- 取消订单改为条件更新（仅 `status='pending'` 生效）：并发取消同一订单只有一个 200，其余按状态冲突返回 409，不会出现“都成功取消”。

---

## 2026-11-08 — `21fd49d` 重复预约 409

- 同一用户、同一套餐、同一预约时间只允许一个 `pending` 订单；重复提交返回 **409**。
- 由部分唯一索引 `uq_bookings_pending_slot`（`WHERE status = 'pending'`）兜底，并发请求也只有一个成功。
- 取消后可以重新预约同一时段；换日期不受影响。
- 迁移 `b3c9d1e5f7a2`。

---

## 2026-11-08 — `c6dda42` 本地化邮件模板

- 密码重置邮件改为 HTML + 纯文本双版本，按用户 `preferred_language` 选择语言；文件后端写 `mail_preview/*.eml` 便于本地检查。

---

## 2026-11-08 — `31de7bd` 请求体上限与安全响应头

- 全局请求体上限 `MEDITOUR_MAX_REQUEST_BYTES`（默认 10 MiB），超限由中间件返回 **413**；必须大于上传上限。
- 增加安全响应头与统一异常兜底，未捕获异常不泄露堆栈。

---

## 2026-11-08 — `4268f1d` 翻译 CSV 导入

- 新增幂等 CSV 导入脚本，用于人工维护 `content_translations`；重复导入不会产生重复行。

---

## 2026-11-08 — `c8776bb` 员工图片上传

- `POST /staff/uploads`（仅 `staff`，`multipart/form-data` 的 `file`）。
- 仅接受 JPEG / PNG / WebP，并读取文件头校验真实格式；声明类型与内容不符返回 **415**。
- 默认上限 5 MiB（`MEDITOUR_UPLOAD_MAX_BYTES`），超限 **413**，空文件 **422**。
- 文件名由服务端生成（uuid4 + 服务端判定扩展名），不使用客户端文件名；按 UTC 日期分目录。

---

## 2026-11-08 — `8929bd3` 员工内容管理与套餐上下架

### 新增接口

- `/staff/packages`、`/staff/hospitals`、`/staff/destinations` 的列表 / 详情 / 创建 / 更新 / 删除；非 `staff` 一律 403。
- `GET /staff/packages` 默认包含下架套餐，传 `include_inactive=false` 只看在售。

### 字段与行为

- `medical_packages.is_active`（迁移 `f5a1c3e7d9b2`）：下架后公开 `GET /medical/packages` 不再返回，对其下单返回 **404**；历史订单金额快照不受影响。
- 删除保护：
  - 套餐已有订单 → **409**，应改为下架；
  - 医院仍有套餐 → **409**；
  - 目的地仍被行程引用 → **409**。
- 目的地 `id` 为前端 slug，创建后不可修改；重复 slug **409**，格式非法 **422**。

---

## 2026-11-08 — `4ef0f26` 备份与恢复脚本

- `scripts/backup_db.py`：在线备份（sqlite3 backup API），写临时文件后原子替换，并重新统计行数与订单指标校验。
- `scripts/restore_db.py`：目标非空必须 `--force`；覆盖前自动保留 `*.pre-restore-*.bak`；恢复后重新校验，不一致以非零状态退出。
- 非 SQLite 连接串显式拒绝，避免“以为备份成功”。

---

## 2026-11-08 — `aca79dd` 列表分页与查询索引

- 列表接口统一 `page` / `page_size`（上限 100），越界返回 422。
- 增加订单、行程与译文的查询索引（迁移 `e3f5a7c9b1d2`）。

---

## 2026-11-08 — `82da1f4` / `52f9033` 员工角色与订单操作

### 新增接口

- `GET /staff/bookings`：分页/状态过滤；列表项不含 `notes`，联系方式打码。
- `GET /staff/bookings/{id}`：完整联系方式与备注，并写 `booking.view` 审计。
- `PATCH /staff/bookings/{id}/status`：`confirmed` / `completed` / `cancelled`。

### 角色与字段

- `users.role`：`user` / `staff`（迁移 `b7d2e4f6a8c1`）。注册接口不接受客户端指定角色。
- 授予方式：`MEDITOUR_STAFF_EMAILS` 白名单登录时引导，或 `scripts/manage_staff.py` 显式授予/撤销；撤销立即生效。
- 审计表 `audit_logs`（迁移 `d9e4f1a2b6c8`）。

---

## 2026-11-08 — `76df9d6` / `348b173` / `d44087d` / `5900446` 账号闭环与多语言

### 新增接口

- `POST /auth/register`、`POST /auth/login`、`POST /auth/refresh`、`POST /auth/logout`、`GET /auth/me`。
- `POST /auth/password-reset/request`、`POST /auth/password-reset/confirm`、`POST /auth/change-password`。
- `DELETE /auth/account`：软删除 + 匿名化，保留订单外键。
- `GET /auth/export`：导出本人数据 JSON。
- `GET /medical/packages`、`GET /medical/hospitals` 支持可选 `lang=zh|en|de|fr`；不传时响应与旧版本一致。
- 目的地、行程、预约、健康检查等基础端点在更早的基线中提供。

### 字段与行为

- 新表：`token_revocations`、`password_reset_tokens`、`email_verification_tokens`、`content_translations`。
- `users.token_version`：改密/重置/注销时自增，使已签发的 access/refresh 一并失效。
- `users.deleted_at`：软删除标记；注销后禁止登录。
- 译文表唯一约束 `(entity_type, entity_id, lang, field)`，同时覆盖按实体 + 语言的批量查询。
- 登录失败限流；审计日志与请求日志对密码、令牌等字段做脱敏。

---

## 基线（项目初始）

- FastAPI + SQLAlchemy + SQLite，路径前缀 `/api/v1`。
- 基础资源：目的地列表/详情、行程 CRUD、套餐分页、医院列表、创建/查询/取消预约、健康检查。
- 启动时自动执行数据库迁移并写入幂等种子数据。
