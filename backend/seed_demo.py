"""演示数据生成器：为指定用户灌入近 N 天的饮食 / 体重 / 运动 / 饮水记录。

用途：新库或演示账号页面全空时，一键生成可信的展示数据。

用法（在 backend 目录下）：
    python seed_demo.py                 # 为 demo 用户补齐近 14 天缺失数据
    python seed_demo.py --reset         # 先清空该用户近 14 天数据再灌入
    python seed_demo.py --user demo --days 14

注意：只处理目标用户的数据，不影响其他账号。
"""
import argparse
import random
from datetime import date, timedelta

from database.db import SessionLocal, create_tables
from database.models import DietRecord, ExerciseRecord, User, WaterRecord, WeightRecord

# meal_type: 1 早 / 2 午 / 3 晚 / 4 加餐
# (食物名, 克, 热量, 蛋白g, 脂肪g, 碳水g, 糖g, 纤维g, 钠mg)
FOODS = {
    1: [  # 早餐
        ("燕麦粥", 250, 150, 5.0, 3.0, 27.0, 1.0, 3.0, 60),
        ("水煮蛋", 50, 78, 6.5, 5.5, 0.6, 0.6, 0.0, 70),
        ("全麦面包", 60, 156, 6.0, 2.4, 27.0, 3.0, 3.6, 300),
        ("无糖豆浆", 250, 80, 7.0, 4.0, 4.0, 0.5, 1.0, 40),
        ("蒸红薯", 150, 129, 1.6, 0.3, 30.0, 12.0, 2.3, 55),
        ("小米粥", 250, 138, 4.5, 1.0, 29.0, 0.5, 1.0, 30),
        ("脱脂牛奶", 250, 85, 8.5, 0.5, 12.0, 12.0, 0.0, 105),
        ("水煮玉米", 160, 168, 6.0, 2.5, 35.0, 6.0, 4.2, 20),
    ],
    2: [  # 午餐
        ("杂粮饭", 150, 195, 4.5, 1.5, 41.0, 0.5, 2.5, 5),
        ("清蒸鸡胸肉", 120, 165, 31.0, 3.6, 0.5, 0.0, 0.0, 65),
        ("白灼西兰花", 150, 51, 4.2, 0.6, 6.0, 1.5, 3.8, 40),
        ("番茄炒蛋", 180, 162, 8.5, 11.0, 7.0, 4.0, 1.2, 420),
        ("清蒸鲈鱼", 130, 156, 26.0, 5.2, 0.3, 0.0, 0.0, 180),
        ("凉拌黄瓜", 120, 22, 1.0, 0.2, 3.6, 2.0, 0.7, 240),
        ("蒜蓉菠菜", 150, 45, 3.5, 1.2, 4.5, 0.6, 2.6, 210),
        ("虾仁豆腐", 180, 175, 20.0, 7.5, 6.5, 1.5, 0.8, 380),
    ],
    3: [  # 晚餐
        ("蒸红薯", 150, 129, 1.6, 0.3, 30.0, 12.0, 2.3, 55),
        ("香煎龙利鱼", 120, 140, 21.0, 5.0, 0.5, 0.0, 0.0, 150),
        ("紫薯", 130, 130, 1.8, 0.3, 30.0, 11.0, 2.5, 45),
        ("冬瓜汤", 200, 30, 1.2, 0.8, 4.5, 2.0, 1.0, 320),
        ("凉拌木耳", 100, 40, 1.5, 1.8, 4.0, 0.8, 2.8, 220),
        ("水煮虾", 110, 105, 22.0, 1.2, 0.5, 0.0, 0.0, 165),
        ("清炒油麦菜", 150, 38, 2.4, 1.0, 4.0, 1.5, 2.0, 190),
        ("小米粥", 220, 122, 4.0, 0.9, 26.0, 0.5, 0.9, 26),
    ],
    4: [  # 加餐
        ("苹果", 200, 104, 0.5, 0.3, 26.0, 20.0, 3.6, 2),
        ("无糖酸奶", 120, 72, 4.5, 2.4, 6.0, 6.0, 0.0, 60),
        ("原味坚果", 20, 118, 3.6, 10.0, 3.2, 1.2, 1.8, 1),
        ("圣女果", 150, 33, 1.4, 0.4, 6.6, 4.5, 1.5, 8),
    ],
}

# (运动名, 时长区间分钟, MET)
EXERCISES = [
    ("快走", (30, 45), 4.3),
    ("慢跑", (20, 35), 7.0),
    ("跳绳", (10, 20), 11.0),
    ("力量训练", (30, 50), 5.0),
    ("瑜伽", (25, 40), 3.0),
    ("户外骑行", (30, 60), 6.8),
]

WEIGHT_START = 80.0
WEIGHT_END = 78.2


def _exists(db, model, user_id, d):
    return db.query(model).filter_by(user_id=user_id, record_date=d).first()


def seed_user(db, user: User, days: int, reset: bool, rng: random.Random) -> dict:
    today = date.today()
    start = today - timedelta(days=days - 1)

    if reset:
        n = 0
        for model in (DietRecord, WeightRecord, WaterRecord, ExerciseRecord):
            n += db.query(model).filter(
                model.user_id == user.id, model.record_date >= start
            ).delete(synchronize_session=False)
        db.commit()
        print(f"  已清空 {user.username} 近 {days} 天旧记录 {n} 条")

    created = {"diet": 0, "weight": 0, "water": 0, "exercise": 0}
    prev_weight = None

    for i in range(days):
        d = start + timedelta(days=i)
        ratio = i / max(days - 1, 1)
        w = WEIGHT_START + (WEIGHT_END - WEIGHT_START) * ratio + rng.uniform(-0.25, 0.25)
        w = round(w, 1)

        # 体重（weight_diff = 相对前一天的变化，负值=下降）
        if not _exists(db, WeightRecord, user.id, d):
            db.add(WeightRecord(
                user_id=user.id, record_date=d, weight=w,
                weight_diff=round(w - prev_weight, 1) if prev_weight is not None else 0.0,
            ))
            created["weight"] += 1
        prev_weight = w

        # 饮水（每天一条汇总行）
        if not _exists(db, WaterRecord, user.id, d):
            target = int(float(user.current_weight or 60) * 35)
            db.add(WaterRecord(
                user_id=user.id, record_date=d,
                total_amount=rng.choice([1200, 1600, 2000, 2400]),
                target_amount=max(target, 1500),
            ))
            created["water"] += 1

        # 运动（70% 概率有）
        if not _exists(db, ExerciseRecord, user.id, d) and rng.random() < 0.7:
            name, (lo, hi), met = rng.choice(EXERCISES)
            minutes = rng.randint(lo, hi)
            burn = round(met * w * (minutes / 60.0))
            db.add(ExerciseRecord(
                user_id=user.id, record_date=d,
                exercise_type=name, duration=minutes, calorie_burn=float(burn),
            ))
            created["exercise"] += 1

        # 饮食：早/午/晚 各 2~3 项 + 50% 概率一次加餐
        if not db.query(DietRecord).filter_by(user_id=user.id, record_date=d).first():
            plan = {1: rng.sample(FOODS[1], k=rng.randint(2, 3)),
                    2: rng.sample(FOODS[2], k=rng.randint(2, 3)),
                    3: rng.sample(FOODS[3], k=2)}
            if rng.random() < 0.5:
                plan[4] = rng.sample(FOODS[4], k=1)
            for meal, items in plan.items():
                for (name, g, kcal, p, f, c, su, fi, na) in items:
                    db.add(DietRecord(
                        user_id=user.id, record_date=d, meal_type=meal,
                        food_desc=f"{name} {g}g", input_type=1,
                        calorie=float(kcal), protein=float(p), fat=float(f),
                        carbohydrate=float(c), sugar=float(su), fiber=float(fi),
                        sodium=float(na),
                    ))
                    created["diet"] += 1

    db.commit()
    return created


def main():
    ap = argparse.ArgumentParser(description="知食 NutriMind演示数据生成器")
    ap.add_argument("--user", default="demo", help="目标用户名（默认 demo）")
    ap.add_argument("--days", type=int, default=14, help="生成近几天数据（默认 14）")
    ap.add_argument("--reset", action="store_true", help="先清空该用户近 N 天数据")
    args = ap.parse_args()

    create_tables()
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.username == args.user).all()
        if not users:
            print(f"未找到用户 {args.user}，请先注册。现有用户：")
            for u in db.query(User).limit(10).all():
                print("  -", u.username)
            return
        rng = random.Random(20260927)  # 固定种子，结果可复现
        for u in users:
            print(f"为用户 {u.username} (id={u.id}) 生成近 {args.days} 天数据 ...")
            print("  完成：", seed_user(db, u, args.days, args.reset, rng))
    finally:
        db.close()


if __name__ == "__main__":
    main()
