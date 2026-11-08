#!/bin/sh
# Noto Sans/Serif CJK (OTC 版) を fonts/noto/ に用意する。
# 1) Debian/Ubuntu のパッケージから取得（apt が使える環境）
# 2) 使えない場合は https://github.com/notofonts/noto-cjk/releases から
#    NotoSansCJK-*.ttc / NotoSerifCJK-*.ttc を手動で fonts/noto/ に置く。
set -eu
cd "$(dirname "$0")/.."
mkdir -p fonts/noto
tmp=$(mktemp -d)
( cd "$tmp" && apt-get download fonts-noto-cjk fonts-noto-cjk-extra )
for d in "$tmp"/*.deb; do dpkg-deb -x "$d" "$tmp/x"; done
cp "$tmp"/x/usr/share/fonts/opentype/noto/Noto*CJK-*.ttc fonts/noto/
rm -rf -- "$tmp"
ls -l fonts/noto
