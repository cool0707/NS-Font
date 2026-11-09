#!/usr/bin/env python3
"""生成済みの NS フォント (TTF) に日本語の異体字を追加した「日本語異体字追加版」を作る。

追加するもの（Noto CJK JP にあるもの）
  - 異体字セレクタ (IVS, cmap format 14 / Adobe-Japan1 IVD)  例: 葛 + U+E0100
  - OpenType feature: jp78 / jp83 / nlck / hist / aalt（字形切替・異体字一覧）

追加する字形は、同じ文字の既定字形（NS フォントに収録済み）と同じ変換
（大きさ・位置・送り幅・縦書きメトリクス）を Noto の字形に施して作る。
変換は既定字形の Noto 原本と NS フォントの字面枠を比べて求めるので、
MS フォント原本や build/ms/ の計測データは不要（必要なのは Noto CJK 原本のみ）。

  python3 scripts/variants.py                 # Regular の 5 書体 → build/jpvar/*-Regular-JPVariants.ttf
  python3 scripts/variants.py --weights all   # 全ウェイト
  python3 scripts/variants.py -i in.ttf -o out.ttf --noto fonts/noto/NotoSansCJK-Regular.ttc
"""
import argparse
import os
import re
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontTools import subset  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable  # noqa: E402
from fontTools.pens.boundsPen import BoundsPen  # noqa: E402
from fontTools.pens.transformPen import TransformPen  # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen  # noqa: E402
from fontTools.pens.cu2quPen import Cu2QuPen  # noqa: E402

from nsfont.fontutil import open_face  # noqa: E402
from nsfont.coverage import LAYOUT_FEATURES  # noqa: E402
from build import TARGETS, weights_for  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANT_FEATURES = ["jp78", "jp83", "nlck", "hist", "aalt"]
SUFFIX = "-JPVariants"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def gsub_edges(font, features):
    """features に属する lookup の (入力, 出力) 対。"""
    t = font["GSUB"].table
    idx = []
    for fr in t.FeatureList.FeatureRecord:
        if fr.FeatureTag in features:
            idx += [(features.index(fr.FeatureTag), i) for i in fr.Feature.LookupListIndex]
    out = []
    for _, i in sorted(set(idx)):
        lk = t.LookupList.Lookup[i]
        for st in lk.SubTable:
            typ = lk.LookupType
            if typ == 7:
                typ, st = st.ExtensionLookupType, st.ExtSubTable
            if typ == 1:
                out += list(st.mapping.items())
            elif typ == 3:
                out += [(a, b) for a, bs in st.alternates.items() for b in bs]
    return out


class Xform:
    """NS 字形 = (sx, sy, tx, ty) × Noto 字形。送り幅等も併せて持つ。"""
    __slots__ = ("sx", "sy", "tx", "ty", "adv", "nadv", "vadv", "nvadv", "dvorg")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def noto_bounds(gs, g):
    bp = BoundsPen(gs)
    gs[g].draw(bp)
    return bp.bounds


def derive(ns, noto, gs, g, cache):
    """NS に収録済みの字形 g について、Noto → NS の変換を字面枠から求める。"""
    if g in cache:
        return cache[g]
    x = None
    nglyf = ns["glyf"][g] if g in ns["glyf"] else None
    nb = noto_bounds(gs, g)
    if nglyf is not None and nglyf.numberOfContours > 0 and nb:
        w, h = nb[2] - nb[0], nb[3] - nb[1]
        if w > 20 and h > 20:
            sx = (nglyf.xMax - nglyf.xMin) / w
            sy = (nglyf.yMax - nglyf.yMin) / h
            adv, _ = ns["hmtx"][g]
            vadv, tsb = ns["vmtx"][g]
            vorg_ns = tsb + nglyf.yMax
            vorg_noto = noto["VORG"].VOriginRecords.get(g, noto["VORG"].defaultVertOriginY)
            x = Xform(sx=sx, sy=sy, tx=nglyf.xMin - sx * nb[0], ty=nglyf.yMin - sy * nb[1],
                      adv=adv, nadv=noto["hmtx"][g][0], vadv=vadv, nvadv=noto["vmtx"][g][0],
                      dvorg=vorg_ns - sy * vorg_noto)
    cache[g] = x
    return x


def for_variant(base, noto, g):
    """既定字形の変換 base を、送り幅の異なりうる Noto 字形 g に当てはめる。"""
    nadv, nvadv = noto["hmtx"][g][0], noto["vmtx"][g][0]
    if nadv == base.nadv:
        adv, tx = base.adv, base.tx
    else:      # 送り幅の比を保ち、字送りの中心に対する位置を保つ
        adv = round(nadv * base.adv / base.nadv) if base.nadv else nadv
        off = base.tx - (base.adv / 2 - base.sx * base.nadv / 2)
        tx = adv / 2 - base.sx * nadv / 2 + off
    vadv = base.vadv if nvadv == base.nvadv else round(nvadv * base.vadv / (base.nvadv or nvadv))
    return Xform(sx=base.sx, sy=base.sy, tx=tx, ty=base.ty, adv=adv, nadv=nadv,
                 vadv=vadv, nvadv=nvadv, dvorg=base.dvorg)


def noto_path_of(ns, noto_dir):
    m = re.search(r"based on (\S+\.ttc)", ns["name"].getDebugName(5) or "")
    if not m:
        sys.exit("name ID 5 から Noto 原本のファイル名が分かりません。--noto で指定してください")
    return os.path.join(noto_dir, m.group(1))


def add_variants(in_path, out_path, noto_path):
    log("load", in_path)
    ns = TTFont(in_path)
    log("load", noto_path)
    noto = open_face(noto_path, "CJK JP")
    noto_cmap = noto.getBestCmap()
    ns_cmap = ns.getBestCmap()
    keep = [cp for cp in ns_cmap if cp in noto_cmap]

    # Noto を NS と同じ収録字で、異体字 feature と IVS を含めてサブセット化
    opts = subset.Options()
    opts.layout_features = LAYOUT_FEATURES + VARIANT_FEATURES
    opts.name_IDs, opts.name_languages = ["*"], ["*"]
    opts.notdef_outline = True
    opts.glyph_names = True
    opts.hinting = False
    opts.drop_tables = ["DSIG"]
    uvs = next(t for t in noto["cmap"].tables if t.format == 14)
    keep_set = set(keep)
    uvs_dict = {vs: [(cp, g) for cp, g in lst if cp in keep_set] for vs, lst in uvs.uvsDict.items()}
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=keep,
                 glyphs=[g for lst in uvs_dict.values() for _, g in lst if g])
    sub.subset(noto)
    gs = noto.getGlyphSet()

    ns_order = list(ns.getGlyphOrder())
    ns_set = set(ns_order)
    noto_order = noto.getGlyphOrder()
    missing = [g for g in noto_order if g not in ns_set and not g.startswith("cid") and g != ".notdef"]
    if missing:
        sys.exit(f"NS 側に無い名前のグリフがあります: {missing[:10]}")
    new = [g for g in noto_order if g not in ns_set]
    log("new glyphs", len(new))

    # 追加字形ごとに、変換を借りる既定字形を決める（IVS → jp78 → … → aalt の順に優先）
    base_of = {}
    for vs, lst in sorted(uvs_dict.items()):
        for cp, g in lst:
            if g and g not in ns_set and g not in base_of:
                base_of[g] = noto_cmap[cp]
    for a, b in gsub_edges(noto, VARIANT_FEATURES):
        if b not in ns_set and b not in base_of and a != b:
            base_of[b] = a

    cache, plans, how = {}, {}, Counter()
    pending = list(new)
    while pending:
        rest = []
        for g in pending:
            a = base_of.get(g)
            if a is None:
                continue
            bx = plans.get(a) if a not in ns_set else derive(ns, noto, gs, a, cache)
            if bx is None and a not in ns_set:
                rest.append(g)
                continue
            if bx is None:
                continue
            plans[g] = for_variant(bx, noto, g)
            how["ns" if a in ns_set else "chain"] += 1
        if len(rest) == len(pending):
            break
        pending = rest
    # 既定字形の変換が求まらなかったもの（ごく少数）は漢字の代表値を使う
    kanji = [derive(ns, noto, gs, ns_cmap[cp], cache) for cp in range(0x4E00, 0xA000, 37)
             if cp in ns_cmap]
    kanji = [k for k in kanji if k and k.adv == 1000]

    def med(attr):
        v = sorted(getattr(k, attr) for k in kanji)
        return v[len(v) // 2]
    rep = Xform(**{k: med(k) for k in Xform.__slots__})
    for g in new:
        if g not in plans:
            plans[g] = for_variant(rep, noto, g)
            how["representative"] += 1
    log("plans", dict(how))

    # 字形を TrueType に変換して追加
    glyf, hmtx, vmtx = ns["glyf"], ns["hmtx"], ns["vmtx"]
    for g in new:
        p = plans[g]
        pen = TTGlyphPen(None)
        gs[g].draw(TransformPen(Cu2QuPen(pen, max_err=0.5, reverse_direction=True),
                                (p.sx, 0, 0, p.sy, p.tx, p.ty)))
        gl = pen.glyph()
        gl.recalcBounds(glyf)
        glyf[g] = gl
        vorg_noto = noto["VORG"].VOriginRecords.get(g, noto["VORG"].defaultVertOriginY)
        vorg = p.sy * vorg_noto + p.dvorg
        hmtx[g] = (max(0, int(round(p.adv))), gl.xMin if gl.numberOfContours else 0)
        vmtx[g] = (max(0, int(round(p.vadv))),
                   int(round(vorg - gl.yMax)) if gl.numberOfContours else 0)
    ns.setGlyphOrder(ns_order + new)
    glyf.glyphOrder = ns_order + new

    # GSUB/GDEF は異体字 feature 入りのサブセットのものに差し替える
    # （NS の GSUB は同じ原本を LAYOUT_FEATURES でサブセットしたものなので、その上位集合になる）
    ns["GSUB"] = noto["GSUB"]
    if "GDEF" in noto:
        ns["GDEF"] = noto["GDEF"]

    # IVS (cmap format 14)。既定字形と同じものは「既定」(None) として NS 側の cmap に従う
    t14 = CmapSubtable.newSubtable(14)
    t14.platformID, t14.platEncID, t14.language = 0, 5, 0xFF
    t14.cmap = {}
    t14.uvsDict = {}
    n_uvs = 0
    for vs, lst in uvs_dict.items():
        ent = [(cp, None if (g is None or g == noto_cmap[cp]) else g) for cp, g in lst]
        if ent:
            t14.uvsDict[vs] = ent
            n_uvs += len(ent)
    tables = [t for t in ns["cmap"].tables if t.format != 14]
    ns["cmap"].tables = sorted(tables + [t14], key=lambda t: (t.platformID, t.platEncID, t.format))
    log("IVS", n_uvs)

    name = ns["name"]
    for rec in name.names:
        if rec.nameID in (3, 5):
            s = rec.toUnicode()
            if "JP variants" not in s:
                rec.string = s + ("; JP variants" if rec.nameID == 5 else "-JPVariants")
    ns["post"].formatType = 2.0
    ns["post"].extraNames = []
    ns["post"].mapping = {}
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    ns.save(out_path)
    log("save", out_path, f"{os.path.getsize(out_path) / 1e6:.1f} MB", len(ns.getGlyphOrder()), "glyphs")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", default=list(TARGETS))
    ap.add_argument("--weights", default="Regular")
    ap.add_argument("--src", default=None,
                    help="NS の TTF の場所（既定: build/ttf/ があればそこ、無ければ dist/Regular/）")
    ap.add_argument("--noto-dir", default=os.path.join(ROOT, "fonts", "noto"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "jpvar"))
    ap.add_argument("-i", "--input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--noto")
    args = ap.parse_args()
    if args.input:
        ns = TTFont(args.input, lazy=True)
        add_variants(args.input, args.output or args.input.replace(".ttf", SUFFIX + ".ttf"),
                     args.noto or noto_path_of(ns, args.noto_dir))
        return
    for t in args.targets:
        fam = TARGETS[t][3].replace(" ", "")
        for w in weights_for(t, args.weights):
            fn = f"{fam}-{w}.ttf"
            src = args.src
            if src is None:
                src = os.path.join(ROOT, "build", "ttf")
                if not os.path.exists(os.path.join(src, fn)):
                    src = os.path.join(ROOT, "dist", "Regular")
            inp = os.path.join(src, fn)
            ns = TTFont(inp, lazy=True)
            add_variants(inp, os.path.join(args.out, f"{fam}-{w}{SUFFIX}.ttf"),
                         noto_path_of(ns, args.noto_dir))


if __name__ == "__main__":
    main()
