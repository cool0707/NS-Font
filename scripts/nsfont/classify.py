"""文字の分類。

分類は 2 段階:
  1. 文字種 (script / block / 字形の性格) による「基本分類」
  2. MS フォント側の送り幅による「幅区分」 (H=半角, F=全角, P=プロポーショナル, Z=幅0)

統計はまず「基本分類 + 幅区分」で取り、サンプル不足の場合は基本分類のみ →
上位グループ (GROUP_OF) → 全体 の順にフォールバックする。
"""
import unicodedata

# (開始, 終了, 基本分類)  ※上から順に評価
_RANGES = [
    (0x0020, 0x0020, "space"),
    (0x0030, 0x0039, "digit"),
    (0x0041, 0x005A, "latin_upper"),
    (0x0061, 0x007A, "latin_lower"),
    (0x0021, 0x007E, "ascii_punct"),
    (0x00A0, 0x00A0, "space"),
    (0x00A1, 0x00BF, "latin1_symbol"),
    (0x00D7, 0x00D7, "math"),
    (0x00F7, 0x00F7, "math"),
    (0x00C0, 0x00DE, "latin_ext_upper"),
    (0x00DF, 0x00FF, "latin_ext_lower"),
    (0x0100, 0x024F, "latin_ext"),        # 大小は後で判定
    (0x0250, 0x02AF, "ipa"),
    (0x02B0, 0x02FF, "modifier"),
    (0x0300, 0x036F, "combining"),
    (0x0370, 0x03FF, "greek"),
    (0x0400, 0x04FF, "cyrillic"),
    (0x1E00, 0x1EFF, "latin_ext"),
    (0x2000, 0x200F, "space"),
    (0x2010, 0x2027, "general_punct"),
    (0x2028, 0x202F, "space"),
    (0x2030, 0x206F, "general_punct"),
    (0x2070, 0x209F, "superscript"),
    (0x20A0, 0x20CF, "currency"),
    (0x20D0, 0x20FF, "combining"),
    (0x2100, 0x214F, "letterlike"),
    (0x2150, 0x218F, "number_forms"),
    (0x2190, 0x21FF, "arrows"),
    (0x2200, 0x22FF, "math"),
    (0x2300, 0x23FF, "misc_technical"),
    (0x2400, 0x245F, "control_pictures"),
    (0x2460, 0x24FF, "enclosed"),
    (0x2500, 0x257F, "box_drawing"),
    (0x2580, 0x259F, "block"),
    (0x25A0, 0x25FF, "geometric"),
    (0x2600, 0x27BF, "misc_symbols"),
    (0x27C0, 0x2BFF, "math"),
    (0x2E80, 0x2FDF, "radical"),
    (0x2FF0, 0x2FFF, "radical"),
    (0x3000, 0x3000, "ideo_space"),
    (0x3001, 0x3003, "cjk_punct_low"),     # 、。〃
    (0x3004, 0x3007, "cjk_symbol"),
    (0x3008, 0x3011, "cjk_bracket"),
    (0x3012, 0x3013, "cjk_symbol"),
    (0x3014, 0x301B, "cjk_bracket"),
    (0x301C, 0x303F, "cjk_symbol"),
    (0x3041, 0x309F, "hiragana"),
    (0x30A0, 0x30FF, "katakana"),
    (0x3100, 0x31BF, "bopomofo"),
    (0x31F0, 0x31FF, "katakana"),
    (0x3200, 0x32FF, "cjk_enclosed"),
    (0x3300, 0x33FF, "cjk_compat"),
    (0x3400, 0x4DBF, "kanji"),
    (0x4DC0, 0x4DFF, "misc_symbols"),
    (0x4E00, 0x9FFF, "kanji"),
    (0xE000, 0xF8FF, "pua"),
    (0xF900, 0xFAFF, "kanji"),
    (0xFE10, 0xFE1F, "vertical_form"),
    (0xFE30, 0xFE4F, "vertical_form"),
    (0xFE50, 0xFE6F, "small_form"),
    (0xFF01, 0xFF0F, "fw_punct"),
    (0xFF10, 0xFF19, "fw_digit"),
    (0xFF1A, 0xFF20, "fw_punct"),
    (0xFF21, 0xFF3A, "fw_upper"),
    (0xFF3B, 0xFF40, "fw_punct"),
    (0xFF41, 0xFF5A, "fw_lower"),
    (0xFF5B, 0xFF60, "fw_punct"),
    (0xFF61, 0xFF65, "hw_punct"),
    (0xFF66, 0xFF9F, "hw_katakana"),
    (0xFFA0, 0xFFDF, "hw_other"),
    (0xFFE0, 0xFFE6, "fw_symbol"),
    (0xFFE8, 0xFFEF, "hw_symbol"),
    (0x1F100, 0x1F2FF, "cjk_enclosed"),
    (0x1F300, 0x1FAFF, "misc_symbols"),
    (0x20000, 0x3FFFF, "kanji"),
]

SMALL_KANA = set("ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿｧｨｩｪｫｬｭｮｯ")

# 基本分類 → 上位グループ（統計が足りない時のフォールバック先）
GROUP_OF = {
    "latin_upper": "latin", "latin_lower": "latin", "digit": "latin",
    "latin_ext_upper": "latin", "latin_ext_lower": "latin",
    "ipa": "latin", "modifier": "latin_symbol",
    "greek_upper": "latin", "greek_lower": "latin",
    "cyrillic_upper": "latin", "cyrillic_lower": "latin",
    "ascii_punct": "latin_symbol", "latin1_symbol": "latin_symbol",
    "general_punct": "latin_symbol", "superscript": "latin_symbol",
    "currency": "latin_symbol", "combining": "latin_symbol",
    "letterlike": "symbol", "number_forms": "symbol", "arrows": "symbol",
    "math": "symbol", "misc_technical": "symbol", "control_pictures": "symbol",
    "enclosed": "symbol", "geometric": "symbol", "misc_symbols": "symbol",
    "box_drawing": "box", "block": "box",
    "radical": "kanji", "kanji": "kanji",
    "ideo_space": "space", "space": "space",
    "cjk_punct_low": "cjk_punct", "cjk_bracket": "cjk_punct",
    "cjk_symbol": "cjk_punct", "vertical_form": "cjk_punct", "small_form": "cjk_punct",
    "hiragana": "kana", "katakana": "kana",
    "hiragana_small": "kana", "katakana_small": "kana",
    "hw_katakana": "hw_kana", "hw_katakana_small": "hw_kana", "hw_punct": "hw_kana",
    "hw_other": "hw_kana", "hw_symbol": "latin_symbol",
    "bopomofo": "kana",
    "cjk_enclosed": "cjk_symbol", "cjk_compat": "cjk_symbol",
    "fw_upper": "fw_latin", "fw_lower": "fw_latin", "fw_digit": "fw_latin",
    "fw_punct": "cjk_punct", "fw_symbol": "cjk_punct",
    "pua": "symbol", "other": "symbol",
}

# 「ベースライン系」= 欧文のようにベースラインと字面高さを揃えるべき分類。
# これらは縦位置をグリフ毎に動かさず、分類共通の変換で縦位置を決める。
BASELINE_GROUPS = {"latin", "fw_latin"}

# 罫線・ブロック要素は隣接字と繋がる必要があるため MS の字面枠に完全一致させる
EXACT_FIT_GROUPS = {"box"}


def base_class(cp: int) -> str:
    ch = chr(cp)
    for lo, hi, name in _RANGES:
        if lo <= cp <= hi:
            break
    else:
        name = "other"
    if name in ("latin_ext", "greek", "cyrillic"):
        cat = unicodedata.category(ch)
        prefix = {"latin_ext": "latin_ext", "greek": "greek", "cyrillic": "cyrillic"}[name]
        if cat == "Lu" or cat == "Lt":
            name = prefix + "_upper"
        elif cat.startswith("L"):
            name = prefix + "_lower"
        else:
            name = "latin1_symbol" if name == "latin_ext" else prefix + "_lower"
    if name in ("hiragana", "katakana") and ch in SMALL_KANA:
        name += "_small"
    if name == "hw_katakana" and ch in SMALL_KANA:
        name = "hw_katakana_small"
    return name


def group_of(cls: str) -> str:
    return GROUP_OF.get(cls, "symbol")


def width_bucket(adv: float, upem: float) -> str:
    r = adv / upem
    if r < 0.02:
        return "Z"
    if abs(r - 0.5) < 0.02:
        return "H"
    if abs(r - 1.0) < 0.02:
        return "F"
    return "P"


def decompose_base(cp: int, canonical=False):
    """アクセント付き欧文などを基底文字に分解する（無ければ None）。
    canonical=True なら <wide> <super> などの互換分解は対象外。"""
    d = unicodedata.decomposition(chr(cp))
    if not d or (canonical and d.startswith("<")):
        return None
    parts = [p for p in d.split() if not p.startswith("<")]
    if not parts:
        return None
    try:
        b = int(parts[0], 16)
    except ValueError:
        return None
    return b if b != cp else None
