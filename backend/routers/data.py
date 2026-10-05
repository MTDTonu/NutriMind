"""数据路由：导出 / 导入 / 提醒设置。

导出走文件下载（Content-Disposition），不走统一的 resp 包装，
否则前端拿到的是 JSON 包装体而不是可直接打开的文件。
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query, Response
from sqlalchemy.orm import Session

from database.db import get_db
from middleware.auth import get_current_user_id
from services import data_service
from services.auth_service import get_current_user
from schemas.data import ReminderUpdate
from utils.common import resp

router = APIRouter(prefix="/api/v1/data", tags=["数据"])

_MAX_IMPORT_BYTES = 2 * 1024 * 1024  # 2MB，足以覆盖数万行 CSV


@router.get("/export")
def export_data(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    format: str = Query("csv", pattern="^(csv|json)$"),
    days: int = Query(0, ge=0, le=3650),
):
    """导出个人数据。format=csv（饮食明细+体重）/ json（全量数据包）。"""
    user = get_current_user(db, user_id)
    payload = data_service.build_export(db, user, days)

    stamp = payload["meta"]["exported_at"][:10]
    if format == "json":
        body = data_service.export_json(payload)
        filename = f"nutrimind-{user.username}-{stamp}.json"
        media = "application/json; charset=utf-8"
    else:
        # BOM：Excel 打开 UTF-8 CSV 才不会乱码（尤其是中文表头）
        body = "\ufeff" + data_service.export_csv(payload)
        filename = f"nutrimind-{user.username}-{stamp}.csv"
        media = "text/csv; charset=utf-8"

    return Response(
        content=body.encode("utf-8"),
        media_type=media,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "X-Export-Counts": str(payload["meta"]["counts"]),
        },
    )


@router.post("/import")
async def import_data(
    kind: str = Query("weight", pattern="^(weight|diet)$"),
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """导入 CSV。

    weight 需要表头：日期, 体重（可选 体脂率/腰围）
    diet   需要表头：日期, 餐次, 食物, 热量（可选 蛋白质/脂肪/碳水）
    同一天重复导入不会产生重复记录。
    """
    get_current_user(db, user_id)

    raw = await file.read()
    if len(raw) > _MAX_IMPORT_BYTES:
        return resp(400, "文件过大，请拆分后再试（单次 ≤ 2MB）", None)

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return resp(400, "文件编码不是 UTF-8，请另存为 UTF-8 后重试", None)

    result = data_service.import_csv(db, user_id, kind, text)
    msg = f"导入完成：新增 {result['inserted']} 条"
    if result["updated"]:
        msg += f"，更新 {result['updated']} 条"
    if result["skipped"]:
        msg += f"，跳过重复 {result['skipped']} 条"
    if result["errors"]:
        msg += f"，{len(result['errors'])} 行失败"
    return resp(200, msg, result)


@router.get("/reminders")
def get_reminders(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """读取提醒设置（未配置过返回推荐默认值）。"""
    return resp(200, "success", data_service.get_reminders(db, user_id))


@router.put("/reminders")
def update_reminders(
    body: ReminderUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """局部更新提醒设置。"""
    patch = body.model_dump(exclude_unset=True)
    data = data_service.update_reminders(db, user_id, patch)
    return resp(200, "已保存提醒设置", data)
