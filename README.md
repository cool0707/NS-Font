# NS-Font

**MS ゴシック・MS P ゴシック・MS UI Gothic・MS 明朝・MS P 明朝が入っていない環境で、代わりに使うためのフォント**です。

Noto Sans CJK JP / Noto Serif CJK JP（Google・Adobe のオープンソースフォント）を元に、
文字の大きさ・字送り・行の高さを MS 系フォントと同じにしています。
Windows 向けに作られた文書や画面（Excel・Word の文書、MS ゴシック指定の Web ページ、ゲームやアプリの UI など）を、
Mac・Linux・スマートフォンなどで開いても、レイアウトが崩れにくくなります。

字形（文字のデザイン）は Noto のままです。MS フォントそのものではありません。

## ダウンロード

**[最新リリース](https://github.com/cool0707/NS-Font/releases/latest)** から入手できます。迷ったら「レギュラー一式」を使ってください。

| 用途 | ダウンロード |
|---|---|
| レギュラー一式（おすすめ） | [NS-Font-Regular.zip](https://github.com/cool0707/NS-Font/releases/latest/download/NS-Font-Regular.zip) |
| 全ウェイト（太さ違い）一式 | [NS-Font-AllWeights.zip](https://github.com/cool0707/NS-Font/releases/latest/download/NS-Font-AllWeights.zip) |
| 日本語異体字追加版（レギュラー）一式 | [NS-Font-Regular-JPVariants.zip](https://github.com/cool0707/NS-Font/releases/latest/download/NS-Font-Regular-JPVariants.zip) |
| OTF 版（レギュラー）一式 | [NS-Font-Regular-OTF.zip](https://github.com/cool0707/NS-Font/releases/latest/download/NS-Font-Regular-OTF.zip) |
| WOFF2 版（Web フォント用、レギュラー）一式 | [NS-Font-Regular-WOFF2.zip](https://github.com/cool0707/NS-Font/releases/latest/download/NS-Font-Regular-WOFF2.zip) |

**同じ書体名のフォントが重複するので、インストールするのはどれか 1 組だけにしてください。**

## フォントの種類

| NS-Font の書体名 | 代わりになる MS フォント |
|---|---|
| NS ゴシック（NS Gothic） | MS ゴシック（等幅） |
| NS Pゴシック（NS PGothic） | MS P ゴシック（プロポーショナル） |
| NS UI Gothic | MS UI Gothic |
| NS 明朝（NS Mincho） | MS 明朝（等幅） |
| NS P明朝（NS PMincho） | MS P明朝（プロポーショナル） |

### 版の違い

| 版 | 内容 | 形式 |
|---|---|---|
| レギュラー | 普通の太さ 1 種類 | TTF、等幅とプロポーショナルを 1 ファイルにまとめた TTC |
| 全ウェイト | 太さ 7 段階（ゴシック: Thin〜Black、明朝: ExtraLight〜Black） | TTC |
| 日本語異体字追加版 | レギュラーに、漢字の異体字（下記）を追加したもの | TTF / TTC |
| OTF 版・WOFF2 版 | レギュラーと日本語異体字追加版を別の形式にしたもの | OTF / WOFF2 |

- 太字は「Bold」が使われます。アプリの太字ボタンでそのまま太字になります
- 日本語異体字追加版は、書体名が通常版と同じです（通常版の代わりにそのまま使えます）
- WOFF2 版は Web ページ用です。例:

```css
@font-face {
  font-family: "NS Gothic";
  src: url("NSGothic-Regular.woff2") format("woff2");
}
```

## 含まれている文字

1 書体あたり約 16,700 字です。

| 種類 | 内容 |
|---|---|
| 漢字 | 13,160 字。MS ゴシック等に入っている漢字、JIS 第 1〜第 4 水準（JIS X 0213）、Windows の機種依存文字（NEC・IBM 拡張漢字）をすべて含む |
| 仮名 | ひらがな・カタカナ・小書き仮名・半角カタカナ・アイヌ語用の小書きカタカナ |
| 英数字 | 半角・全角の英数字、アクセント付きのラテン文字（À ñ Ł Ő Ş など）、発音記号（IPA） |
| ギリシャ文字・キリル文字 | MS ゴシック等に入っているものを含む |
| 記号 | 句読点・括弧・矢印・数学記号・単位記号（㎝ ㎏ など）・丸数字（① ㉑ など）・ローマ数字・囲み文字（㈱ ㊤ など）・罫線・ブロック要素 ほか |
| 縦書き | 縦書き用の句読点・括弧・長音記号など |

**MS ゴシック・MS 明朝等に入っている文字は、次の 3 字を除いてすべて含んでいます。** 3 字は「㌬」など、Noto 系のどのフォントにも字形がない文字です。

### 日本語異体字追加版で使える異体字

| 機能 | 例 |
|---|---|
| 異体字セレクタ（IVS） | 葛 の下部の違い、辻 の一点しんにょう/二点しんにょう、吉 と「つちよし」の切り替えなど（Adobe-Japan1 の 14,543 組） |
| 字形切替（OpenType 機能） | JIS78 字形（`jp78`）、JIS83 字形（`jp83`）、印刷標準字体（`nlck`）、旧字形（`hist`）、異体字一覧（`aalt`） |

通常版にも JIS90 字形（`jp90`）の切り替えは入っています。

## 含まれていない文字

| 種類 | 備考 |
|---|---|
| 中国語・韓国語用の漢字 | 日本語で使わない漢字（簡体字、繁体字のみの字など）。Noto CJK には入っていますが除いています |
| ハングル | |
| 絵文字（カラー） | 白黒の記号（☺ ☀ ♪ など）は含みます |
| アラビア文字・タイ文字などのその他の文字 | 通貨記号（฿ ﷼ など）だけは含みます |
| 漢字の異体字 | 通常版には含みません（日本語異体字追加版を使ってください） |

## 注意

- 字形のデザインは MS フォントと違います。文字の位置・大きさ・字送り・行の高さは MS フォントに合わせているので、レイアウトはほぼ同じになります
- 小さい文字サイズ用の調整（ヒンティング）や、MS フォントのような小サイズ用のビットマップは入っていません
- 本リポジトリに MS フォントそのものは含まれていません

## ライセンス

SIL Open Font License 1.1（[`OFL.txt`](OFL.txt)）。元にした Noto フォントと同じライセンスです。
商用・非商用を問わず無料で使用・同梱・再配布できます。
