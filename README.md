# 術式の系譜 — 形成外科 原典データベース

形成外科の**術式・皮弁・植皮・マイクロサージャリー**の原著論文と、それを**世界で初めて行った人**を、一次資料の出典リンク付きで**年代順**にまとめた検索データベース（日本語）。

**公開サイト**: https://ymgtksk-blip.github.io/plastic-surgery-atlas/

## 特長
- 紀元前600年（スシュルタ）〜現代までの里程標を収録（全項目に出典URL）。
- ライブ検索・カテゴリ絞り込み・「一覧⇄年表」切替。
- SEO最適化：本文は静的HTML、JSON-LD（WebSite / Dataset / ItemList）、OG/Twitter、canonical、sitemap.xml、robots.txt。
- 信頼度を明示（`high` / `medium=史料に諸説あり` / `low=要確認`）。引用時は各原著リンクで最終確認を。

## 構成
- `data/entries.json` — 検証済みデータセット（複数エージェントによる一次資料のWeb検証を経たもの）。
- `build.py` — データセット → 静的サイトを生成する決定的ビルダ（外部依存なし・Python 3）。
- `docs/` — GitHub Pages で公開される生成物。

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
```

①を②の後にやると、entries.json には配線済みなのに公開HTMLにリンクが出ない（実際に踏んだ）。
`--base-url` の既定値は `https://example.com` で、忘れると robots.txt / sitemap.xml が壊れる。
