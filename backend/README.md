# MediTour 后端

FastAPI + SQLAlchemy + SQLite 的 MediTour API，路径前缀 `/api/v1`，契约以 Flutter 前端为准。

## 本地启动

要求 Python 3.12。

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # 填入 MEDITOUR_SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

启动时会自动执行数据库迁移并写入幂等种子数据（医院、套餐、目的地等）。
演示账号仅在 `MEDITOUR_SEED_DEMO_USER=1` 时创建（`.env.example` 已为本地开启）；关闭开关只会停止创建，不会删除库里已有的账号。
接口文档：`http://127.0.0.1:8000/docs`。

### 一键运维脚本（Windows）

不想记上面的命令时，用 `scripts/dev_server.ps1`：

```powershell
cd backend
.\scripts\dev_server.ps1 start     # 后台启动，日志写 var/dev_server.log
.\scripts\dev_server.ps1 status    # 进程、端口与健康检查
.\scripts\dev_server.ps1 restart
.\scripts\dev_server.ps1 stop
.\scripts\dev_server.ps1 start -Port 8001 -Force   # 换端口；强制结束占用端口的进程
```

脚本会处理三类常见问题：

- **端口占用**：先查 `Get-NetTCPConnection`，占用者是本服务则直接停止；是其它进程时
  默认拒绝并打印 PID/进程名，确认后可加 `-Force` 结束它。
- **虚拟环境缺失**：自动创建 `backend/.venv` 并安装 `requirements.txt`（首次执行较慢）。
- **密钥未设置**：若 `backend/.env` 不存在，从 `.env.example` 复制并写入随机的
  `MEDITOUR_SECRET_KEY`；已有占位值也会被替换。`.env` 已被 `.gitignore` 忽略。

PID 写入 `backend/var/dev_server.pid`；重复 `start` 不会启动第二个实例。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `MEDITOUR_SECRET_KEY`（或 `SECRET_KEY`） | 是 | 无 | JWT 签名密钥；缺失时进程直接启动失败，不会回退到默认值 |
| `DATABASE_URL` | 否 | `sqlite:///backend/meditour.db` | SQLAlchemy 连接串 |
| `MEDITOUR_CURRENCY` | 否 | `EUR` | 种子套餐与订单金额使用的币种 |
| `MEDITOUR_CORS_ORIGINS` | 否 | `http://localhost:8123,http://127.0.0.1:8123` | 允许的浏览器来源，逗号分隔 |
| `MEDITOUR_SEED_DEMO_USER` | 否 | 关闭 | 设为 `1` 时创建演示账号 `demo@meditour.com / Demo123456`；生产环境不要开启，关闭开关不会删除已有账号 |
| `MEDITOUR_SEED_DEMO_DATA` | 否 | 关闭 | 设为 `1` 时增量写入联调演示目录（+6 医院 / +20 套餐 / +10 目的地 / 40 条 de·fr 译文）；只插入不修改，生产环境不要开启 |
| `MEDITOUR_STAFF_EMAILS` | 否 | 空 | 员工邮箱白名单，逗号分隔；命中名单的账号登录时自动授予 `staff`，不会自动建号 |
| `MEDITOUR_ACCESS_TOKEN_EXPIRE_DAYS` | 否 | `7` | access token 有效期（天） |
| `MEDITOUR_REFRESH_TOKEN_EXPIRE_DAYS` | 否 | `30` | refresh token 有效期（天） |
| `MEDITOUR_RESET_TOKEN_EXPIRE_MINUTES` | 否 | `30` | 忘记密码令牌有效期（分钟） |
| `MEDITOUR_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES` | 否 | `60` | 邮箱验证令牌有效期（分钟） |
| `MEDITOUR_REQUIRE_EMAIL_VERIFICATION` | 否 | `false` | 是否把“邮箱已验证”作为创建预约的前置条件；默认关闭，开启后未验证用户登录仍可用，但下单返回 403 |
| `MEDITOUR_PUBLIC_BASE_URL` | 否 | `http://localhost:8123` | 邮件里链接的站点地址（重置密码、验证邮箱） |
| `MEDITOUR_ENV` | 否 | `development` | 运行环境；设为 `production` 时 `/metrics` 默认关闭 |
| `MEDITOUR_METRICS_ENABLED` | 否 | 开发 `true` / 生产 `false` | 是否开放 `/metrics`；显式设置优先于环境默认值 |
| `MEDITOUR_METRICS_ALLOWED_IPS` | 否 | 空 | `/metrics` 来源白名单，精确 IP、逗号分隔；空表示不限来源（风险见「运行指标」） |
| `MEDITOUR_TOKEN_RETENTION_DAYS` | 否 | `30` | 过期/已使用令牌与已失效会话的保留天数 |
| `MEDITOUR_AUDIT_LOG_RETENTION_DAYS` | 否 | `365` | 审计日志保留天数 |
| `MEDITOUR_SOFT_DELETED_ACCOUNT_RETENTION_DAYS` | 否 | `30` | 软删除账号的关联数据（行程、会话、令牌）保留天数；用户行与订单不删 |
| `MEDITOUR_MAIL_PREVIEW_RETENTION_DAYS` | 否 | `14` | `mail_preview/` 的 `.eml` 与 outbox 索引行保留天数 |
| `MEDITOUR_UPLOAD_TEMP_RETENTION_DAYS` | 否 | `1` | 上传目录中 `.tmp/.part/.upload` 临时文件保留天数 |
| `MEDITOUR_MAIL_BACKEND` | 否 | `file` | 邮件实现：`file`（开发，写 outbox 文件）或 `smtp`（生产） |
| `MEDITOUR_MAIL_OUTBOX` | 否 | `backend/var/mail_outbox.log` | `file` 后端的输出文件，已被 `.gitignore` 忽略 |
| `MEDITOUR_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_FROM` / `_STARTTLS` | 否 | 空 / `587` / 空 / 空 / `no-reply@meditour.local` / 开 | `smtp` 后端配置位 |
| `MEDITOUR_STORAGE_BACKEND` | 否 | `local` | 上传存储后端；`local` 落本机磁盘，`s3` 为预留位（未实现时显式报错） |
| `MEDITOUR_UPLOAD_DIR` | 否 | `backend/var/uploads` | 本地上传目录（已被 `.gitignore` 忽略） |
| `MEDITOUR_UPLOAD_MAX_BYTES` | 否 | `5242880`（5 MiB） | 单张图片大小上限，超出返回 413 |
| `MEDITOUR_MAX_REQUEST_BYTES` | 否 | `10485760`（10 MiB） | 全局请求体上限，超出由中间件返回 413；必须大于上传上限 |
| `MEDITOUR_MEDIA_BASE_URL` | 否 | 空 | 媒体对外域名/CDN；留空时上传接口返回站内相对路径 |
| `MEDITOUR_DB_POOL_SIZE` | 否 | `20` | 连接池常驻连接数；与 `_MAX_OVERFLOW` 之和应不小于单进程同步请求线程数（见「连接池与单机容量」） |
| `MEDITOUR_DB_MAX_OVERFLOW` | 否 | `20` | 连接池允许的临时溢出连接数 |
| `MEDITOUR_DB_POOL_TIMEOUT` | 否 | `10` | 拿不到连接时最多排队秒数；超过直接报 `QueuePool limit ... timed out` |
| `MEDITOUR_DB_SQLITE_WAL` | 否 | `true` | 文件型 SQLite 是否开启 WAL；只影响本地 SQLite，对 PostgreSQL 无效 |
| `MEDITOUR_DB_SQLITE_BUSY_TIMEOUT_MS` | 否 | `15000` | SQLite 写锁等待毫秒数；写冲突排队而非立刻 `database is locked` |

本地可把变量写进 `backend/.env`（已被 `.gitignore` 忽略）；生产环境请通过运行环境注入，不要提交 `.env`。

## 预约与订单规则

- `appointment_date` 必须是未来时间，过去时间返回 422。
- `notes` 最长 2000 字符；`contact_phone` 允许 `+` 开头、7–15 位数字（空格、括号、短横线会被规范化）；`contact_email` 必须是合法邮箱。
- 同一用户对同一套餐、同一预约时间只允许一个 `pending` 订单，重复提交返回 409；换日期不受影响。
  该规则同时由部分唯一索引 `uq_bookings_pending_slot`（`WHERE status = 'pending'`）保证，
  并发请求也只有一个成功，其余返回同样形状的 409。取消后可以重新预约同一时段。
- 取消接口：`POST /api/v1/bookings/{id}/cancel`，只能取消自己的 `pending` 订单。
  - 不存在或属于他人：404（不暴露他人订单是否存在）。
  - 已确认（`confirmed`）：409，提示 `Confirmed bookings cannot be cancelled by the user; please contact staff`。
    已确认订单已进入员工处理流程，用户不能单方面取消，需由员工操作。
  - 其它非 `pending` 状态（`completed` / `cancelled`）：409。请求本身合法，但与资源
    当前状态冲突，因此用 409 而非 422；422 仅用于请求体校验失败。
  - 取消后 `status` 变为 `cancelled`，写入 `cancelled_at`，其余响应字段保持不变。
  - 取消使用条件更新（仅当 `status='pending'` 时生效）；并发取消同一订单只有一个
    返回 200，其余按状态冲突返回 409，不会出现多个请求都“成功取消”。
  - 每次成功取消写入审计：`action=booking.cancel`，`details` 记录
    `before={"status": "pending"}`、`after={"status": "cancelled"}`。

## 订单运营与员工角色

订单状态机（`completed` / `cancelled` 是终态，任何角色都不能再流转）：

```text
pending ──> confirmed ──> completed
   │             │
   └──> cancelled <┘
```

- 用户侧：`pending → cancelled`（自助取消）；`confirmed` 不允许用户取消，需员工操作。
- 员工侧：`pending → confirmed|cancelled`、`confirmed → completed|cancelled`。
- `completed` / `cancelled` 再流转一律 409；把 `completed` “退回 pending” 也不是合法
  目标值，返回 422（`status` 只接受 confirmed/completed/cancelled）。
- 状态时间戳：`confirmed_at`、`cancelled_at`、`completed_at` 只在对应流转发生时写入，
  互不覆盖。迁移前的历史订单这三列为 NULL（无法回溯真实时刻），巡检脚本会单列出来。
- 状态流转使用条件更新（`WHERE id=? AND status=<读到的状态>`），两个员工同时操作时
  只有一个成功，另一个返回 409（`Booking status changed concurrently...`）。

角色只有 `user` 与 `staff`，注册接口不接受客户端指定 `role`，因此普通用户无法
自助提升。授予方式有两种，都需要服务端权限：

1. `MEDITOUR_STAFF_EMAILS` 白名单：把已有账号邮箱写进环境变量，该账号下次登录时
   自动变成 `staff`。白名单只引导已有账号，不会自动注册。
2. `scripts/manage_staff.py`：显式授予/撤销，便于运维审计。
   ```bash
   python scripts/manage_staff.py --email staff@example.com            # 授予已有账号
   python scripts/manage_staff.py --email staff@example.com --revoke   # 撤销
   python scripts/manage_staff.py --email staff@example.com --password "Staff123456"  # 直接建员工账号
   ```
   撤销立即生效：每次请求都从数据库读取角色，旧令牌也会立刻失去员工权限。
   白名单不会自动降级，移除名单后仍需执行一次 `--revoke`，避免误删环境变量导致
   正在值班的员工突然失去权限。

员工可以查看**全部**订单，而不是只看与自己无关的订单：当前系统没有派单/归属字段，
客服需要能处理任意客户发起的订单。后续若引入归属，应在服务端加过滤条件，而不是靠
前端隐藏。

- `GET /api/v1/staff/bookings`：分页 `page` / `page_size`（上限 100）/ `status` 过滤；
  列表项**不含 `notes`**，`contact_phone`、`contact_email` 返回打码值。
- `GET /api/v1/staff/bookings/{id}`：详情返回完整联系方式与备注，并写入 `audit_logs`
  审计记录（操作者 id/邮箱、`action=booking.view`、`entity_type=booking`、`entity_id`、
  `created_at`）。列表访问不记录审计；审计写入失败时不会返回敏感详情。
- `PATCH /api/v1/staff/bookings/{id}/status`，请求体 `{"status": "confirmed"}`、
  `{"status": "completed"}` 或 `{"status": "cancelled"}`。
  - 非 `staff`：403；未登录：401；订单不存在：404。
  - 跳过中间状态（`pending → completed`）或对已结束订单再流转：409。
  - 目标值不是 `confirmed` / `completed` / `cancelled`：422（请求体校验失败）。
  - 成功流转写入对应时间戳与审计（`action=booking.status_change`，含变更前后状态）。
- 普通用户即使拥有订单本身，也不能调用以上员工接口修改状态（测试覆盖 403）。

### 审计日志

所有审计写入 `audit_logs`，字段包括操作者 id/邮箱、`action`、`entity_type`、
`entity_id`、`details`（JSON 的 `before` / `after` 快照）与 `created_at`。
`entity_id` 统一为字符串，兼容整数主键与目的地 slug。

| 事件 | `action` | 谁触发 | `details` |
| --- | --- | --- | --- |
| 员工查看订单详情 | `booking.view` | 员工 | 无（只读访问） |
| 员工流转订单状态 | `booking.status_change` | 员工 | `{"before":{"status":...},"after":{"status":...}}` |
| 用户取消订单 | `booking.cancel` | 用户 | 同上 |
| 员工改价/改内容 | `package.update` | 员工 | 仅实际变化的字段前后值 |
| 员工删除内容 | `package.delete` / `hospital.delete` / `destination.delete` | 员工 | 删除前快照（名称、价格、状态等） |
| 用户导出数据 | `user.export` | 用户 | `{"after":{"bookings":N,"itineraries":N}}` |

员工查询接口：

```text
GET /api/v1/staff/audit-logs
  ?action=booking.status_change        # 精确匹配
  &entity_type=booking&entity_id=42    # 可选
  &actor_user_id=7                     # 可选
  &created_from=2026-11-01T00:00:00Z   # 含边界，无时区按 UTC
  &created_to=2026-11-08T23:59:59Z
  &page=1&page_size=20                 # page_size 上限 100
```

- 仅 `staff` 可访问（否则 403），按 `created_at` 倒序返回。
- `created_from > created_to` 返回 422。
- 审计与业务写入同事务提交：写不进去就不返回敏感数据，避免出现无记录的访问。

## 内容运营（员工）

员工可维护套餐、医院与目的地，全部在 `/api/v1/staff/*` 下，非 `staff` 一律 403。

| 资源 | 列表 | 详情 | 创建 | 更新 | 删除 |
| --- | --- | --- | --- | --- | --- |
| 套餐 | `GET /staff/packages` | `GET /staff/packages/{id}` | `POST /staff/packages` | `PATCH` | `DELETE` |
| 医院 | `GET /staff/hospitals` | `GET /staff/hospitals/{id}` | `POST /staff/hospitals` | `PATCH` | `DELETE` |
| 目的地 | `GET /staff/destinations` | `GET /staff/destinations/{slug}` | `POST /staff/destinations` | `PATCH` | `DELETE` |

- 套餐新增 `is_active`。`PATCH /staff/packages/{id}` 传 `{"is_active": false}` 即下架：
  公开 `GET /medical/packages` 不再返回该套餐，`POST /bookings/` 对它返回 404
  （`Medical package is not available for booking`）。员工列表默认包含下架套餐，
  传 `include_inactive=false` 只看在售。
- 订单价格是快照：`bookings.total_price` 在下单时写入，之后调价不影响历史订单。
  测试 `test_price_change_does_not_affect_existing_booking` 同时校验用户侧列表与员工侧详情；
  新订单才使用新价格。注意 `package_name` 仍实时取自套餐关系，改名会改变历史订单的
  展示名称（价格与币种不受影响）。
- 删除保护（不会级联删除业务数据）：
  - 套餐已有订单 → 409，应改为下架；
  - 医院仍有套餐 → 409，需先迁移或删除套餐；
  - 目的地仍被任意行程（整体或按天）引用 → 409。
- 目的地 `id` 是前端使用的 slug（小写字母、数字、连字符），创建后不可修改；
  重复 slug 返回 409，格式不合法返回 422。员工目的地列表额外返回 `sort_order`。
  公开的 `/destinations` 端点未改动。
- 员工侧写接口放在 `app/routers/staff_content.py`，与公开只读的 `destinations.py` 分离。

## 图片上传

`POST /api/v1/staff/uploads`（需要 `staff`），`multipart/form-data` 的 `file` 字段。

- 仅接受 JPEG / PNG / WebP，并读取文件头校验真实格式；声明类型与内容不符返回 415。
- 默认上限 5 MiB（`MEDITOUR_UPLOAD_MAX_BYTES`），超出返回 413；空文件返回 422。
- 文件名由服务端生成（uuid4 + 服务端判定的扩展名），**完全不使用客户端文件名**，
  避免路径穿越与重名；按 UTC 日期分目录：`var/uploads/YYYY/MM/DD/<32位hex>.png`。
- 返回 `{"url", "path", "filename", "size", "content_type"}`。`url` 在未配置
  `MEDITOUR_MEDIA_BASE_URL` 时是站内相对路径（如 `/media/uploads/2026/11/08/....png`），
  配置后返回绝对地址，可直接交给前端 `Image.network`。
- 后端用 `StaticFiles` 在 `/media/uploads` 直接提供文件。
- **当前实现只能单机使用**：文件写在本机磁盘，多实例部署时请求落到另一台机器会 404。
  多实例必须改用对象存储（`app/storage.py` 的 `s3` 预留位，未实现时显式报错）或把
  上传目录挂到共享卷。缩略图/压缩/病毒扫描尚未实现，生产接入前需要补齐。

## 分页约定与索引

统一分页规则（`app/pagination.py`）：

- `page` 从 1 开始；`page_size` 默认 20、上限 100；越界统一返回 422。
- 返回分页结构的列表统一为 `{items, total, page, page_size, pages}`。
- 当前适用：`/medical/packages`、`/staff/bookings`、`/staff/packages`、
  `/staff/hospitals`、`/staff/destinations`。

受 Flutter 现有契约限制，以下端点必须保持裸数组，**不能**改成 `{items: ...}`：
`/medical/hospitals`（前端按数组解析）、`/bookings/`、`/itineraries`、`/destinations`。
这些列表如需分页，只能新增端点或做 API 版本化。

索引（迁移 `e3f5a7c9b1d2`）：

| 表 | 索引 | 用途 |
| --- | --- | --- |
| `bookings` | `ix_bookings_user_status (user_id, status)` | 用户订单/状态过滤，前缀覆盖仅 `user_id` 的查询 |
| `bookings` | `ix_bookings_status_created_at (status, created_at)` | 员工按状态过滤并按时间排序 |
| `bookings` | `ix_bookings_created_at (created_at)` | 员工不筛选状态时的时间排序 |
| `itineraries` | `ix_itineraries_user_start (user_id, start_date)` | 行程按用户过滤并按出发日期排序 |
| `content_translations` | 唯一约束 `(entity_type, entity_id, lang, field)` | 查询前缀已包含 `entity_type + entity_id + lang` |

同时清理重复索引：`ix_bookings_user_id`、`ix_itineraries_user_id`（复合索引前缀已覆盖）
与 `ix_content_translations_lookup`（与唯一约束前缀重复）。`order_no`、`token_hash`、
`jti` 等唯一索引保留，用于等值查找。

### 列表接口查询次数（N+1）

`tests/test_query_counts.py` 用 SQLAlchemy 的 `before_cursor_execute` 统计单次请求的
SELECT 数，确认列表接口是常数查询而不是随条数增长。当前结果（`pytest -s` 可见）：

| 接口 | 数据量 A | 数据量 B | 结论 |
| --- | --- | --- | --- |
| `GET /bookings/` | 2 条 → 4 次 | 8 条 → 4 次 | 常数 |
| `GET /itineraries` | 2 条 → 5 次 | 8 条 → 5 次 | 常数（已修复 N+1） |
| `GET /medical/packages` | page_size=1 → 2 次 | page_size=100 → 2 次 | 常数 |
| `GET /medical/hospitals` | — | 1 次 | 单查询 |
| `GET /destinations` | — | 1 次 | 单查询 |
| `GET /staff/bookings` | page_size=2 → 5 次 | page_size=20 → 5 次 | 常数 |

认证链路固定消耗 3 次查询（吊销表、会话表、用户），因此用户侧列表的基线是 3 + 列表查询。
`GET /itineraries` 修复前是 `2 条 → 6 次、8 条 → 12 次`（每条行程懒加载一次 `days`）；
加上 `selectinload(Itinerary.days)` 后固定为 5 次（3 次认证 + 1 次行程 + 1 次批量加载每日安排）。
行程详情/创建/更新仍是单条记录，不会触发该问题。

## 认证与令牌

- `POST /api/v1/auth/login` 返回 `access_token` 与 `refresh_token`，原有字段含义不变。
- `POST /api/v1/auth/refresh` 用 refresh token 换新令牌；旧 refresh token 立即失效，重复使用返回 401。
- `POST /api/v1/auth/logout` 吊销当前设备会话：当前 access token、可选的 refresh token，以及同一会话里更早签发但尚未过期的 access token 一并失效。前端登出后应丢弃本地令牌并重新登录。
- 吊销名单存放在数据库表 `token_revocations`（按 `jti`），服务和进程重启后仍然有效；过期记录在刷新/登出时顺带清理。
- 登录签发的 access/refresh token 带 `sid`，绑定到 `auth_sessions` 里的一次登录会话；单独吊销该会话后，即使 access token 未过期也会立即被拒绝。上线前签发、没有 `sid` 的旧令牌不受会话吊销影响，只能等自然过期。
- 旧版本签发、没有 `type`/`jti` 的 access token 仍可继续使用；这类令牌无法被登出吊销，会在过期后自然失效。
- 令牌载荷带 `ver`（用户 `token_version`）；改密、重置密码、注销账号会自增该版本，使该用户所有已签发的 access/refresh 令牌立即失效。旧令牌缺少 `ver` 时按 `0` 处理，兼容上线前签发的令牌。
- 所有 401 的错误体保持 `{"detail": "..."}` 字符串形状。

## 邮箱验证

- 注册成功后立即按 `preferred_language` 发送验证邮件（`zh/en/de/fr`，复用现有 HTML + 纯文本模板机制）；发送失败不回滚注册，也不改变响应。
- `POST /api/v1/auth/email-verification/confirm`，请求体 `{"token": "..."}`：公开接口，令牌默认 60 分钟有效、只能成功使用一次；成功返回 `200`，无效/过期/已使用统一返回 `400`。
- `POST /api/v1/auth/email-verification/request`：需要 Bearer 鉴权，重发验证邮件。已验证的账号不再发信，但无论当前是否已验证、发信是否成功，都返回**同一个** `200` 响应；重发会使之前未使用的令牌作废。
- 验证状态通过 `email_verified` 返回：`POST /auth/register`、`GET /auth/me`，以及登录/刷新响应（`TokenResponse`）都带该字段。
- **当前不阻断登录**：未验证用户与已验证用户的登录、浏览、导出等权限完全相同。这是为了不打断前端尚未做验证引导的现有流程。
- **强制验证是可配置开关，默认关闭**：`MEDITOUR_REQUIRE_EMAIL_VERIFICATION=true` 时，未验证用户仍可登录与浏览，但 `POST /bookings/` 返回 `403`（`detail="Email verification required"`）。默认 `false`，现有流程不受影响；产品确认要强制时只需改环境变量，无需改代码。测试 `test_booking_requires_verified_email_when_switch_enabled` 覆盖开关打开后的 403 与确认邮箱后的 201。

## 会话管理

- `GET /api/v1/auth/sessions`：需要 Bearer，列出当前用户未吊销且未过期的会话。每项只包含：
  - `id`：随机会话标识（不是令牌）；
  - `created_at`、`last_used_at`；
  - `user_agent`：截断到 200 字符；
  - `ip`：IPv4 打码最后一段、IPv6 只保留前两段；
  - `current`：是否当前请求所用会话。
  **不返回 access/refresh token、jti 或完整 IP。**
- `DELETE /api/v1/auth/sessions/{id}`：吊销自己的单个会话；不存在、属于他人或已吊销统一返回 `404`。吊销后该会话的 access/refresh 令牌立即失效。
- `POST /api/v1/auth/sessions/revoke-all`：吊销全部会话并自增 `token_version`，已经签发的令牌（包括当前令牌）立即失效。
- 选型：`token_revocations` 只记录已吊销的 jti，缺少设备元信息，也无法表达“会话仍有效但某个 access token 已单独登出”；因此新增正向表 `auth_sessions`，每次登录一行，refresh 轮换沿用同一行，只更新 jti 与最后使用时间。两张表职责不同，不合并。

## 账号闭环

- `POST /api/v1/auth/password-reset/request`，请求体 `{"email": "..."}`。
  - 无论邮箱是否注册，都返回同样的 `200` 与同一句 `detail`，不泄露“该邮箱是否已注册”。
  - 令牌为随机字符串，数据库只存 SHA-256 摘要（`password_reset_tokens.token_hash`），默认 30 分钟过期、只能使用一次；同一用户再次请求会作废之前未使用的令牌。
- `POST /api/v1/auth/password-reset/confirm`，请求体 `{"token": "...", "new_password": "..."}`。
  - 成功 `200`；令牌不存在、已用过或已过期统一返回 `400`，错误体不区分具体原因。
  - 成功后 `token_version` 自增，旧 access/refresh 令牌全部失效。
- `POST /api/v1/auth/change-password`，需要 Bearer 鉴权，请求体 `{"current_password": "...", "new_password": "..."}`。
  - 当前密码错误返回 `400`；成功后同样自增 `token_version`，该用户已有的 refresh token（以及 access token）全部失效，需要重新登录。
- `DELETE /api/v1/auth/account`，需要 Bearer 鉴权，请求体 `{"password": "..."}`。
  - 采用**软删除 + 匿名化**，而不是物理删除：订单是财务凭证且被外键引用，直接删用户会破坏订单完整性。
  - 该用户的 `pending` 订单改为 `cancelled`；所有订单的联系人姓名/电话/邮箱/备注被匿名化；行程与每日安排属于纯个人数据，直接删除。
  - 用户行保留，但邮箱改为 `deleted-<id>-<随机串>@deleted.invalid`，姓名、电话、密码哈希被清空/随机化，并写入 `deleted_at`；此后无法登录，旧令牌也因 `token_version` 自增而失效。
  - 后端目前没有收藏表，收藏只存在客户端本地，因此注销时没有服务端收藏可级联删除。

## 邮件发送（开发 / 生产）

- 重置密码、邮箱验证邮件都是 HTML + 纯文本双版本（`app/mail_templates.py`），语言取用户 `preferred_language`，支持 `zh/en/de/fr`；`zh-CN`、`de_DE` 这类地区变体归一到主语言，不认识的语言回退英文。
- 本批注册流程实际生成的验证邮件预览（中文用户）：
  `backend/var/mail_preview/20261108T025150416034Z-6b0aaaa4.eml`，主题
  `验证你的 MediTour 邮箱`，同样包含 `text/plain` 与 `text/html` 两个 part。验证邮件的 outbox 索引行额外带 `kind=email_verification`，便于脚本区分重置令牌与验证令牌。
- 开发默认 `MEDITOUR_MAIL_BACKEND=file`：
  - 完整邮件（含 HTML 与纯文本两个 part）写成 `.eml`，落在 `backend/var/mail_preview/`（可用 `MEDITOUR_MAIL_PREVIEW_DIR` 覆盖），可直接用邮件客户端打开看效果；
  - `backend/var/mail_outbox.log` 只保留一行索引（收件人、主题、`token=`、`.eml` 文件名），**不再写入完整重置链接**，该文件已被 `.gitignore` 忽略。
  - 本机实测（德语用户，经 `POST /auth/password-reset/request` 触发）生成的预览文件：
    `backend/var/mail_preview/20261108T022655083971Z-53ceffd9.eml`，主题
    `MediTour-Passwort zurücksetzen`，包含 `text/plain` 与 `text/html` 两个 part。
- 常规请求日志只记录 `password_reset_email_written` 和预览文件路径，不记录收件人、令牌或完整链接；日志脱敏规则同时覆盖邮箱与 `token` 键值。
- 生产设置 `MEDITOUR_MAIL_BACKEND=smtp` 并配置 `MEDITOUR_SMTP_*`；缺少 `MEDITOUR_SMTP_HOST` 时发信直接抛错，不会静默伪装成功。
- 发信失败不会改变接口响应（仍返回统一的 `200`），失败原因写入日志，避免通过响应差异判断邮箱是否存在。当前环境如果仍是 `file` 后端，就是“写文件”而不是“已真实发信”。

## 医疗内容多语言

- `GET /api/v1/medical/packages` 与 `GET /api/v1/medical/hospitals` 增加可选查询参数 `lang`，支持 `zh` / `en` / `de` / `fr`。
- **不传 `lang` 时响应与旧版本完全一致**：`name` 仍是中文、`name_en` 仍是英文，前端无需改动。
- 传 `lang` 时，`name`（套餐还有 `description`）按 `请求语言 → en → zh` 回退：
  - `lang=zh` 返回中文；`lang=en` 使用现有英文列；
  - `lang=de/fr` 先查 `content_translations` 表，没有译文时回退英文，再回退中文。
- 译文存放在 `content_translations`（`entity_type` / `entity_id` / `lang` / `field` / `value`），没有给业务表平铺 `name_de`、`name_fr` 列；新增语言只需补数据，不改表结构。
- 种子数据包含一条德语示例（膝关节置换套餐与协和医院），仅用于验证接口与回退逻辑，**不是可直接上线的人工译文**。
- 上线前必须由人工翻译并复核的字段：套餐 `name` / `description`、医院 `name` / `level`，以及任何医疗适应症、风险提示、价格与疗效相关文案。机器翻译只能作为草稿，不能冒充成品；未完成人工翻译的字段会按上述顺序回退，不会被机器生成的文本覆盖。
- 人工译文通过 `scripts/import_translations.py` 批量导入（见下节），不走接口自动翻译。

## 人工翻译批量导入

`scripts/import_translations.py` 把人工翻译结果导入 `content_translations`。

为什么用 CSV 而不是 JSON：翻译/运营人员直接用 Excel/Numbers 维护，导出 CSV 即可；
五列扁平结构没有嵌套，JSON 需要处理层级、引号与转义，对非工程人员更容易出错，
也不利于逐行 review。

```csv
entity_type,entity_id,lang,field,value
package,1,fr,name,Remplacement du genou
package,1,fr,description,"Intervention réalisée par une équipe expérimentée, avec prothèse importée."
hospital,1,fr,name,Hôpital Peking Union
```

```bash
cd backend
python scripts/import_translations.py var/translations.csv --dry-run   # 只校验并统计
python scripts/import_translations.py var/translations.csv
```

- 两阶段执行：先全量校验（缺列、非法语言码、空值、未知实体、未知字段、文件内重复
  唯一键），任一行有错就打印**全部问题与行号**并退出码 1，**不写入任何一行**；
  全部通过后才按 `(entity_type, entity_id, lang, field)` 幂等 upsert。
- 语言码必须在 `zh/en/de/fr` 内，但**不接受 `en` / `zh`**：这两类主数据在业务表列
  （`name` / `name_en` 等）中维护，写进翻译表不会被公开接口读取，属于“看似生效”的死数据。
- 字段白名单：`package` 的 `name` / `description`、`hospital` 的 `name`。
  `destination` 暂不支持——`content_translations.entity_id` 是整数，而目的地主键是 slug。
- 重复执行同一文件不会产生重复行或额外更新；文件内同一唯一键出现两次会直接报错，
  避免“后一行覆盖前一行”的静默行为。

本机演练（演练库 `backend/var/drill/`，已被 `.gitignore` 忽略）真实输出：

```text
> python scripts\import_translations.py var\drill\translations-sample.csv --dry-run
预演完成（未写库）
  文件: var\drill\translations-sample.csv
  总行数: 3
  新增: 3
  更新: 0
  未变化: 0

> python scripts\import_translations.py var\drill\translations-sample.csv
导入完成
  文件: var\drill\translations-sample.csv
  总行数: 3
  新增: 3
  更新: 0
  未变化: 0

# 再执行同一文件：幂等
导入完成
  文件: var\drill\translations-sample.csv
  总行数: 3
  新增: 0
  更新: 0
  未变化: 3

> python scripts\import_translations.py var\drill\translations-bad.csv
导入失败，共 3 处问题：
第 2 行: 不支持的语言码 'es'，允许: de, fr
第 3 行: value 不能为空
第 4 行: package id=999999 不存在
# 退出码 1，库内没有任何新增或修改
```

与其它脚本一致，执行前需要设置 `MEDITOUR_SECRET_KEY`（或 `backend/.env`），
并且数据库已执行到最新迁移。

## 用户数据导出

- `GET /api/v1/auth/export`，需要 Bearer 鉴权，返回 `application/json` 下载（`Content-Disposition: attachment; filename="meditour-export-<id>.json"`）。
- 内容为当前令牌所属用户本人的数据：`account`（账号信息）、`bookings`（订单及联系人/备注字段）、`itineraries`（行程与每日安排）、`favorites`（后端没有收藏表，固定为 `[]`）。
- 接口不接受任何用户 id 参数，只按令牌里的 `user_id` 查询，避免越权导出他人数据；响应不包含密码哈希、令牌或其他凭据。
- 顶层字段：`exported_at`、`format_version`（当前为 `1`）、`account`、`bookings`、`itineraries`、`favorites`。

## 登录限流

同一 IP + 账号在 300 秒内失败 5 次后，登录返回 429 并带 `Retry-After`；成功登录会清零计数。
「检查阈值 + 预占失败名额」在同一个进程锁内完成，因此并发失败时最多只有 5 个请求
进入密码校验并返回 401，其余直接 429，不会出现多个请求同时穿过阈值的情况。
限流状态是**进程内**的：多 worker / 多实例部署时各进程独立计数，重启后清零，也无法防止攻击者用大量账号轮换撞库。生产多进程部署应换成 Redis 等共享存储，并配合网关层限流。
副作用是攻击者可能故意失败 5 次导致某个账号短暂无法登录；当前窗口只有 5 分钟，如需更强防护可加验证码或按 IP 维度限流。

## 日志

- 每个请求输出一行 JSON：`ts`、`level`、`logger`、`message`、`request_id`、`method`、`path`、`status`、`duration_ms`。
- 响应头返回 `X-Request-ID`；客户端传入同名头时原样透传，便于跨服务排查。
- 脱敏规则集中在 [app/logging_config.py](app/logging_config.py)：JWT、邮箱、手机号以及 `password`/`token`/`notes`/`phone`/`email` 等键值统一替换为 `[REDACTED]`。
- 请求日志不记录请求体与查询串；路由代码也不做敏感字段拼接。Docker 启动参数已加 `--no-access-log`，避免 uvicorn 另记一份未脱敏访问日志。

## 安全中间件与错误体

所有响应都会经过 [app/middleware.py](app/middleware.py)：

- **请求体上限**：默认 10 MiB（`MEDITOUR_MAX_REQUEST_BYTES`），必须大于上传单文件上限。
  有 `Content-Length` 时直接拒绝；分块传输（chunked）则在流式读取时计数并在超限处中止。
  超限返回 `413` + `{"detail": "Request body too large"}`，不会进入路由与 JSON 解析。
- **安全响应头**：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、
  `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`。
  `/docs`、`/redoc`、`/openapi.json` 不加严格 CSP（Swagger UI 需要加载外部资源）。
- **HSTS**：仅当请求是 HTTPS（直连 TLS，或反代传入 `X-Forwarded-Proto: https`）时下发
  `Strict-Transport-Security: max-age=31536000; includeSubDomains`；本地 HTTP 不会下发。
- **异常兜底**：未处理异常统一返回 `500` + `{"detail": "Internal server error"}`，
  堆栈只进服务端日志（经脱敏），响应体不含异常类名、消息或 traceback。
  错误体形状与现有的 400/401/403/404/409/422 保持一致，前端解析逻辑不需要改动。

## 运行指标 `/metrics`

`GET /metrics` 固定在根路径（不在 `/api/v1` 下），返回 `text/plain`：

- `meditour_requests_total`、`meditour_requests_by_method{method="..."}`
- 状态码分布 `meditour_responses_total{status="..."}`
- 毫秒耗时直方图 `meditour_request_duration_ms_bucket{le="..."}`、`_sum`、`_count`
- 数据库连接池 `meditour_db_pool_size` / `_checked_out` / `_overflow`（非池化后端输出 `meditour_db_pool_available 0`）
- `meditour_uptime_seconds`

不包含路径参数、查询串、请求体、令牌或用户信息；`/metrics` 自身不计入请求数。

选型：输出是 Prometheus 文本格式的兼容子集，但**没有引入 `prometheus_client`**。当前指标数量固定，官方客户端带来的注册表生命周期与多进程聚合问题大于收益。计数保存在进程内，多 worker 各自独立、重启清零；需要聚合时由 Prometheus 抓取。

开关：`MEDITOUR_ENV=production` 时默认关闭，`MEDITOUR_METRICS_ENABLED=true/false` 可显式覆盖；关闭时返回 `404`（而不是 `403`，避免暴露端点存在）。

安全提示：端点无鉴权，开放后任何能访问服务的人都能看到流量与错误分布。生产环境若开启，应在网关/内网层限制来源，或后续增加管理员鉴权；这是运维/产品决策，当前未硬编码。

来源白名单：`MEDITOUR_METRICS_ALLOWED_IPS` 可填精确 IP（逗号分隔，**不支持 CIDR**）。默认空，表示不限制来源——此时任何能访问服务的客户端都能抓取指标。白名单非空时，来源 IP 不在名单内也返回 `404`，与“端点关闭”的响应一致，避免泄露白名单是否生效。反向代理场景下 `request.client.host` 是代理地址，需要按实际部署填写代理 IP 或在网关层做网段限制。

## 错误码对照表

下表按后端代码的实际行为逐条整理，方便前端按状态码分流。除健康检查的 503 外，错误响应体统一为
`{"detail": "..."}`；请求参数校验失败（422）时 `detail` 是字段错误数组。

| 状态码 | 含义 | 触发场景 |
| --- | --- | --- |
| 400 | 请求格式合法，但业务前置条件不满足 | `POST /auth/password-reset/confirm` 令牌不存在、已使用或已过期（统一 `Invalid or expired reset token`）；`POST /auth/email-verification/confirm` 令牌不存在、已使用或已过期（统一 `Invalid or expired verification token`）；`POST /auth/change-password` 当前密码错误；`DELETE /auth/account` 密码错误 |
| 401 | 未认证或凭据失效 | 任意需要 Bearer 的端点：缺少/为空/无效/过期/已吊销的 access token、`token_version` 不匹配、账号已注销（`Not authenticated` 或 `Invalid or expired token`，带 `WWW-Authenticate: Bearer`）；`POST /auth/login` 邮箱或密码错误（含已注销账号）；`POST /auth/refresh` refresh token 无效、过期、重复使用或所属用户失效；`POST /auth/logout` access/refresh token 无效，或 refresh token 不属于当前用户 |
| 403 | 已认证但权限不足 | 非 `staff` 角色访问 `/staff/*` 端点，`detail="Staff privileges required"`。普通用户即使拥有该订单也不能借此修改状态；`MEDITOUR_REQUIRE_EMAIL_VERIFICATION=true` 时未验证用户 `POST /bookings/` 返回 `detail="Email verification required"` |
| 404 | 资源不存在，或存在但不属于当前用户 | `POST /bookings/` 套餐不存在**或已下架**（下架套餐按不存在处理，不暴露其存在）；`POST /bookings/{id}/cancel`、`GET /staff/bookings/{id}`、`PATCH /staff/bookings/{id}/status` 订单不存在（用户侧与不存在/属于他人共用一个 404）；`GET/PUT/DELETE /itineraries/{id}` 行程不存在或属于他人；`GET /destinations/{id}` 目的地不存在；`/staff/packages|hospitals|destinations/{id}` 目标不存在；`DELETE /auth/sessions/{id}` 会话不存在、属于他人或已吊销；`GET /metrics` 指标端点关闭或来源不在白名单时 |
| 409 | 与资源当前状态冲突 | `POST /auth/register` 邮箱已注册；`POST /bookings/` 同用户同套餐同预约时间已有 `pending` 订单；`POST /bookings/{id}/cancel` 当前状态不是 `pending`，其中 `confirmed` 订单会提示需联系员工；`PATCH /staff/bookings/{id}/status` 跳过中间状态、对已结束订单再流转或并发状态已变；员工删除套餐时仍有订单、删除医院时仍有套餐、删除目的地时仍被行程引用；创建目的地时 slug 已存在 |
| 413 | 请求体过大 | 任意端点：请求体超过 `MEDITOUR_MAX_REQUEST_BYTES`（默认 10 MiB），`detail="Request body too large"`；`POST /staff/uploads`：文件大于 `MEDITOUR_UPLOAD_MAX_BYTES`（默认 5 MiB），`detail` 为限制字节数 |
| 415 | 上传文件类型不受支持 | `POST /staff/uploads`：声明类型不是 JPEG/PNG/WebP，或文件头与声明类型不符（防止把非图片改成 `.png` 后缀上传） |
| 422 | 请求体或查询参数校验失败 | 字段缺失/类型错误、邮箱格式、密码长度（6–72）、`notes` 超过 2000 字、预约时间不在未来、`contact_phone` 非 7–15 位、行程日期/目的地/每日编号不合法；分页 `page < 1`、`page_size < 1` 或 `> 100`；员工列表 `status` 不在 `pending/confirmed/completed/cancelled`；员工改状态的目标值不是 `confirmed/completed/cancelled`；审计查询 `created_from > created_to`；员工创建/更新套餐时 `hospital_id` 指向不存在的医院、`price ≤ 0`、`duration_days < 1`；目的地 slug 不符合 `^[a-z0-9][a-z0-9-]*$`；上传空文件；`lang` 不在 `zh/en/de/fr`（`detail` 为字符串 `Unsupported lang; supported values: ...`，其余为字段错误数组） |
| 429 | 触发登录限流 | 仅 `POST /auth/login`：同一 IP + 邮箱 300 秒内失败 5 次，响应带 `Retry-After` 秒数；成功登录会清零计数 |
| 503 | 依赖服务不可用 | 仅 `GET /health`：数据库 `SELECT 1` 失败，返回 `{"status":"error","database":"unavailable"}`（不是 `detail` 结构） |
| 500 | 未预期的服务端异常 | 任意端点：由异常兜底中间件统一返回 `{"detail": "Internal server error"}`；堆栈只写服务端日志，不返回响应体 |

成功状态码：`200` 常规读取/更新/登录/刷新/登出/改密/重置密码/验证邮箱/查询或吊销会话/导出；`201` 注册、创建订单、创建行程、创建套餐/医院/目的地、上传图片；`204` 删除行程、删除套餐/医院/目的地（无响应体）。

## 数据库迁移

迁移由 Alembic 管理，配置见 [alembic.ini](alembic.ini)，脚本在 `migrations/`。

```bash
# 升级到最新版本（服务启动时也会自动执行）
python -m alembic upgrade head

# 检查模型与迁移是否一致
python -m alembic check
```

旧的本地 `meditour.db` 若已存在表但没有 `alembic_version`，服务会拒绝启动并提示。确认库结构与当前模型一致后，先备份再标记基线：

```bash
python -m alembic stamp head
```

`stamp` 只写入版本号，不改动表和数据；之后 `alembic upgrade head` 即可正常执行。
测试环境（`MEDITOUR_TESTING=1`）仍使用 `create_all`，不依赖迁移执行顺序。

迁移 `b3c9d1e5f7a2`（部分唯一索引 `uq_bookings_pending_slot`）升级前会先清理历史竞态
留下的重复 pending 行：同一 `(user_id, package_id, appointment_date)` 保留 id 最小的一条，
其余改为 `cancelled`（不删除订单，也不改动金额），然后创建索引。升级输出会打印处理条数；
本机 `meditour.db` 上实测清理了 2 条，升级后重复组为 0。

迁移 `d1a4b7c9e2f3` 新增 `users.email_verified_at`、`email_verification_tokens` 与
`auth_sessions`，只创建结构和可空列，不改动已有行，可在现有数据上直接升级。

迁移 `a7c2e9f4b6d1` 新增订单的 `confirmed_at` / `cancelled_at` / `completed_at`
（可空），审计表的 `details`（JSON，可空），并把 `audit_logs.entity_id` 从整数放宽为
`String(64)` 以支持目的地 slug。已有订单的三列保持 NULL（无法回溯真实时刻，巡检脚本
会列在“需人工判断”），已有审计行的整数值按文本保留。该迁移也可在现有数据上直接升级。
当前 head 即 `a7c2e9f4b6d1`。

## PostgreSQL 切换脚手架（未验证）

> **重要：当前开发机没有 Docker，`docker-compose.yml` 从未构建或运行过，项目也从未在
> PostgreSQL 上执行过迁移或接口测试。** 本节的 compose 文件与清单只是“切换路径”的
> 草稿，不能据此认为项目“已支持 PostgreSQL”。启用前请按下面的检查清单逐项验证，
> 并把验证结果补进本节。

文件：[docker-compose.yml](docker-compose.yml)，包含 `db`（postgres:16-alpine，带
`pg_isready` 健康检查）与 `api`（由本目录 Dockerfile 构建）。`api` 通过
`depends_on: db: condition: service_healthy` 等待数据库真正可连接后再启动，并在启动
命令里先执行 `alembic upgrade head` 再拉起 uvicorn。

```bash
# 在 backend 目录；先设置一个长随机密钥
docker compose up --build
docker compose down          # 保留 pgdata 卷
docker compose down -v       # 连数据一起删
```

### 连接串与迁移顺序

- 连接串：`postgresql+psycopg://<user>:<password>@<host>:5432/<db>`
  （驱动 `psycopg` 已加入 `requirements.txt`；不要用默认的 psycopg2 方言）。
- 迁移顺序：数据库就绪 → `alembic upgrade head` → `alembic check`（应无 diff）→
  启动应用（应用启动时还会再校验一次 schema 版本并执行种子）。
- 不要用 `Base.metadata.create_all()` 初始化 PostgreSQL；测试环境才走 `create_all`。
- 如果从 SQLite 导数据，不要直接 `COPY` 出带主键的行：先导入业务数据，再用
  `setval(pg_get_serial_sequence(...))` 或重新插入的方式修正自增序列，否则后续插入会撞主键。

### SQLite 与 PostgreSQL 的差异点（切换前必须逐条确认）

1. **金额**：`bookings.total_price` 与 `medical_packages.price` 目前是 `Float`。
   SQLite 存 REAL、PostgreSQL 存 `double precision`，两者都有二进制浮点误差。
   切库前建议改成 `Numeric(10, 2)` 并加迁移与取整策略；当前代码尚未改。
2. **时间精度与类型**：应用统一写入 naive UTC（`app.models.utcnow`）。SQLite 以文本
   保存，PostgreSQL 默认是 `timestamp without time zone`；比较逻辑依赖 naive 值，
   切库后要复测预约时间校验、排序与 `created_at` 序列化（`Z` 后缀）。
3. **布尔默认值**：迁移里 `is_active` 使用 `server_default="1"`。PostgreSQL 的布尔
   字面量建议写 `'true'`；这一点必须在 PG 上实测，失败时改迁移而不是改应用。
4. **JSON 列**：`sa.JSON` 在 SQLite 是文本、在 PostgreSQL 是 `json`（不是 `jsonb`）。
   当前 `destination_ids`、`experiences`、`search_terms` 只在 Python 侧读写，没有做
   JSON 字段查询；若以后要按 JSON 内部字段过滤，需要改用 `jsonb` + GIN 索引。
5. **自增主键**：SQLite 的 `INTEGER PRIMARY KEY` 与 PostgreSQL 的序列语义不同；
   迁移后确认每张表的 sequence 起点与现有最大 id 一致。
6. **并发与连接池**：SQLite 同一时刻只有一个写者；PostgreSQL 真正并发。下单唯一性由
   部分唯一索引 `uq_bookings_pending_slot`（`WHERE status = 'pending'`）保证，SQLite 与
   PostgreSQL 都支持条件索引；切库后必须重跑并发探测确认索引生效（见“并发探测”）。
7. **DDL 事务**：PostgreSQL 的 DDL 可回滚，SQLite（batch mode）行为不同；迁移失败时
   的恢复步骤要按 PG 重新演练。
8. **标识符大小写**：现有表名/列名全部小写，SQLAlchemy 不会加引号；新增迁移时保持
   小写蛇形命名，避免 `"Users"` 与 `users` 两种对象并存。

### 在 PostgreSQL 上需要重新验证的检查清单

- [ ] `alembic upgrade head` 从空库一次成功；`alembic check` 无 diff
- [ ] 种子数据（医院、套餐、目的地）正常写入，无布尔/JSON 类型错误
- [ ] `pytest` 全绿（测试库需改为 PostgreSQL，`create_all` 路径也要验证一次）
- [ ] `scripts/verify_api.py` 全部断言通过（含员工接口）
- [ ] 注册/登录/限流/刷新/登出/注销闭环
- [ ] 重置密码邮件：收件人语言、`.eml` 或 SMTP 实际送达
- [ ] 下单并发：同用户同套餐同时间只产生一个 `pending`，其余 409，无 500
- [ ] 员工订单列表分页与时间排序、审计写入
- [ ] 订单状态机：终态不可流转、已确认订单用户不可取消、时间戳正确落地
- [ ] 审计查询接口按操作类型与时间范围过滤正常
- [ ] `scripts/check_data_consistency.py` 无“确定异常”（历史数据单独确认）
- [ ] 套餐下架后公开列表隐藏、下单 404、改价不影响历史订单金额
- [ ] 内容 CRUD 与删除保护（409）、上传 URL 在容器内可访问
- [ ] 数据导出与备份策略（PG 用 `pg_dump`，本仓库 SQLite 备份脚本不适用）

## 备份与恢复

只支持本地 SQLite（当前部署形态）。PostgreSQL 请使用 `pg_dump` / `pg_restore`
或云厂商的时间点恢复，本脚本遇到非 SQLite 连接串会直接报错，不会假装成功。

```bash
cd backend
# 备份：默认读 DATABASE_URL，写到 var/backups/meditour-<时间戳>.db
python scripts/backup_db.py
python scripts/backup_db.py --output-dir D:\backups --database-url sqlite:///D:/data/meditour.db

# 恢复：先停掉后端进程；目标非空时必须 --force
python scripts/restore_db.py --backup var/backups/meditour-20261108-095413.db --force
```

- 备份使用 SQLite 在线备份 API，先写临时文件，校验行数与订单指标一致后再原子替换，
  不会复制出写入中途的半截文件。
- 恢复的安全阀：目标库已有业务表且未加 `--force` 时拒绝执行；加 `--force` 时也会
  先保留 `<库名>.pre-restore-<时间戳>.db.bak`，再覆盖。
- 恢复完成后会重新统计表行数、订单状态分布与订单金额合计，与备份不一致则以非零
  状态退出。恢复后请用当前代码再执行一次 `python -m alembic upgrade head`。

本机真实演练（演练库 `backend/var/drill/`，含 1 个订单，已从仓库忽略）：

```text
> python scripts\backup_db.py --output-dir var\drill\backups
备份完成
  源库: I:\meditour_app\backend\var\drill\meditour-drill.db
  备份: I:\meditour_app\backend\var\drill\backups\meditour-20261108-095413.db
  大小: 126976 bytes
  sha256: 2b645a86326fe5e228df8fe5c986c3af7279f024910379e38a7a87aff9f0a6c5
  表行数: {'alembic_version': 1, 'audit_logs': 0, 'bookings': 1, 'content_translations': 3, 'destinations': 4, 'hospitals': 2, 'itineraries': 0, 'itinerary_days': 0, 'medical_packages': 2, 'password_reset_tokens': 0, 'token_revocations': 0, 'users': 1}
  订单状态: {'pending': 1}
  订单总金额: 15000.0

> Remove-Item var\drill\meditour-drill.db
> python scripts\restore_db.py --backup var\drill\backups\meditour-20261108-095413.db
恢复完成
  备份: I:\meditour_app\backend\var\drill\backups\meditour-20261108-095413.db
  目标: I:\meditour_app\backend\var\drill\meditour-drill.db
  大小: 126976 bytes
  表行数: {'alembic_version': 1, 'audit_logs': 0, 'bookings': 1, 'content_translations': 3, 'destinations': 4, 'hospitals': 2, 'itineraries': 0, 'itinerary_days': 0, 'medical_packages': 2, 'password_reset_tokens': 0, 'token_revocations': 0, 'users': 1}
  订单状态: {'pending': 1}
  订单总金额: 15000.0
  校验: 与备份一致

# 再执行一次（目标已有数据、未加 --force）
恢复失败：Target database is not empty (12 tables: alembic_version, audit_logs,
bookings, content_translations, destinations, hospitals, itineraries,
itinerary_days, medical_packages, password_reset_tokens, token_revocations,
users). Stop the backend before restoring, then re-run with --force to overwrite it.

# 加 --force 后成功，并留下覆盖前副本
覆盖前副本: I:\meditour_app\backend\var\drill\meditour-drill.pre-restore-20261108-095425.db.bak
校验: 与备份一致
```

恢复后直接查库确认关键业务数据：

```text
[('MT-DRILL-0001', 'Drill Patient', 15000.0, 'pending', 'drill note')]
[('package', 'de', 'name', 'Kniegelenkersatz (Knie-TEP)')]
```

局限：备份文件是**单机本地文件**。多实例部署时各实例的 SQLite 互不相通，
必须改为共享数据库（如 PostgreSQL）并使用数据库自带的备份/时间点恢复；
把备份文件放到对象存储只是异地保存，不能替代数据库级备份。

## 数据保留与清理

`scripts/cleanup_data.py` 按保留期清理可再生的数据。**默认 dry-run**，只打印将删除的内容；确认后加 `--no-dry-run` 才真正写入。

```bash
cd backend
# 预演（推荐先跑）：列出每类将删除的行数/文件数、示例 id 与释放空间
python scripts/cleanup_data.py
# 真正执行；非交互环境（cron / CI）需显式加 --yes
python scripts/cleanup_data.py --no-dry-run --yes
```

| 数据 | 保留期变量 | 默认 | 清理规则 |
| --- | --- | --- | --- |
| `password_reset_tokens` / `email_verification_tokens` | `MEDITOUR_TOKEN_RETENTION_DAYS` | 30 天 | 过期或已使用超过保留期 |
| `token_revocations` | 同上 | 30 天 | `expires_at` 超过保留期（此后令牌本身已过期，无需再记入黑名单） |
| `auth_sessions` | 同上 | 30 天 | 过期或已吊销超过保留期 |
| `audit_logs` | `MEDITOUR_AUDIT_LOG_RETENTION_DAYS` | 365 天 | 按 `created_at` |
| 软删除账号的关联数据 | `MEDITOUR_SOFT_DELETED_ACCOUNT_RETENTION_DAYS` | 30 天 | 只删行程/每日安排、会话、重置与验证令牌 |
| `mail_preview/*.eml` 与 outbox 索引行 | `MEDITOUR_MAIL_PREVIEW_RETENTION_DAYS` | 14 天 | `.eml` 按文件 mtime；outbox 按行首 ISO 时间戳裁剪（索引行含收件人与令牌） |
| 上传目录临时文件 | `MEDITOUR_UPLOAD_TEMP_RETENTION_DAYS` | 1 天 | 仅 `.tmp` / `.part` / `.upload`，最终图片不删 |

**软删除账号为什么不物理删除：**

- `bookings.user_id` 外键引用用户行，物理删除会留下悬空引用或迫使级联删除订单；
- 订单是交易/财务记录，需要保留用于对账与审计，不能因为用户注销就消失；
- 注销接口已经做了匿名化（邮箱/姓名/电话/密码哈希被清空或替换），保留用户空壳行不构成隐私风险。

因此清理任务对到期账号**只删除可再生的关联数据**，用户行与订单保留；脚本输出会注明「保留用户行与 N 条订单」。如果未来产品要求彻底删除账号，需要先决定订单的法定保留策略，再另做迁移，而不是在清理脚本里悄悄删。

清理任务不在应用启动时自动执行，需要由运维按需手动运行或接入 cron。脚本只读取 `MEDITOUR_*` 配置与 `DATABASE_URL`，不访问网络。

## 数据一致性巡检

`scripts/check_data_consistency.py` 是**只读**脚本，只执行 SELECT，不修改数据：

```bash
cd backend
python scripts/check_data_consistency.py
python scripts/check_data_consistency.py --max-examples 10
python scripts/check_data_consistency.py --database-url sqlite:///./meditour.db
```

输出分两类，避免把“设计如此”的数据当成 bug：

**确定异常**（违反数据模型不变量，退出码 1）：

| 检查 | 说明 |
| --- | --- |
| 订单引用不存在的套餐 | `bookings.package_id` 指向已不存在的套餐 |
| 行程 / 行程每日安排引用不存在的目的地 | `destination_ids` 中的 slug 已不在 `destinations` 表 |
| 同一时段多条 pending 订单 | 同一 `(user_id, package_id, appointment_date)` 多于 1 条 pending |
| 软删除账号仍有有效会话 | 用户 `deleted_at` 非空，但会话未吊销且未过期 |
| 状态与时间戳互相矛盾 | `pending` 带任一状态时间戳；`confirmed` 带取消/完成时间；`completed` 带取消时间；`cancelled` 带完成时间 |

**需人工判断**（可能是正常业务结果，退出码不受影响）：

| 检查 | 为什么不自动判错 |
| --- | --- |
| 状态缺少对应时间戳 | 迁移前的历史订单无法回溯真实时刻 |
| 订单金额 ≠ 套餐当前价格 | 价格快照是设计，调价后历史订单不跟着变 |
| 预约时间已过但仍是 pending | 可能是用户爽约或员工未及时处理，需要运营确认 |
| 套餐已下架但仍有 pending 订单 | 下单后下架属正常，是否需要通知改约由业务决定 |

未发现确定异常时退出码为 0，便于接入定时任务；脚本不自动修复任何数据。

## 联调演示数据

默认种子只有 2 家医院、2 个套餐、4 个目的地，列表/筛选/分页看不出问题。设置
`MEDITOUR_SEED_DEMO_DATA=1` 后，启动时会**增量**写入：

| 类别 | 原有 | 新增 | 合计 |
| --- | --- | --- | --- |
| 医院 | 2 | 6 | 8 |
| 套餐 | 2 | 20 | 22 |
| 目的地 | 4 | 10 | 14 |
| de/fr 译文 | 3 条（仅德语） | 40 条（套餐 32 + 医院 8） | 43 |

- 套餐覆盖 12 个分类（骨科、口腔、心血管、肿瘤、眼科、康养、生殖、整形、神经、
  消化、皮肤、儿科），价格 300–45000，疗程 3–30 天，便于验证价格区间筛选与排序。
- 目的地合计 14 个，超过前端一页的展示量，可验证「加载更多」与搜索。
- 已存在同名（`name_en`）或同 id 的条目会跳过；重复启动不会产生重复行。
- 关闭开关**只停止写入，不会删除**已经写入的数据。生产环境不要开启。
- 目的地接口当前只返回 `name` / `name_en`，没有 de/fr 字段（`destinations.py`
  不在本批改动范围内），所以演示译文集中在套餐与医院；这是接口现状，不是数据缺失。

```bash
# 本地：写入演示目录后启动
$env:MEDITOUR_SEED_DEMO_DATA="1"
uvicorn app.main:app --reload
```

`tests/test_demo_seed.py` 在独立的内存库里验证：默认关闭时数量不变、开启后数量正确、
重复执行幂等、关闭开关不删除数据。

## 测试

```bash
cd backend
python -m pytest -q
```

测试使用独立的 `test_meditour.db`，每次会话开始时重建，不依赖本地开发库，也不访问外部网络。
当前覆盖（124 项）：预约字段与校验分支、重复提交、并发重复下单只产生一个 pending、并发取消只成功一次、取消流转与越权、并发登录只放行阈值内的失败、登录限流、令牌刷新/轮换/登出吊销、旧令牌兼容、找回密码（一次性/过期/防枚举）、修改密码后令牌失效、注销账号的匿名化与级联（含会话吊销）、多语言回退、数据导出隔离、员工角色授予与订单状态流转/越权、员工列表字段裁剪、详情访问审计、分页边界与索引存在性、员工内容 CRUD 与删除保护、套餐下架后公开列表隐藏且不可预约、改价不影响历史订单快照、图片上传的类型/大小/随机文件名校验、翻译 CSV 导入的幂等与错误行号、安全中间件（请求体上限、安全响应头与 HSTS 条件、500 兜底形状）、重置邮件多语言模板与 `.eml` 生成、邮件日志不含令牌/链接、日志脱敏与 request id、邮箱验证（注册发信、多语言、不阻断登录、一次性/过期/重发作废旧令牌、防枚举响应）、强制验证开关（未验证下单 403、确认后 201）、会话列表不含令牌、单设备吊销即时失效、越权吊销 404、退出所有设备、/metrics 输出/关闭开关/来源白名单、数据保留清理（dry-run 不写入、只删过期数据、软删除账号保留用户行与订单、邮件与上传临时文件清理）、前后端契约核对（11 个端点的字段名/类型/可空性）、联调演示种子（默认关闭、数量与分类/价格覆盖、重复执行幂等）、列表接口查询次数为常数（订单/行程/套餐/医院/目的地/员工订单）、连接池容量与配置一致、SQLite WAL/busy_timeout/synchronous 实际生效、订单状态机终态锁死与时间戳（用户不能取消已确认、员工可取消、completed 不能退回 pending）、审计覆盖（取消/流转/改价/删除/导出）与查询过滤（操作类型/时间范围/权限）。

## 接口验证脚本

`scripts/verify_api.py` 只用 Python 标准库，覆盖注册、登录（含限流）、鉴权、健康检查、套餐、医院、订单创建/校验/列表/取消、令牌刷新与登出、CORS、request id、错误体形状、账号闭环、多语言回退、数据导出、分页边界与员工订单操作（默认 108 项断言；提供 `--staff-email/--staff-password` 时额外验证员工接口，共 126 项）。本批新增的员工内容运营与图片上传端点由 pytest 覆盖，尚未加入该脚本。

登出会吊销整个设备会话，因此脚本在验证「登出后 access/refresh 被拒绝」之后会重新登录，
后续段落使用新会话的令牌；这不是放宽校验，而是避免复用已登出的令牌。

```bash
# 先启动后端，再执行
python scripts/verify_api.py --base-url http://127.0.0.1:8000/api/v1

# 开发环境 file 邮件后端：验证忘记密码需要从 outbox 读取令牌（默认路径）
python scripts/verify_api.py --mail-outbox var/mail_outbox.log

# 员工接口验证：账号需先由 manage_staff.py 授予 staff
python scripts/verify_api.py --staff-email staff@example.com --staff-password Staff123456

# 验证后清理本次测试账号与订单（仅针对本机默认 SQLite）
python scripts/verify_api.py --cleanup
```

账号闭环部分依赖开发环境 `MEDITOUR_MAIL_BACKEND=file` 写出的 outbox 文件；使用 `smtp` 后端时该段会明确失败并提示，不会伪造通过。

全部通过时退出码为 0，有失败为 1，连接失败为 2。Android 模拟器访问宿主机可用 `http://10.0.2.2:8000/api/v1`。

## 端到端冒烟脚本

`scripts/smoke_journey.py` 只用标准库，把一条完整用户旅程串起来执行，适合上线验收与 CI：

注册 → 从 outbox 读取验证邮件 → 确认邮箱 → 登录 → 读取个人资料 → 浏览套餐 → 浏览医院 →
创建预约 → 查看订单 → 取消预约 → 导出数据 → 修改密码 → 用新密码登录 → 注销账号 →
确认注销后登录被拒（共 15 步）。

每一步都断言状态码与关键字段（如新账号 `email_verified=false`、确认后登录为 `true`、
预约 `status=pending`、取消后 `cancelled`、导出包含当前订单、旧密码与新密码的登录结果等）。
失败时会打印**断在第几步、步骤名、实际值**，并返回非零退出码。

```bash
# 先启动后端（file 邮件后端，开发默认）
python scripts/smoke_journey.py
python scripts/smoke_journey.py --base-url http://127.0.0.1:8000/api/v1 \
  --mail-outbox var/mail_outbox.log
```

- 退出码：`0` 全部通过、`1` 业务断言失败、`2` 无法连接后端。最后一行输出 `通过 15/15，耗时 X.XXs`。
- 需要后端使用 `file` 邮件后端才能从 outbox 读取验证令牌；`smtp` 后端会在第 2 步明确失败，不会伪造通过。
- 每次运行使用随机账号（`smoke-<时间戳>-<随机串>@meditour.com`），最后一步注销，可重复执行。
- 本机实测：15/15 通过，耗时 2.50s。

## 前后端契约核对

`tests/test_contract.py` 逐个调用前端实际消费的端点，把响应里的字段名、JSON 类型、
可空性与前端模型逐项对照：

| 端点 | 对照的前端模型 |
| --- | --- |
| `POST /auth/register`、`GET /auth/me` | `UserProfile`（`lib/data/models/user_profile.dart`） |
| `POST /auth/login` | `AuthTokens`（`api_service.dart`，`access_token` 必须是 String） |
| `GET /medical/packages` | `MedicalService.fromPackage`（id/price/duration_days 等） |
| `GET /medical/hospitals` | `HospitalInfo`（`id` 必须是 int） |
| `GET /destinations` | `Destination`（`id` 必须是 String） |
| `POST /bookings/`、`GET /bookings/`、取消 | `BookingOrder` / `BookingResult`（`id` 必须是 int、`total_price` 必须是数值） |
| `GET /auth/export` | 导出页的账户/订单/行程字段 |

只校验前端**确实读取**的字段；后端额外字段允许存在。可空字段（如 `full_name`、`phone`）
允许 `null`。运行 `pytest tests/test_contract.py -s` 会打印逐端点字段数与差异清单；
有任何差异测试即失败，并列出「字段路径、期望类型、实际值」。

当前结果：**0 处差异**。前端未消费的 `/auth/sessions`、`/metrics`、`/staff/*`
不在核对范围内（脚本会打印提示）。如果未来前端新增解析字段，应先把需求补进
`test_contract.py` 的 SPEC，再改后端。

## 并发探测

`scripts/concurrency_probe.py` 只用标准库（`urllib` + `threading.Barrier`），对关键路径
各打一轮并发，**只看状态码分布与错误率，不是性能基准**：

- `login-rate-limit`：同一邮箱连续错误密码，观察 401 与 429；
- `booking-create`：同一用户、同一套餐、同一预约时间并发下单，应只有 1 个 201；
- `booking-cancel`：并发取消同一个 pending 订单，应只有 1 个 200、其余 409；
- `bookings-list`：并发读取订单列表，观察锁竞争/连接问题导致的 5xx；
- `refresh-token`：同一个 refresh token 并发刷新，应只有 1 个 200、其余 401；
- `upload`（需员工账号）：并发上传同一张图片，观察是否 5xx、返回路径是否唯一；
- `staff-price-update`（需员工账号）：并发修改同一套餐价格，检查最终值是否可预期，
  结束后恢复原价。

```bash
# 先启动后端；脚本会注册临时用户，结束时注销该账号（其 pending 订单会被取消）
python scripts/concurrency_probe.py --threads 12

# 上传与改价场景需要已有 staff 账号（可用 scripts/manage_staff.py 创建）
python scripts/concurrency_probe.py --threads 12 \
  --staff-email probe-staff@meditour.com --staff-password ProbeStaff123456
```

默认单请求超时为 **45 秒**（`DEFAULT_TIMEOUT`），必须大于服务端连接池等待时间
（默认 `pool_timeout=10s`）。如果客户端先超时，会把服务端的 500 截断成 `network` 错误，
看起来像“没有 5xx”，实际掩盖了问题；需要复现连接池耗尽时不要调小 `--timeout`。

本机（SQLite，12 线程，修复后）的真实输出：

```text
[login-rate-limit] requests=12 | 401: 5, 429: 7 | errors(5xx/network)=0 (0%) | p50=39ms p95=44ms max=44ms
[booking-create] requests=12 | 201: 1, 409: 11 | errors(5xx/network)=0 (0%) | p50=100ms p95=122ms max=122ms
[booking-cancel] requests=12 | 200: 1, 409: 11 | errors(5xx/network)=0 (0%) | p50=96ms p95=137ms max=137ms
[bookings-list] requests=12 | 200: 12 | errors(5xx/network)=0 (0%) | p50=70ms p95=77ms max=77ms
[refresh-token] requests=12 | 200: 1, 401: 11 | errors(5xx/network)=0 (0%) | p50=90ms p95=171ms max=171ms
[upload] requests=12 | 201: 12 | errors(5xx/network)=0 (0%) | p50=58ms p95=74ms max=74ms
  upload success=12 unique_paths=12
[staff-price-update] requests=12 | 200: 12 | errors(5xx/network)=0 (0%) | p50=176ms p95=279ms max=279ms
  original=15000.0 final=15008.0 in_submitted=True
  restore original price -> 200
cleanup: DELETE /auth/account -> 200
```

结果解读：

- **重复预约已修复**：`booking-create` 从修复前的 `201: 3, 409: 9` 变为
  `201: 1, 409: 11`。应用层预检查之外由部分唯一索引兜底，`IntegrityError` 统一转成
  既有形状的 409。
- **并发取消已修复**：`booking-cancel` 从 `200: 7, 409: 5` 变为 `200: 1, 409: 11`。
  取消改为条件更新（`UPDATE ... WHERE id=? AND user_id=? AND status='pending'`），
  `rowcount=0` 时回查区分 404（不存在/非本人）与 409（状态已变），错误体形状不变。
- **登录限流已修复**：从 `401: 7, 429: 5` 变为 `401: 5, 429: 7`。检查阈值与预占名额
  在同一把锁内完成，并发下只有 5 个请求进入密码校验，其余直接 429。
- `refresh-token` 只有 1 个 200，其余 401，说明 refresh 轮换在并发下仍只成功一次。
- `upload` 12 个请求全部 201，12 个返回路径互不重复。
- `staff-price-update` 12 个 PATCH 全部 200，最终价格是提交值之一（最后提交者胜出），
  恢复原价成功；没有 5xx 或半写状态。
- 该脚本不测吞吐量、不构造慢查询；SQLite 的写并发受全局写锁限制，结果不能直接外推到
  PostgreSQL。限流计数仍是进程内状态，多 worker 部署前需要换成共享存储。

### 100 并发实测（修复连接池之后）

```bash
# 默认客户端超时 45s，足以等到服务端的真实响应，避免客户端先超时掩盖 500。
python scripts/concurrency_probe.py --threads 100 \
  --staff-email probe-staff@meditour.com --staff-password ProbeStaff123456
```

本机（SQLite，单 uvicorn worker，连接池 `pool_size=20 + max_overflow=20`，
WAL + `busy_timeout=15000`）：

```text
[login-rate-limit] requests=100 | 401: 5, 429: 95 | errors(5xx/network)=0 (0%) | p50=201ms p95=297ms max=307ms
[booking-create] requests=100 | 201: 1, 409: 99 | errors(5xx/network)=0 (0%) | p50=365ms p95=552ms max=560ms
[booking-cancel] requests=100 | 200: 1, 409: 99 | errors(5xx/network)=0 (0%) | p50=389ms p95=596ms max=609ms
[bookings-list] requests=100 | 200: 100 | errors(5xx/network)=0 (0%) | p50=398ms p95=577ms max=581ms
[refresh-token] requests=100 | 200: 1, 401: 99 | errors(5xx/network)=0 (0%) | p50=199ms p95=360ms max=366ms
[upload] requests=100 | 201: 100 | errors(5xx/network)=0 (0%) | p50=437ms p95=708ms max=720ms
  upload success=100 unique_paths=100
[staff-price-update] requests=100 | 200: 100 | errors(5xx/network)=0 (0%) | p50=428ms p95=644ms max=653ms
  original=15061.0 final=15134.0 in_submitted=True
  restore original price -> 200
```

修复前后对比（同一台机器、同一脚本、同一 100 并发）：

| 场景 | 修复前（池 5 + 10） | 修复后（池 20 + 20，WAL） |
| --- | --- | --- |
| `staff-price-update` | `200:64, 500:33, network:3`，错误率 36%，p50 30502ms / p95 30753ms | `200:100`，错误率 0%，p50 428ms / p95 644ms / max 653ms |
| `booking-create` | `201:1, 409:99`，p50 323ms / p95 1867ms | `201:1, 409:99`，p50 365ms / p95 552ms / max 560ms |
| `bookings-list` | `200:100`，p50 156ms / p95 3081ms | `200:100`，p50 398ms / p95 577ms / max 581ms |
| `refresh-token` | `200:1, 401:99`，p50 516ms / p95 2954ms | `200:1, 401:99`，p50 199ms / p95 360ms / max 366ms |
| `upload` | `201:100`，p50 1299ms / p95 10959ms | `201:100`（路径唯一 100），p50 437ms / p95 708ms / max 720ms |
| `login-rate-limit` | `401:5, 429:95`，p50 56ms / p95 1490ms | `401:5, 429:95`，p50 201ms / p95 297ms / max 307ms |

- 修复前的 33 个 500 + 3 个客户端超时，服务端日志确认是
  `QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00`：
  池里最多 15 条连接，而 uvicorn 同步线程池可同时跑 40 个请求，排队超过 30 秒必然失败。
  修复后 100 并发**没有任何 5xx 或网络错误**，业务语义也没变（下单仍只有 1 个 201、
  取消仍只有 1 个 200、刷新令牌仍只有 1 个 200、改价最终值是提交值之一）。
- 修复后延迟的 p50 比修复前高（如列表 156ms → 398ms），是因为修复前大量请求直接失败或
  立即返回，不构成有效对比；同口径应看“成功请求”的 p95：列表 3081ms → 577ms，
  上传 10959ms → 708ms。
- 这次修复不是“SQLite 变快了”，而是**不再把连接池耗尽误当成业务失败**；SQLite 依旧是
  单写者，并发写只是排队。

## 连接池与单机容量

### 默认值怎么来的

配置项见 `app/config.py`，实现见 `app/database.py`：

| 配置 | 默认值 | 作用 |
| --- | --- | --- |
| `MEDITOUR_DB_POOL_SIZE` | `20` | 常驻连接数 |
| `MEDITOUR_DB_MAX_OVERFLOW` | `20` | 峰值临时连接数 |
| `MEDITOUR_DB_POOL_TIMEOUT` | `10` | 排队等连接的上限（秒） |
| `MEDITOUR_DB_SQLITE_WAL` | `true` | 文件型 SQLite 开启 WAL |
| `MEDITOUR_DB_SQLITE_BUSY_TIMEOUT_MS` | `15000` | SQLite 写锁等待上限（毫秒） |

推导依据（不是拍脑袋）：

1. uvicorn 单进程默认用 anyio 的同步线程池执行同步端点，默认 **40 个线程**；
2. 每个在途请求最多占用 **1 条连接**（`get_db` 在请求结束时归还）；
3. 因此池容量必须满足 `pool_size + max_overflow >= 40`，否则 40 个线程里必然有线程
   在池里排队，排队超过 `pool_timeout` 就抛 `QueuePool limit ... timed out`——这正是
   修复前“40 个 worker 抢 15 条连接”的成因；
4. 默认取 `20 + 20 = 40`：常驻 20 条覆盖稳态并发，峰值再溢出 20 条；`pool_timeout=10s`
   小于 SQLite 的 `busy_timeout=15s`，保证先暴露连接池问题而不是让客户端等 30 秒。

部署时按 worker 数计算：

```text
每进程池容量 = MEDITOUR_DB_POOL_SIZE + MEDITOUR_DB_MAX_OVERFLOW
进程所需连接数 = uvicorn --workers 数 × 每进程池容量
数据库 max_connections >= 进程所需连接数 + 运维余量
```

例如 `--workers 4`、默认池：`4 × 40 = 160`，PostgreSQL 的 `max_connections` 至少留到
`200`。每个 worker 进程有**独立**的连接池，不会共享；`pool_timeout` 保持小于
`busy_timeout`。如果同步线程数被显式调大（anyio 的线程限制），池容量要同步跟上。

### SQLite 的改善与上限

- `journal_mode=WAL`：读操作不再被写事务阻塞，读与写可以并行；这是本次列表/上传
  p95 大幅下降的主要原因之一。
- `busy_timeout=15000`：写冲突时等待最多 15 秒再报错，把“立刻 `database is locked`”
  变成“排队”。配合驱动的 `timeout` 参数一起设置。
- `synchronous=NORMAL`：WAL 下少一次 fsync，崩溃最多丢失最后一个事务。

**上限没有变**：SQLite 任何时刻只允许一个写者，WAL 只是让读不被写阻塞、让写冲突排队。
上面的数字说明的是“100 并发下不报错、延迟可接受”，**不是**“SQLite 支持高写并发”。
需要真正的写并发时应切换 PostgreSQL（见「PostgreSQL 切换脚手架（未验证）」）。

### 当前单机容量（实测）

同一台机器、单 uvicorn worker、文件型 SQLite、上述默认配置，用同一脚本逐级加压：

| 并发 | 结果 | 下单 p95 | 列表 p95 | 改价 p95 | 上传 p95 | 登录 p95 |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | 0 错误 / 0 5xx | 552ms | 577ms | 644ms | 708ms | 297ms |
| 150 | 0 错误 / 0 5xx | 806ms | 749ms | 1049ms | 1202ms | — |
| 300 | 0 错误 / 0 5xx | 1583ms | 1457ms | 2024ms | 2369ms | 835ms |

结论（给上线决策用）：

- 这台机器、这个配置下，**100–300 并发都不再出现 5xx**；劣化表现为延迟线性上升，
  不是报错。写路径（改价/下单）比读路径更早劣化，因为 SQLite 单写者要串行化。
- 经验阈值：**~100 并发**内写路径 p95 < 0.7s，可视为舒适区；**~150 并发**写路径
  p95 约 1s，属于可接受但已开始排队；**300 并发**写路径 p95 约 2s，延迟明显，
  不适合作为常态容量。
- 这是**单进程 + SQLite** 的数字，不能外推到多 worker：多 worker 下 SQLite 的写锁
  竞争会更严重，而 PostgreSQL 会好很多。上线前应在目标数据库上重跑本脚本。
- 未测量项：长连接/流式响应、超大图片、慢查询、磁盘 IO 抖动；这些都会改变上述阈值。

## 健康检查

```bash
curl http://127.0.0.1:8000/api/v1/health
# {"status":"ok","database":"ok"}
```

该端点会执行一次 `SELECT 1`；数据库不可用时返回 503，便于容器编排和本地排障。

## Docker

```bash
cd backend
docker build -t meditour-backend .
docker run --rm -p 8000:8000 \
  -e MEDITOUR_SECRET_KEY=<long-random-string> \
  -v meditour-data:/data \
  meditour-backend
```

镜像以非 root 用户运行，SQLite 数据默认落在 `/data/meditour.db`，请挂载卷持久化。容器内置 `HEALTHCHECK`，请求 `/api/v1/health`。

PostgreSQL + API 的 compose 脚手架（**未构建、未运行，不能视为已验证支持**）见上一节
「PostgreSQL 切换脚手架（未验证）」。
