#!/usr/bin/env python3
"""TTF から OTF (CFF アウトライン) / WOFF2 を作る。

  python3 scripts/convert.py otf   out_dir a.ttf b.ttf ...
  python3 scripts/convert.py woff2 out_dir a.ttf b.ttf ...

OTF: TrueType の 2 次ベジエ輪郭を 3 次ベジエに戻して (qu2cu) CFF にし、
     cffsubr があればサブルーチン化してサイズを抑える。縦書き原点は VORG 表に入れる。
WOFF2: TTF をそのまま WOFF2 (glyf 変換 + Brotli) に圧縮する。
"""
import os
import sys

from fontTools.ttLib import TTFont, newTable
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.t2CharStringPen import T2CharStringPen


def to_otf(src, dst):
    f = TTFont(src)
    gs = f.getGlyphSet()
    glyf, hmtx = f["glyf"], f["hmtx"]
    order = f.getGlyphOrder()
    charstrings = {}
    vorg = {}
    for g in order:
        pen = T2CharStringPen(hmtx[g][0], gs)
        # TrueType は時計回り、CFF は反時計回りが外側輪郭
        gs[g].draw(Qu2CuPen(pen, max_err=0.5, all_cubic=True, reverse_direction=True))
        charstrings[g] = pen.getCharString()
        gl = glyf[g]
        if "vmtx" in f and gl.numberOfContours:
            vorg[g] = f["vmtx"][g][1] + gl.yMax
    name = f["name"]
    ps = name.getDebugName(6)
    info = {
        "FullName": name.getDebugName(4),
        "FamilyName": name.getDebugName(1),
        "Weight": name.getDebugName(2),
        "version": f"{f['head'].fontRevision:.3f}",
        "Notice": "",
        "isFixedPitch": f["post"].isFixedPitch,
        "UnderlinePosition": f["post"].underlinePosition,
        "UnderlineThickness": f["post"].underlineThickness,
    }
    for t in ("glyf", "loca", "gasp", "cvt ", "fpgm", "prep"):
        if t in f:
            del f[t]
    f.sfntVersion = "OTTO"
    fb = FontBuilder(font=f, isTTF=False)
    fb.setupCFF(ps, info, charstrings, {})
    maxp = f["maxp"]
    maxp.tableVersion = 0x00005000
    f["post"].formatType = 3.0
    if vorg:
        t = newTable("VORG")
        t.majorVersion, t.minorVersion = 1, 0
        default = f["OS/2"].sTypoAscender
        t.defaultVertOriginY = default
        t.VOriginRecords = {g: v for g, v in vorg.items() if v != default}
        t.numVertOriginYMetrics = len(t.VOriginRecords)
        f["VORG"] = t
    try:
        import cffsubr
        cffsubr.subroutinize(f)
    except ImportError:
        print("  (cffsubr が無いのでサブルーチン化しません: pip install cffsubr)", file=sys.stderr)
    f.save(dst)
    return dst


def to_woff2(src, dst):
    f = TTFont(src)
    f.flavor = "woff2"
    f.save(dst)
    return dst


def main():
    if len(sys.argv) < 4 or sys.argv[1] not in ("otf", "woff2"):
        sys.exit(__doc__)
    kind, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for src in sys.argv[3:]:
        base = os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(out, f"{base}.{kind}")
        (to_otf if kind == "otf" else to_woff2)(src, dst)
        print(f"{dst}: {os.path.getsize(dst) / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
