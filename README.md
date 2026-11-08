# NS-Font

Noto Sans CJK JP / Noto Serif CJK JP を改造し、**MS ゴシック・MS P ゴシック・MS 明朝・MS P 明朝と
同じ文字サイズ・送り幅・余白・行メトリクス**になるよう調整したフォントです。
字形は Noto のままで、レイアウト上の寸法（どこに・どの大きさで・どれだけ字送りするか）を MS 系に合わせています。

| ファイル | 書体名（英/和） | 原本 | 寸法の基準 |
|---|---|---|---|
| `dist/NSGothic-Regular.ttf` | NS Gothic / NS ゴシック | Noto Sans CJK JP | MS ゴシック（等幅） |
| `dist/NSPGothic-Regular.ttf` | NS PGothic / NS Pゴシック | Noto Sans CJK JP | MS P ゴシック（プロポーショナル） |
| `dist/NSMincho-Regular.ttf` | NS Mincho / NS 明朝 | Noto Serif CJK JP | MS 明朝（等幅） |
| `dist/NSPMincho-Regular.ttf` | NS PMincho / NS P明朝 | Noto Serif CJK JP | MS P 明朝（プロポーショナル） |

ライセンス: SIL Open Font License 1.1（`OFL.txt`）。
**MS フォント本体はリポジトリに含めません**（`.gitignore` で `fonts/ms/`・`*.ttc` 等を除外）。
ビルドには手元の Windows からコピーした `msgothic.ttc` / `msmincho.ttc` が必要です。

## 合わせている属性

| 属性 | 内容 |
|---|---|
| 行メトリクス | ascent 0.859em / descent 0.141em / lineGap 0（hhea・OS/2 typo・win すべて MS と同値）。Noto 原本は 1.160/0.288em で行が高い |
| em 枠 | 全角字の em 枠を MS と同じ y = -0.141〜0.859em に移動（Noto は -0.12〜0.88em） |
| 送り幅 | MS 収録字はすべて MS と同じ値（4 書体とも一致率 100%） |
| 字面の大きさ・位置・左右余白 | MS 収録字は MS の字面枠に合わせる（下記） |
| 縦書き | 縦送り・縦書き原点（tsb）を MS と同値に。縦書き用字形 (vert) も MS の縦書き用字形の位置に合わせる |
| その他 | xAvgCharWidth、x ハイト/キャップハイト、下線・取消線の位置と太さ、isFixedPitch、PANOSE の bProportion、BASE の基準線 |

## 方法

### 1. MS 系フォントの計測と分類（`scripts/analyze_ms.py`）

MS ゴシック / MS P ゴシック / MS UI ゴシック / MS 明朝 / MS P 明朝 の全収録文字（各約 16,100 字）について
送り幅・字面枠（xMin/xMax/yMin/yMax）・左右余白・縦送り・縦書き上余白・縦書き用字形の寸法を計測し、
次の 2 軸で分類します（`scripts/nsfont/classify.py`）。

- **基本分類**（約 60 種）: 漢字、平仮名、片仮名、小書き仮名、半角カナ、欧文大文字/小文字/数字、
  ラテン拡張、ギリシャ、キリル、IPA、和文括弧、句読点、全角英数、罫線、ブロック要素、矢印、数学記号、
  囲み文字、CJK 互換文字 など。さらに上位グループ（kanji / kana / latin / cjk_punct / symbol / box …）にまとめる
- **幅区分**: H=半角、F=全角、P=プロポーショナル、Z=幅 0

分類ごとの統計は [`docs/ms_classes.md`](docs/ms_classes.md)（中央値の要約のみ。グリフ単位の生データは
`build/ms/*.json` に出力され、git 管理外）。

### 2. Noto の変形（`scripts/build.py`）

1. Noto CJK の JP 書体を取り出し、ハングルを除いてサブセット化（約 33,000 字 / 51,000 グリフ）
2. 等幅版では、MS 側で半角/全角の文字は Noto の `hwid`/`fwid` 字形（半角用・全角用にデザインされた字形）を既定字形にする
   （例: 英数字は Noto の半角用字形を使う）
3. 各グリフがどの文字の、どの役割（通常 / 縦書き用 / 異体字など）の字形かを GSUB から求める
4. **MS に同じ文字があるグリフ** — その文字の MS の値を使う
   - 送り幅・縦送り・縦書き原点 = MS の値
   - 大きさ = 分類共通の倍率 × グリフごとの補正（MS の字面寸法に寄せる。字形の太さが揃うよう分類ごとに上限: 漢字 ±5%、仮名 ±8% など）
   - 位置 = MS の字面中心に合わせる。欧文系はベースラインを保つため縦位置のみ分類共通
   - 字面が MS の字面幅より大きくはみ出す場合は横方向のみ詰める（最大 25%）
   - 罫線・ブロック要素は隣の字とつながるよう MS の字面枠に完全一致
5. **MS にないグリフ** — 似た分類の値を使う
   - アクセント付き欧文 → 基底文字（例: Ž → Z）の値
   - 異体字（jp78/jp90/aalt 等）→ 同じ文字の既定字形と同じ変換
   - それ以外 → 同じ分類の代表値（中央値）。分類+幅区分 → 分類 → 上位グループ → 全体 の順にフォールバック。
     プロポーショナル版で仮名など MS 側がプロポーショナルな分類は、余白の代表値から送り幅を決める
6. 3 次ベジエを 2 次（TrueType）に変換して保存

使われた分類別のパラメータは `docs/transform_<書体>-Regular.md` に出力されます。

### 3. 検証（`scripts/compare.py`）

MS 収録字について送り幅と字面枠を比較した結果（字面枠ずれ = 4 辺のずれの最大値、em 比）:

| グループ | 字数 | 送り幅一致 | Gothic ずれ中央値 | PGothic | Mincho | PMincho |
|---|---:|---:|---:|---:|---:|---:|
| kanji | 13160 | 100% | 0.006em | 0.006em | 0.010em | 0.010em |
| kana | 205 | 100% | 0.010em | 0.010em | 0.012em | 0.012em |
| hw_kana | 63 | 100% | 0.008em | 0.049em | 0.010em | 0.034em |
| latin | 294 | 100% | 0.013em | 0.027em | 0.021em | 0.015em |
| cjk_punct | 86 | 100% | 0.023em | 0.019em | 0.010em | 0.010em |
| symbol | 438 | 100% | 0.006em | 0.006em | 0.010em | 0.010em |
| box | 150 | 100% | 0.000em | 0.000em | 0.000em | 0.000em |

残るずれは字形デザインそのものの違い（例: 「W」の幅、半角カナの字形）によるものです。
`scripts/compare.py` は MS（赤）と生成フォント（青）を重ね描きした画像も `build/compare/` に出力します。

## ビルド手順

```sh
pip install -r requirements.txt
# MS フォント（Windows の C:\Windows\Fonts からコピー）を置く。コミットされません
cp /path/to/msgothic.ttc /path/to/msmincho.ttc fonts/ms/
# Noto CJK (OTC) を fonts/noto/ に置く
scripts/fetch_noto.sh
python3 scripts/analyze_ms.py          # MS 計測・分類
python3 scripts/build.py -j 4          # 4 書体を dist/ に生成
python3 scripts/compare.py             # 検証（任意）
```

- `python3 scripts/build.py UIGothic` で MS UI Gothic 相当（NS UI Gothic）も生成できます
- `--weights Regular,Bold` で Noto の Bold を原本にした太字も生成できます（寸法は MS の Regular に合わせます）

## 注意・制限

- MS 系に収録されていて Noto CJK に字形がない文字が約 1,070 字あります
  （ラテン拡張 A の一部〔Ą Č Ğ Ł Ő Ř Ş など〕、IPA、キリル拡張、一部の数学記号・矢印など）。これらは収録されません
- ヒンティングなし（unhinted）の TrueType です。MS フォントの埋め込みビットマップに相当するものもありません
- 送り幅を変更したため、Noto の GPOS（palt/kern/vpal 等の詰め情報）は削除しています（MS 系も同様の詰め情報は持っていません）
- 書体名から “Noto” は外しています（改変版であることを明確にするため）
