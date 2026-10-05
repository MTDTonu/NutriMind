"""食物库路由。

注册顺序有意为之：字面路径（/search、/categories、/favorites、/quick-add）
必须排在 /{food_id} 之前，否则会被路径参数路由吃掉。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.db import get_db
from middleware.auth import get_current_user_id
from schemas.food import FoodCreate, QuickAddBody, FoodOut, FoodSearchItem, PortionOut
from services.food_service import (
    ensure_base_foods, list_categories, search_foods, get_food_detail,
    create_food, toggle_favorite, quick_add, top_used, list_categories as _cats,
)
from services.user_service import mark_checkin
from utils.common import resp

router = APIRouter(prefix="/api/v1/foods", tags=["食物库"])


@router.get("/categories")
def food_categories():
    """食物分类字典。"""
    return resp(200, "success", {"categories": list_categories()})


@router.get("/search")
def search(
    keyword: str = Query("", description="关键词，匹配名称/别名/品牌"),
    category: str = Query("", description="分类 key，空表示全部"),
    favorite: int = Query(0, description="1=仅看收藏"),
    limit: int = Query(30, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """食物搜索：结果已按「收藏 → 命中位置 → 使用频次」重排。"""
    items = search_foods(db, user_id, keyword, category, favorite == 1, limit)
    return resp(200, "success", {
        "items": [FoodSearchItem(**i) for i in items],
        "total": len(items),
    })


@router.get("/favorites")
def favorites(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """当前用户的常用食物。"""
    items = search_foods(db, user_id, "", "", True, 50)
    return resp(200, "success", {"items": [FoodSearchItem(**i) for i in items]})


@router.get("/frequent")
def frequent(
    limit: int = Query(8, ge=1, le=20),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """高频食物：首页快捷入口用。"""
    items = top_used(db, user_id, limit)
    return resp(200, "success", {"items": [FoodSearchItem(**i) for i in items]})


@router.post("/quick-add")
def quick_add_record(
    body: QuickAddBody,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """从食物库一键写入饮食记录（自动换算 nutrition = per100g * 克重 / 100）。"""
    from schemas.food import QuickAddOut
    from utils.common import parse_date

    data = quick_add(db, user_id, body)
    mark_checkin(db, user_id, parse_date(data["record_date"]))
    return resp(200, "success", QuickAddOut(**data).model_dump())


@router.post("/custom")
def create_custom(
    body: FoodCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """新建自定义食物（置信度 0.6，界面标注为「自估」）。"""
    food = create_food(db, user_id, body)
    return resp(200, "success", {"id": food.id, "name": food.name})


@router.get("/ensure-base")
def ensure_base(db: Session = Depends(get_db)):
    """幂等补齐内置食物库（幂等，可重复调用）。

    首次访问任一食物接口时会自动执行一次，这里额外暴露以便运维手动触发。
    """
    added = ensure_base_foods(db)
    return resp(200, "success", {"added": added})


@router.get("/{food_id}")
def detail(
    food_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """食物详情（含全部份量单位）。"""
    return resp(200, "success", FoodOut(**get_food_detail(db, user_id, food_id)).model_dump())


@router.post("/{food_id}/favorite")
def favorite(
    food_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """收藏 / 取消收藏。"""
    return resp(200, "success", toggle_favorite(db, user_id, food_id))
