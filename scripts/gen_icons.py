"""生成 PWA 图标（与 public/favicon.svg 同一图形，栅格化为 PNG）。

用途：manifest 的 icons 需要位图才能被部分浏览器判定为「可安装」，
SVG 在 Android/Chrome 之外的环境支持不完整。图形参数与 favicon.svg 保持一致：
碗形容器 + 同心半弧 + 右上智能点，青柠底 #C6F24E、墨 #23231F。

用法：python scripts/gen_icons.py
"""
import os

from PIL import Image, ImageDraw

LIME = (198, 242, 78, 255)
INK = (35, 35, 31, 255)

SS = 4  # 超采样倍率：先画大图再缩小，边缘更干净


def make(size, maskable=False):
    big = size * SS
    sc = big / 64.0
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 背景：普通图标为圆角方形；maskable 必须满幅（系统会按任意形状裁切）
    if maskable:
        d.rectangle([0, 0, big, big], fill=LIME)
        # 安全区：内容收进中心 80%，避免被系统遮罩切掉
        k = 0.66
    else:
        d.rounded_rectangle([0, 0, big, big], radius=int(15 * sc), fill=LIME)
        k = 1.0

    def tx(x, y):
        # 以画布中心为原点缩放后再平移回去
        c = 32.0
        return ((c + (x - c) * k) * sc, (c + (y - c) * k) * sc)

    def half_disc(cx, cy, r, color):
        """以 (cx,cy) 为圆心、r 为半径的下半圆。

        PIL 的 pieslice 角度从 3 点钟起顺时针计，0→180 正好是屏幕坐标系下的下半圆；
        这里刻意用填充半圆而不是 arc 描边——arc 的线宽在缩小后会糊成一团，
        用「外圈填充 + 内圈回填」的方式能得到与 SVG 一致的清晰圆环。
        """
        x0, y0 = tx(cx - r, cy - r)
        x1, y1 = tx(cx + r, cy + r)
        d.pieslice([x0, y0, x1, y1], start=0, end=180, fill=color)

    # 碗：圆心 (32,32) 半径 20 的下半圆
    half_disc(32, 32, 20, INK)

    # 碗内同心半弧（下半弧）：半径 13.5 / 9.5 / 5.5，线宽 2.6
    for r in (13.5, 9.5, 5.5):
        half_disc(32, 32, r + 1.3, LIME)
        half_disc(32, 32, r - 1.3, INK)

    # 右上智能指示点
    dx0, dy0 = tx(46.5 - 3.8, 17 - 3.8)
    dx1, dy1 = tx(46.5 + 3.8, 17 + 3.8)
    d.ellipse([dx0, dy0, dx1, dy1], fill=INK)

    return img.resize((size, size), Image.LANCZOS)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "icons")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    for size in (192, 512):
        make(size).save(os.path.join(out_dir, f"icon-{size}.png"))
    make(512, maskable=True).save(os.path.join(out_dir, "icon-maskable-512.png"))
    print("icons written to", out_dir)


if __name__ == "__main__":
    main()
