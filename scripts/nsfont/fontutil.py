"""フォント読み込み・計測の共通処理。"""
from fontTools.ttLib import TTCollection, TTFont
from fontTools.pens.boundsPen import BoundsPen


def open_face(path, name_suffix=None, index=None, lazy=None):
    """TTC/OTC から書体名 (fullName 末尾一致) か index で 1 書体を取り出す。"""
    if path.lower().endswith((".ttc", ".otc")):
        coll = TTCollection(path, lazy=lazy)
        if index is not None:
            return coll[index]
        for f in coll:
            names = {f["name"].getDebugName(i) for i in (1, 4, 16)} - {None}
            if name_suffix in names or any(n.endswith(name_suffix) for n in names):
                return f
        # "Noto Sans CJK JP Bold" のようにウェイト名が付く場合
        for f in coll:
            if name_suffix and name_suffix in (f["name"].getDebugName(4) or "") and \
                    "Mono" not in (f["name"].getDebugName(4) or ""):
                return f
        raise KeyError(f"{name_suffix} not found in {path}: "
                       f"{[f['name'].getDebugName(4) for f in coll]}")
    return TTFont(path, lazy=lazy)


def single_subst_map(font, feature_tags):
    """指定 feature の SingleSubst を合成した {glyph: glyph}。"""
    out = {}
    if "GSUB" not in font:
        return out
    t = font["GSUB"].table
    if not t.FeatureList:
        return out
    idx = set()
    for fr in t.FeatureList.FeatureRecord:
        if fr.FeatureTag in feature_tags:
            idx.update(fr.Feature.LookupListIndex)
    for i in sorted(idx):
        lk = t.LookupList.Lookup[i]
        for st in lk.SubTable:
            if lk.LookupType == 7:
                st = st.ExtSubTable
            mapping = getattr(st, "mapping", None)
            if mapping:
                for a, b in mapping.items():
                    out.setdefault(a, b)
    return out


def glyph_bounds(font, gname, glyphset=None):
    if "glyf" in font:
        g = font["glyf"][gname]
        if g.numberOfContours == 0:
            return None
        if g.isComposite():
            g.recalcBounds(font["glyf"])
        return (g.xMin, g.yMin, g.xMax, g.yMax)
    gs = glyphset or font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[gname].draw(bp)
    return bp.bounds


def vertical_origin(font, gname):
    """縦書き原点 (グリフ座標系での y)。"""
    if "VORG" in font:
        v = font["VORG"]
        return v.VOriginRecords.get(gname, v.defaultVertOriginY)
    if "vmtx" in font and "glyf" in font:
        g = font["glyf"][gname]
        if g.numberOfContours:
            return font["vmtx"][gname][1] + g.yMax
    return font["OS/2"].sTypoAscender
