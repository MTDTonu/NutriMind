"""内置食物库导入脚本（CLI）。

用法：
    python seed_foods.py            # 幂等补齐缺失条目（默认）
    python seed_foods.py --count    # 只打印数据源条目数，不写库

说明：
- 脚本与 web 服务共用 services.food_service.ensure_base_foods，逻辑只有一份，
  不会出现「脚本导入的和启动时导入的不一致」这种问题。
- 已存在的同名内置条目不会被覆盖，避免冲掉订正过的数据。
"""
import sys


def main():
    args = sys.argv[1:]
    from data.foods_seed import count, RAW

    if "--count" in args:
        total = count()
        print(f"数据源条目数：{total}")
        for line in RAW.strip().splitlines()[:3]:
            print("  样例:", line)
        return

    from database.db import SessionLocal, create_tables
    from services.food_service import ensure_base_foods

    # 独立进程运行时库里可能还没有新表，先建表再导入
    create_tables()
    db = SessionLocal()
    try:
        added = ensure_base_foods(db)
        if added:
            print(f"已导入 {added} 条内置食物")
        else:
            print("内置食物库已是最新，无需导入")
    finally:
        db.close()


if __name__ == "__main__":
    main()
