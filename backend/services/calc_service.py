"""代谢指标计算服务。

计算公式：
- BMR（基础代谢率）：
    男 = 10*体重(kg) + 6.25*身高(cm) - 5*年龄 + 5
    女 = 10*体重(kg) + 6.25*身高(cm) - 5*年龄 - 161
- TDEE（每日总消耗）= BMR * 活动系数
    1 久坐=1.2 / 2 轻度=1.375 / 3 中度=1.55 / 4 重度=1.725
- 推荐摄入热量 = TDEE - 400（缺口 300~500 取中值），最低不低于 BMR
- BMI = 体重(kg) / (身高(m))^2
"""


def activity_coefficient(level: int) -> float:
    """活动水平 -> 系数。"""
    mapping = {1: 1.2, 2: 1.375, 3: 1.55, 4: 1.725}
    return mapping.get(level, 1.2)


def calc_bmr(gender: int, age: int, height: float, weight: float) -> float:
    """计算基础代谢率 BMR。gender: 0 女 / 1 男。"""
    base = 10 * weight + 6.25 * height - 5 * age
    return base + 5 if gender == 1 else base - 161


def calc_tdee(bmr: float, activity_level: int) -> float:
    """计算每日总消耗 TDEE。"""
    return bmr * activity_coefficient(activity_level)


def calc_recommend(tdee: float, bmr: float) -> float:
    """计算推荐每日摄入热量，最低不低于 BMR。"""
    return max(tdee - 400, bmr)


def calc_bmi(weight: float, height: float) -> float:
    """计算 BMI。"""
    h = height / 100.0
    return round(weight / (h * h), 1)
