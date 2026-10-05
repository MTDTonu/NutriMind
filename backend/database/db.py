"""数据库引擎、会话与自动建表。

说明：
- 使用 SQLAlchemy 2.0 风格（declarative_base + sessionmaker）。
- 默认 SQLite（零运维）；设置 DATABASE_URL 即切到 PostgreSQL，
  迁移脚本见 scripts/migrate_to_pg.py。
- create_tables() 在应用启动时调用，使用 Base.metadata.create_all 自动建表，
  禁止手写 SQL 建表。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os
from dotenv import load_dotenv

# 加载 .env（若存在）
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "diet.db")

# 优先使用显式连接串（PostgreSQL）；未设置则退回 SQLite 文件
DATABASE_URL = os.getenv("DATABASE_URL") or ""
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    # SQLite 需要关闭同线程检查（FastAPI 的多线程请求模型下必需）
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    # PostgreSQL：按环境变量调池，默认值偏保守，够用且不至于占满上游连接数
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("PG_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("PG_MAX_OVERFLOW", "10")),
        pool_recycle=int(os.getenv("PG_POOL_RECYCLE", "1800")),
        pool_timeout=int(os.getenv("PG_POOL_TIMEOUT", "30")),
        pool_pre_ping=bool(int(os.getenv("PG_POOL_PRE_PING", "1"))),
    )

# 会话工厂：关闭自动提交/自动 flush，绑定引擎
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有 ORM 模型的基类
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每次请求创建一个会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_columns():
    """轻量列迁移：SQLite 的 create_all 不会补列，这里为后加的字段做 ALTER。

    仅对「模型里有、表里没有」的列做 ADD COLUMN，安全可重复执行。
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    from database import models  # noqa: F401

    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            col_type = col.type.compile(engine.dialect)
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}')
                    )
            except Exception:  # noqa: BLE001
                # 已有同名列 / SQLite 不支持的默认值等情况直接跳过
                pass


def create_tables():
    """自动建表：导入 models 使所有表注册到 Base.metadata，然后 create_all。"""
    # 必须在建表前导入模型，否则表不会被注册
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
