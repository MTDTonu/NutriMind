"""SQLite → PostgreSQL 迁移脚本。

用法（在 backend 目录下，用项目虚拟环境执行）：

    # 1) 先准备好目标库：createdb nutrimind
    # 2) 干跑：只搬模型里已有的表，打印会写入多少行，不落库
    ./.venv/Scripts/python.exe scripts/migrate_to_pg.py ^
        --to postgresql+psycopg://user:pwd@localhost:5432/nutrimind --dry-run

    # 3) 正式迁移（目标表已有数据会报错退出，避免重复导入；确需覆盖加 --truncate）
    ./.venv/Scripts/python.exe scripts/migrate_to_pg.py ^
        --to postgresql+psycopg://user:pwd@localhost:5432/nutrimind

设计要点：
- **目标表结构以 ORM 模型为准**（Base.metadata），不靠 SQLite 的表结构推断：
  SQLite 里 DateTime 存成字符串、Boolean 存成 0/1，照搬类型会把脏东西带进 PG。
- **按主键顺序分批搬迁**，每批 500 行：单表几十万行时不会撑爆内存，
  也方便中途 Ctrl-C 后用 --only 断点续传。
- **搬完重置自增序列**：PG 的 SERIAL/IDENTITY 不会因为 INSERT 自动前进，
  不重置的话第一条新记录会因主键冲突直接插入失败——这是本脚本最容易漏的一步。
- **行数校验**：迁移后逐表比对源/目标行数，不一致立刻标红，让问题在迁移阶段暴露。
"""
import argparse
import os
import sys
from pathlib import Path

# 让脚本可以直接以 `python scripts/migrate_to_pg.py` 运行（无需设置 PYTHONPATH）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import create_engine, inspect, select, text  # noqa: E402
from database.db import Base  # noqa: E402
from database import models  # noqa: F401,E402  (确保所有模型已注册)

BATCH = 500


def fail(msg: str, code: int = 1):
    print(f"\n[错误] {msg}")
    sys.exit(code)


def build_args():
    p = argparse.ArgumentParser(description="把 SQLite 数据迁到 PostgreSQL")
    p.add_argument(
        "--from",
        dest="src",
        default=os.getenv("DB_PATH", "diet.db"),
        help="源 SQLite 文件（默认 diet.db）",
    )
    p.add_argument("--to", dest="dst", default=os.getenv("DATABASE_URL") or "", help="目标 PG 连接串")
    p.add_argument("--dry-run", action="store_true", help="只统计不写入")
    p.add_argument("--truncate", action="store_true", help="迁移前清空目标表（危险）")
    p.add_argument("--only", default="", help="只迁移指定表，逗号分隔，如 user,diet_record")
    return p.parse_args()


def main():
    args = build_args()
    if not args.dst:
        fail("缺少 --to 目标连接串（或设置环境变量 DATABASE_URL）")

    src_path = args.src.replace("sqlite:///", "")
    if not os.path.isfile(src_path):
        fail(f"源数据库不存在：{src_path}")

    src_engine = create_engine(f"sqlite:///{src_path}")
    dst_engine = create_engine(args.dst)

    if "postgres" not in dst_engine.dialect.name:
        fail(f"目标不是 PostgreSQL：{dst_engine.dialect.name}")

    src_insp = inspect(src_engine)
    src_tables = set(src_insp.get_table_names())

    only = {t.strip() for t in args.only.split(",") if t.strip()}
    tables = [
        t
        for t in Base.metadata.sorted_tables
        if t.name in src_tables and (not only or t.name in only)
    ]

    missing = [t.name for t in Base.metadata.sorted_tables if t.name not in src_tables and (not only or t.name in only)]
    print(f"源库：{src_path}")
    print(f"目标：{args.dst.split('@')[-1]}")
    print(f"待迁移表 {len(tables)} 张：{', '.join(t.name for t in tables)}")
    if missing:
        print(f"跳过（源库无此表）：{', '.join(missing)}")
    if args.dry_run:
        print("\n[干跑] 以下为各表行数，不会写入目标库")

    # ---- 目标库建表 ----
    if not args.dry_run:
        with dst_engine.begin() as conn:
            if args.truncate:
                print("\n[警告] --truncate：清空目标库中所有 ORM 表")
                for t in reversed(Base.metadata.sorted_tables):
                    conn.execute(text(f'TRUNCATE TABLE "{t.name}" CASCADE'))
        Base.metadata.create_all(bind=dst_engine)

    # ---- 搬迁 ----
    report = []
    total_rows = 0
    for table in tables:
        # 源与目标列取交集：源库若是更老的版本（缺后加的列），缺失部分交给列的默认值，
        # 而不是让整张表迁移失败。
        src_cols = {c["name"] for c in src_insp.get_columns(table.name)}
        usable = [c for c in table.columns if c.name in src_cols]
        if not usable:
            print(f"  {table.name:<20} 源库无可迁移列，跳过")
            continue

        src_count = src_engine.connect().execute(
            text(f'SELECT COUNT(*) FROM "{table.name}"')
        ).scalar()

        if args.dry_run:
            print(f"  {table.name:<20} {src_count:>8} 行")
            report.append((table.name, src_count, src_count, True))
            total_rows += src_count
            continue

        # 用 SQLAlchemy Core 的 select 而不是裸 SQL：这样 result/bind 的类型转换都会生效。
        # 裸 SQL 从 SQLite 取出的日期是 'YYYY-MM-DD' 字符串，直接塞给 Date 列会被类型检查拒绝。
        order_cols = list(table.primary_key.columns)
        moved = 0
        with src_engine.connect() as src_conn, dst_engine.begin() as dst_conn:
            offset = 0
            while True:
                stmt = select(*usable)
                if order_cols:
                    stmt = stmt.order_by(*[c for c in order_cols if c.name in src_cols])
                rows = src_conn.execute(stmt.limit(BATCH).offset(offset)).mappings().all()
                if not rows:
                    break
                dst_conn.execute(table.insert(), [dict(r) for r in rows])
                moved += len(rows)
                offset += BATCH
                print(f"  {table.name:<20} {moved}/{src_count}", end="\r", flush=True)

        print(f"  {table.name:<20} {moved:>8} 行" + " " * 20)
        total_rows += moved
        report.append((table.name, src_count, moved, src_count == moved))

    if args.dry_run:
        print(f"\n合计 {total_rows} 行（干跑，未写入）。")
        return

    # ---- 重置自增序列：不做这一步，新记录会撞主键 ----
    reset_sequences(dst_engine)

    # ---- 校验 ----
    print("\n校验行数：")
    bad = []
    with dst_engine.connect() as conn:
        for name, src_count, moved, ok in report:
            dst_count = conn.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar()
            flag = "OK " if dst_count == src_count else "✗  "
            print(f"  {flag}{name:<20} 源 {src_count:>8} / 目标 {dst_count:>8}")
            if dst_count != src_count:
                bad.append(name)

    if bad:
        fail(f"以下表行数不一致，请检查：{', '.join(bad)}")

    print(f"\n迁移完成，共 {total_rows} 行。")
    print("下一步：把 .env 里的 DATABASE_URL 指向新库，并把 DB_PATH 行注释掉，重启服务。")


def reset_sequences(engine):
    """把每个自增主键对应的序列推到当前最大值。

    直接用 pg_get_serial_sequence 找序列名：自己拼 `表名_列名_seq` 在 IDENTITY 列
    或改名过的情况下会找不到，而「序列没推进」的表现是第一条新记录就主键冲突，
    属于迁移后立刻炸的类型，必须一次做对。
    """
    print("\n重置自增序列：")
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            pk = next(iter(table.primary_key.columns), None)
            if pk is None or pk.type.python_type is not int:
                continue
            try:
                conn.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:tbl, :col), "
                        "COALESCE((SELECT MAX("
                        + f'"{pk.name}"'
                        + ") FROM "
                        + f'"{table.name}"'
                        + "), 0) + 1, false)"
                    ),
                    {"tbl": f'"{table.name}"', "col": pk.name},
                )
                print(f"  {table.name}: ok")
            except Exception as exc:  # noqa: BLE001
                # 普通整型主键（非 SERIAL/IDENTITY）没有序列，跳过即可
                print(f"  {table.name}: 跳过（{str(exc)[:40]}）")


if __name__ == "__main__":
    main()
