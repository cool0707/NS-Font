#!/usr/bin/env python3
"""MS フォントと生成フォントを重ね描きした比較画像、および数値差の要約を出力する。

  赤 = MS フォント, 青 = 生成フォント, 紫 = 一致部分
出力は build/compare/ （MS フォントの描画を含むため git 管理外）
"""
import argparse
import os
import statistics
import sys

from PIL import Image, ImageDraw, ImageFont, ImageChops
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nsfont.fontutil import open_face, glyph_bounds  # noqa: E402
from nsfont.classify import base_class, group_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAIRS = {
    "Gothic": ("msgothic.ttc", 0, "NSGothic-Regular.ttf"),
    "PGothic": ("msgothic.ttc", 2, "NSPGothic-Regular.ttf"),
    "UIGothic": ("msgothic.ttc", 1, "NSUIGothic-Regular.ttf"),
    "Mincho": ("msmincho.ttc", 0, "NSMincho-Regular.ttf"),
    "PMincho": ("msmincho.ttc", 1, "NSPMincho-Regular.ttf"),
}

SAMPLE = [
    "あいうえお、かきくけこ。アイウエオ「カキクケコ」",
    "漢字仮名交じり文の組版テスト（括弧）・中黒…―",
    "ABCDEFGHIJKLM abcdefghijklm 0123456789",
    "NOPQRSTUVWXYZ nopqrstuvwxyz !\"#$%&'()*+,-./",
    "ＡＢＣａｂｃ０１２ ｱｲｳｴｵｶﾞﾊﾟ ①②③ ㈱㌔ ←→↑↓",
    "┌─┬─┐│■□◆◇○●★☆※〒♪ ÀÉÎÕÜ ñçß",
]


def render(path, index, text, size):
    """hmtx の送り幅 (em 比) で 1 文字ずつ配置する（ヒンティングによる送り幅の丸めを避ける）。"""
    font = ImageFont.truetype(path, size, index=index, layout_engine=ImageFont.Layout.BASIC)
    tt = open_face(path, index=index) if path.endswith(".ttc") else TTFont(path)
    cmap, hmtx, upem = tt.getBestCmap(), tt["hmtx"], tt["head"].unitsPerEm
    asc = tt["hhea"].ascent / upem * size
    advs = [hmtx[cmap[ord(c)]][0] / upem * size if ord(c) in cmap else size for c in text]
    img = Image.new("L", (int(sum(advs)) + 20, int(size * 1.3)), 0)
    d = ImageDraw.Draw(img)
    x = 10.0
    for c, a in zip(text, advs):
        d.text((round(x), int(size * 0.15 + asc)), c, font=font, fill=255, anchor="ls")
        x += a
    return img


def overlay(ms_path, ms_index, ns_path, out, size=48):
    rows = []
    for line in SAMPLE:
        a = render(ms_path, ms_index, line, size)
        b = render(ns_path, 0, line, size)
        W, H = max(a.width, b.width), max(a.height, b.height)
        a2, b2 = Image.new("L", (W, H)), Image.new("L", (W, H))
        a2.paste(a), b2.paste(b)
        inv = Image.new("L", (W, H), 255)
        r = ImageChops.subtract(inv, b2)          # 生成フォント部分を青に
        g = ImageChops.subtract(inv, ImageChops.lighter(a2, b2))
        bl = ImageChops.subtract(inv, a2)          # MS 部分を赤に
        rows.append(Image.merge("RGB", (r, g, bl)))
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows)), "white")
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(out)


def numeric(ms_font, ns_font):
    """MS 収録字について 送り幅一致率・字面枠の差 (em 比) を分類グループ別に集計。"""
    mc, nc = ms_font.getBestCmap(), ns_font.getBestCmap()
    mu, nu = ms_font["head"].unitsPerEm, ns_font["head"].unitsPerEm
    acc = {}
    for cp, mg in mc.items():
        ng = nc.get(cp)
        if ng is None:
            continue
        grp = group_of(base_class(cp))
        a = acc.setdefault(grp, {"n": 0, "adv_ok": 0, "d": []})
        a["n"] += 1
        if abs(ms_font["hmtx"][mg][0] / mu - ns_font["hmtx"][ng][0] / nu) < 0.002:
            a["adv_ok"] += 1
        mb, nb = glyph_bounds(ms_font, mg), glyph_bounds(ns_font, ng)
        if mb and nb:
            a["d"].append(max(abs(mb[i] / mu - nb[i] / nu) for i in range(4)))
    lines = ["| グループ | 字数 | 送り幅一致 | 字面枠ずれ中央値 | 90%点 |", "|---|---:|---:|---:|---:|"]
    for g, a in sorted(acc.items()):
        d = sorted(a["d"])
        q = d[int(len(d) * 0.9)] if d else 0
        lines.append(f"| {g} | {a['n']} | {a['adv_ok'] / a['n']:.1%} | "
                     f"{statistics.median(d) if d else 0:.3f}em | {q:.3f}em |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", default=["Gothic", "PGothic", "Mincho", "PMincho"])
    ap.add_argument("--ms-dir", default=os.path.join(ROOT, "fonts", "ms"))
    ap.add_argument("--dist", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "compare"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for t in args.targets:
        msf, idx, nsf = PAIRS[t]
        ms_path, ns_path = os.path.join(args.ms_dir, msf), os.path.join(args.dist, nsf)
        if not os.path.exists(ns_path):
            continue
        overlay(ms_path, idx, ns_path, os.path.join(args.out, f"{t}.png"))
        rep = numeric(open_face(ms_path, index=idx), TTFont(ns_path))
        with open(os.path.join(args.out, f"{t}.md"), "w") as fp:
            fp.write(rep + "\n")
        print(f"## {t}\n{rep}\n")


if __name__ == "__main__":
    main()
