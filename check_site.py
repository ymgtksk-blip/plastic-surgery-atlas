#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/（公開物）の整合チェック。デプロイ手順③の後に実行する（標準ライブラリのみ）。
- 全項目の個別ページ docs/entries/<slug>.html が過不足なく存在するか
- sitemap.xml の URL 数と、各 URL に対応するファイルの存在
- index / 個別ページ / 解説ページ の内部リンク切れ
- 個別ページの canonical・lang・JSON-LD・信頼度表示"""
import json, pathlib, re, sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

import build

ROOT = pathlib.Path(__file__).parent
DOCS = ROOT / "docs"
BASE = "https://ymgtksk-blip.github.io/plastic-surgery-atlas"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids, self.ld, self._in_ld = [], set(), [], False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k) and tag in ("a", "link", "img", "audio", "script"):
                self.hrefs.append(a[k])
        self._in_ld = tag == "script" and a.get("type") == "application/ld+json"
    def handle_data(self, data):
        if self._in_ld:
            self.ld.append(data)
    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False

def parse(p):
    lp = Links()
    lp.feed(p.read_text(encoding="utf-8"))
    return lp

def resolve(page, href):
    """内部リンクを docs/ 上のファイルに解決。外部・アンカー・data: は None。"""
    if re.match(r"^(https?:|mailto:|data:|#|javascript:)", href):
        if href.startswith(BASE):
            href = href[len(BASE):].lstrip("/") or "index.html"
            return DOCS / unquote(urlsplit(href).path)
        return None
    path = unquote(urlsplit(href).path)
    t = (page.parent / path).resolve()
    if href.endswith("/") or path in ("", "."):
        t = t / "index.html"
    return t

def main():
    errs = []
    entries, _ = build.load_entries()
    build.assign_slugs(entries)
    slugs = [e["_slug"] for e in entries]

    # 1) 個別ページの過不足・slug の形
    files = {p.stem for p in (DOCS / "entries").glob("*.html")}
    for s in slugs:
        if not re.fullmatch(r"[a-z0-9-]+", s):
            errs.append(f"slug に半角英数字・ハイフン以外: {s}")
    missing, extra = set(slugs) - files, files - set(slugs)
    if missing: errs.append(f"個別ページが無い: {sorted(missing)}")
    if extra: errs.append(f"データに無い古い個別ページ: {sorted(extra)}")

    # 2) sitemap
    sm = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    papers = sorted((DOCS / "papers").glob("*.html"))
    expect = 1 + len(slugs) + len(papers)
    if len(locs) != expect or len(set(locs)) != len(locs):
        errs.append(f"sitemap の URL 数 {len(locs)}（重複除く {len(set(locs))}）≠ 期待 {expect}")
    for u in locs:
        t = resolve(DOCS / "index.html", u)
        if t is None or not t.exists():
            errs.append(f"sitemap の URL に対応するファイルが無い: {u}")

    # 3) 内部リンク切れ（index・個別・解説）
    pages = [DOCS / "index.html"] + sorted((DOCS / "entries").glob("*.html")) + papers
    n_links = 0
    for p in pages:
        lp = parse(p)
        for h in lp.hrefs:
            t = resolve(p, h)
            if t is None:
                continue
            n_links += 1
            if not t.exists():
                errs.append(f"リンク切れ: {p.relative_to(DOCS)} → {h}")

    # 4) index のカード → 個別ページのリンク
    idx = (DOCS / "index.html").read_text(encoding="utf-8")
    linked = set(re.findall(r'href="entries/([a-z0-9-]+)\.html"', idx))
    if linked != set(slugs):
        errs.append(f"index から個別ページへのリンク不一致: 不足 {sorted(set(slugs)-linked)}")

    # 5) 個別ページの SEO 要素と信頼度表示
    for e in entries:
        p = DOCS / "entries" / f"{e['_slug']}.html"
        if not p.exists():
            continue
        h = p.read_text(encoding="utf-8")
        url = f"{BASE}/entries/{e['_slug']}.html"
        if f'<link rel="canonical" href="{url}">' not in h: errs.append(f"canonical 不正: {p.name}")
        if '<html lang="ja">' not in h: errs.append(f"lang 不正: {p.name}")
        if not re.search(r'<meta name="description" content="[^"]+">', h): errs.append(f"description 無し: {p.name}")
        for k in ("og:title", "og:image", "og:url"):
            if f'property="{k}"' not in h: errs.append(f"{k} 無し: {p.name}")
        if 'name="twitter:card"' not in h: errs.append(f"twitter:card 無し: {p.name}")
        try:
            ld = json.loads("".join(parse(p).ld).replace("<\\/", "</"))
            types = {g["@type"] for g in ld["@graph"]}
            wp = next(g for g in ld["@graph"] if g["@type"] == "WebPage")
            if not {"BreadcrumbList", "WebPage"} <= types or not wp.get("citation"):
                errs.append(f"JSON-LD 不足: {p.name}")
        except Exception as ex:
            errs.append(f"JSON-LD 解析失敗: {p.name}: {ex}")
        conf = e.get("confidence")
        if conf in ("medium", "low") and 'class="conf-box"' not in h:
            errs.append(f"信頼度 {conf} の注記が無い: {p.name}")
        if e.get("name_ja") and build.esc(e["name_ja"]) not in h:
            errs.append(f"本文に術式名が静的出力されていない: {p.name}")

    print(f"個別ページ {len(files)} / 項目 {len(slugs)}  解説ページ {len(papers)}")
    print(f"sitemap URL {len(locs)}（期待 {expect}）  内部リンク検査 {n_links} 本  index→個別リンク {len(linked)}")
    if errs:
        print(f"NG {len(errs)} 件:")
        for x in errs:
            print("  -", x)
        sys.exit(1)
    print("OK: 問題なし")

if __name__ == "__main__":
    main()
