#!/usr/bin/env python3
"""Noto Sans/Serif CJK JP を MS ゴシック系/明朝系のメトリクスに合わせて改造する。

前提: scripts/analyze_ms.py を実行して build/ms/*.json を作っておくこと。

処理の概要
  1. Noto の JP 書体を取り出し、ハングルを除いてサブセット化
  2. 等幅版 (Gothic/Mincho) では、MS 側が半角/全角の文字について Noto の
     hwid/fwid 字形（半角/全角用デザイン）を既定字形に差し替える
  3. 全グリフについて「どの文字の、どの役割 (cmap/vert/その他) の字形か」を求める
  4. MS に同じ文字があるグリフ:
        送り幅・縦送り・縦書き原点 = MS の値
        字面の大きさ = 分類共通の倍率 × グリフ毎の補正（MS の字面寸法に寄せる、分類毎に上限あり）
        字面の位置 = MS の字面中心に一致（欧文系は縦位置のみ分類共通＝ベースライン維持）
        罫線・ブロック要素 = MS の字面枠に完全一致
     MS に無いグリフ:
        アクセント付き欧文 → 基底文字の値
        異体字等 → 同じ文字の既定字形と同じ変換
        それ以外 → 同じ分類 (基本分類+幅区分 → 基本分類 → グループ → 全体) の統計値
  5. 2 次ベジエ (TrueType) へ変換し、縦横メトリクス・名前等を設定して保存
"""
import argparse
import json
import math
import os
import statistics
import sys
import time
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontTools import subset  # noqa: E402
from fontTools.ttLib import newTable  # noqa: E402
from fontTools.ttLib.tables._g_l_y_f import Glyph  # noqa: E402
from fontTools.pens.boundsPen import BoundsPen  # noqa: E402
from fontTools.pens.transformPen import TransformPen  # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen  # noqa: E402
from fontTools.pens.cu2quPen import Cu2QuPen  # noqa: E402

from nsfont.classify import (base_class, group_of, width_bucket, decompose_base,  # noqa: E402
                             BASELINE_GROUPS, EXACT_FIT_GROUPS)
from nsfont.fontutil import open_face, single_subst_map  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPEM = 1000

TARGETS = {
    # key: (MS 計測データ, Noto 原本ファイル(ウェイト置換用 {w}), 等幅か, 英名, 和名)
    "Gothic": ("MSGothic", "NotoSansCJK-{w}.ttc", True, "NS Gothic", "NS ゴシック"),
    "PGothic": ("MSPGothic", "NotoSansCJK-{w}.ttc", False, "NS PGothic", "NS Pゴシック"),
    "UIGothic": ("MSUIGothic", "NotoSansCJK-{w}.ttc", False, "NS UI Gothic", "NS UI Gothic"),
    "Mincho": ("MSMincho", "NotoSerifCJK-{w}.ttc", True, "NS Mincho", "NS 明朝"),
    "PMincho": ("MSPMincho", "NotoSerifCJK-{w}.ttc", False, "NS PMincho", "NS P明朝"),
}
DEFAULT_TARGETS = ["Gothic", "PGothic", "UIGothic", "Mincho", "PMincho"]

# グリフ毎の大きさ補正の上限（分類共通倍率からの ± 比率）
SCALE_TOLERANCE = {
    "kanji": 0.05, "kana": 0.08, "hw_kana": 0.08, "latin": 0.08, "fw_latin": 0.15,
    "cjk_punct": 0.15, "cjk_symbol": 0.10, "latin_symbol": 0.15, "symbol": 0.12,
}
MIN_SAMPLES = 3

HANGUL = [(0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F), (0xAC00, 0xD7FF),
          (0xFFA0, 0xFFDC)]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def med(v, default=None):
    v = [x for x in v if x is not None]
    return statistics.median(v) if v else default


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# --------------------------------------------------------------------------
# 1. 原本の準備
# --------------------------------------------------------------------------
def load_noto(path):
    font = open_face(path, "CJK JP")
    keep = [cp for cp in font.getBestCmap()
            if not any(lo <= cp <= hi for lo, hi in HANGUL)]
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.glyph_names = True
    opts.hinting = False
    opts.desubroutinize = False
    opts.drop_tables = ["DSIG"]
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=keep)
    sub.subset(font)
    return font


# --------------------------------------------------------------------------
# 3. グリフの持ち主（文字・役割）
# --------------------------------------------------------------------------
def gsub_edges(font):
    """GSUB から (入力グリフ, 出力グリフ, feature) の列を作る。"""
    t = font["GSUB"].table
    lk_feats = defaultdict(set)
    for fr in t.FeatureList.FeatureRecord:
        for i in fr.Feature.LookupListIndex:
            lk_feats[i].add(fr.FeatureTag)
    edges = []
    for i, lk in enumerate(t.LookupList.Lookup):
        feats = lk_feats.get(i) or {"(ctx)"}
        feat = "vert" if feats & {"vert", "vrt2"} else sorted(feats)[0]
        for st in lk.SubTable:
            typ = lk.LookupType
            if typ == 7:
                typ, st = st.ExtensionLookupType, st.ExtSubTable
            if typ == 1:
                edges += [(a, b, feat) for a, b in st.mapping.items()]
            elif typ == 2:
                edges += [(a, b, feat) for a, bs in st.mapping.items() for b in bs]
            elif typ == 3:
                edges += [(a, b, feat) for a, bs in st.alternates.items() for b in bs]
            elif typ == 4:
                edges += [(a, lig.LigGlyph, feat) for a, ligs in st.ligatures.items() for lig in ligs]
    return edges


def glyph_owners(font, prefer=None):
    """{glyph: (cp, role, feature)}  role は cmap / vert / other
    複数の文字が同じ字形を指す場合は prefer(cp) が小さい文字を持ち主にする。"""
    owners = {}
    items = sorted(font.getBestCmap().items(), key=lambda kv: (prefer(kv[0]) if prefer else 0, kv[0]))
    for cp, g in items:
        owners.setdefault(g, (cp, "cmap", None))
    edges = gsub_edges(font)
    # vert を優先して割り当て、その後その他の置換を不動点まで辿る
    for pass_vert in (True, False):
        changed = True
        while changed:
            changed = False
            for a, b, feat in edges:
                if (feat == "vert") != pass_vert or b in owners or a not in owners:
                    continue
                cp, role, _ = owners[a]
                owners[b] = (cp, "vert" if feat == "vert" and role == "cmap" else "other", feat)
                changed = True
    return owners


# --------------------------------------------------------------------------
# 4. 変換パラメータ
# --------------------------------------------------------------------------
class Box:
    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    w = property(lambda s: s.x1 - s.x0)
    h = property(lambda s: s.y1 - s.y0)
    cx = property(lambda s: (s.x0 + s.x1) / 2)
    cy = property(lambda s: (s.y0 + s.y1) / 2)
    maxdim = property(lambda s: max(s.x1 - s.x0, s.y1 - s.y0))


def ms_box(r):
    if "xMin" not in r:
        return None
    return Box(r["xMin"] * UPEM, r["yMin"] * UPEM, r["xMax"] * UPEM, r["yMax"] * UPEM)


class Plan:
    """1 グリフ分の変換: x' = sx*x + tx, y' = sy*y + ty"""
    __slots__ = ("sx", "sy", "tx", "ty", "adv", "vadv", "vorg", "how")

    def __init__(self, sx, sy, tx, ty, adv, vadv, vorg, how):
        self.sx, self.sy, self.tx, self.ty = sx, sy, tx, ty
        self.adv, self.vadv, self.vorg, self.how = adv, vadv, vorg, how


class Builder:
    def __init__(self, target, weight, args):
        self.target = target
        self.ms_key, noto_file, self.fixed, self.family, self.family_ja = TARGETS[target]
        self.weight = weight
        self.args = args
        with open(os.path.join(args.ms_data, self.ms_key + ".json")) as fp:
            d = json.load(fp)
        self.ms_face = d["face"]
        self.ms = {int(k): v for k, v in d["glyphs"].items()}
        self.noto_path = os.path.join(args.noto_dir, noto_file.format(w=weight))
        self.report = {}

    # ---- 原本 -------------------------------------------------------------
    def prepare(self):
        log(self.target, self.weight, "load+subset", self.noto_path)
        self.font = load_noto(self.noto_path)
        self.gs = self.font.getGlyphSet()
        self.hmtx = self.font["hmtx"]
        self.vmtx = self.font["vmtx"]
        self.vorg = self.font["VORG"]
        self.src = {}
        self.remap_widths()
        self.split_shared()
        self.cmap = self.font.getBestCmap()
        self.owners = glyph_owners(
            self.font, prefer=lambda cp: (cp not in self.ms,
                                          not (0x3000 <= cp <= 0x9FFF or 0xFF00 <= cp <= 0xFFEF)))
        log(self.target, "glyphs", len(self.font.getGlyphOrder()), "cmap", len(self.cmap),
            "owned", len(self.owners))
        self.bounds = {}
        for g in self.font.getGlyphOrder():
            bp = BoundsPen(self.gs)
            self.gs[self.src.get(g, g)].draw(bp)
            self.bounds[g] = Box(*bp.bounds) if bp.bounds else None

    def remap_widths(self):
        """MS 側の幅区分に合わせて既定字形を半角/全角デザインに差し替える。"""
        hw = single_subst_map(self.font, {"hwid"})
        fw = single_subst_map(self.font, {"fwid"})
        n = Counter()
        for table in self.font["cmap"].tables:
            if not table.isUnicode():
                continue
            for cp, g in list(table.cmap.items()):
                r = self.ms.get(cp)
                if not r:
                    continue
                nb = width_bucket(self.hmtx[g][0], UPEM)
                if r["w"] == nb:
                    continue
                if r["w"] == "H" and g in hw and nb != "H":
                    table.cmap[cp] = hw[g]
                    n["hwid"] += 1
                elif r["w"] == "F" and g in fw and nb != "F":
                    table.cmap[cp] = fw[g]
                    n["fwid"] += 1
        self.report["width_remap"] = dict(n)
        log(self.target, "width remap", dict(n))

    def split_shared(self):
        """Noto で複数の文字が同じ字形を共有し、MS 側ではメトリクスが異なる場合は字形を複製する。
        (例: U+2027 と U+30FB が同一字形だが MS では半角/全角で異なる)"""
        uni = [t for t in self.font["cmap"].tables if t.isUnicode()]
        best = self.font.getBestCmap()
        by_glyph = defaultdict(list)
        for cp, g in best.items():
            if cp in self.ms:
                by_glyph[g].append(cp)

        def sig(cp):
            r = self.ms[cp]
            return (round(r["adv"], 3),) + tuple(round(r.get(k, 0), 2) for k in ("xMin", "xMax", "yMin", "yMax"))

        def prio(cp):          # 縦書き置換などを保つため、和文の文字に元の字形を残す
            return (0 if 0x3000 <= cp <= 0x9FFF or 0xFF00 <= cp <= 0xFFEF else 1, cp)

        order = list(self.font.getGlyphOrder())
        new = []
        for g, cps in by_glyph.items():
            if len(cps) < 2 or len({sig(c) for c in cps}) < 2:
                continue
            cps.sort(key=prio)
            keep_sig = sig(cps[0])
            for cp in cps[1:]:
                if sig(cp) == keep_sig:
                    continue
                ng = f"{g}.u{cp:04X}"
                self.src[ng] = g
                self.hmtx[ng] = self.hmtx[g]
                self.vmtx[ng] = self.vmtx[g]
                for t in uni:
                    if t.cmap.get(cp) == g:
                        t.cmap[cp] = ng
                new.append(ng)
        if new:
            self.font.setGlyphOrder(order + new)
            # CFF 側は元の名前で描画するので、glyphset には元字形を引けるようにしておく
        self.report["split_shared"] = len(new)
        log(self.target, "split shared glyphs", len(new))

    def nbucket(self, g):
        return width_bucket(self.hmtx[g][0], UPEM)

    def nvorg(self, g):
        g = self.src.get(g, g)
        return self.vorg.VOriginRecords.get(g, self.vorg.defaultVertOriginY)

    # ---- 統計 -------------------------------------------------------------
    @staticmethod
    def keys(cls, b):
        grp = group_of(cls)
        return [(cls, b), (cls, "*"), (grp, b), (grp, "*"), ("*", b), ("*", "*")]

    def lookup(self, table, cls, b, need=MIN_SAMPLES):
        for k in self.keys(cls, b):
            v = table.get(k)
            if v and v["n"] >= need:
                return v, k
        return None, None

    def pairs(self):
        """MS にもある cmap グリフの対応 (cp, glyph, MS 記録, Noto 枠, MS 枠)"""
        out = []
        for cp, g in self.cmap.items():
            r = self.ms.get(cp)
            if r is None:
                continue
            out.append((cp, g, r, self.bounds.get(g), ms_box(r)))
        return out

    def class_scale(self):
        """分類共通の倍率と（欧文系の）縦オフセット。"""
        acc = defaultdict(lambda: {"r": [], "dy": [], "dy_c": []})
        for cp, g, r, nb, mb in self.pairs():
            if not nb or not mb or nb.maxdim < 20 or mb.maxdim < 20:
                continue
            cls = r["cls"]
            ratio = mb.maxdim / nb.maxdim
            for k in self.keys(cls, r["w"]):
                a = acc[k]
                a["r"].append(ratio)
                a["_cls"] = cls
        scale = {}
        for k, a in acc.items():
            scale[k] = {"n": len(a["r"]), "s": med(a["r"])}
        # 縦オフセット（倍率確定後）
        dys = defaultdict(list)
        for cp, g, r, nb, mb in self.pairs():
            if not nb or not mb or nb.maxdim < 20 or mb.maxdim < 20:
                continue
            st, _ = self.lookup(scale, r["cls"], r["w"])
            s = st["s"]
            if abs(nb.y0) < 20 and abs(mb.y0) < 0.03 * UPEM:   # ベースラインに乗っている字
                d = mb.y0 - s * nb.y0
            else:
                d = None
            for k in self.keys(r["cls"], r["w"]):
                dys[k].append(d)
        for k, v in dys.items():
            v = [x for x in v if x is not None]
            if k in scale:
                scale[k]["dy_base"] = med(v, 0.0) if len(v) >= 2 else None
        self.scale = scale

    def class_scale_for(self, cls, b):
        st, k = self.lookup(self.scale, cls, b)
        dy = None
        for kk in self.keys(cls, b):
            v = self.scale.get(kk)
            if v and v.get("dy_base") is not None:
                dy = v["dy_base"]
                break
        return st["s"], (dy if dy is not None else 0.0)

    # ---- グリフ毎の変換 -----------------------------------------------------
    def plan_paired(self, g, cp, r, role_rec):
        """MS に対応字があるグリフ。role_rec は MS 側の計測（cmap または vert 字形）。"""
        cls = r["cls"]
        grp = group_of(cls)
        b = role_rec_bucket = width_bucket(role_rec["adv"] * UPEM, UPEM)
        adv = role_rec["adv"] * UPEM
        vadv = role_rec["vadv"] * UPEM
        nb = self.bounds.get(g)
        mb = ms_box(role_rec)
        s, dy_base = self.class_scale_for(cls, role_rec_bucket)
        vorg_ms = role_rec.get("vorg", self.ms_face["ascent"]) * UPEM
        if nb is None or mb is None:
            # 空白など
            return Plan(s, s, 0, dy_base, adv, vadv, vorg_ms, "paired-empty")
        if grp in EXACT_FIT_GROUPS:
            sx = mb.w / nb.w if nb.w > 5 else s
            sy = mb.h / nb.h if nb.h > 5 else s
            return Plan(sx, sy, mb.x0 - sx * nb.x0, mb.y0 - sy * nb.y0, adv, vadv,
                        vorg_ms, "paired-exact")
        tol = SCALE_TOLERANCE.get(grp, 0.10)
        base = s * nb.maxdim
        f = clamp(mb.maxdim / base, 1 - tol, 1 + tol) if base > 20 and mb.maxdim > 20 else 1.0
        sy = sx = s * f
        # 字面幅が MS より大きく溢れる場合は横方向のみ詰める（最大 25%）
        limit = mb.w + 0.02 * UPEM
        if sx * nb.w > limit and nb.w > 0:
            sx = max(limit / nb.w, sy * 0.75)
        tx = mb.cx - sx * nb.cx
        if grp in BASELINE_GROUPS:
            ty = dy_base
            how = "paired-baseline"
        else:
            ty = mb.cy - sy * nb.cy
            how = "paired-center"
        del b
        return Plan(sx, sy, tx, ty, adv, vadv, vorg_ms, how)

    def build_fallback_stats(self, plans):
        """MS 対応字の最終変換から、分類別の代表値を作る。"""
        acc = defaultdict(lambda: defaultdict(list))
        for cp, g, r, nb, mb in self.pairs():
            p = plans.get(g)
            if not p or not nb or not mb or p.how in ("paired-empty",):
                continue
            nadv = self.hmtx[g][0]
            vals = {
                "sx": p.sx, "sy": p.sy,
                "dy": p.ty,                                   # y' = sy*y + dy
                "dcx": (p.sx * nb.cx + p.tx - p.adv / 2) - p.sx * (nb.cx - nadv / 2),
                "dlsb": (p.sx * nb.x0 + p.tx) - p.sx * nb.x0,
                "drsb": (p.adv - (p.sx * nb.x1 + p.tx)) - p.sx * (nadv - nb.x1),
                "dvorg": p.vorg - p.sy * self.nvorg(g),
                "vadv_ratio": p.vadv / (self.vmtx[g][0] or UPEM),
            }
            for k in self.keys(r["cls"], r["w"]):
                for kk, v in vals.items():
                    acc[k][kk].append(v)
        stats = {}
        for k, d in acc.items():
            stats[k] = {kk: med(v) for kk, v in d.items()}
            stats[k]["n"] = len(d["sx"])
        self.fb = stats
        # 分類毎の MS 側の主な幅区分
        dom = defaultdict(Counter)
        for r in self.ms.values():
            dom[r["cls"]][r["w"]] += 1
            dom[group_of(r["cls"])][r["w"]] += 1
        self.dominant = {k: c.most_common(1)[0][0] for k, c in dom.items()}

    def plan_fallback(self, g, cp, role):
        cls = base_class(cp) if cp is not None else "other"
        grp = group_of(cls)
        nadv, _ = self.hmtx[g]
        nvadv, _ = self.vmtx[g]
        nb_ = self.nbucket(g)
        dom = self.dominant.get(cls) or self.dominant.get(grp) or "F"
        sb_mode = nb_ == "P" or (role == "cmap" and dom == "P" and nb_ != "Z")
        st, key = self.lookup(self.fb, cls, "P" if sb_mode else nb_)
        sx, sy = st["sx"], st["sy"]
        if grp in EXACT_FIT_GROUPS:       # 罫線類は em 比例のまま
            sx = sy = self.class_scale_for(cls, nb_)[0]
        nb = self.bounds.get(g)
        ty = st["dy"]
        vorg = sy * self.nvorg(g) + st["dvorg"]
        vadv = nvadv * st["vadv_ratio"] if abs(st["vadv_ratio"] - 1) > 0.02 else nvadv
        if nb is None:
            adv = nadv * sx if sb_mode else nadv
            return Plan(sx, sy, 0, ty, adv, vadv, vorg, f"fallback-empty{key}")
        if sb_mode:
            lsb = sx * nb.x0 + st["dlsb"]
            rsb = sx * (nadv - nb.x1) + st["drsb"]
            ink = sx * nb.w
            adv = max(lsb + ink + rsb, ink)
            tx = lsb - sx * nb.x0
        else:
            adv = nadv
            tx = adv / 2 + st["dcx"] - sx * nadv / 2
        return Plan(sx, sy, tx, ty, adv, vadv, vorg, f"fallback{key}")

    def plan_all(self):
        self.class_scale()
        plans = {}
        # (a) MS に対応がある cmap / vert グリフ
        for g, (cp, role, feat) in self.owners.items():
            r = self.ms.get(cp)
            if r is None:
                continue
            if role == "cmap":
                plans[g] = self.plan_paired(g, cp, r, r)
            elif role == "vert" and "vert" in r:
                plans[g] = self.plan_paired(g, cp, r, r["vert"])
        # (a') 縦書き用字形が縦書き専用文字 (U+FE11 等) の cmap と共有されている場合も、
        #      MS 側に縦書き用字形の計測があればそちらを優先する
        vmap = single_subst_map(self.font, {"vert", "vrt2"})
        for cp, r in self.ms.items():
            g = self.cmap.get(cp)
            vg = vmap.get(g)
            if not vg or "vert" not in r:
                continue
            p = plans.get(vg)
            if p is None or not (self.owners.get(vg, (None,))[0] in self.ms
                                 and self.owners[vg][1] == "cmap"):
                plans[vg] = self.plan_paired(vg, cp, r, r["vert"])
        self.build_fallback_stats(plans)
        # (b) それ以外
        for g in self.font.getGlyphOrder():
            if g in plans:
                continue
            cp, role, feat = self.owners.get(g, (None, "orphan", None))
            p = None
            if role == "cmap" and cp is not None:
                base = decompose_base(cp)
                bg = self.cmap.get(base) if base else None
                if bg in plans and base in self.ms and plans[bg].how.startswith("paired"):
                    q = plans[bg]
                    nbb, nbt = self.bounds.get(bg), self.bounds.get(g)
                    if nbb and nbt:
                        # 基底文字部分が MS の基底文字と同じ位置に来るよう同じ変換を使う
                        dx = (self.hmtx[g][0] - self.hmtx[bg][0]) / 2
                        p = Plan(q.sx, q.sy, q.tx + q.sx * (-dx) + 0, q.ty, q.adv, q.vadv,
                                 q.vorg, "decomposed")
            elif role == "other" and cp is not None:
                cg = self.cmap.get(cp)
                q = plans.get(cg)
                if q and q.how.startswith("paired") and self.hmtx[g][0] == self.hmtx[cg][0] \
                        and self.vmtx[g][0] == self.vmtx[cg][0]:
                    p = Plan(q.sx, q.sy, q.tx, q.ty, q.adv, q.vadv, q.vorg, "variant")
            if p is None:
                p = self.plan_fallback(g, cp, role)
            plans[g] = p
        self.plans = plans
        hows = Counter(p.how.split("(")[0] for p in plans.values())
        self.report["plans"] = dict(hows)
        log(self.target, "plans", dict(hows))

    # ---- 5. 出力 ----------------------------------------------------------
    def build_glyf(self):
        order = self.font.getGlyphOrder()
        glyf = newTable("glyf")
        glyf.glyphOrder = order
        glyf.glyphs = {}
        hmtx, vmtx = {}, {}
        for g in order:
            p = self.plans[g]
            pen = TTGlyphPen(None)
            tp = TransformPen(Cu2QuPen(pen, max_err=0.5, reverse_direction=True),
                              (p.sx, 0, 0, p.sy, p.tx, p.ty))
            self.gs[self.src.get(g, g)].draw(tp)
            gl = pen.glyph()
            gl.recalcBounds(glyf)
            glyf.glyphs[g] = gl
            adv = max(0, int(round(p.adv)))
            ymax = gl.yMax if gl.numberOfContours else 0
            xmin = gl.xMin if gl.numberOfContours else 0
            hmtx[g] = (adv, xmin)
            vmtx[g] = (max(0, int(round(p.vadv))), int(round(p.vorg - ymax)) if gl.numberOfContours else 0)
        return glyf, hmtx, vmtx

    def finalize(self):
        f = self.font
        log(self.target, "outlines -> TrueType")
        glyf, hmtx, vmtx = self.build_glyf()
        del f["CFF "]
        del f["VORG"]
        if "GPOS" in f:            # Noto の palt/kern 等は送り幅変更後は無効になるため削除
            del f["GPOS"]
        f.sfntVersion = "\x00\x01\x00\x00"
        f["glyf"] = glyf
        f["loca"] = newTable("loca")
        f["hmtx"].metrics = hmtx
        f["vmtx"].metrics = vmtx
        maxp = f["maxp"]
        maxp.tableVersion = 0x00010000
        for a in ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs",
                  "maxInstructionDefs", "maxStackElements", "maxSizeOfInstructions"):
            setattr(maxp, a, 0)
        maxp.maxZones = 1
        for a in ("maxPoints", "maxContours", "maxCompositePoints", "maxCompositeContours",
                  "maxComponentElements", "maxComponentDepth"):
            setattr(maxp, a, 0)
        head = f["head"]
        head.glyphDataFormat = 0
        head.unitsPerEm = UPEM
        gasp = newTable("gasp")
        gasp.version = 1
        gasp.gaspRange = {0xFFFF: 0x000F}
        f["gasp"] = gasp
        post = f["post"]
        post.formatType = 2.0
        post.extraNames = []
        post.mapping = {}
        post.glyphOrder = None
        self.set_metrics()
        self.set_base()
        self.set_names()

    def set_metrics(self):
        f, m = self.font, self.ms_face
        asc = int(round(m["ascent"] * UPEM))
        desc = UPEM - asc          # MS は ascent+descent = 1em
        os2, hhea, vhea, post = f["OS/2"], f["hhea"], f["vhea"], f["post"]
        hhea.ascent, hhea.descent, hhea.lineGap = asc, -desc, 0
        os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = asc, -desc, 0
        os2.usWinAscent, os2.usWinDescent = asc, desc
        os2.fsSelection &= ~(1 << 7)          # USE_TYPO_METRICS は MS と同じく立てない
        os2.sxHeight = int(round(m["xHeight"] * UPEM))
        os2.sCapHeight = int(round(m["capHeight"] * UPEM))
        os2.yStrikeoutPosition = int(round(m["strikeoutPosition"] * UPEM))
        os2.yStrikeoutSize = int(round(m["strikeoutSize"] * UPEM))
        os2.panose.bProportion = m["panose"]["bProportion"]
        os2.fsType = 0
        post.underlinePosition = int(round(m["underlinePosition"] * UPEM))
        post.underlineThickness = int(round(m["underlineThickness"] * UPEM))
        post.isFixedPitch = m["isFixedPitch"]
        # 縦書きの行メトリクスも MS と同じ値にする
        vhea.ascent = int(round(m["vheaAscent"] * UPEM))
        vhea.descent = int(round(m["vheaDescent"] * UPEM))
        vhea.lineGap = 0
        # Word 等は xAvgCharWidth を字送り計算に使うため、再計算せず MS の値を採用する
        os2.xAvgCharWidth = int(round(m["xAvgCharWidth"] * UPEM))

    def set_base(self):
        """BASE の基準線を新しい em 枠に合わせる。"""
        f = self.font
        if "BASE" not in f:
            return
        s, dy = self.class_scale_for("kanji", "F")
        st, _ = self.lookup(self.fb, "kanji", "F")
        sy, ty, sx = st["sy"], st["dy"], st["sx"]
        ideo = int(round(self.ms_face["descent"] * UPEM))      # 負値
        b = f["BASE"].table
        for axn in ("HorizAxis", "VertAxis"):
            ax = getattr(b, axn)
            if not ax:
                continue
            tags = ax.BaseTagList.BaselineTag
            for sr in ax.BaseScriptList.BaseScriptRecord:
                bv = sr.BaseScript.BaseValues
                if not bv:
                    continue
                for tag, c in zip(tags, bv.BaseCoord):
                    v = c.Coordinate
                    if axn == "HorizAxis":
                        c.Coordinate = {"ideo": ideo, "romn": 0}.get(tag, int(round(sy * v + ty)))
                    else:
                        c.Coordinate = {"ideo": 0, "romn": -ideo}.get(
                            tag, int(round(UPEM / 2 + sx * (v - UPEM / 2))))

    def set_names(self):
        f = self.font
        name = f["name"]
        bold = self.weight.lower() == "bold"
        sub = "Bold" if bold else "Regular"
        fam, fam_ja = self.family, self.family_ja
        ps = fam.replace(" ", "") + "-" + sub
        version = "Version 1.000"
        noto_copy = name.getDebugName(0) or ""
        src = os.path.basename(self.noto_path)
        copyright_ = (noto_copy + " Modified in 2026 by the NS-Font project "
                      "(metrics adjusted to match the layout of common Japanese system fonts).")
        lic = name.getDebugName(13) or "This Font Software is licensed under the SIL Open Font License, Version 1.1."
        lic_url = name.getDebugName(14) or "https://openfontlicense.org"
        name.names = []
        recs = {
            0: copyright_, 1: fam, 2: sub, 3: f"{version};NS-Font;{ps}", 4: f"{fam} {sub}" if bold else fam,
            5: f"{version}; based on {src}", 6: ps, 13: lic, 14: lic_url,
        }
        for nid, s in recs.items():
            name.setName(s, nid, 3, 1, 0x409)
        name.setName(fam_ja, 1, 3, 1, 0x411)
        name.setName(sub, 2, 3, 1, 0x411)
        name.setName(f"{fam_ja} {sub}" if bold else fam_ja, 4, 3, 1, 0x411)
        os2 = f["OS/2"]
        os2.usWeightClass = 700 if bold else 400
        os2.fsSelection = (os2.fsSelection & ~0b1100001) | (0b100000 if bold else 0b1000000)
        f["head"].macStyle = 1 if bold else 0

    def write_report(self, out_dir):
        rows = []
        for k, v in sorted(self.scale.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
            fb = self.fb.get(k, {})
            rows.append({"class": k[0], "width": k[1], "n": v["n"], "scale": v["s"],
                         "dy_base": v.get("dy_base"), **{kk: fb.get(kk) for kk in
                                                         ("sx", "sy", "dy", "dcx", "dlsb", "drsb")}})
        rep = {"target": self.target, "weight": self.weight, "family": self.family,
               "summary": self.report, "classes": rows}
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"transform_{self.target}-{self.weight}.json"), "w",
                  encoding="utf-8") as fp:
            json.dump(rep, fp, ensure_ascii=False, indent=1)
        lines = [f"# {self.family} {self.weight} 変換パラメータ", "",
                 f"- 原本: `{os.path.basename(self.noto_path)}` (Noto CJK JP)",
                 f"- メトリクス基準: {self.ms_face['name']}",
                 f"- 半角/全角字形への差し替え: {self.report.get('width_remap')}",
                 f"- グリフ毎の変換方式の内訳: {self.report.get('plans')}", "",
                 "`scale` は分類共通倍率 (MS 字面最大寸法 / Noto 字面最大寸法 の中央値)。",
                 "`sx`/`sy`/`dy`/`dcx`/`dlsb`/`drsb` は MS 非収録字に使う代表値（1000 upem 単位）。", "",
                 "| 分類 | 幅 | 字数 | scale | sx | sy | dy | dcx | dlsb | drsb |",
                 "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]

        def fm(v, d=3):
            return "" if v is None else f"{v:.{d}f}"
        for r in rows:
            lines.append(f"| {r['class']} | {r['width']} | {r['n']} | {fm(r['scale'])} | {fm(r['sx'])} | "
                         f"{fm(r['sy'])} | {fm(r['dy'], 1)} | {fm(r['dcx'], 1)} | {fm(r['dlsb'], 1)} | "
                         f"{fm(r['drsb'], 1)} |")
        with open(os.path.join(out_dir, f"transform_{self.target}-{self.weight}.md"), "w",
                  encoding="utf-8") as fp:
            fp.write("\n".join(lines) + "\n")

    def run(self):
        self.prepare()
        self.plan_all()
        self.finalize()
        os.makedirs(self.args.out, exist_ok=True)
        fn = self.family.replace(" ", "") + "-" + ("Bold" if self.weight.lower() == "bold" else "Regular")
        path = os.path.join(self.args.out, fn + ".ttf")
        log(self.target, "save", path)
        self.font.save(path)
        self.write_report(self.args.docs)
        log(self.target, "done")
        return path


def _run(job):
    target, weight, args = job
    return Builder(target, weight, args).run()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", default=DEFAULT_TARGETS, help=f"{list(TARGETS)}")
    ap.add_argument("--weights", default="Regular", help="Regular,Bold など（Noto の .ttc 名）")
    ap.add_argument("--noto-dir", default=os.path.join(ROOT, "fonts", "noto"))
    ap.add_argument("--ms-data", default=os.path.join(ROOT, "build", "ms"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    ap.add_argument("-j", "--jobs", type=int, default=1)
    args = ap.parse_args()
    jobs = [(t, w, args) for t in args.targets for w in args.weights.split(",")]
    if args.jobs > 1:
        from multiprocessing import Pool
        with Pool(args.jobs) as pool:
            for p in pool.imap_unordered(_run, jobs):
                print(p)
    else:
        for j in jobs:
            print(_run(j))


if __name__ == "__main__":
    main()
