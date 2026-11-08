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

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `MEDITOUR_SECRET_KEY`（或 `SECRET_KEY`） | 是 | 无 | JWT 签名密钥；缺失时进程直接启动失败，不会回退到默认值 |
| `DATABASE_URL` | 否 | `sqlite:///backend/meditour.db` | SQLAlchemy 连接串 |
| `MEDITOUR_CURRENCY` | 否 | `EUR` | 种子套餐与订单金额使用的币种 |
| `MEDITOUR_CORS_ORIGINS` | 否 | `http://localhost:8123,http://127.0.0.1:8123` | 允许的浏览器来源，逗号分隔 |
| `MEDITOUR_SEED_DEMO_USER` | 否 | 关闭 | 设为 `1` 时创建演示账号 `demo@meditour.com / Demo123456`；生产环境不要开启，关闭开关不会删除已有账号 |
| `MEDITOUR_STAFF_EMAILS` | 否 | 空 | 员工邮箱白名单，逗号分隔；命中名单的账号登录时自动授予 `staff`，不会自动建号 |
| `MEDITOUR_ACCESS_TOKEN_EXPIRE_DAYS` | 否 | `7` | access token 有效期（天） |
| `MEDITOUR_REFRESH_TOKEN_EXPIRE_DAYS` | 否 | `30` | refresh token 有效期（天） |
| `MEDITOUR_RESET_TOKEN_EXPIRE_MINUTES` | 否 | `30` | 忘记密码令牌有效期（分钟） |
| `MEDITOUR_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES` | 否 | `60` | 邮箱验证令牌有效期（分钟） |
| `MEDITOUR_PUBLIC_BASE_URL` | 否 | `http://localhost:8123` | 邮件里链接的站点地址（重置密码、验证邮箱） |
| `MEDITOUR_ENV` | 否 | `development` | 运行环境；设为 `production` 时 `/metrics` 默认关闭 |
| `MEDITOUR_METRICS_ENABLED` | 否 | 开发 `true` / 生产 `false` | 是否开放 `/metrics`；显式设置优先于环境默认值 |
| `MEDITOUR_MAIL_BACKEND` | 否 | `file` | 邮件实现：`file`（开发，写 outbox 文件）或 `smtp`（生产） |
| `MEDITOUR_MAIL_OUTBOX` | 否 | `backend/var/mail_outbox.log` | `file` 后端的输出文件，已被 `.gitignore` 忽略 |
| `MEDITOUR_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_FROM` / `_STARTTLS` | 否 | 空 / `587` / 空 / 空 / `no-reply@meditour.local` / 开 | `smtp` 后端配置位 |
| `MEDITOUR_STORAGE_BACKEND` | 否 | `local` | 上传存储后端；`local` 落本机磁盘，`s3` 为预留位（未实现时显式报错） |
| `MEDITOUR_UPLOAD_DIR` | 否 | `backend/var/uploads` | 本地上传目录（已被 `.gitignore` 忽略） |
| `MEDITOUR_UPLOAD_MAX_BYTES` | 否 | `5242880`（5 MiB） | 单张图片大小上限，超出返回 413 |
| `MEDITOUR_MAX_REQUEST_BYTES` | 否 | `10485760`（10 MiB） | 全局请求体上限，超出由中间件返回 413；必须大于上传上限 |
| `MEDITOUR_MEDIA_BASE_URL` | 否 | 空 | 媒体对外域名/CDN；留空时上传接口返回站内相对路径 |

本地可把变量写进 `backend/.env`（已被 `.gitignore` 忽略）；生产环境请通过运行环境注入，不要提交 `.env`。

## 预约与订单规则

- `appointment_date` 必须是未来时间，过去时间返回 422。
- `notes` 最长 2000 字符；`contact_phone` 允许 `+` 开头、7–15 位数字（空格、括号、短横线会被规范化）；`contact_email` 必须是合法邮箱。
- 同一用户对同一套餐、同一预约时间只允许一个 `pending` 订单，重复提交返回 409；换日期不受影响。
  该规则同时由部分唯一索引 `uq_bookings_pending_slot`（`WHERE status = 'pending'`）保证，
  并发请求也只有一个成功，其余返回同样形状的 409。取消后可以重新预约同一时段。
- 取消接口：`POST /api/v1/bookings/{id}/cancel`，只能取消自己的 `pending` 订单。
  - 不存在或属于他人：404（不暴露他人订单是否存在）。
  - 当前状态不是 `pending`：409。请求本身合法，但与资源当前状态冲突，因此用 409 而非 422；422 仅用于请求体校验失败。
  - 取消后 `status` 变为 `cancelled`，其余响应字段保持不变。
  - 取消使用条件更新（仅当 `status='pending'` 时生效）；并发取消同一订单只有一个
    返回 200，其余按状态冲突返回 409，不会出现多个请求都“成功取消”。

## 订单运营与员工角色

订单状态只允许两种前进路径：`pending → confirmed → completed`；取消仍由用户侧
`POST /api/v1/bookings/{id}/cancel` 完成（`pending → cancelled`）。

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
- `PATCH /api/v1/staff/bookings/{id}/status`，请求体 `{"status": "confirmed"}` 或
  `{"status": "completed"}`。
  - 非 `staff`：403；未登录：401；订单不存在：404。
  - 跳过中间状态或对已结束订单再流转：409。
  - 目标值不是 `confirmed` / `completed`：422（请求体校验失败）。
- 普通用户即使拥有订单本身，也不能调用以上员工接口修改状态（测试覆盖 403）。

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
- **当前不阻断登录**：未验证用户与已验证用户的登录、下单、导出等权限完全相同。这是为了不打断前端尚未做验证引导的现有流程。
- **上线前是否强制验证需要产品决策**（例如未验证只能浏览、不能下单，或登录后限制部分功能）。后端目前没有硬编码拦截；产品确认后需要另行实现并同步前端。

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

## 错误码对照表

下表按后端代码的实际行为逐条整理，方便前端按状态码分流。除健康检查的 503 外，错误响应体统一为
`{"detail": "..."}`；请求参数校验失败（422）时 `detail` 是字段错误数组。

| 状态码 | 含义 | 触发场景 |
| --- | --- | --- |
| 400 | 请求格式合法，但业务前置条件不满足 | `POST /auth/password-reset/confirm` 令牌不存在、已使用或已过期（统一 `Invalid or expired reset token`）；`POST /auth/email-verification/confirm` 令牌不存在、已使用或已过期（统一 `Invalid or expired verification token`）；`POST /auth/change-password` 当前密码错误；`DELETE /auth/account` 密码错误 |
| 401 | 未认证或凭据失效 | 任意需要 Bearer 的端点：缺少/为空/无效/过期/已吊销的 access token、`token_version` 不匹配、账号已注销（`Not authenticated` 或 `Invalid or expired token`，带 `WWW-Authenticate: Bearer`）；`POST /auth/login` 邮箱或密码错误（含已注销账号）；`POST /auth/refresh` refresh token 无效、过期、重复使用或所属用户失效；`POST /auth/logout` access/refresh token 无效，或 refresh token 不属于当前用户 |
| 403 | 已认证但权限不足 | 非 `staff` 角色访问 `/staff/*` 端点，`detail="Staff privileges required"`。普通用户即使拥有该订单也不能借此修改状态 |
| 404 | 资源不存在，或存在但不属于当前用户 | `POST /bookings/` 套餐不存在**或已下架**（下架套餐按不存在处理，不暴露其存在）；`POST /bookings/{id}/cancel`、`GET /staff/bookings/{id}`、`PATCH /staff/bookings/{id}/status` 订单不存在（用户侧与不存在/属于他人共用一个 404）；`GET/PUT/DELETE /itineraries/{id}` 行程不存在或属于他人；`GET /destinations/{id}` 目的地不存在；`/staff/packages|hospitals|destinations/{id}` 目标不存在；`DELETE /auth/sessions/{id}` 会话不存在、属于他人或已吊销；`GET /metrics` 指标端点关闭时 |
| 409 | 与资源当前状态冲突 | `POST /auth/register` 邮箱已注册；`POST /bookings/` 同用户同套餐同预约时间已有 `pending` 订单；`POST /bookings/{id}/cancel` 当前状态不是 `pending`；`PATCH /staff/bookings/{id}/status` 跳过中间状态或对已结束订单再流转；员工删除套餐时仍有订单、删除医院时仍有套餐、删除目的地时仍被行程引用；创建目的地时 slug 已存在 |
| 413 | 请求体过大 | 任意端点：请求体超过 `MEDITOUR_MAX_REQUEST_BYTES`（默认 10 MiB），`detail="Request body too large"`；`POST /staff/uploads`：文件大于 `MEDITOUR_UPLOAD_MAX_BYTES`（默认 5 MiB），`detail` 为限制字节数 |
| 415 | 上传文件类型不受支持 | `POST /staff/uploads`：声明类型不是 JPEG/PNG/WebP，或文件头与声明类型不符（防止把非图片改成 `.png` 后缀上传） |
| 422 | 请求体或查询参数校验失败 | 字段缺失/类型错误、邮箱格式、密码长度（6–72）、`notes` 超过 2000 字、预约时间不在未来、`contact_phone` 非 7–15 位、行程日期/目的地/每日编号不合法；分页 `page < 1`、`page_size < 1` 或 `> 100`；员工列表 `status` 不在 `pending/confirmed/completed/cancelled`；员工改状态的目标值不是 `confirmed/completed`；员工创建/更新套餐时 `hospital_id` 指向不存在的医院、`price ≤ 0`、`duration_days < 1`；目的地 slug 不符合 `^[a-z0-9][a-z0-9-]*$`；上传空文件；`lang` 不在 `zh/en/de/fr`（`detail` 为字符串 `Unsupported lang; supported values: ...`，其余为字段错误数组） |
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
当前 head 即 `d1a4b7c9e2f3`。

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

## 测试

```bash
cd backend
python -m pytest -q
```

测试使用独立的 `test_meditour.db`，每次会话开始时重建，不依赖本地开发库，也不访问外部网络。
当前覆盖（103 项）：预约字段与校验分支、重复提交、并发重复下单只产生一个 pending、并发取消只成功一次、取消流转与越权、并发登录只放行阈值内的失败、登录限流、令牌刷新/轮换/登出吊销、旧令牌兼容、找回密码（一次性/过期/防枚举）、修改密码后令牌失效、注销账号的匿名化与级联、多语言回退、数据导出隔离、员工角色授予与订单状态流转/越权、员工列表字段裁剪、详情访问审计、分页边界与索引存在性、员工内容 CRUD 与删除保护、套餐下架后公开列表隐藏且不可预约、改价不影响历史订单快照、图片上传的类型/大小/随机文件名校验、翻译 CSV 导入的幂等与错误行号、安全中间件（请求体上限、安全响应头与 HSTS 条件、500 兜底形状）、重置邮件多语言模板与 `.eml` 生成、邮件日志不含令牌/链接、日志脱敏与 request id、邮箱验证（注册发信、多语言、不阻断登录、一次性/过期/重发作废旧令牌、防枚举响应）、会话列表不含令牌、单设备吊销即时失效、越权吊销 404、退出所有设备、/metrics 输出与关闭开关。

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
