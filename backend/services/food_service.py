"""食物库服务：搜索 / 详情 / 自定义 / 收藏 / 份量换算 / 一键入库。

三条硬约束：
1. 每条食物必须带 source 与 confidence，第三方数据与估算值不得冒充权威值。
2. 营养一律以「每 100g 可食部」存储，录入时按实际克重线性换算。
3. 用户自定义与第三方导入只对创建者可见，内置库全员可见。
"""
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from datetime import datetime

from data.foods_seed import iter_foods, CATEGORIES
from database.models import Food, FoodPortion, FoodFavorite, DietRecord
from utils.common import parse_date, today
from utils.exceptions import AppException


# ---------------------------------------------------------------- 内置库导入

def ensure_base_foods(db: Session) -> int:
    """幂等导入内置食物库。

    已存在的同名条目会被补齐份量，但**不会覆盖**已有营养值，
    避免把用户或第三方订正过的数据冲掉。

    Returns:
        int: 本次新增条目数。
    """
    added = 0
    existing_names = {row[0] for row in db.query(Food.name).filter(Food.source == "system").all()}

    for item in iter_foods():
        if item["name"] in existing_names:
            continue
        food = Food(
            name=item["name"],
            aliases=item["aliases"],
            category=item["category"],
            source=item["source"],
            calorie=item["calorie"],
            protein=item["protein"],
            fat=item["fat"],
            carbohydrate=item["carbohydrate"],
            sugar=item["sugar"],
            fiber=item["fiber"],
            sodium=item["sodium"],
            gi=item["gi"],
            confidence=item["confidence"],
        )
        db.add(food)
        db.flush()  # 拿到自增 id 再写份量
        for p in item["portions"]:
            db.add(
                FoodPortion(
                    food_id=food.id,
                    label=p["label"],
                    grams=p["grams"],
                    is_default=1 if p["is_default"] else 0,
                )
            )
        added += 1

    if added:
        db.commit()
    return added


def list_categories() -> list:
    """返回分类字典 [{key,label}]，user 分类单独追加。"""
    cats = [{"key": k, "label": v} for k, v in CATEGORIES.items()]
    cats.append({"key": "user", "label": "我的自定义"})
    return cats


# ---------------------------------------------------------------- 查询

def _visible_filter(user_id: int):
    """可见范围：内置库 + 自己创建的条目。"""
    return or_(Food.source == "system", Food.owner_user_id == user_id)


def _fav_ids(db: Session, user_id: int) -> set:
    rows = db.query(FoodFavorite.food_id).filter(FoodFavorite.user_id == user_id).all()
    return {r[0] for r in rows}


def _default_portion(db: Session, food_id: int):
    return (
        db.query(FoodPortion)
        .filter(FoodPortion.food_id == food_id)
        .order_by(FoodPortion.is_default.desc(), FoodPortion.grams)
        .first()
    )


def search_foods(
    db: Session,
    user_id: int,
    keyword: str = "",
    category: str = "",
    only_favorite: bool = False,
    limit: int = 30,
) -> list:
    """食物搜索。

    排序意图：**先给「用户大概率要找的」**，而不是按字母序。
    优先级依次为：收藏状态 → 名称完全命中 → 前缀命中 → 包含命中 → 使用频次。
    """
    q = db.query(Food).filter(_visible_filter(user_id))
    if category:
        q = q.filter(Food.category == category)

    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            or_(Food.name.like(like), Food.aliases.like(like), Food.brand.like(like))
        )

    if only_favorite:
        q = q.join(FoodFavorite, FoodFavorite.food_id == Food.id).filter(
            FoodFavorite.user_id == user_id
        )

    foods = q.limit(limit * 4).all()  # 多取一些再做 Python 侧重排
    fav = _fav_ids(db, user_id)

    def rank(f: Food):
        name = f.name
        if kw:
            hit_exact = 0 if name == kw else 1
            hit_prefix = 0 if name.startswith(kw) else 1
        else:
            hit_exact = hit_prefix = 0
        return (0 if f.id in fav else 1, hit_exact, hit_prefix, -f.use_count, len(name))

    foods.sort(key=rank)

    result = []
    for f in foods[:limit]:
        portion = _default_portion(db, f.id)
        result.append(
            {
                "id": f.id,
                "name": f.name,
                "category": f.category,
                "category_label": CATEGORIES.get(f.category, f.category),
                "source": f.source,
                "confidence": f.confidence,
                "calorie": f.calorie,
                "protein": f.protein,
                "fat": f.fat,
                "carbohydrate": f.carbohydrate,
                "default_portion_label": portion.label if portion else "100 克",
                "default_portion_grams": portion.grams if portion else 100.0,
                "use_count": f.use_count,
                "favorited": 1 if f.id in fav else 0,
            }
        )
    return result


def get_food(db: Session, user_id: int, food_id: int) -> Food:
    """按 id 取食物（含可见性校验）。"""
    food = db.query(Food).filter(Food.id == food_id, _visible_filter(user_id)).first()
    if not food:
        raise AppException(404, "食物不存在或无权访问")
    return food


def get_food_detail(db: Session, user_id: int, food_id: int) -> dict:
    """食物详情：营养 + 全部份量 + 收藏状态。"""
    food = get_food(db, user_id, food_id)
    portions = (
        db.query(FoodPortion)
        .filter(FoodPortion.food_id == food_id)
        .order_by(FoodPortion.is_default.desc(), FoodPortion.grams)
        .all()
    )
    data = {
        "id": food.id,
        "name": food.name,
        "aliases": food.aliases,
        "category": food.category,
        "category_label": CATEGORIES.get(food.category, food.category),
        "source": food.source,
        "confidence": food.confidence,
        "brand": food.brand,
        "barcode": food.barcode,
        "owner_user_id": food.owner_user_id,
        "calorie": food.calorie,
        "protein": food.protein,
        "fat": food.fat,
        "carbohydrate": food.carbohydrate,
        "sugar": food.sugar,
        "fiber": food.fiber,
        "sodium": food.sodium,
        "gi": food.gi,
        "use_count": food.use_count,
        "portions": [
            {
                "id": p.id,
                "label": p.label,
                "grams": p.grams,
                "is_default": p.is_default,
            }
            for p in portions
        ],
        "favorited": 1 if food.id in _fav_ids(db, user_id) else 0,
    }
    return data


# ---------------------------------------------------------------- 自定义

def create_food(db: Session, user_id: int, body) -> Food:
    """创建用户自定义食物。

    用户自填数据的置信度给 0.6（低于内置库的 0.85），
    界面据此展示「自估」标记，避免用户把估算当成权威。
    """
    dup = db.query(Food).filter(Food.name == body.name, Food.owner_user_id == user_id).first()
    if dup:
        raise AppException(400, f"已存在同名自定义食物：{body.name}")

    food = Food(
        name=body.name,
        aliases=body.aliases,
        category="user" if body.category == "user" else body.category,
        source="user",
        owner_user_id=user_id,
        brand=body.brand,
        barcode=body.barcode,
        calorie=body.calorie,
        protein=body.protein,
        fat=body.fat,
        carbohydrate=body.carbohydrate,
        sugar=body.sugar,
        fiber=body.fiber,
        sodium=body.sodium,
        gi=body.gi,
        confidence=0.6,
    )
    db.add(food)
    db.flush()
    if body.portion_label and body.portion_grams:
        db.add(
            FoodPortion(
                food_id=food.id,
                label=body.portion_label,
                grams=body.portion_grams,
                is_default=1,
            )
        )
    db.add(FoodPortion(food_id=food.id, label="100 克", grams=100, is_default=0))
    db.commit()
    db.refresh(food)
    return food


# ---------------------------------------------------------------- 收藏

def toggle_favorite(db: Session, user_id: int, food_id: int) -> dict:
    """收藏 / 取消收藏，返回最新状态。"""
    get_food(db, user_id, food_id)  # 顺带校验可见性
    fav = (
        db.query(FoodFavorite)
        .filter(FoodFavorite.user_id == user_id, FoodFavorite.food_id == food_id)
        .first()
    )
    if fav:
        db.delete(fav)
        db.commit()
        return {"food_id": food_id, "favorited": 0}

    db.add(FoodFavorite(user_id=user_id, food_id=food_id))
    db.commit()
    return {"food_id": food_id, "favorited": 1}


# ---------------------------------------------------------------- 换算与入库

def resolve_grams(db: Session, food_id: int, body) -> tuple:
    """把「份量 / 克重 / 份数」解析为最终克重。

    Returns:
        (grams, portion_label, quantity)
    """
    portion_label = None
    if body.portion_id:
        portion = (
            db.query(FoodPortion)
            .filter(FoodPortion.id == body.portion_id, FoodPortion.food_id == food_id)
            .first()
        )
        if not portion:
            raise AppException(404, "份量单位不存在")
        per = portion.grams
        portion_label = portion.label
    elif body.grams:
        per = body.grams
        portion_label = "自定义克重"
    else:
        portion = _default_portion(db, food_id)
        per = portion.grams if portion else 100.0
        portion_label = portion.label if portion else "100 克"

    quantity = float(body.quantity or 1)
    grams = round(per * quantity, 1)
    return grams, portion_label, quantity


def _scale(value: float, grams: float) -> float:
    """每 100g -> 实际克重换算，保留 1 位小数。"""
    return round(value * grams / 100.0, 2)


def quick_add(db: Session, user_id: int, body) -> dict:
    """按「食物 + 份量 + 份数」写入一条饮食记录。

    换算过程随结果返回，界面必须展示「2 碗米饭 ≈ 400g」这类证据，
    让用户看得见热量是怎么算出来的。
    """
    food = get_food(db, user_id, body.food_id)
    grams, portion_label, quantity = resolve_grams(db, body.food_id, body)
    d = parse_date(body.record_date) if body.record_date else today()

    quantity_desc = f"{quantity:g}" if quantity != 1 else ""
    portion_desc = portion_label or f"{grams:g} 克"
    if quantity != 1:
        food_desc = f"{food.name}（{quantity_desc} × {portion_desc}）"
    else:
        food_desc = f"{food.name}（{portion_desc}）"

    rec = DietRecord(
        user_id=user_id,
        record_date=d,
        meal_type=body.meal_type,
        food_desc=food_desc,
        food_image_path=body.food_image_path,
        # 输入方式沿用既有约定：3 = 食物库快捷录入
        input_type=3,
        calorie=_scale(food.calorie, grams),
        protein=_scale(food.protein, grams),
        fat=_scale(food.fat, grams),
        carbohydrate=_scale(food.carbohydrate, grams),
        sugar=_scale(food.sugar, grams),
        fiber=_scale(food.fiber, grams),
        sodium=_scale(food.sodium, grams),
    )
    db.add(rec)

    # 使用频次 +1，让搜索越用越准
    food.use_count = (food.use_count or 0) + 1
    db.commit()
    db.refresh(rec)

    return {
        "id": rec.id,
        "record_date": rec.record_date.strftime("%Y-%m-%d"),
        "meal_type": rec.meal_type,
        "food_desc": rec.food_desc,
        "input_type": rec.input_type,
        "calorie": rec.calorie,
        "protein": rec.protein,
        "fat": rec.fat,
        "carbohydrate": rec.carbohydrate,
        "sugar": rec.sugar,
        "fiber": rec.fiber,
        "sodium": rec.sodium,
        "food_image_path": rec.food_image_path,
        "create_time": rec.create_time,
        "food_id": food.id,
        "grams": grams,
        "quantity": quantity,
        "portion_label": portion_label,
    }


def top_used(db: Session, user_id: int, limit: int = 8) -> list:
    """高频使用的食物（首页快捷入口）。"""
    foods = (
        db.query(Food)
        .filter(_visible_filter(user_id), Food.use_count > 0)
        .order_by(Food.use_count.desc())
        .limit(limit)
        .all()
    )
    return search_foods(db, user_id, limit=limit) if not foods else [
        {
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "category_label": CATEGORIES.get(f.category, f.category),
            "source": f.source,
            "confidence": f.confidence,
            "calorie": f.calorie,
            "protein": f.protein,
            "fat": f.fat,
            "carbohydrate": f.carbohydrate,
            "default_portion_label": (
                _default_portion(db, f.id).label if _default_portion(db, f.id) else "100 克"
            ),
            "default_portion_grams": (
                _default_portion(db, f.id).grams if _default_portion(db, f.id) else 100.0
            ),
            "use_count": f.use_count,
            "favorited": 1 if f.id in _fav_ids(db, user_id) else 0,
        }
        for f in foods
    ]
