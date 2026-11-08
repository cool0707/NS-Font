"""Noto CJK に無い文字を、同じ OFL ライセンスの Noto 欧文・記号系フォントから補う。

- ウェイト: CJK 側の欧文の線幅（「l」の縦画、記号は「+」の縦画）を実測し、
  補完フォントの各ウェイトの線幅（CJK の単位に換算）が最も近いものを選ぶ。
  残った差と、Regular しかないフォント（Math / Symbols2）の差は、
  輪郭を法線方向にずらす太らせ/細らせ処理（FreeType の FT_Outline_Embolden と同じ方式）で補正する。
- 大きさ: 欧文フォントの「H」の高さを CJK 側の「H」に揃える倍率で CJK の単位に換算する
  （記号・各言語フォントも同じ倍率。いずれも Noto Sans/Serif と大きさが揃うよう設計されている）。
- 字幅: 補完先 (MS) の字面幅に収まらない欧文字形は、SemiCondensed → Condensed →
  ExtraCondensed の順に幅の狭い字形を選ぶ（等幅版の半角に入れるキリル文字など）。
"""
import math
import os
import statistics
import unicodedata

from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.transformPen import TransformPen

WEIGHT_NAMES = ["Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold",
                "ExtraBold", "Black"]
WIDTHS = ["", "SemiCondensed", "Condensed", "ExtraCondensed"]

# (ファミリー, 種類)  種類: text=欧文（「l」で線幅を測る）, symbol=記号（「+」で測る）, script=各言語
CHAINS = {
    "NotoSansCJK": [("NotoSans", "text"), ("NotoSansMath", "symbol"), ("NotoSansSymbols", "symbol"),
                    ("NotoSansSymbols2", "symbol"), ("NotoSansBengali", "script"),
                    ("NotoSansThai", "script"), ("NotoSansKhmer", "script"),
                    ("NotoSansArabic", "script")],
    "NotoSerifCJK": [("NotoSerif", "text"), ("NotoSansMath", "symbol"), ("NotoSansSymbols", "symbol"),
                     ("NotoSansSymbols2", "symbol"), ("NotoSerifBengali", "script"),
                     ("NotoSerifThai", "script"), ("NotoSerifKhmer", "script"),
                     ("NotoNaskhArabic", "script")],
}
MAX_EMBOLDEN = 60      # 補完フォント単位での片側の最大補正量

# 線幅の基準にする文字（字面高さの 30% の位置で切ったときの最初の縦画）
REF = {"upper": "LHEIT", "lower": "lnhim"}
SLICE = 0.3


def file_name(fam, width, weight):
    if width and weight == "Regular":
        return f"{fam}-{width}.ttf"
    return f"{fam}-{width}{weight}.ttf"


# ---------------------------------------------------------------------------
# 線幅の計測
# ---------------------------------------------------------------------------
class _FlattenPen(BasePen):
    def __init__(self, glyphSet=None):
        super().__init__(glyphSet)
        self.polys, self.cur = [], []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, 13):
            t = i / 12
            mt = 1 - t
            self.cur.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                             mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, 9):
            t = i / 8
            mt = 1 - t
            self.cur.append((mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                             mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]))

    def _closePath(self):
        if self.cur:
            self.polys.append(self.cur)
        self.cur = []

    _endPath = _closePath


def stem_width(draw, frac):
    """draw(pen) の輪郭を、字面の高さ frac の位置で水平に切ったときの最初の黒地の幅。"""
    bp = BoundsPen(None)
    draw(bp)
    if not bp.bounds:
        return None
    x0, y0, x1, y1 = bp.bounds
    y = y0 + (y1 - y0) * frac
    fp = _FlattenPen()
    draw(fp)
    xs = []
    for poly in fp.polys:
        n = len(poly)
        for i in range(n):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
    xs.sort()
    spans = [xs[i + 1] - xs[i] for i in range(0, len(xs) - 1, 2)]
    return spans[0] if spans else None


def cap_height(draw):
    bp = BoundsPen(None)
    draw(bp)
    return bp.bounds[3] - bp.bounds[1] if bp.bounds else None


# ---------------------------------------------------------------------------
# 太らせ / 細らせ
# ---------------------------------------------------------------------------
def embolden(ops, d, fx=1.0, fy=1.0):
    """RecordingPen の値を、輪郭の外向き法線方向に d だけずらす（d<0 で細く）。
    TrueType の輪郭向き（外側=時計回り）を前提とする（CFF の向きなら d の符号を反転して渡す）。
    fx/fy はずらし量の x/y 成分への係数（fy=0 なら縦画だけを太らせる）。"""
    if abs(d) < 0.5:
        return ops
    out, contour = [], []

    def flush(closing):
        if not contour:
            return
        pts = [p for _, args in contour for p in args if p is not None]
        n = len(pts)
        new = list(pts)
        if n >= 3:
            for i, p in enumerate(pts):
                j = (i - 1) % n
                while j != i and pts[j] == p:
                    j = (j - 1) % n
                k = (i + 1) % n
                while k != i and pts[k] == p:
                    k = (k + 1) % n
                if j == i or k == i:
                    continue
                a, b = pts[j], pts[k]
                d1 = (p[0] - a[0], p[1] - a[1])
                d2 = (b[0] - p[0], b[1] - p[1])
                l1, l2 = math.hypot(*d1), math.hypot(*d2)
                n1 = (-d1[1] / l1, d1[0] / l1)
                n2 = (-d2[1] / l2, d2[0] / l2)
                dot = n1[0] * n2[0] + n1[1] * n2[1]
                if 1 + dot < 0.15:
                    sx, sy = n1[0] * d, n1[1] * d
                else:
                    f = d / (1 + dot)
                    sx, sy = (n1[0] + n2[0]) * f, (n1[1] + n2[1]) * f
                new[i] = (p[0] + sx * fx, p[1] + sy * fy)
        it = iter(new)
        for op, args in contour:
            out.append((op, tuple(None if a is None else next(it) for a in args)))
        contour.clear()

    for op, args in ops:
        if op in ("closePath", "endPath"):
            flush(op == "closePath")
            out.append((op, args))
        elif op == "moveTo":
            flush(False)
            contour.append((op, args))
        else:
            contour.append((op, args))
    flush(False)
    return out


class SuppGlyph:
    """CJK の単位に換算・線幅補正済みの補完グリフ。draw(pen) で描ける。"""
    __slots__ = ("ops", "adv", "source")

    def __init__(self, ops, adv, source):
        self.ops, self.adv, self.source = ops, adv, source

    def draw(self, pen):
        rp = RecordingPen()
        rp.value = self.ops
        rp.replay(pen)


class Supplement:
    def __init__(self, extra_dir, cjk_family, cjk_draw):
        """cjk_draw(ch) は CJK 側の文字 ch を描く関数（無ければ None を返す）。"""
        self.dir = extra_dir
        self.chain = CHAINS[cjk_family]
        self.cache = {}
        self.choice = {}            # family -> (weight, {"upper"/"lower"/"other": embolden})
        text_fam = self.chain[0][0]
        # CJK 側の基準（大文字・小文字それぞれの縦画、記号は「+」の縦画）
        self.T = {grp: {c: stem_width(cjk_draw(c), SLICE) for c in chars if cjk_draw(c)}
                  for grp, chars in REF.items()}
        self.T_sym = stem_width(cjk_draw("+"), 0.88)
        H_cjk = cap_height(cjk_draw("H"))
        H_sup = cap_height(self._drawer(text_fam, "", "Regular", "H"))
        self.k = H_cjk / H_sup
        self.text_fam = text_fam

    # ---- フォント ---------------------------------------------------------
    def font(self, fam, width, weight):
        key = (fam, width, weight)
        if key not in self.cache:
            p = os.path.join(self.dir, file_name(fam, width, weight))
            if os.path.exists(p):
                f = TTFont(p, lazy=True)
                self.cache[key] = (f, f.getGlyphSet(), f.getBestCmap())
            else:
                self.cache[key] = None
        return self.cache[key]

    def _drawer(self, fam, width, weight, ch):
        f = self.font(fam, width, weight)
        if not f or ord(ch) not in f[2]:
            return None
        gs, g = f[1], f[2][ord(ch)]
        return lambda pen: gs[g].draw(pen)

    def weights(self, fam):
        return [w for w in WEIGHT_NAMES if self.font(fam, "", w)]

    def _diffs(self, fam, kind, weight):
        """(CJK 目標 − 補完フォントの線幅×k) を基準文字ごとに求める（CJK 単位）。
        自身に基準文字が無いフォントは欧文フォントの同ウェイトで代用する。"""
        out = {}
        if kind == "symbol":
            dr = self._drawer(fam, "", weight, "+") or self._drawer(self.text_fam, "", weight, "+") \
                or self._drawer(self.text_fam, "", "Regular", "+")
            s = stem_width(dr, 0.88) if dr else None
            if s and self.T_sym:
                out["other"] = [self.T_sym - s * self.k]
            return out
        src = fam if kind == "text" else self.text_fam
        if not self.font(src, "", weight):
            src, weight = self.text_fam, ("Regular" if not self.font(self.text_fam, "", weight) else weight)
        for grp, targets in self.T.items():
            v = []
            for c, t in targets.items():
                dr = self._drawer(src, "", weight, c)
                s = stem_width(dr, SLICE) if dr else None
                if s and t:
                    v.append(t - s * self.k)
            if v:
                out[grp] = v
        if out:
            out["other"] = [x for v in out.values() for x in v]
        return out

    def pick(self, fam, kind):
        if fam in self.choice:
            return self.choice[fam]
        best = None
        for w in self.weights(fam):
            diffs = self._diffs(fam, kind, w)
            if not diffs:
                continue
            err = statistics.mean(abs(x) for x in diffs["other"])
            if best is None or err < best[0]:
                best = (err, w, diffs)
        if best is None:
            ws = self.weights(fam)
            self.choice[fam] = (("Regular" if "Regular" in ws else ws[0]) if ws else None, {})
        else:
            _, w, diffs = best
            d = {g: max(-MAX_EMBOLDEN, min(MAX_EMBOLDEN, statistics.median(v) / 2 / self.k))
                 for g, v in diffs.items()}
            self.choice[fam] = (w, d)
        return self.choice[fam]

    # ---- グリフ取得 -------------------------------------------------------
    def glyph(self, cp, target_w=None):
        """cp の補完グリフ。target_w (CJK 単位の字面幅) を超える欧文は幅の狭い字形を選ぶ。"""
        cat = unicodedata.category(chr(cp))
        grp = "upper" if cat in ("Lu", "Lt") else "lower" if cat == "Ll" else "other"
        for fam, kind in self.chain:
            weight, dd = self.pick(fam, kind)
            d = dd.get(grp, dd.get("other", 0.0))
            if weight is None:
                continue
            base = self.font(fam, "", weight)
            if not base or cp not in base[2]:
                continue
            widths = WIDTHS if kind == "text" else [""]
            cand = None
            for wd in widths:
                f = self.font(fam, wd, weight)
                if not f or cp not in f[2]:
                    continue
                g = f[2][cp]
                rp = DecomposingRecordingPen(f[1])
                f[1][g].draw(rp)
                ops = embolden(rp.value, d)
                out = RecordingPen()
                tp = TransformPen(out, (self.k, 0, 0, self.k, 0, 0))
                tmp = RecordingPen()
                tmp.value = ops
                tmp.replay(tp)
                adv = f[0]["hmtx"][g][0] * self.k
                bp = BoundsPen(None)
                out.replay(bp)
                w = (bp.bounds[2] - bp.bounds[0]) if bp.bounds else 0
                cand = SuppGlyph(out.value, adv, f"{file_name(fam, wd, weight)}"
                                 + (f" {d:+.0f}" if abs(d) >= 0.5 else ""))
                if target_w is None or w <= target_w * 1.08:
                    break
            if cand:
                return cand
        return None
