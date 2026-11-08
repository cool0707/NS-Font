#!/usr/bin/env python3
"""複数の TTF を 1 つの TrueType Collection (.ttc) にまとめる。

msgothic.ttc（MS ゴシック + MS P ゴシック + MS UI ゴシック）と同じく、
インストールすると全書体が使えるようになる。

各書体で輪郭が同一のグリフ（漢字など）は同じグリフ ID を共有させ、
glyf/loca を書体間で 1 つにまとめてファイルサイズを抑える。
書体ごとに異なるのは cmap・hmtx・vmtx・GSUB・name などの小さい表だけになる。

  python3 scripts/make_ttc.py                    # 既定の 2 組 (Gothic 系 / Mincho 系)
  python3 scripts/make_ttc.py out.ttc a.ttf b.ttf  # 任意の組み合わせ
"""
import os
import sys

from fontTools.ttLib import TTFont, TTCollection

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

DEFAULT = {
    "NSGothic.ttc": ["NSGothic-Regular.ttf", "NSPGothic-Regular.ttf", "NSUIGothic-Regular.ttf"],
    "NSMincho.ttc": ["NSMincho-Regular.ttf", "NSPMincho-Regular.ttf"],
}

# 書体ごとに持つ表（グリフ ID を介して glyf を参照するもの・書体固有の情報）
# それ以外の表で中身が同じものは TTCollection.save(shareTables=True) が自動で共有する


def glyph_bytes(glyf, name):
    g = glyf[name]
    return g.compile(glyf, recalcBBoxes=False) if g.numberOfContours else b""


def merge(paths, out):
    fonts = [TTFont(p, lazy=False) for p in paths]
    for f in fonts:                    # グリフ順を差し替える前に全表を名前ベースで読み込む
        for tag in f.keys():
            f[tag]
    glyfs = [f["glyf"] for f in fonts]

    # 統合グリフ列: ids[i] = (書体番号, グリフ名)  ※輪郭の実体
    base_order = fonts[0].getGlyphOrder()
    ids = [(0, n) for n in base_order]
    data = [glyph_bytes(glyfs[0], n) for n in base_order]
    by_name = {n: [i] for i, n in enumerate(base_order)}   # 名前 → 候補 ID 群
    face_maps = [{n: i for i, n in enumerate(base_order)}]

    for k in range(1, len(fonts)):
        m = {}
        for n in fonts[k].getGlyphOrder():
            b = glyph_bytes(glyfs[k], n)
            hit = next((i for i in by_name.get(n, []) if data[i] == b and i not in m.values()), None)
            if hit is None:
                hit = len(ids)
                ids.append((k, n))
                data.append(b)
                by_name.setdefault(n, []).append(hit)
            m[n] = hit
        face_maps.append(m)

    total = len(ids)
    if total > 65535:
        sys.exit(f"グリフ数 {total} が上限 65535 を超えます")

    for k, f in enumerate(fonts):
        m = face_maps[k]
        order = [None] * total
        for n, i in m.items():
            order[i] = n
        used = set(m)
        for i in range(total):
            if order[i] is None:
                d = f"_g{i}"
                while d in used:
                    d += "_"
                order[i] = d
                used.add(d)
        src_glyf = {j: glyfs[j] for j in range(len(fonts))}
        new_glyphs = {}
        hm, vm = f["hmtx"].metrics, f["vmtx"].metrics if "vmtx" in f else None
        for i, n in enumerate(order):
            fk, fn = ids[i]
            g = src_glyf[fk][fn]
            new_glyphs[n] = g
            if n not in m:                 # この書体からは参照されない枠
                xmin = g.xMin if g.numberOfContours else 0
                ymax = g.yMax if g.numberOfContours else 0
                hm[n] = (0, xmin)
                if vm is not None:
                    vm[n] = (0, -ymax)
        f["glyf"].glyphs = new_glyphs
        f["glyf"].glyphOrder = order
        f.setGlyphOrder(order)
        f["post"].formatType = 2.0
        f["post"].extraNames = []
        f["post"].mapping = {}
        print(f"  {os.path.basename(paths[k])}: 独自グリフ "
              f"{sum(1 for i in m.values() if ids[i][0] == k) if k else len(base_order)}")

    coll = TTCollection()
    coll.fonts = fonts
    coll.save(out, shareTables=True)
    print(f"{out}: {len(fonts)} 書体, 統合グリフ数 {total}, {os.path.getsize(out) / 1e6:.1f} MB")


def main():
    if len(sys.argv) > 2:
        merge(sys.argv[2:], sys.argv[1])
        return
    for out, names in DEFAULT.items():
        paths = [os.path.join(DIST, n) for n in names if os.path.exists(os.path.join(DIST, n))]
        if len(paths) >= 2:
            merge(paths, os.path.join(DIST, out))


if __name__ == "__main__":
    main()
