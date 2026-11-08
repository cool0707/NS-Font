"""収録字の範囲（日本語向け）。

漢字は MS 系フォントの収録字 ∪ JIS X 0213 (第1〜4水準) ∪ CP932 に限定し、
仮名・記号・欧文など漢字以外は Noto にあるものをすべて残す（ハングルは除く）。
"""
import glob
import json
import os

HANGUL = [(0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F), (0xAC00, 0xD7FF),
          (0xFFA0, 0xFFDC)]

KANJI = [(0x2E80, 0x2FDF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF),
         (0x20000, 0x3FFFF)]

# 残す GSUB feature。aalt/jp78/jp83/nlck/hist 等の異体字切替は字形数が多いため除外する
# （jp90 は MS 系も持っているので残す）
LAYOUT_FEATURES = ["ccmp", "liga", "dlig", "calt", "vert", "vrt2", "hwid", "fwid", "pwid",
                   "ruby", "jp90"]


def _in(cp, ranges):
    return any(lo <= cp <= hi for lo, hi in ranges)


def jis_chars():
    out = set()
    for pre in (b"", b"\x8f"):                       # JIS X 0213 第1面 / 第2面
        for a in range(0xA1, 0xFF):
            for b in range(0xA1, 0xFF):
                try:
                    out.update(map(ord, (pre + bytes([a, b])).decode("euc_jis_2004")))
                except UnicodeDecodeError:
                    pass
    for a in list(range(0x81, 0xA0)) + list(range(0xE0, 0xFD)):   # CP932 (NEC/IBM 拡張含む)
        for b in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            try:
                out.update(map(ord, bytes([a, b]).decode("cp932")))
            except UnicodeDecodeError:
                pass
    return out


def ms_chars(ms_data_dir):
    out = set()
    for p in glob.glob(os.path.join(ms_data_dir, "*.json")):
        with open(p) as fp:
            out.update(int(k) for k in json.load(fp)["glyphs"])
    return out


def keep_predicate(ms_data_dir, full=False):
    if full:
        return lambda cp: not _in(cp, HANGUL)
    allowed = jis_chars() | ms_chars(ms_data_dir)
    return lambda cp: not _in(cp, HANGUL) and (not _in(cp, KANJI) or cp in allowed)
