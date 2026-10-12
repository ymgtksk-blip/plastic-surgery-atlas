# 術式の系譜 — 形成外科 原典データベース

形成外科の**術式・皮弁・植皮・マイクロサージャリー**の原著論文と、それを**世界で初めて行った人**を、一次資料の出典リンク付きで**年代順**にまとめた検索データベース（日本語・英語）。

**公開サイト**: https://ymgtksk-blip.github.io/plastic-surgery-atlas/ （英語版: https://ymgtksk-blip.github.io/plastic-surgery-atlas/en/ ）

## 特長
- 紀元前600年（スシュルタ）〜現代までの里程標を収録（全項目に出典URL）。
- ライブ検索・カテゴリ絞り込み・「一覧⇄年表」切替。
- SEO最適化：本文は静的HTML、JSON-LD（WebSite / Dataset / ItemList）、OG/Twitter、canonical、sitemap.xml、robots.txt。
- 信頼度を明示（`high` / `medium=史料に諸説あり` / `low=要確認`）。引用時は各原著リンクで最終確認を。

## 構成
- `data/entries.json` — 検証済みデータセット（複数エージェントによる一次資料のWeb検証を経たもの）。
- `data/i18n/en.json` — 英語版の訳（画面の文言・カテゴリ名・時代区分と、項目ごとの術式名・意義・歴史メモ。キーは個別ページの slug）。`entries.json` は日本語のまま変更しない。
- `build.py` — データセット → 静的サイトを生成する決定的ビルダ（外部依存なし・Python 3）。
- `docs/` — GitHub Pages で公開される生成物（`entries/` 個別ページ、`papers/` 日本語解説、`en/` 英語版のトップと個別ページ）。
- `check_site.py` — 公開物の整合チェック。
- `reports/` — データ点検レポート。

## ビルド / 更新
```bash
python3 build.py --base-url https://ymgtksk-blip.github.io/plastic-surgery-atlas
cp dist/index.html dist/sitemap.xml dist/robots.txt dist/og.svg docs/ && touch docs/.nojekyll
git add -A && git commit -m "update" && git push
```

## 免責
本サイトは医学史の教育・参照を目的とした非営利のまとめです。年代・出典に史料的な幅がある項目があります。臨床判断・学術引用の際は必ずリンク先の原著・一次資料を確認してください。

## 図の掲載ポリシー

論文解説ページの図は `data/commentaries/*.json` の各 section の `figures` に記述する。
**原著（Elsevier/Wolters Kluwer 等）の図は著作権上ここに転載しない。**
掲載してよいのは CC BY 等で再利用が明示的に許諾された図のみで、
`credit`（著者・誌名・出典URL・ライセンス）は必須。原著の図でない場合は `note` で明示する。

## デプロイ手順（順序厳守）

```bash
python3 link_commentaries.py                                              # ①解説を entries.json へ配線
python3 build.py --base-url "https://ymgtksk-blip.github.io/plastic-surgery-atlas"   # ②ビルド(--base-url必須)
cp dist/index.html dist/sitemap.xml dist/robots.txt dist/og.svg docs/ && cp -R dist/papers/. docs/papers/
rm -rf docs/entries && cp -R dist/entries docs/entries                     # ③全項目の個別ページ（丸ごと入れ替え＝古いslugを残さない）
rm -rf docs/en && cp -R dist/en docs/en                                   # ③'英語版（トップ＋個別ページ。丸ごと入れ替え）
python3 check_site.py                                                     # ④整合チェック（個別ページの過不足・sitemap・リンク切れ・hreflang・英語ページの訳漏れ）
```

### 英語版について
- 英語版は `docs/en/index.html`（トップ）と `docs/en/entries/<slug>.html`（全項目。slug は日本語版と同じ）。日本語解説（`papers/`）は訳しておらず、英語の個別ページから日本語解説へリンクするだけ。
- 日英の対応ページは hreflang（ja / en / x-default=ja）で相互に結び、sitemap.xml にも同じ対応を `xhtml:link` で書いている。
- **項目を追加したら `data/i18n/en.json` にも訳を足す**（無いと build.py が止まる）。訳すのは日本語の表示項目だけで、人名・原題・誌名・年・URL は原データをそのまま使う。原データの書誌欄に読み仮名など日本語が混じる場合だけ、`author` / `paper_title` / `journal` / `papers` で英語表記を上書きする。
- 各訳の `src` は訳したときの日本語原文のハッシュ。`entries.json` の日本語を直すと build.py が WARNING を出し、check_site.py が NG にする。訳を見直してから `src` を `build.ja_source_hash(e)` の値に更新する。

- 個別ページ `docs/entries/<slug>.html` は entries.json の表示項目すべてに1枚ずつ生成される。slug は「年＋原語名（name_original）」から決まるため、**name_original や year_sort を書き換えると URL が変わる**（古い URL は消える）。
- `docs/og.png`（og.svg の PNG 版、1200×630）は build.py では作らない静的ファイル。件数が焼き込まれているので、項目数が変わったら作り直す：
  `chromium --headless=new --hide-scrollbars --window-size=1200,900 --screenshot=og_full.png <og.svgを1200×630で表示するHTML>` → 上端から 1200×630 を切り出して `docs/og.png` に置く。

①を②の後にやると、entries.json には配線済みなのに公開HTMLにリンクが出ない（実際に踏んだ）。
`--base-url` の既定値は `https://example.com` で、忘れると robots.txt / sitemap.xml が壊れる。
