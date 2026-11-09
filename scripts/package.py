#!/usr/bin/env python3
"""build/ttf/ の TTF から配布物を dist/ に組み立てる。

dist/Regular/     レギュラーのみ
    NSGothic-Regular.ttf             等幅
    NSPGothic-Regular.ttf            プロポーショナル
    NSGothic-NSPGothic-Regular.ttc   等幅 + プロポーショナル
    NSUIGothic-Regular.ttf           UI（等幅版なし）
    NSMincho-Regular.ttf / NSPMincho-Regular.ttf / NSMincho-NSPMincho-Regular.ttc
dist/AllWeights/  Noto にある全ウェイト入り（TTC）
    NSGothic-AllWeights.ttc               等幅 × 全ウェイト
    NSPGothic-AllWeights.ttc              プロポーショナル × 全ウェイト
    NSGothic-NSPGothic-AllWeights.ttc     等幅 + プロポーショナル × 全ウェイト
    NSUIGothic-AllWeights.ttc             UI × 全ウェイト
    （明朝も同様）
dist/Regular-JPVariants/  レギュラーの日本語異体字追加版（build/jpvar/ ← scripts/variants.py）
    NSGothic-Regular-JPVariants.ttf ... / NSGothic-NSPGothic-Regular-JPVariants.ttc など
dist/OTF/    dist/Regular/ と dist/Regular-JPVariants/ の TTF を OTF (CFF) にしたもの
dist/WOFF2/  同じく WOFF2 にしたもの（Web フォント用）

TTC では、同じウェイト内で輪郭が同一のグリフ（漢字など）は等幅/プロポーショナル間で
グリフ ID を共有させ、glyf/loca を 1 つにまとめてサイズを抑える。

  python3 scripts/package.py                       # 上記を全部作る
  python3 scripts/package.py --only jpvar,otf,woff2  # 一部だけ作る（ttf / jpvar / otf / woff2）
  python3 scripts/package.py out.ttc a.ttf b.ttf   # 任意の TTF を 1 グループ（glyf 共有）でまとめる
"""
import os
import shutil
import sys

from fontTools.ttLib import TTFont, TTCollection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import WEIGHTS  # noqa: E402
from variants import SUFFIX  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build", "ttf")
DIST = os.path.join(ROOT, "dist")

SETS = [
    # (等幅, プロポーショナル, Noto の系統)
    ("NSGothic", "NSPGothic", "NotoSansCJK"),
    (None, "NSUIGothic", "NotoSansCJK"),
    ("NSMincho", "NSPMincho", "NotoSerifCJK"),
]


def glyph_bytes(glyf, name):
    g = glyf[name]
    return g.compile(glyf, recalcBBoxes=False) if g.numberOfContours else b""


def load(path):
    f = TTFont(path, lazy=False)
    for tag in f.keys():               # グリフ順を差し替える前に全表を名前ベースで読み込む
        f[tag]
    return f


def share_glyf(fonts):
    """fonts の glyf を統合し、全書体が同一の glyf/loca を持つようにする。"""
    glyfs = [f["glyf"] for f in fonts]
    base_order = fonts[0].getGlyphOrder()
    ids = [(0, n) for n in base_order]                 # 統合グリフ ID → (書体番号, 名前)
    data = [glyph_bytes(glyfs[0], n) for n in base_order]
    by_name = {n: [i] for i, n in enumerate(base_order)}
    face_maps = [{n: i for i, n in enumerate(base_order)}]
    for k in range(1, len(fonts)):
        m, taken = {}, set()
        for n in fonts[k].getGlyphOrder():
            b = glyph_bytes(glyfs[k], n)
            hit = next((i for i in by_name.get(n, []) if data[i] == b and i not in taken), None)
            if hit is None:
                hit = len(ids)
                ids.append((k, n))
                data.append(b)
                by_name.setdefault(n, []).append(hit)
            m[n] = hit
            taken.add(hit)
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
        hm = f["hmtx"].metrics
        vm = f["vmtx"].metrics if "vmtx" in f else None
        new_glyphs = {}
        for i, n in enumerate(order):
            fk, fn = ids[i]
            g = glyfs[fk][fn]
            new_glyphs[n] = g
            if n not in m:                     # この書体からは参照されない枠
                hm[n] = (0, g.xMin if g.numberOfContours else 0)
                if vm is not None:
                    vm[n] = (0, -(g.yMax if g.numberOfContours else 0))
        f["glyf"].glyphs = new_glyphs
        f["glyf"].glyphOrder = order
        f.setGlyphOrder(order)
        f["post"].formatType = 2.0
        f["post"].extraNames = []
        f["post"].mapping = {}
    return total


def make_ttc(groups, out):
    """groups: [[path, ...], ...]  グループ内で glyf を共有。全書体を 1 つの TTC に入れる。"""
    fonts = []
    for g in groups:
        fs = [load(p) for p in g]
        if len(fs) > 1:
            share_glyf(fs)
        fonts += fs
    coll = TTCollection()
    coll.fonts = fonts
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    coll.save(out, shareTables=True)
    print(f"{os.path.relpath(out, ROOT)}: {len(fonts)} 書体, {os.path.getsize(out) / 1e6:.1f} MB",
          flush=True)


def ttf(fam, w):
    return os.path.join(SRC, f"{fam}-{w}.ttf")


def package_jpvariants():
    """build/jpvar/ の異体字追加版（レギュラー）を dist/Regular-JPVariants/ に置く。"""
    src = os.path.join(ROOT, "build", "jpvar")
    out = os.path.join(DIST, "Regular" + SUFFIX)
    os.makedirs(out, exist_ok=True)
    for fixed, prop, _ in SETS:
        paths = [os.path.join(src, f"{f}-Regular{SUFFIX}.ttf") for f in (fixed, prop) if f]
        if not all(os.path.exists(p) for p in paths):
            print(f"skip {paths}: scripts/variants.py を先に実行してください", file=sys.stderr)
            continue
        for p in paths:
            shutil.copy2(p, out)
            print(os.path.relpath(os.path.join(out, os.path.basename(p)), ROOT), flush=True)
        if fixed:
            make_ttc([paths], os.path.join(out, f"{fixed}-{prop}-Regular{SUFFIX}.ttc"))


def _convert(job):
    import convert
    kind, src, out = job
    dst = os.path.join(out, os.path.splitext(os.path.basename(src))[0] + "." + kind)
    (convert.to_otf if kind == "otf" else convert.to_woff2)(src, dst)
    return f"{os.path.relpath(dst, ROOT)}: {os.path.getsize(dst) / 1e6:.1f} MB"


def package_converted(kinds, jobs=os.cpu_count()):
    """dist/Regular/ と dist/Regular-JPVariants/ の TTF を OTF / WOFF2 にする。"""
    import glob
    from multiprocessing import Pool
    srcs = sorted(glob.glob(os.path.join(DIST, "Regular", "*.ttf")) +
                  glob.glob(os.path.join(DIST, "Regular" + SUFFIX, "*.ttf")))
    work = []
    for kind in kinds:
        out = os.path.join(DIST, kind.upper())
        os.makedirs(out, exist_ok=True)
        work += [(kind, s, out) for s in srcs]
    work.sort(key=lambda j: (j[0] != "otf", "Mincho" not in j[1]))     # 時間のかかるものから
    with Pool(max(1, jobs or 1)) as pool:
        for msg in pool.imap_unordered(_convert, work):
            print(msg, flush=True)


def main():
    only = None
    if len(sys.argv) > 2 and sys.argv[1] == "--only":
        only = set(sys.argv[2].split(","))
    elif len(sys.argv) > 2:
        make_ttc([sys.argv[2:]], sys.argv[1])
        return
    if only is None or "ttf" in only:
        package_ttf()
    if only is None or "jpvar" in only:
        package_jpvariants()
    kinds = [k for k in ("otf", "woff2") if only is None or k in only]
    if kinds:
        package_converted(kinds)


def package_ttf():
    reg, allw = os.path.join(DIST, "Regular"), os.path.join(DIST, "AllWeights")
    os.makedirs(reg, exist_ok=True)
    for fixed, prop, noto in SETS:
        fams = [f for f in (fixed, prop) if f]
        weights = [w for w in WEIGHTS[noto] if all(os.path.exists(ttf(f, w)) for f in fams)]
        if "Regular" not in weights:
            print(f"skip {fams}: Regular の TTF がありません", file=sys.stderr)
            continue
        # レギュラー版
        for f in fams:
            shutil.copy2(ttf(f, "Regular"), os.path.join(reg, f"{f}-Regular.ttf"))
            print(f"dist/Regular/{f}-Regular.ttf", flush=True)
        if fixed:
            make_ttc([[ttf(fixed, "Regular"), ttf(prop, "Regular")]],
                     os.path.join(reg, f"{fixed}-{prop}-Regular.ttc"))
        # 全ウェイト版
        if len(weights) < 2:
            continue
        for f in fams:
            make_ttc([[ttf(f, w)] for w in weights], os.path.join(allw, f"{f}-AllWeights.ttc"))
        if fixed:
            make_ttc([[ttf(fixed, w), ttf(prop, w)] for w in weights],
                     os.path.join(allw, f"{fixed}-{prop}-AllWeights.ttc"))


if __name__ == "__main__":
    main()
