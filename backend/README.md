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
| `MEDITOUR_PUBLIC_BASE_URL` | 否 | `http://localhost:8123` | 重置邮件里链接的站点地址 |
| `MEDITOUR_MAIL_BACKEND` | 否 | `file` | 邮件实现：`file`（开发，写 outbox 文件）或 `smtp`（生产） |
| `MEDITOUR_MAIL_OUTBOX` | 否 | `backend/var/mail_outbox.log` | `file` 后端的输出文件，已被 `.gitignore` 忽略 |
| `MEDITOUR_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_FROM` / `_STARTTLS` | 否 | 空 / `587` / 空 / 空 / `no-reply@meditour.local` / 开 | `smtp` 后端配置位 |
| `MEDITOUR_STORAGE_BACKEND` | 否 | `local` | 上传存储后端；`local` 落本机磁盘，`s3` 为预留位（未实现时显式报错） |
| `MEDITOUR_UPLOAD_DIR` | 否 | `backend/var/uploads` | 本地上传目录（已被 `.gitignore` 忽略） |
| `MEDITOUR_UPLOAD_MAX_BYTES` | 否 | `5242880`（5 MiB） | 单张图片大小上限，超出返回 413 |
| `MEDITOUR_MEDIA_BASE_URL` | 否 | 空 | 媒体对外域名/CDN；留空时上传接口返回站内相对路径 |

本地可把变量写进 `backend/.env`（已被 `.gitignore` 忽略）；生产环境请通过运行环境注入，不要提交 `.env`。

## 预约与订单规则

- `appointment_date` 必须是未来时间，过去时间返回 422。
- `notes` 最长 2000 字符；`contact_phone` 允许 `+` 开头、7–15 位数字（空格、括号、短横线会被规范化）；`contact_email` 必须是合法邮箱。
- 同一用户对同一套餐、同一预约时间只允许一个 `pending` 订单，重复提交返回 409；换日期不受影响。
- 取消接口：`POST /api/v1/bookings/{id}/cancel`，只能取消自己的 `pending` 订单。
  - 不存在或属于他人：404（不暴露他人订单是否存在）。
  - 当前状态不是 `pending`：409。请求本身合法，但与资源当前状态冲突，因此用 409 而非 422；422 仅用于请求体校验失败。
  - 取消后 `status` 变为 `cancelled`，其余响应字段保持不变。

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
- `POST /api/v1/auth/logout` 吊销当前 access token，可选在请求体传入 `refresh_token` 一并吊销。
- 吊销名单存放在数据库表 `token_revocations`（按 `jti`），服务和进程重启后仍然有效；过期记录在刷新/登出时顺带清理。
- 旧版本签发、没有 `type`/`jti` 的 access token 仍可继续使用；这类令牌无法被登出吊销，会在过期后自然失效。
- 令牌载荷带 `ver`（用户 `token_version`）；改密、重置密码、注销账号会自增该版本，使该用户所有已签发的 access/refresh 令牌立即失效。旧令牌缺少 `ver` 时按 `0` 处理，兼容上线前签发的令牌。
- 所有 401 的错误体保持 `{"detail": "..."}` 字符串形状。

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

- 开发默认 `MEDITOUR_MAIL_BACKEND=file`：邮件写入 `backend/var/mail_outbox.log`（路径可用 `MEDITOUR_MAIL_OUTBOX` 覆盖），一行一封，包含收件人、重置令牌与重置链接。该文件已被 `.gitignore` 忽略，不属于常规请求日志。
- 常规请求日志只记录 `password_reset_email_written` 和文件路径，不记录收件人或令牌；日志脱敏规则同时覆盖邮箱与 `token` 键值。
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
限流状态是**进程内**的：多 worker / 多实例部署时各进程独立计数，重启后清零，也无法防止攻击者用大量账号轮换撞库。生产多进程部署应换成 Redis 等共享存储，并配合网关层限流。
副作用是攻击者可能故意失败 5 次导致某个账号短暂无法登录；当前窗口只有 5 分钟，如需更强防护可加验证码或按 IP 维度限流。

## 日志

- 每个请求输出一行 JSON：`ts`、`level`、`logger`、`message`、`request_id`、`method`、`path`、`status`、`duration_ms`。
- 响应头返回 `X-Request-ID`；客户端传入同名头时原样透传，便于跨服务排查。
- 脱敏规则集中在 [app/logging_config.py](app/logging_config.py)：JWT、邮箱、手机号以及 `password`/`token`/`notes`/`phone`/`email` 等键值统一替换为 `[REDACTED]`。
- 请求日志不记录请求体与查询串；路由代码也不做敏感字段拼接。Docker 启动参数已加 `--no-access-log`，避免 uvicorn 另记一份未脱敏访问日志。

## 错误码对照表

下表按后端代码的实际行为逐条整理，方便前端按状态码分流。除健康检查的 503 外，错误响应体统一为
`{"detail": "..."}`；请求参数校验失败（422）时 `detail` 是字段错误数组。

| 状态码 | 含义 | 触发场景 |
| --- | --- | --- |
| 400 | 请求格式合法，但业务前置条件不满足 | `POST /auth/password-reset/confirm` 令牌不存在、已使用或已过期（统一 `Invalid or expired reset token`）；`POST /auth/change-password` 当前密码错误；`DELETE /auth/account` 密码错误 |
| 401 | 未认证或凭据失效 | 任意需要 Bearer 的端点：缺少/为空/无效/过期/已吊销的 access token、`token_version` 不匹配、账号已注销（`Not authenticated` 或 `Invalid or expired token`，带 `WWW-Authenticate: Bearer`）；`POST /auth/login` 邮箱或密码错误（含已注销账号）；`POST /auth/refresh` refresh token 无效、过期、重复使用或所属用户失效；`POST /auth/logout` access/refresh token 无效，或 refresh token 不属于当前用户 |
| 403 | 已认证但权限不足 | 非 `staff` 角色访问 `/staff/*` 端点，`detail="Staff privileges required"`。普通用户即使拥有该订单也不能借此修改状态 |
| 404 | 资源不存在，或存在但不属于当前用户 | `POST /bookings/` 套餐不存在**或已下架**（下架套餐按不存在处理，不暴露其存在）；`POST /bookings/{id}/cancel`、`GET /staff/bookings/{id}`、`PATCH /staff/bookings/{id}/status` 订单不存在（用户侧与不存在/属于他人共用一个 404）；`GET/PUT/DELETE /itineraries/{id}` 行程不存在或属于他人；`GET /destinations/{id}` 目的地不存在；`/staff/packages|hospitals|destinations/{id}` 目标不存在 |
| 409 | 与资源当前状态冲突 | `POST /auth/register` 邮箱已注册；`POST /bookings/` 同用户同套餐同预约时间已有 `pending` 订单；`POST /bookings/{id}/cancel` 当前状态不是 `pending`；`PATCH /staff/bookings/{id}/status` 跳过中间状态或对已结束订单再流转；员工删除套餐时仍有订单、删除医院时仍有套餐、删除目的地时仍被行程引用；创建目的地时 slug 已存在 |
| 413 | 上传文件超过大小上限 | `POST /staff/uploads`：文件大于 `MEDITOUR_UPLOAD_MAX_BYTES`（默认 5 MiB），`detail` 为限制字节数 |
| 415 | 上传文件类型不受支持 | `POST /staff/uploads`：声明类型不是 JPEG/PNG/WebP，或文件头与声明类型不符（防止把非图片改成 `.png` 后缀上传） |
| 422 | 请求体或查询参数校验失败 | 字段缺失/类型错误、邮箱格式、密码长度（6–72）、`notes` 超过 2000 字、预约时间不在未来、`contact_phone` 非 7–15 位、行程日期/目的地/每日编号不合法；分页 `page < 1`、`page_size < 1` 或 `> 100`；员工列表 `status` 不在 `pending/confirmed/completed/cancelled`；员工改状态的目标值不是 `confirmed/completed`；员工创建/更新套餐时 `hospital_id` 指向不存在的医院、`price ≤ 0`、`duration_days < 1`；目的地 slug 不符合 `^[a-z0-9][a-z0-9-]*$`；上传空文件；`lang` 不在 `zh/en/de/fr`（`detail` 为字符串 `Unsupported lang; supported values: ...`，其余为字段错误数组） |
| 429 | 触发登录限流 | 仅 `POST /auth/login`：同一 IP + 邮箱 300 秒内失败 5 次，响应带 `Retry-After` 秒数；成功登录会清零计数 |
| 503 | 依赖服务不可用 | 仅 `GET /health`：数据库 `SELECT 1` 失败，返回 `{"status":"error","database":"unavailable"}`（不是 `detail` 结构） |
| 500 | 未预期的服务端异常 | 未做自定义处理，由 FastAPI/Starlette 默认返回；响应体不是 `{"detail": ...}`，前端应按未知错误处理并上报 |

成功状态码：`200` 常规读取/更新/登录/刷新/登出/改密/重置密码/导出；`201` 注册、创建订单、创建行程、创建套餐/医院/目的地、上传图片；`204` 删除行程、删除套餐/医院/目的地（无响应体）。

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
当前覆盖（77 项）：预约字段与校验分支、重复提交、取消流转与越权、登录限流、令牌刷新/轮换/登出吊销、旧令牌兼容、找回密码（一次性/过期/防枚举）、修改密码后令牌失效、注销账号的匿名化与级联、多语言回退、数据导出隔离、员工角色授予与订单状态流转/越权、员工列表字段裁剪、详情访问审计、分页边界与索引存在性、员工内容 CRUD 与删除保护、套餐下架后公开列表隐藏且不可预约、改价不影响历史订单快照、图片上传的类型/大小/随机文件名校验、翻译 CSV 导入的幂等与错误行号、日志脱敏与 request id。

## 接口验证脚本

`scripts/verify_api.py` 只用 Python 标准库，覆盖注册、登录（含限流）、鉴权、健康检查、套餐、医院、订单创建/校验/列表/取消、令牌刷新与登出、CORS、request id、错误体形状、账号闭环、多语言回退、数据导出、分页边界与员工订单操作（默认 107 项断言；提供 `--staff-email/--staff-password` 时额外验证员工接口，共 125 项）。本批新增的员工内容运营与图片上传端点由 pytest 覆盖，尚未加入该脚本。

```bash
# 先启动后端，再执行
python scripts/verify_api.py --base-url http://127.0.0.1:8000/api/v1

# 开发环境 file 邮件后端：验证忘记密码需要从 outbox 读取令牌（默认路径）
python scripts/verify_api.py --mail-outbox backend/var/mail_outbox.log

# 员工接口验证：账号需先由 manage_staff.py 授予 staff
python scripts/verify_api.py --staff-email staff@example.com --staff-password Staff123456

# 验证后清理本次测试账号与订单（仅针对本机默认 SQLite）
python scripts/verify_api.py --cleanup
```

账号闭环部分依赖开发环境 `MEDITOUR_MAIL_BACKEND=file` 写出的 outbox 文件；使用 `smtp` 后端时该段会明确失败并提示，不会伪造通过。

全部通过时退出码为 0，有失败为 1，连接失败为 2。Android 模拟器访问宿主机可用 `http://10.0.2.2:8000/api/v1`。

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
