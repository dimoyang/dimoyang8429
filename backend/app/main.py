"""MediTour 后端入口。"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_migrate import ensure_database_schema
from app.routers import auth, bookings, destinations, health, itineraries, medical
from app.seed import seed_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("MEDITOUR_TESTING") == "1":
        # 测试使用临时数据库，直接建表，避免依赖迁移脚本的执行顺序。
        Base.metadata.create_all(bind=engine)
    else:
        ensure_database_schema()
    with SessionLocal() as db:
        seed_data(db)
    yield


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(medical.router, prefix=settings.API_V1_PREFIX)
app.include_router(bookings.router, prefix=settings.API_V1_PREFIX)
app.include_router(destinations.router, prefix=settings.API_V1_PREFIX)
app.include_router(itineraries.router, prefix=settings.API_V1_PREFIX)
