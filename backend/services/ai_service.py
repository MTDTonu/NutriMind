"""AI 服务：封装多厂商大模型调用（智谱 / 百炼 / 豆包 / 文心 / 自定义）。

职责：
- 图片识别（视觉理解模型）：识别食物并估算营养。
- 食谱生成（文字模型）：根据用户情况生成一日减脂食谱并落库。
- 对话（文字模型）：结合用户上下文的多轮对话。
- 每日复盘（文字模型）：根据当日饮食汇总生成 ≤300 字复盘。

配置来源：
- 调用方（路由层）从数据库 user_ai_settings 读取用户配置（provider/api_key/model），
  以 dict 形式传入各方法（cfg）。无配置时退回环境变量 ZHIPU_API_KEY（兼容老用法）。
- 语言转文字（ASR）由前端浏览器 Web Speech API 完成，后端不实现。

统一要求：
- 超时 90s（食谱等长文本任务实测 30~40s，太短会触发重试假死）。
- 异常统一抛 AppException，由路由层转 SSE error 或 500。
"""
import json
import base64

from utils.exceptions import AppException
from services.llm_dispatch import complete, stream_complete


# ---------- 提示词（必须原样使用）----------

RECOGNIZE_PROMPT = (
    "你是专业营养师，识别图片中的食物，估算每种食物的份量与数量，计算对应的营养数据。"
    "必须严格返回JSON格式，不要任何多余文字，格式如下："
    "{\"food_list\":[{\"name\":\"食物名称\",\"quantity\":1,\"weight\":100,\"calorie\":110,"
    "\"protein\":3.5,\"fat\":0.5,\"carbohydrate\":25,\"sugar\":2,\"fiber\":1.2,\"sodium\":5}],"
    "\"total_calorie\":总热量}。"
    "关于 quantity：表示数量（个/只/片/份），无法判断时填 1；"
    "若图中同一种食物有多个（例如 3 个鸡蛋），必须把数量写进 quantity，且 weight/热量等为该条的总量，"
    "不要因为同名就合并计为 1。"
    "同类食物但做法不同（如煎蛋与煮蛋）应各自单独成条。"
    "注意：分量估算要符合中国居民日常饮食实际，营养数据准确。"
)

# 食谱生成提示词模板，使用 {占位符} 替换
PLAN_PROMPT_TEMPLATE = (
    "你是注册营养师，根据用户情况生成一日减脂食谱。用户信息："
    "- 性别：{gender}- 年龄：{age}岁- 身高：{height}cm- 体重：{weight}kg"
    "- 每日推荐摄入热量：{recommend_calorie}kcal- 饮食偏好：{diet_preference}"
    "- 当日已摄入热量：{eaten_calorie}kcal。"
    "要求：1.生成早中晚三餐，总热量接近推荐值，误差不超过100kcal "
    "2.食材常见，做法简单，符合中国饮食习惯 "
    "3.蛋白质充足，脂肪适量，碳水合理 "
    "4.必须严格返回JSON格式，不要多余文字，格式如下："
    "{\"breakfast\":[{\"name\":\"\",\"weight\":\"\",\"calorie\":0,\"practice\":\"\"}],"
    "\"lunch\":[...],\"dinner\":[...],\"total_calorie\":0,\"adapt_desc\":\"方案说明\"}"
)


class AIService:
    """多厂商 AI 服务。配置由调用方以 cfg dict 传入，本类无状态依赖 Key。"""

    # ---------- 视觉理解：食物识别 ----------
    def recognize_food(self, image_bytes: bytes, mime: str, cfg: dict = None) -> dict:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime};base64,{b64}"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": RECOGNIZE_PROMPT},
                ],
            }
        ]
        text = complete(cfg, messages, cap="视觉理解")
        return self._parse_json(text)

    # ---------- 文字：食谱生成 ----------
    def generate_plan(self, db, user, target_date, eaten_calorie: float, cfg: dict = None) -> dict:
        prompt = (
            PLAN_PROMPT_TEMPLATE
            .replace("{gender}", "男" if user.gender == 1 else "女")
            .replace("{age}", str(user.age))
            .replace("{height}", str(user.height))
            .replace("{weight}", str(user.current_weight))
            .replace("{recommend_calorie}", str(user.recommend_calorie))
            .replace("{diet_preference}", user.diet_preference or "无")
            .replace("{eaten_calorie}", str(round(eaten_calorie, 1)))
        )
        messages = [{"role": "user", "content": prompt}]

        # AI 不可用时降级为本地通用食谱，保证接口始终可用
        try:
            text = complete(cfg, messages, cap="文字")
            data = self._parse_json(text)
        except Exception as e:  # noqa: BLE001
            # 记录降级原因，避免「静默吞异常」导致问题无迹可寻
            import logging
            logging.getLogger("ai_service").warning("食谱生成降级为本地方案：%s", e)
            data = self._local_plan(user)

        breakfast = data.get("breakfast", [])
        lunch = data.get("lunch", [])
        dinner = data.get("dinner", [])
        total = data.get("total_calorie", 0)
        adapt = data.get("adapt_desc", "")

        from database.models import AiDietPlan
        # 同一天重新生成时 upsert，避免每次「重新生成」都新增一行导致表无限膨胀
        exist = db.query(AiDietPlan).filter(
            AiDietPlan.user_id == user.id,
            AiDietPlan.plan_date == target_date,
        ).first()
        if exist:
            exist.breakfast = json.dumps(breakfast, ensure_ascii=False)
            exist.lunch = json.dumps(lunch, ensure_ascii=False)
            exist.dinner = json.dumps(dinner, ensure_ascii=False)
            exist.total_calorie = float(total)
            exist.adapt_desc = adapt
            plan = exist
        else:
            plan = AiDietPlan(
                user_id=user.id,
                plan_date=target_date,
                breakfast=json.dumps(breakfast, ensure_ascii=False),
                lunch=json.dumps(lunch, ensure_ascii=False),
                dinner=json.dumps(dinner, ensure_ascii=False),
                total_calorie=float(total),
                adapt_desc=adapt,
            )
            db.add(plan)
        db.commit()
        db.refresh(plan)

        return {
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
            "total_calorie": float(total),
            "adapt_desc": adapt,
        }

    # ---------- 文字：多轮对话（一次性）----------
    def chat(self, user, message: str, history: list = None, memories: list = None, cfg: dict = None, brief: dict = None) -> str:
        messages = self.build_chat_messages(user, message, history, memories, brief)
        return complete(cfg, messages, cap="文字").strip()

    # ---------- 文字：多轮对话（流式）----------
    def chat_stream(self, user, message: str, history: list = None, memories: list = None, cfg: dict = None, brief: dict = None):
        messages = self.build_chat_messages(user, message, history, memories, brief)
        yield from stream_complete(cfg, messages, cap="文字")

    # ---------- 文字：每日复盘 ----------
    def daily_review(self, db, user_id: int, target_date, cfg: dict = None) -> str:
        from database.models import DietRecord, User
        from sqlalchemy import func
        recs = db.query(DietRecord).filter(
            DietRecord.user_id == user_id, DietRecord.record_date == target_date
        ).all()
        if not recs:
            return "今日暂无饮食记录，建议从记录一日三餐开始，逐步建立健康的减脂饮食习惯。"

        intake = sum(r.calorie for r in recs)
        protein = sum(r.protein for r in recs)
        fat = sum(r.fat for r in recs)
        carb = sum(r.carbohydrate for r in recs)
        sugar = sum(r.sugar for r in recs)
        fiber = sum(r.fiber for r in recs)
        sodium = sum(r.sodium for r in recs)
        user = db.query(User).filter(User.id == user_id).first()
        recommend = user.recommend_calorie if user else 0

        prompt = (
            f"你是营养师。以下是用户{target_date.strftime('%Y-%m-%d')}的饮食记录汇总："
            f"总热量{round(intake,1)}kcal，蛋白质{round(protein,1)}g，脂肪{round(fat,1)}g，"
            f"碳水{round(carb,1)}g，糖{round(sugar,1)}g，纤维{round(fiber,1)}g，钠{round(sodium,1)}mg，"
            f"当日推荐摄入{recommend}kcal。"
            f"请生成不超过300字的中文复盘，包含：1.今日饮食优点 2.不足 3.明日改进建议。只输出复盘正文，不要多余解释。"
        )
        text = complete(cfg, [{"role": "user", "content": prompt}], cap="文字")
        return text.strip()[:300]

    # ---------- 公共：构造对话消息体 ----------
    def build_chat_messages(
        self, user, message: str, history: list = None, memories: list = None, brief: dict = None
    ) -> list:
        system = self._build_chat_system(user)
        mem_list = [str(m).strip()[:120] for m in (memories or []) if str(m).strip()][:20]
        if mem_list:
            system += (
                "\n\n以下是用户长期记忆（跨会话保存的个人信息与偏好，请结合这些内容回答，"
                "但不要逐条复述）：\n- " + "\n- ".join(mem_list)
            )
        # 今日实况：让建议落在「今天吃了什么」上，而不是泛泛而谈
        brief_text = (brief or {}).get("text") if isinstance(brief, dict) else None
        if brief_text:
            system += (
                "\n\n以下是用户今日实况（真实记录，优先依据这些数据作答；"
                "用户问「今天」「现在」相关问题时直接引用，不要反问用户吃了什么）：\n"
                + brief_text
            )
        messages = [{"role": "system", "content": system}]
        for h in (history or []):
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append({"role": h["role"], "content": str(h["content"])})
        messages.append({"role": "user", "content": message})
        return messages

    # ---------- 本地兜底食谱 ----------
    _FALLBACK_PLAN = {
        "breakfast": [
            {"name": "燕麦粥（燕麦 50g）", "ratio": 0.11, "practice": "燕麦加水煮 3 分钟，可加少许脱脂牛奶"},
            {"name": "水煮蛋 1 个", "ratio": 0.05, "practice": "冷水下锅，水开后煮 8 分钟"},
            {"name": "无糖豆浆 250ml", "ratio": 0.04, "practice": "直接饮用，不加糖"},
            {"name": "小番茄 100g", "ratio": 0.02, "practice": "洗净即食"},
        ],
        "lunch": [
            {"name": "杂粮饭 130g", "ratio": 0.14, "practice": "糙米与燕麦米按 2:1 蒸熟"},
            {"name": "清蒸鸡胸肉 120g", "ratio": 0.12, "practice": "加姜片、少许生抽蒸 12 分钟"},
            {"name": "白灼西兰花 150g", "ratio": 0.04, "practice": "沸水焯 90 秒，淋少许生抽"},
            {"name": "凉拌黑木耳 80g", "ratio": 0.03, "practice": "泡发焯水，加香醋与蒜末拌匀"},
        ],
        "dinner": [
            {"name": "蒸红薯 150g", "ratio": 0.12, "practice": "洗净隔水蒸 20 分钟"},
            {"name": "香煎龙利鱼 120g", "ratio": 0.10, "practice": "少油小火两面各煎 3 分钟"},
            {"name": "蒜蓉菠菜 150g", "ratio": 0.03, "practice": "蒜末爆香后大火快炒 1 分钟"},
            {"name": "无糖酸奶 100g", "ratio": 0.03, "practice": "餐后食用"},
        ],
    }

    def _local_plan(self, user) -> dict:
        target = float(getattr(user, "recommend_calorie", 0) or 1500)
        out = {}
        for meal, items in self._FALLBACK_PLAN.items():
            out[meal] = [
                {
                    "name": it["name"],
                    "weight": "",
                    "calorie": round(target * it["ratio"]),
                    "practice": it["practice"],
                }
                for it in items
            ]
        out["total_calorie"] = round(sum(x["calorie"] for items in out.values() for x in items))
        out["adapt_desc"] = (
            "AI 服务暂不可用，以上为按你的推荐热量生成的通用减脂食谱，"
            "可先参考执行，稍后再点击「重新生成」获取专属方案。"
        )
        return out

    # ---------- 系统提示词 ----------
    def _build_chat_system(self, user) -> str:
        pref = user.diet_preference or "无"
        return (
            f"你是专业的减脂营养师。用户基础信息：性别{'男' if user.gender == 1 else '女'}，"
            f"年龄{user.age}岁，身高{user.height}cm，当前体重{user.current_weight}kg，"
            f"目标体重{user.target_weight}kg，每日推荐摄入热量{user.recommend_calorie}kcal，"
            f"饮食偏好：{pref}。"
            f"请结合以上信息给出专业、通俗、可执行的建议。"
            f"禁止推荐极端节食（每日摄入低于基础代谢或低于1200kcal）。"
            f"回答要温暖、鼓励用户坚持。"
            f"输出格式要求：直接使用 Markdown 排版（标题、列表、加粗、表格按需使用）；"
            f"不要把整段回答放进 ```markdown 或 ``` 代码围栏里，否则会被当成纯代码展示。"
        )

    # ---------- JSON 解析（兼容 markdown 包裹）----------
    def _parse_json(self, text):
        if not text:
            raise AppException(502, "AI 返回内容为空，请稍后重试")
        t = text.strip()
        if t.startswith("```"):
            idx = t.find("\n")
            if idx != -1:
                t = t[idx + 1:]
            if t.endswith("```"):
                t = t[:-3]
            t = t.strip()
            if t.lower().startswith("json"):
                t = t[4:].strip()
        try:
            return json.loads(t)
        except Exception:
            s = t.find("{")
            e = t.rfind("}")
            if s != -1 and e != -1 and e > s:
                return json.loads(t[s:e + 1])
            raise AppException(502, "AI 返回内容无法解析为 JSON，请稍后重试")


# 单例
ai_service = AIService()
