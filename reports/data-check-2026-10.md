# データ点検レポート（2026-10-12）

対象：`data/entries.json`（生データ 99 件／サイト表示 91 件。同年・同著者頭の重複は build.py が 1 枚に集約）
前回点検：2026-07-10

## 結論

- 前回指摘の **出典URLの使い回し 5 組・計 14 件は、現在もそのまま残っている**（件数・組み合わせとも前回と同一）。
- `history_note_ja` が空の項目は **前回と同じ 1 件**（ファーロー 二重対向Z形成 1986）。
- **この作業環境からは外部サイトへ接続できず（後述）、原著ページを開いて書誌を照合することが一度もできなかった。**
  そのため、指示どおり URL・DOI・歴史メモの推測補完は一切しておらず、**`entries.json` は変更していない**。全件「要確認」のまま。

### 接続確認の記録

| 手段 | 宛先 | 結果 |
|---|---|---|
| curl（エージェントプロキシ経由） | pmc.ncbi.nlm.nih.gov / pubmed.ncbi.nlm.nih.gov / eutils.ncbi.nlm.nih.gov | `CONNECT tunnel failed, response 403`（プロキシが接続拒否） |
| curl | europepmc（ebi.ac.uk）/ api.crossref.org / doi.org / thelancet.com / nejm.org / en.wikipedia.org | 接続不可（000） |
| WebFetch | pmc.ncbi.nlm.nih.gov / pubmed.ncbi.nlm.nih.gov | `getaddrinfo ENOTFOUND` |

ネットワークが使える環境で、下表の「確認すべきこと」を実施してください。

---

## 1. 同じ出典URLを複数項目で使い回している組

`#` は `entries.json` 配列の 0 始まりインデックス。

### 1-1. PMC8071142 × 5（植皮の歴史を扱う総説と思われる。各項目の原著ではない）

| # | 年 | 項目 | 記載の書誌 | 信頼度 | 状態 |
|---|---|---|---|---|---|
| 5 | 1804 | 自家植皮の動物実験（Baronio） | Degli innesti animali／Milano 単行書 | medium | **要確認** |
| 7 | 1823 | ヒト遊離全層植皮の初成功（Bünger） | Journal der practischen Heilkunde 等 | medium | **要確認** |
| 27 | 1939 | ダーマトーム（Padgett & Hood） | SGO 系／学会発表 | medium | **要確認** |
| 67 | 1981 | 培養表皮自家移植の初臨床（O'Connor ほか） | Lancet 1981;1(8211):75-78 | high | **要確認** |
| 74 | 1984 | 超広範囲熱傷児への培養表皮（Gallico ほか） | N Engl J Med 1984;311(7):448-451 | high | **要確認** |

確認すべきこと：
- #67・#74 は誌名・巻号・頁まで記載があるので、PubMed で書誌一致する原著レコードを開いて確認できれば、その PubMed URL に差し替えられる見込みが高い（未確認のため今回は差し替えていない）。
- #5・#7・#27 は 19 世紀の単行書・学会報告で、オンラインの原著ページが無い可能性がある。その場合は総説 URL のままでよいが、カード上「原著・出典を見る」が総説に飛ぶことを注記するか検討を。
- PMC8071142 自体の書誌（題名・著者・誌名）もネット環境で確認し、5 項目の記述と矛盾しないか照合すること。

### 1-2. PMC8066645 × 3（同上、植皮の歴史総説と思われる）

| # | 年 | 項目 | 記載の書誌 | 信頼度 | 状態 |
|---|---|---|---|---|---|
| 15 | 1872 | 分層植皮（Ollier） | Comptes rendus／同時代フランス外科報告 | medium | **要確認** |
| 17 | 1874/1886 | 薄い分層植皮（Thiersch） | Verhandlungen der Deutschen Gesellschaft für Chirurgie | medium | **要確認** |
| 19 | 1893 | 全層植皮の確立（Krause） | Verhandlungen der Deutschen Gesellschaft für Chirurgie | medium | **要確認** |

確認すべきこと：いずれも巻・頁の記載が無く、原著を特定できる情報がデータ内に無い。総説の参考文献欄で巻頁を確認 → その原著のデジタル版（BHL・Gallica 等）の有無を確認、の順で。

### 1-3. jprasurg（McGregor & Jackson 1972 "The groin flap"）× 2

| # | 項目 | 状態 |
|---|---|---|
| 55 | 鼠径皮弁 ― 軸走型皮弁の確立 | 同一論文の重複項目 |
| 56 | 鼠径皮弁（グロインフラップ／McGregor皮弁） | 同一論文の重複項目 |

- 2 項目とも同じ論文（Br J Plast Surg 1972;25:3-16）なので **URL の共有自体は誤りではない**。
- build.py の重複集約で 1 枚に統合済み（サイト上は 1 項目・個別ページも 1 枚）。対応不要。

### 1-4. jprasurg（Taylor & Palmer 1987 angiosome）× 2

| # | カテゴリ | 項目 | 状態 |
|---|---|---|---|
| 78 | micro | アンジオソーム（血管領域）の概念（Taylor GI, Palmer JH） | 同一論文の重複項目 |
| 79 | local_flap | アンジオソームの概念（G. Ian Taylor & J. H. Palmer） | 同一論文の重複項目 |

- 同じ論文（Br J Plast Surg 1987;40(2):113-141）なので URL 共有は誤りではない。
- **ただし著者表記の頭（"Taylor" と "Ian"）が違うため build.py の集約に掛からず、サイト上で 2 項目として表示されている**（個別ページも 2 枚：`1987-angiosome-concept-taylor-palmer` と `1987-g-ian-taylor-j-h-palmer-angiosome`）。
  なお 1987 年にはもう 1 件「アンギオソーム（血管領域）の概念」（PubMed 3567445）もあり、こちらと #79 が集約されている。統合するかは持ち主の判断（今回は未変更）。

### 1-5. Wikipedia「Jaques-Louis Reverdin」× 2

| # | カテゴリ | 項目 | 記載の書誌 | 状態 |
|---|---|---|---|---|
| 13 | skin_graft | ピンチグラフト（点状植皮） | Bull Soc Imp Chir Paris 1869;10:511-515 | **要確認** |
| 14 | history | 遊離皮膚移植 ― 近代植皮術の起点 | Bull Soc Imp Chir Paris, 1869 | **要確認** |

- 同じ原著（Reverdin 1869 "Greffe épidermique"）を指す 2 項目。出典が Wikipedia で一次資料ではない。
- 原著のデジタル版（Gallica 等）を実際に開いて巻頁一致を確認できれば差し替え可能。今回は確認できず未変更。
- 著者綴り（"Jaques" / "Jacques"）が違うため集約されず、**サイト上で 2 項目表示**（個別ページ 2 枚）。

---

## 2. `history_note_ja` が空の項目

| # | 年 | 項目 | 著者 | 原著 | 状態 |
|---|---|---|---|---|---|
| 76 | 1986 | 二重対向Z形成による口蓋形成術（ファーロー法） | Leonard T. Furlow Jr. | Cleft Palate Repair by Double Opposing Z-Plasty（Plast Reconstr Surg, PubMed 3786527） | **空のまま** |

- 出典を開いて裏を取れなかったため記入していない。個別ページでは「歴史メモ」節を出さない（空欄の見出しを作らない）実装にしてある。

---

## 3. 参考：点検中に気づいた表示上の重複（未変更）

著者表記の揺れで build.py の集約（同年＋著者名の最初の英単語）に掛からず、同じ出来事が 2 項目表示されているもの：

| 年 | 個別ページ（slug） |
|---|---|
| 1869 | `1869-jaques-louis-reverdin-greffe-epidermique` ／ `1869-jacques-louis-reverdin-epidermic-pinch-skin-graft` |
| 1960 | `1960-julius-h-jacobson-ernesto-l-suarez` ／ `1960-julius-jacobson-ernesto-suarez-microvascular-anastomosis` |
| 1966 | `1966-harry-j-buncke-w-p-schulz` ／ `1966-harry-j-buncke-experimental-microvascular-free-tissue` |
| 1987 | `1987-angiosome-concept-taylor-palmer` ／ `1987-g-ian-taylor-j-h-palmer-angiosome` |

カテゴリ（例：植皮 と 歴史）を分けて意図的に置いている可能性もあるため、今回は触っていない。統合する場合は entries.json 側で片方を削るか、著者表記を揃える（＝集約される）ことになる。その場合は個別ページの URL が 1 本消えるので注意。

## 4. og.svg の PNG 版

- 変換手段：ImageMagick（`/usr/bin/convert`）とヘッドレス Chromium があった。SVG の再現性が高い Chromium でスクリーンショットを撮り、1200×630 に切り出して `docs/og.png` を作成（PIL は切り出しのみに使用。build.py は標準ライブラリのまま）。
- **この環境には明朝体が無く、日本語は IPA ゴシックで描画されている**（og.svg は閲覧側の Hoefler Text／Georgia 等に依存）。レイアウト・色・文言は同じだが書体の雰囲気は異なる。気になる場合は明朝体のある環境で作り直すこと。
- PNG には件数「91 の原著・里程標」が焼き込まれている。項目数が変わったら作り直しが必要（README に手順を記載）。
- `docs/og.png` がある場合、build.py は解説ページ・個別ページの og:image を PNG に向ける。トップ（index）は従来どおりポッドキャストのカバー画像 `audio/cover.png`（既に PNG）を使う。
