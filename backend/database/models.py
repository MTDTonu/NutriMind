"""全部 ORM 模型定义。

核心业务表：
1. user            用户信息 + 代谢指标
2. diet_record     饮食记录
3. weight_record   体重记录（按天唯一，计算差值）
4. ai_diet_plan    AI 生成的一日减脂食谱
5. exercise_record 运动记录
6. water_record    饮水记录（按天唯一，累加）
7. user_checkin    用户打卡（连续天数）
8. user_ai_settings 用户大模型配置（文字 / 视觉 / 语音三套）

食物数据引擎（阶段 1）：
9.  food           食物库（内置 / 用户自定义 / 第三方导入，统一带来源与置信度）
10. food_portion   份量单位（一碗 / 一个 / 一份，含克重）
11. food_favorite  用户常用食物（快捷入口排序依据）
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, Date, DateTime, ForeignKey, UniqueConstraint,
)
from datetime import datetime

from database.db import Base


class User(Base):
    """用户表：保存基础体征信息与计算得到的代谢指标。"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    # 性别：0 女 / 1 男
    gender = Column(Integer, nullable=False)
    age = Column(Integer, nullable=False)
    height = Column(Float, nullable=False)
    current_weight = Column(Float, nullable=False)
    target_weight = Column(Float, nullable=False)
    # 活动水平：1 久坐1.2 / 2 轻度1.375 / 3 中度1.55 / 4 重度1.725
    activity_level = Column(Integer, nullable=False)
    # 基础代谢率（BMR）
    bmr = Column(Float, nullable=False)
    # 每日总消耗（TDEE）
    tdee = Column(Float, nullable=False)
    # 推荐每日摄入热量（TDEE - 400，不低于 BMR）
    recommend_calorie = Column(Float, nullable=False)
    # ---- 智能目标引擎（阶段 2）----
    # 由「热量收支 + 体重变化」反推出的真实 TDEE（kcal/日），未校准前为空
    tdee_adaptive = Column(Float, nullable=True)
    # 上次执行周校准的日期
    last_calibrate_at = Column(Date, nullable=True)
    # 目标模式：deficit=按热量缺口 / rate=按每周减重速率
    target_mode = Column(String(20), nullable=False, default="deficit")
    # 每周减重目标（kg），target_mode='rate' 时生效，推荐 0.25~1.0
    target_rate = Column(Float, nullable=True)
    # 每日热量缺口（kcal），target_mode='deficit' 时生效
    target_deficit = Column(Float, nullable=True)
    # 饮食偏好（JSON 字符串，可空）
    diet_preference = Column(Text, nullable=True)
    # 忌口 / 过敏（纯文本，可空）
    diet_avoid = Column(Text, nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DietRecord(Base):
    """饮食记录表：每餐一条记录。"""
    __tablename__ = "diet_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    # 记录日期
    record_date = Column(Date, index=True, nullable=False)
    # 餐型：1 早 / 2 午 / 3 晚 / 4 加餐
    meal_type = Column(Integer, nullable=False)
    # 食物描述
    food_desc = Column(Text, nullable=False)
    # 食物图片路径（可空）
    food_image_path = Column(String(255), nullable=True)
    # 录入方式：1 文字 / 2 图片
    input_type = Column(Integer, nullable=False)
    calorie = Column(Float, nullable=False)
    protein = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)
    carbohydrate = Column(Float, nullable=False)
    sugar = Column(Float, nullable=False)
    fiber = Column(Float, nullable=False)
    sodium = Column(Float, nullable=False)
    create_time = Column(DateTime, default=datetime.now)


class WeightRecord(Base):
    """体重记录表：同一天只保留最新，新增时计算与上一记录的差值。"""
    __tablename__ = "weight_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    # 记录日期（与 user_id 联合唯一）
    record_date = Column(Date, index=True, nullable=False)
    weight = Column(Float, nullable=False)
    # 体脂率（可空）
    body_fat = Column(Float, nullable=True)
    # 腰围（可空）
    waist = Column(Float, nullable=True)
    # 与上一条记录的差值
    weight_diff = Column(Float, nullable=False)
    remark = Column(String(255), nullable=True)
    create_time = Column(DateTime, default=datetime.now)

    # 联合唯一约束（用户 + 日期）：同一天只保留一条最新记录
    __table_args__ = (
        UniqueConstraint("user_id", "record_date", name="uq_weight_user_date"),
    )


class AiDietPlan(Base):
    """AI 生成的一日减脂食谱表。"""
    __tablename__ = "ai_diet_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    plan_date = Column(Date, index=True, nullable=False)
    # 早餐（JSON 字符串）
    breakfast = Column(Text, nullable=False)
    lunch = Column(Text, nullable=False)
    dinner = Column(Text, nullable=False)
    total_calorie = Column(Float, nullable=False)
    # 方案说明（可空）
    adapt_desc = Column(String(255), nullable=True)
    create_time = Column(DateTime, default=datetime.now)


class ExerciseRecord(Base):
    """运动记录表。"""
    __tablename__ = "exercise_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)
    exercise_type = Column(String(50), nullable=False)
    # 时长（分钟）
    duration = Column(Integer, nullable=False)
    # 消耗热量
    calorie_burn = Column(Float, nullable=False)
    create_time = Column(DateTime, default=datetime.now)


class WaterRecord(Base):
    """饮水记录表：同一天累加，目标量 = 体重 * 35ml。"""
    __tablename__ = "water_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    # 记录日期（与 user_id 联合唯一）
    record_date = Column(Date, index=True, nullable=False)
    # 当日累计饮水量（ml）
    total_amount = Column(Integer, nullable=False)
    # 目标饮水量（ml）
    target_amount = Column(Integer, nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    # 联合唯一约束（用户 + 日期）：同一天累加同一条记录
    __table_args__ = (
        UniqueConstraint("user_id", "record_date", name="uq_water_user_date"),
    )


class UserCheckin(Base):
    """用户打卡表：记录连续打卡天数。"""
    __tablename__ = "user_checkin"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    checkin_date = Column(Date, nullable=False)
    # 连续打卡天数
    continuous_days = Column(Integer, nullable=False)
    # 状态：1 正常
    status = Column(Integer, nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    # 联合唯一约束（用户 + 日期）
    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_checkin_user_date"),
    )


class UserAISettings(Base):
    """用户大模型配置：文字 / 视觉理解 / 语言转文字 三套独立配置。

    每套能力各自选国内厂商（provider）+ 填 Key + 填模型名（model）；
    custom 厂商额外填 base_url。三套可混搭不同厂商。
    该表是关键个性化配置，由「我的」页维护，并同步写 .env。
    """
    __tablename__ = "user_ai_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 与 user 一对一
    user_id = Column(Integer, ForeignKey("user.id"), unique=True, index=True, nullable=False)

    # 文字（对话 / 食谱 / 复盘）
    text_provider = Column(String(30), nullable=True)
    text_api_key = Column(Text, nullable=True)
    text_model = Column(String(80), nullable=True)
    text_base_url = Column(Text, nullable=True)

    # 视觉理解（食物图片识别等）
    vision_provider = Column(String(30), nullable=True)
    vision_api_key = Column(Text, nullable=True)
    vision_model = Column(String(80), nullable=True)
    vision_base_url = Column(Text, nullable=True)

    # 语言转文字（ASR）——当前识别引擎为浏览器内置 Web Speech API，
    # 这里的配置作为服务端 ASR 的预留，后续可按厂商接入。
    asr_provider = Column(String(30), nullable=True)
    asr_api_key = Column(Text, nullable=True)
    asr_model = Column(String(80), nullable=True)
    asr_base_url = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# =============================================================
#  食物数据引擎
# =============================================================


class Food(Base):
    """食物库。

    设计要点：
    - 一表承载三种来源：system（内置）/ user（用户自定义）/ off|usda（第三方导入）。
      来源与置信度必须原样带到界面，禁止把估算值冒充权威值。
    - 所有营养字段均为「每 100g 可食部」，录入时按份量克重换算，避免口径混乱。
    - use_count 用于搜索排序：被选中过的食物排前面，越用越准。
    """
    __tablename__ = "food"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), nullable=False, index=True)
    # 别名 / 俗称，逗号分隔，参与模糊搜索
    aliases = Column(String(255), nullable=True)
    # 分类 key（staple / protein / veg ...），标签字典见 data.foods_seed.CATEGORIES
    category = Column(String(20), nullable=False, index=True)
    # 来源：system / user / off / usda
    source = Column(String(20), nullable=False, default="system", index=True)
    # 自定义食物的归属用户（system 来源为空）
    owner_user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    # 品牌（第三方导入或用户自定义时填写）
    brand = Column(String(80), nullable=True)
    barcode = Column(String(40), nullable=True, index=True)

    # ---- 每 100g 可食部营养 ----
    calorie = Column(Float, nullable=False)
    protein = Column(Float, nullable=False, default=0)
    fat = Column(Float, nullable=False, default=0)
    carbohydrate = Column(Float, nullable=False, default=0)
    sugar = Column(Float, nullable=False, default=0)
    fiber = Column(Float, nullable=False, default=0)
    # 钠（mg / 100g）
    sodium = Column(Float, nullable=False, default=0)
    # 升糖指数，可空表示无可靠数据
    gi = Column(Integer, nullable=True)

    # 数据置信度 0~1：内置 0.85 / 用户自填 0.6 / 第三方按源给
    confidence = Column(Float, nullable=False, default=0.85)
    # 被引用次数（搜索排序权重）
    use_count = Column(Integer, nullable=False, default=0)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FoodPortion(Base):
    """食物份量单位：把「一碗 / 一个 / 一份」落成确定的克重。"""
    __tablename__ = "food_portion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(Integer, ForeignKey("food.id"), index=True, nullable=False)
    label = Column(String(30), nullable=False)
    grams = Column(Float, nullable=False)
    is_default = Column(Integer, nullable=False, default=0)


class FoodFavorite(Base):
    """用户常用食物：快捷入口 + 搜索加权。"""
    __tablename__ = "food_favorite"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    food_id = Column(Integer, ForeignKey("food.id"), index=True, nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "food_id", name="uq_fav_user_food"),
    )


class ReminderSetting(Base):
    """提醒设置：三餐 / 称重 / 饮水提醒与免打扰时段。

    时间字段统一存 "HH:MM" 字符串，避免 SQLite 时间类型带来的时区困扰。
    """
    __tablename__ = "reminder_setting"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False, unique=True)

    # 三餐提醒
    meal_enabled = Column(Integer, nullable=False, default=1)
    breakfast_time = Column(String(5), nullable=False, default="08:00")
    lunch_time = Column(String(5), nullable=False, default="12:00")
    dinner_time = Column(String(5), nullable=False, default="18:30")

    # 称重提醒（晨起空腹称重最稳定）
    weigh_enabled = Column(Integer, nullable=False, default=1)
    weigh_time = Column(String(5), nullable=False, default="07:30")

    # 饮水提醒
    water_enabled = Column(Integer, nullable=False, default=1)
    water_start = Column(String(5), nullable=False, default="09:00")
    water_end = Column(String(5), nullable=False, default="21:00")
    water_interval_hours = Column(Integer, nullable=False, default=2)

    # 免打扰时段
    quiet_enabled = Column(Integer, nullable=False, default=1)
    quiet_start = Column(String(5), nullable=False, default="22:30")
    quiet_end = Column(String(5), nullable=False, default="07:00")

    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# =============================================================
#  提醒触达（后台推送）
# =============================================================


class PushSubscription(Base):
    """Web Push 订阅。

    浏览器调 `pushManager.subscribe()` 拿到 endpoint 与两把钥匙（p256dh / auth），
    上报到这里后，服务端就能在**页面关闭时**把提醒推到系统通知中心。

    endpoint 全局唯一且带索引：重复订阅同一台设备只会更新行，不会堆积。
    失效的订阅（推送服务返回 404/410）在发送失败时直接删除，避免无效重试。
    """
    __tablename__ = "push_subscription"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    # 推送服务的回调地址（含订阅标识），天然唯一
    endpoint = Column(Text, nullable=False, unique=True, index=True)
    # 客户端公钥（用于加密载荷）
    p256dh = Column(String(255), nullable=False)
    # 鉴权密钥
    auth = Column(String(255), nullable=False)
    user_agent = Column(String(255), nullable=True)
    enabled = Column(Integer, nullable=False, default=1)
    fail_count = Column(Integer, nullable=False, default=0)
    last_sent_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.now)


class ReminderLog(Base):
    """提醒触发记录：服务端去重的唯一依据。

    唯一约束（用户 + 日期 + 提醒槽位 + 通道）保证「同一天同一条提醒只发一次」，
    服务重启也不会重复轰炸——这比把去重状态放在内存里可靠得多。
    """
    __tablename__ = "reminder_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    fire_date = Column(Date, index=True, nullable=False)
    # 提醒槽位 key： breakfast / lunch / dinner / weigh / water-0900 ...
    slot_key = Column(String(40), nullable=False)
    channel = Column(String(20), nullable=False, default="push")
    sent_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "fire_date", "slot_key", "channel", name="uq_reminder_fire"),
    )


# =============================================================
#  AI 会话历史（服务端化）
# =============================================================


class AiChatSession(Base):
    """AI 对话会话：跨设备、跨刷新持久化的对话容器。

    对外暴露 sid（uuid4 hex）而非自增 id，避免顺序 id 泄露用户规模。
    updated_at 随每次新消息自动刷新，列表按它倒序展示「最近对话」。
    """

    __tablename__ = "ai_chat_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sid = Column(String(40), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    title = Column(String(100), nullable=False, default="新对话")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AiChatMessage(Base):
    """会话内的单条消息。

    role 为 user / assistant；image 仅用户消息可能有（食物图片的 data URL 缩略图）。
    seq 保证同会话内顺序稳定（即便同秒插入也不乱序）。
    """

    __tablename__ = "ai_chat_message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_sid = Column(String(40), ForeignKey("ai_chat_session.sid"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    image = Column(Text, nullable=True)
    seq = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now)


class UserMemory(Base):
    """用户长期记忆：跨会话保留的个人信息与偏好，每次提问自动注入 system prompt。"""

    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    text = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "text", name="uq_user_memory"),
    )


# =============================================================
#  写入幂等（重复提交去重）
# =============================================================


class RequestIdempotency(Base):
    """写入请求幂等记录：以客户端生成的 X-Idempotency-Key 为唯一键。

    同 key 的重复提交（网络重试 / 离线补发 / 手抖双点）只会真正执行一次，
    其余直接回放首次的响应。status 区分 processing / done；expires_at 过期后记录失效，
    允许同 key 再次执行（一般 24h 内视为同一动作）。
    """

    __tablename__ = "request_idempotency"

    key = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    path = Column(String(200), nullable=False)
    status = Column(String(10), nullable=False, default="processing")
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
