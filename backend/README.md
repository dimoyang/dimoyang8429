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
接口文档：`http://127.0.0.1:8000/docs`。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `MEDITOUR_SECRET_KEY`（或 `SECRET_KEY`） | 是 | 无 | JWT 签名密钥；缺失时进程直接启动失败，不会回退到默认值 |
| `DATABASE_URL` | 否 | `sqlite:///backend/meditour.db` | SQLAlchemy 连接串 |
| `MEDITOUR_CURRENCY` | 否 | `EUR` | 种子套餐与订单金额使用的币种 |
| `MEDITOUR_CORS_ORIGINS` | 否 | `http://localhost:8123,http://127.0.0.1:8123` | 允许的浏览器来源，逗号分隔 |

本地可把变量写进 `backend/.env`（已被 `.gitignore` 忽略）；生产环境请通过运行环境注入，不要提交 `.env`。

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

## 测试

```bash
cd backend
python -m pytest -q
```

测试使用独立的 `test_meditour.db`，每次会话开始时重建，不依赖本地开发库，也不访问外部网络。

## 接口验证脚本

`scripts/verify_api.py` 只用 Python 标准库，覆盖注册、登录、鉴权、套餐、医院、订单创建/列表、CORS 与错误体形状。

```bash
# 先启动后端，再执行
python scripts/verify_api.py --base-url http://127.0.0.1:8000/api/v1

# 验证后清理本次测试账号与订单（仅针对本机默认 SQLite）
python scripts/verify_api.py --cleanup
```

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
