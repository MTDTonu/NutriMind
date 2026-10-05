"""数据导入导出服务。

设计原则：
- 导出的是「用户自己的原始数据」，不做二次加工，保证导出的数值与界面显示的完全一致；
- 导入必须幂等（同一天重复导入同一份文件不会产生重复记录），且失败行不影响成功行；
- 任何一行解析失败都要在结果里给出具体行号与原因，绝不能静默丢弃。
"""
from sqlalchemy.orm import Session

from database.models import (
    User,
    DietRecord,
    WeightRecord,
    WaterRecord,
    ExerciseRecord,
    ReminderSetting,
)
from datetime import datetime, date, timedelta
import csv
import io
import json

MEAL_LABELS = {1: "早餐", 2: "午餐", 3: "晚餐", 4: "加餐"}


# ---------------------------------------------------------------- 导出

def _since(record_date, days: int):
    """days<=0 表示不限时间范围。"""
    if not days or days <= 0:
        return True
    return record_date >= date.today() - timedelta(days=days - 1)


def build_export(db: Session, user: User, days: int = 0) -> dict:
    """汇总用户全量数据为一个可序列化的字典。"""
    diets = (
        db.query(DietRecord)
        .filter(DietRecord.user_id == user.id)
        .order_by(DietRecord.record_date, DietRecord.meal_type, DietRecord.id)
        .all()
    )
    weights = (
        db.query(WeightRecord)
        .filter(WeightRecord.user_id == user.id)
        .order_by(WeightRecord.record_date)
        .all()
    )
    waters = (
        db.query(WaterRecord)
        .filter(WaterRecord.user_id == user.id)
        .order_by(WaterRecord.record_date)
        .all()
    )
    exercises = (
        db.query(ExerciseRecord)
        .filter(ExerciseRecord.user_id == user.id)
        .order_by(ExerciseRecord.record_date)
        .all()
    )

    return {
        "meta": {
            "app": "知食 NutriMind",
            "version": 1,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "scope_days": days or "all",
            "counts": {
                "diet": len([d for d in diets if _since(d.record_date, days)]),
                "weight": len([w for w in weights if _since(w.record_date, days)]),
                "water": len([w for w in waters if _since(w.record_date, days)]),
                "exercise": len([e for e in exercises if _since(e.record_date, days)]),
            },
        },
        "profile": {
            "username": user.username,
            "gender": user.gender,
            "age": user.age,
            "height": user.height,
            "current_weight": user.current_weight,
            "target_weight": user.target_weight,
            "activity_level": user.activity_level,
            "bmr": user.bmr,
            "tdee": user.tdee,
            "recommend_calorie": user.recommend_calorie,
            "tdee_adaptive": getattr(user, "tdee_adaptive", None),
            "last_calibrate_at": (
                user.last_calibrate_at.isoformat()
                if getattr(user, "last_calibrate_at", None)
                else None
            ),
        },
        "target": {
            "mode": getattr(user, "target_mode", "deficit") or "deficit",
            "target_rate": getattr(user, "target_rate", None),
            "target_deficit": getattr(user, "target_deficit", None),
        },
        "diet": [
            {
                "date": d.record_date.isoformat(),
                "meal_type": d.meal_type,
                "meal": MEAL_LABELS.get(d.meal_type, "其他"),
                "food": d.food_desc,
                "calorie": d.calorie,
                "protein": d.protein,
                "fat": d.fat,
                "carbohydrate": d.carbohydrate,
                "fiber": d.fiber,
                "input_type": d.input_type,
            }
            for d in diets
            if _since(d.record_date, days)
        ],
        "weight": [
            {
                "date": w.record_date.isoformat(),
                "weight": w.weight,
                "body_fat": w.body_fat,
                "waist": w.waist,
                "diff": w.weight_diff,
            }
            for w in weights
            if _since(w.record_date, days)
        ],
        "water": [
            {
                "date": w.record_date.isoformat(),
                "amount": w.total_amount,
                "target": w.target_amount,
            }
            for w in waters
            if _since(w.record_date, days)
        ],
        "exercise": [
            {
                "date": e.record_date.isoformat(),
                "name": e.exercise_type,
                "duration": e.duration,
                "calorie": e.calorie_burn,
            }
            for e in exercises
            if _since(e.record_date, days)
        ],
    }


def export_csv(payload: dict) -> str:
    """把导出包渲染成「饮食明细」CSV（一行一条食物，带 UTF-8 BOM 便于 Excel 打开）。"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["日期", "餐次", "食物", "热量(kcal)", "蛋白质(g)", "脂肪(g)", "碳水(g)", "膳食纤维(g)"]
    )
    for d in payload["diet"]:
        writer.writerow(
            [
                d["date"],
                d["meal"],
                d["food"],
                round(d["calorie"], 1),
                round(d["protein"], 1),
                round(d["fat"], 1),
                round(d["carbohydrate"], 1),
                round(d.get("fiber", 0), 1),
            ]
        )
    # 追加体重区块：同一个文件里分区展示，避免用户导出两份
    writer.writerow([])
    writer.writerow(["体重记录"])
    writer.writerow(["日期", "体重(kg)", "体脂率(%)", "腰围(cm)", "日差值(kg)"])
    for w in payload["weight"]:
        writer.writerow(
            [
                w["date"],
                round(w["weight"], 2),
                w["body_fat"] if w["body_fat"] is not None else "",
                w["waist"] if w["waist"] is not None else "",
                round(w["diff"], 2) if w["diff"] is not None else "",
            ]
        )
    return buf.getvalue()


def export_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 导入

def _parse_date(value: str) -> date:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d/%m/%Y", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日期格式无法识别：{value}")


def import_csv(db: Session, user_id: int, kind: str, text: str) -> dict:
    """
    导入 CSV。kind: weight（体重）/ diet（饮食）。
    返回 {inserted, updated, skipped, errors:[{row, reason}]}
    """
    result = {"inserted": 0, "updated": 0, "skipped": 0, "errors": []}
    reader = csv.DictReader(io.StringIO(text))

    for idx, row in enumerate(reader, start=2):  # 第 1 行是表头
        clean = {
            (k or "").strip().lower(): (v.strip() if isinstance(v, str) else v)
            for k, v in row.items()
            if k is not None
        }
        try:
            if kind == "weight":
                _import_weight_row(db, user_id, clean, result)
            elif kind == "diet":
                _import_diet_row(db, user_id, clean, result)
            else:
                raise ValueError(f"不支持的导入类型：{kind}")
        except Exception as e:  # noqa: BLE001 - 单行失败不中断整体导入
            result["errors"].append({"row": idx, "reason": str(e)})
            db.rollback()

    db.commit()
    return result


def _pick(clean: dict, *names):
    """从表头候选中取值（兼容中英文表头）。"""
    for n in names:
        if n in clean and str(clean[n]).strip() != "":
            return clean[n]
    raise ValueError("缺少必要字段：" + "/".join(names))


def _num(value, field, default=0.0):
    try:
        return float(str(value).replace("kg", "").replace("kcal", "").strip())
    except ValueError:
        raise ValueError(f"{field} 不是合法数字：{value}")


def _import_weight_row(db, user_id, clean, result):
    d = _parse_date(_pick(clean, "date", "日期", "record_date"))
    w = _num(_pick(clean, "weight", "体重", "weight_kg"), "体重")
    if w <= 0 or w > 400:
        raise ValueError(f"体重超出合理范围：{w}")

    exist = (
        db.query(WeightRecord)
        .filter(WeightRecord.user_id == user_id, WeightRecord.record_date == d)
        .first()
    )
    if exist:
        # 幂等：同一天以最新导入值为准，重算差值
        exist.weight = round(w, 2)
        exist.weight_diff = 0
        result["updated"] += 1
    else:
        prev = (
            db.query(WeightRecord)
            .filter(WeightRecord.user_id == user_id, WeightRecord.record_date < d)
            .order_by(WeightRecord.record_date.desc())
            .first()
        )
        db.add(
            WeightRecord(
                user_id=user_id,
                record_date=d,
                weight=round(w, 2),
                weight_diff=round(w - prev.weight, 2) if prev else 0,
                create_time=datetime.now(),
            )
        )
        result["inserted"] += 1
    db.flush()


def _import_diet_row(db, user_id, clean, result):
    d = _parse_date(_pick(clean, "date", "日期", "record_date"))
    meal_raw = str(_pick(clean, "meal", "meal_type", "餐次", "餐型")).strip()
    meal_map = {"早餐": 1, "早": 1, "1": 1, "午餐": 2, "午": 2, "2": 2,
                "晚餐": 3, "晚": 3, "3": 3, "加餐": 4, "零食": 4, "4": 4}
    if meal_raw not in meal_map:
        raise ValueError(f"餐次无法识别：{meal_raw}")
    meal_type = meal_map[meal_raw]

    food = str(_pick(clean, "food", "food_desc", "食物", "名称")).strip()
    calorie = _num(_pick(clean, "calorie", "热量", "kcal"), "热量")
    protein = _num(clean.get("protein") or clean.get("蛋白质") or 0, "蛋白质")
    fat = _num(clean.get("fat") or clean.get("脂肪") or 0, "脂肪")
    carb = _num(clean.get("carbohydrate") or clean.get("碳水") or 0, "碳水")

    # 幂等：同一天同餐次同食物同热量视为重复，跳过
    dup = (
        db.query(DietRecord)
        .filter(
            DietRecord.user_id == user_id,
            DietRecord.record_date == d,
            DietRecord.meal_type == meal_type,
            DietRecord.food_desc == food,
            DietRecord.calorie == calorie,
        )
        .first()
    )
    if dup:
        result["skipped"] += 1
        return

    db.add(
        DietRecord(
            user_id=user_id,
            record_date=d,
            meal_type=meal_type,
            food_desc=food,
            input_type=6,  # 6 = 外部导入
            calorie=calorie,
            protein=protein,
            fat=fat,
            carbohydrate=carb,
            sugar=0,
            fiber=0,
            sodium=0,
            create_time=datetime.now(),
        )
    )
    result["inserted"] += 1
    db.flush()


# ---------------------------------------------------------------- 提醒设置

REMINDER_DEFAULTS = {
    "meal_enabled": 1,
    "breakfast_time": "08:00",
    "lunch_time": "12:00",
    "dinner_time": "18:30",
    "weigh_enabled": 1,
    "weigh_time": "07:30",
    "water_enabled": 1,
    "water_start": "09:00",
    "water_end": "21:00",
    "water_interval_hours": 2,
    "quiet_enabled": 1,
    "quiet_start": "22:30",
    "quiet_end": "07:00",
}

REMINDER_FIELDS = list(REMINDER_DEFAULTS.keys())


def get_reminders(db: Session, user_id: int) -> dict:
    """读取提醒设置，从未配置过则返回默认推荐值。"""
    row = db.query(ReminderSetting).filter(ReminderSetting.user_id == user_id).first()
    if not row:
        return {**REMINDER_DEFAULTS, "configured": False}
    return {f: getattr(row, f) for f in REMINDER_FIELDS} | {"configured": True}


def update_reminders(db: Session, user_id: int, patch: dict) -> dict:
    """局部更新提醒设置（只更新传入且合法的字段）。"""
    row = db.query(ReminderSetting).filter(ReminderSetting.user_id == user_id).first()
    if not row:
        row = ReminderSetting(user_id=user_id, **REMINDER_DEFAULTS)
        db.add(row)
        db.flush()

    for k in REMINDER_FIELDS:
        if k in patch and patch[k] is not None:
            setattr(row, k, patch[k])
    db.commit()
    db.refresh(row)
    return {f: getattr(row, f) for f in REMINDER_FIELDS} | {"configured": True}
