# NS-Font

Noto Sans CJK JP / Noto Serif CJK JP を改造し、**MS ゴシック・MS P ゴシック・MS 明朝・MS P 明朝と
同じ文字サイズ・送り幅・余白・行メトリクス**になるよう調整したフォントです。
字形は Noto のままで、レイアウト上の寸法（どこに・どの大きさで・どれだけ字送りするか）を MS 系に合わせています。

Noto にある全ウェイト（ゴシック 7 段階・明朝 7 段階）を、それぞれ MS 系の寸法に合わせて作っています。

## ダウンロード

**[最新リリース](https://github.com/cool0707/NS-Font/releases/latest)** から入手できます。

| 用途 | ダウンロード |
|---|---|
| レギュラーのみ一式 | [NS-Font-Regular.zip](https://github.com/cool0707/NS-Font/releases/latest/download/NS-Font-Regular.zip) |
| 全ウェイト一式 | [NS-Font-AllWeights.zip](https://github.com/cool0707/NS-Font/releases/latest/download/NS-Font-AllWeights.zip) |
| ゴシック 等幅+P（レギュラー） | [NSGothic-NSPGothic-Regular.ttc](https://github.com/cool0707/NS-Font/releases/latest/download/NSGothic-NSPGothic-Regular.ttc) |
| 明朝 等幅+P（レギュラー） | [NSMincho-NSPMincho-Regular.ttc](https://github.com/cool0707/NS-Font/releases/latest/download/NSMincho-NSPMincho-Regular.ttc) |
| UI Gothic（レギュラー） | [NSUIGothic-Regular.ttf](https://github.com/cool0707/NS-Font/releases/latest/download/NSUIGothic-Regular.ttf) |
| ゴシック 等幅+P（全ウェイト） | [NSGothic-NSPGothic-AllWeights.ttc](https://github.com/cool0707/NS-Font/releases/latest/download/NSGothic-NSPGothic-AllWeights.ttc) |
| 明朝 等幅+P（全ウェイト） | [NSMincho-NSPMincho-AllWeights.ttc](https://github.com/cool0707/NS-Font/releases/latest/download/NSMincho-NSPMincho-AllWeights.ttc) |
| UI Gothic（全ウェイト） | [NSUIGothic-AllWeights.ttc](https://github.com/cool0707/NS-Font/releases/latest/download/NSUIGothic-AllWeights.ttc) |

下の「配布ファイル」にある他のファイルも、同じリリースに個別に添付しています。
リリースは GitHub Actions（`.github/workflows/release.yml`）で作成します（`v*` タグの push、または Actions 画面からタグ名を指定して手動実行）。

## 配布ファイル

### `dist/Regular/` — レギュラーのみ

| ファイル | 内容 |
|---|---|
| `NSGothic-Regular.ttf` | NS ゴシック（等幅） |
| `NSPGothic-Regular.ttf` | NS Pゴシック（プロポーショナル） |
| `NSGothic-NSPGothic-Regular.ttc` | NS ゴシック + NS Pゴシック（1 ファイルで両方入る） |
| `NSUIGothic-Regular.ttf` | NS UI Gothic（MS UI Gothic 相当。元から等幅版はなし） |
| `NSMincho-Regular.ttf` | NS 明朝（等幅） |
| `NSPMincho-Regular.ttf` | NS P明朝（プロポーショナル） |
| `NSMincho-NSPMincho-Regular.ttc` | NS 明朝 + NS P明朝 |

### `dist/AllWeights/` — Noto にある全ウェイト入り

| ファイル | 内容 |
|---|---|
| `NSGothic-AllWeights.ttc` | NS ゴシック（等幅）× 7 ウェイト |
| `NSPGothic-AllWeights.ttc` | NS Pゴシック × 7 ウェイト |
| `NSGothic-NSPGothic-AllWeights.ttc` | 等幅 + プロポーショナル × 7 ウェイト |
| `NSUIGothic-AllWeights.ttc` | NS UI Gothic × 7 ウェイト |
| `NSMincho-AllWeights.ttc` | NS 明朝（等幅）× 7 ウェイト |
| `NSPMincho-AllWeights.ttc` | NS P明朝 × 7 ウェイト |
| `NSMincho-NSPMincho-AllWeights.ttc` | 等幅 + プロポーショナル × 7 ウェイト |

ウェイト:

| 系統 | ウェイト（usWeightClass） |
|---|---|
| ゴシック・UI | Thin (100) / Light (300) / DemiLight (350) / Regular (400) / Medium (500) / Bold (700) / Black (900) |
| 明朝 | ExtraLight (200) / Light (300) / Regular (400) / Medium (500) / SemiBold (600) / Bold (700) / Black (900) |

- Regular と Bold は同じファミリー（例: 「NS ゴシック」）としてリンクしているので、アプリの太字ボタンで Bold が使われます
- それ以外のウェイトは「NS ゴシック Light」のような別名のファミリーとして一覧に出ます（Windows の標準的な扱い）
- 寸法（送り幅・余白・行の高さ）はすべてのウェイトで MS 系 Regular の値に合わせています。MS 系に太字はなく、Windows が擬似的に太らせています
- TTC 内では同じウェイトの等幅/プロポーショナル間で同一の字形（漢字など）を共有しているため、単体を並べるよりサイズが小さくなります

**同じ書体名が重複するので、インストールするのはいずれか 1 組だけにしてください**
（例: `NSGothic-NSPGothic-AllWeights.ttc` を入れたら、`Regular/` のゴシック系や `NSGothic-AllWeights.ttc` は入れない）。

## 収録字

漢字は日本語向けに絞っています: **MS 系の収録漢字 ∪ JIS X 0213（第 1〜4 水準）∪ CP932** の 13,160 字（Noto CJK JP の 30,289 字のうち主に中国語用の漢字を除外）。
仮名・記号・欧文・ギリシャ・キリルなど漢字以外は Noto にあるものを残しています（ハングルは除外）。
異体字切替（`jp78`/`jp83`/`aalt`/`nlck`/`hist`）用の字形も除いています（`jp90`・縦書き・半角/全角切替は残しています）。
これで 1 書体あたり約 5〜7 MB になり、全ウェイト入りの TTC も GitHub の 1 ファイル上限（100 MB）に収まります。
Noto の全収録字を残したい場合は `scripts/build.py --full` でビルドできます（1 書体約 19〜26 MB）。

### Noto 欧文・記号系フォントによる補完

MS 系にあって Noto CJK に字形がない 1,070 字のうち **1,067 字** を、同じ OFL ライセンスの Noto フォントから補っています
（`scripts/nsfont/supplement.py`）。補完した字も MS の送り幅・字面位置に合わせています。

| 補完元 | 主な文字 |
|---|---|
| Noto Sans / Noto Serif（明朝系） | ラテン拡張 A（Ą Č Ğ Ł Ő Ř Ş …）、IPA 発音記号、キリル拡張（Ђ Є І Ї Љ …）、ギリシャ（アクセント付き）、上付き・下付き数字、分数 |
| Noto Sans Math | 数学記号（∄ ∯ ≇ …）、矢印、文字様記号（ℂ ℝ ℤ …） |
| Noto Sans Symbols / Symbols2 | 記号（☑ ☠ ☺ …）、幾何学模様（► ◘ …） |
| Noto Sans/Serif Bengali・Thai・Khmer、Noto Sans Arabic / Naskh Arabic | 通貨記号 ৳ ฿ ៛ ﷼ |

- **ウェイト合わせ**: CJK 側の欧文の縦画（大文字 L H E I T / 小文字 l n h i m、記号は「+」）の太さを実測し、
  補完フォントの 9 段階のウェイトから最も近いものを選択。残る差と、Regular しかない Math / Symbols2 の差は
  輪郭を法線方向にずらす太らせ/細らせ処理で補正（大文字・小文字で別々に補正）
- **大きさ**: 補完フォントの「H」の高さを CJK 側の「H」に揃えたうえで、MS の字面に合わせる
- **字幅**: 等幅版の半角に入りきらない字形は、Noto Sans/Serif の SemiCondensed → Condensed → ExtraCondensed から幅の合うものを選ぶ
- 補完できないのは ㌬ など 3 字（いずれの Noto フォントにも字形がない、または制御文字）
- 補完をしない場合は `build.py --no-supplement`

あわせて、次の 2 点を CJK 側の既存文字も含めて改善しています。

- MS 収録のアクセント付き文字（À È Ĺ ñ …）は、基底文字（A E L n …）と同じ倍率・ベースラインで変換（以前はアクセント込みの高さで合わせていたため本体が約 13% 小さかった）
- 半角に収めるために横だけ縮めた字は、縮めた分だけ縦画を横方向に太らせて線の太さを揃える

ライセンス: SIL Open Font License 1.1（`OFL.txt`）。
**MS フォント本体はリポジトリに含めません**（`.gitignore` で `fonts/ms/`・`*.ttc` 等を除外）。
ビルドには手元の Windows からコピーした `msgothic.ttc` / `msmincho.ttc` が必要です。

## 合わせている属性

| 属性 | 内容 |
|---|---|
| 行メトリクス | ascent 0.859em / descent 0.141em / lineGap 0（hhea・OS/2 typo・win すべて MS と同値）。Noto 原本は 1.160/0.288em で行が高い |
| em 枠 | 全角字の em 枠を MS と同じ y = -0.141〜0.859em に移動（Noto は -0.12〜0.88em） |
| 送り幅 | MS 収録字はすべて MS と同じ値（全書体・全ウェイトで一致率 100%） |
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

1. Noto CJK の JP 書体を取り出し、上記「収録字」の範囲にサブセット化（約 15,700 字 / 16,300 グリフ）
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
   - 異体字（jp90 等）→ 同じ文字の既定字形と同じ変換
   - それ以外 → 同じ分類の代表値（中央値）。分類+幅区分 → 分類 → 上位グループ → 全体 の順にフォールバック。
     プロポーショナル版で仮名など MS 側がプロポーショナルな分類は、余白の代表値から送り幅を決める
6. 3 次ベジエを 2 次（TrueType）に変換して保存

使われた分類別のパラメータは `docs/transform_<書体>-Regular.md` に出力されます。

### 3. 検証（`scripts/compare.py`）

MS 収録字について送り幅と字面枠を比較した結果（字面枠ずれ = 4 辺のずれの最大値、em 比）:

| グループ | 字数 | 送り幅一致 | Gothic ずれ中央値 | PGothic | Mincho | PMincho |
|---|---:|---:|---:|---:|---:|---:|
| kanji | 13160 | 100% | 0.006em | 0.006em | 0.010em | 0.010em |
| kana | 205 | 100% | 0.011em | 0.012em | 0.013em | 0.013em |
| hw_kana | 63 | 100% | 0.008em | 0.049em | 0.013em | 0.034em |
| latin | 681 | 100% | 0.059em | 0.041em | 0.037em | 0.036em |
| fw_latin | 62 | 100% | 0.034em | 0.035em | 0.020em | 0.021em |
| latin_symbol | 219 | 100% | 0.017em | 0.019em | 0.017em | 0.017em |
| cjk_punct | 86 | 100% | 0.023em | 0.020em | 0.014em | 0.014em |
| cjk_symbol | 481 | 100% | 0.006em | 0.006em | 0.007em | 0.007em |
| symbol | 991 | 100% | 0.016em | 0.015em | 0.015em | 0.015em |
| box | 150 | 100% | 0.000em | 0.000em | 0.000em | 0.000em |

残るずれは字形デザインそのものの違い（例: 「W」の幅、半角カナの字形、アクセント記号の高さ）によるものです。
latin・symbol には Noto 欧文・記号系フォントで補完した字を含みます。送り幅は全 35 書体（5 種 × 7 ウェイト）で MS と一致しています。
`scripts/compare.py` は MS（赤）と生成フォント（青）を重ね描きした画像も `build/compare/` に出力します。

## ビルド手順

```sh
pip install -r requirements.txt
# MS フォント（Windows の C:\Windows\Fonts からコピー）を置く。コミットされません
cp /path/to/msgothic.ttc /path/to/msmincho.ttc fonts/ms/
# Noto CJK (OTC) を fonts/noto/、補完用 Noto を fonts/noto-extra/ に置く
scripts/fetch_noto.sh
python3 scripts/analyze_ms.py          # MS 計測・分類
python3 scripts/build.py -j 4          # 5 種 × 7 ウェイト = 35 書体を build/ttf/ に生成
python3 scripts/package.py             # dist/Regular/, dist/AllWeights/ に組み立て
python3 scripts/compare.py             # 検証（任意）
```

- `build.py --weights Regular,Bold` のようにウェイトを限定できます。`build.py Gothic PGothic` で書体も限定できます
- `python3 scripts/package.py out.ttc a.ttf b.ttf ...` で任意の TTF を 1 つの TTC にまとめられます

## 注意・制限

- MS 系に収録されていて Noto CJK に字形がない文字は、上記のとおり Noto 欧文・記号系フォントで補完しています（デザインは Noto Sans/Serif 等のもの）。
  Math と Symbols2 は Regular しかないため、他のウェイトは輪郭の太らせ/細らせで近づけています
- ヒンティングなし（unhinted）の TrueType です。MS フォントの埋め込みビットマップに相当するものもありません
- 送り幅を変更したため、Noto の GPOS（palt/kern/vpal 等の詰め情報）は削除しています（MS 系も同様の詰め情報は持っていません）
- 書体名から “Noto” は外しています（改変版であることを明確にするため）
