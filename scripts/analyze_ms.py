#!/usr/bin/env python3
"""MS ゴシック / MS P ゴシック / MS 明朝 / MS P 明朝 の全収録文字を計測・分類する。

出力:
  build/ms/<face>.json   グリフ単位の計測値（MS フォント由来の生データ。git 管理外）
  docs/ms_classes.md     分類ごとの統計表（要約のみ）
  docs/ms_classes.json   同上（機械可読）

計測値はすべて em 比 (値 / unitsPerEm) で保存する。
"""
import argparse
import json
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nsfont.classify import base_class, group_of, width_bucket  # noqa: E402
from nsfont.fontutil import open_face, single_subst_map, glyph_bounds  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FACES = {
    "MSGothic": ("msgothic.ttc", "MS Gothic"),
    "MSPGothic": ("msgothic.ttc", "MS PGothic"),
    "MSUIGothic": ("msgothic.ttc", "MS UI Gothic"),
    "MSMincho": ("msmincho.ttc", "MS Mincho"),
    "MSPMincho": ("msmincho.ttc", "MS PMincho"),
}


def glyph_record(font, gname, upem):
    adv, _ = font["hmtx"][gname]
    vadv, tsb = font["vmtx"][gname] if "vmtx" in font else (upem, 0)
    b = glyph_bounds(font, gname)
    r = {"adv": adv / upem, "vadv": vadv / upem}
    if b:
        x0, y0, x1, y1 = b
        r.update(xMin=x0 / upem, yMin=y0 / upem, xMax=x1 / upem, yMax=y1 / upem,
                 tsb=tsb / upem, vorg=(tsb + y1) / upem)
    return r


def analyze_face(font):
    upem = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    vert = single_subst_map(font, {"vert", "vrt2"})
    glyphs = {}
    for cp, gn in sorted(cmap.items()):
        rec = glyph_record(font, gn, upem)
        rec["cls"] = base_class(cp)
        rec["w"] = width_bucket(rec["adv"] * upem, upem)
        if gn in vert:
            rec["vert"] = glyph_record(font, vert[gn], upem)
        glyphs[cp] = rec
    os2, hhea = font["OS/2"], font["hhea"]
    face = {
        "name": font["name"].getDebugName(4),
        "unitsPerEm": upem,
        "ascent": hhea.ascent / upem, "descent": hhea.descent / upem,
        "lineGap": hhea.lineGap / upem,
        "typoAscender": os2.sTypoAscender / upem, "typoDescender": os2.sTypoDescender / upem,
        "winAscent": os2.usWinAscent / upem, "winDescent": os2.usWinDescent / upem,
        "xHeight": getattr(os2, "sxHeight", 0) / upem,
        "capHeight": getattr(os2, "sCapHeight", 0) / upem,
        "underlinePosition": font["post"].underlinePosition / upem,
        "underlineThickness": font["post"].underlineThickness / upem,
        "strikeoutPosition": os2.yStrikeoutPosition / upem,
        "strikeoutSize": os2.yStrikeoutSize / upem,
        "isFixedPitch": font["post"].isFixedPitch,
        "xAvgCharWidth": os2.xAvgCharWidth / upem,
        "panose": vars(os2.panose),
        "vheaAscent": font["vhea"].ascent / upem if "vhea" in font else None,
        "vheaDescent": font["vhea"].descent / upem if "vhea" in font else None,
    }
    return face, glyphs


def summarize(glyphs):
    """分類 (基本分類, 幅区分) ごとの統計。"""
    buckets = defaultdict(list)
    for cp, r in glyphs.items():
        buckets[(r["cls"], r["w"])].append(r)
    out = []
    for (cls, w), rs in sorted(buckets.items(), key=lambda kv: (group_of(kv[0][0]), kv[0])):
        inked = [r for r in rs if "xMin" in r]

        def med(key, src=inked):
            v = [key(r) for r in src]
            return round(statistics.median(v), 4) if v else None

        out.append({
            "class": cls, "group": group_of(cls), "width": w, "count": len(rs),
            "adv": med(lambda r: r["adv"], rs),
            "lsb": med(lambda r: r["xMin"]),
            "rsb": med(lambda r: r["adv"] - r["xMax"]),
            "inkW": med(lambda r: r["xMax"] - r["xMin"]),
            "inkH": med(lambda r: r["yMax"] - r["yMin"]),
            "yMin": med(lambda r: r["yMin"]),
            "yMax": med(lambda r: r["yMax"]),
            "cx": med(lambda r: (r["xMin"] + r["xMax"]) / 2 - r["adv"] / 2),
            "cy": med(lambda r: (r["yMin"] + r["yMax"]) / 2),
            "vadv": med(lambda r: r["vadv"], rs),
            "tsb": med(lambda r: r["tsb"]),
        })
    return out


def write_markdown(path, faces):
    lines = ["# MS 系フォント 分類別メトリクス", "",
             "`scripts/analyze_ms.py` で生成。値はすべて em 比（1.0 = 1em）の中央値。",
             "`lsb`/`rsb` は左右の余白、`inkW`/`inkH` は字面の幅/高さ、",
             "`cx` は送り幅中心からの字面中心のずれ、`cy` は字面中心の高さ、`tsb` は縦書き時の上余白。",
             "幅区分: H=半角, F=全角, P=プロポーショナル, Z=幅0", ""]
    for key, (face, summary) in faces.items():
        lines += [f"## {face['name']}", "",
                  f"- unitsPerEm {face['unitsPerEm']} / ascent {face['ascent']:.4f} / "
                  f"descent {face['descent']:.4f} / lineGap {face['lineGap']:.4f}",
                  f"- xHeight {face['xHeight']:.4f} / capHeight {face['capHeight']:.4f} / "
                  f"isFixedPitch {face['isFixedPitch']}", "",
                  "| 分類 | グループ | 幅 | 字数 | 送り幅 | lsb | rsb | inkW | inkH | yMin | yMax | cx | cy | 縦送り | tsb |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for s in summary:
            def f(v):
                return "" if v is None else f"{v:.3f}"
            lines.append(f"| {s['class']} | {s['group']} | {s['width']} | {s['count']} | "
                         + " | ".join(f(s[k]) for k in ("adv", "lsb", "rsb", "inkW", "inkH", "yMin",
                                                        "yMax", "cx", "cy", "vadv", "tsb")) + " |")
        lines.append("")
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ms-dir", default=os.path.join(ROOT, "fonts", "ms"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "ms"))
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.docs, exist_ok=True)
    report = {}
    for key, (fn, name) in FACES.items():
        path = os.path.join(args.ms_dir, fn)
        if not os.path.exists(path):
            print(f"skip {key}: {path} がありません", file=sys.stderr)
            continue
        font = open_face(path, name)
        face, glyphs = analyze_face(font)
        with open(os.path.join(args.out, key + ".json"), "w") as fp:
            json.dump({"face": face, "glyphs": glyphs}, fp)
        summary = summarize(glyphs)
        report[key] = (face, summary)
        print(f"{key}: {len(glyphs)} chars, {len(summary)} classes")
    write_markdown(os.path.join(args.docs, "ms_classes.md"), report)
    with open(os.path.join(args.docs, "ms_classes.json"), "w", encoding="utf-8") as fp:
        json.dump({k: {"face": f, "classes": s} for k, (f, s) in report.items()}, fp,
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
