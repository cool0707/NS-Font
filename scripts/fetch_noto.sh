#!/bin/sh
# 原本フォントを用意する。
#   fonts/noto/        Noto Sans/Serif CJK (OTC 版、全ウェイト)
#   fonts/noto-extra/  補完用の Noto 欧文・記号・各言語フォント (TTF)
# 1) Debian/Ubuntu のパッケージから取得（apt が使える環境）
# 2) 使えない場合は https://github.com/notofonts/noto-cjk/releases と
#    https://github.com/notofonts/notofonts.github.io から同名のファイルを手動で置く。
set -eu
cd "$(dirname "$0")/.."
mkdir -p fonts/noto fonts/noto-extra
tmp=$(mktemp -d)
( cd "$tmp" && apt-get download fonts-noto-cjk fonts-noto-cjk-extra fonts-noto-core )
for d in "$tmp"/*.deb; do dpkg-deb -x "$d" "$tmp/x"; done
cp "$tmp"/x/usr/share/fonts/opentype/noto/Noto*CJK-*.ttc fonts/noto/
t="$tmp/x/usr/share/fonts/truetype/noto"
for fam in NotoSans NotoSerif NotoSansMath NotoSansSymbols NotoSansSymbols2 \
           NotoSansBengali NotoSerifBengali NotoSansThai NotoSerifThai \
           NotoSansKhmer NotoSerifKhmer NotoSansArabic NotoNaskhArabic; do
  for f in "$t/$fam"-*.ttf; do
    case "$f" in *Italic*|*UI-*) continue ;; esac
    cp "$f" fonts/noto-extra/
  done
done
rm -rf -- "$tmp"
ls fonts/noto; ls fonts/noto-extra | wc -l
