#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/（公開物）の整合チェック。デプロイ手順③の後に実行する（標準ライブラリのみ）。
- 全項目の個別ページ docs/entries/<slug>.html が過不足なく存在するか
- sitemap.xml の URL 数と、各 URL に対応するファイルの存在
- index / 個別ページ / 解説ページ の内部リンク切れ
- 個別ページの canonical・lang・JSON-LD・信頼度表示
- 英語版（docs/en/）：個別ページ数＝項目数、hreflang の相互リンク、英語ページに日本語（かな・和文記号）が残っていないか、
  訳の元の日本語が後から変わっていないか（data/i18n/en.json の src）"""
import json, pathlib, re, sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

import build

ROOT = pathlib.Path(__file__).parent
DOCS = ROOT / "docs"
BASE = "https://ymgtksk-blip.github.io/plastic-surgery-atlas"

# 英語ページに残っていてはいけない文字：ひらがな・カタカナ・和文の句読点/括弧・全角英数記号
# （漢字は中国語の原題・人名の原表記があるので許可する）
JA_CHARS = re.compile(r"[\u3001-\u303f\u3040-\u30ff\uff01-\uff60]")
TEXT_ATTRS = ("title", "alt", "content", "aria-label", "placeholder")

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids, self.ld, self._in_ld = [], set(), [], False
        self.alternates = {}   # hreflang → href
        self.canonical = None
        self.texts = []        # 画面に出る文字列（本文・表示用属性・JSONデータ。CSS と JS のコードは除く）
        self._skip = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k) and tag in ("a", "link", "img", "audio", "script"):
                self.hrefs.append(a[k])
        if tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.alternates[a["hreflang"]] = a.get("href")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        for k in TEXT_ATTRS:
            if a.get(k) and not (tag == "link"):
                self.texts.append(a[k])
        self._in_ld = tag == "script" and a.get("type") == "application/ld+json"
        self._skip = tag == "style" or (tag == "script" and a.get("type") not in ("application/json", "application/ld+json"))
    def handle_data(self, data):
        if self._in_ld:
            self.ld.append(data)
        if not self._skip:
            self.texts.append(data)
    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False
        if tag in ("script", "style"):
            self._skip = False

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

    i18n = build.load_i18n("en")
    L_EN = build.make_lang("en", i18n)
    try:
        stale = build.attach_translations(entries, i18n)
    except SystemExit as ex:
        errs.append(str(ex))
        stale = []
    for s in stale:
        errs.append(f"日本語の原文が訳の後に変わっている（en.json の訳を見直して src を更新）: {s}")

    # 1) 個別ページの過不足・slug の形
    files = {p.stem for p in (DOCS / "entries").glob("*.html")}
    en_files = {p.stem for p in (DOCS / "en" / "entries").glob("*.html")}
    for s in slugs:
        if not re.fullmatch(r"[a-z0-9-]+", s):
            errs.append(f"slug に半角英数字・ハイフン以外: {s}")
    missing, extra = set(slugs) - files, files - set(slugs)
    if missing: errs.append(f"個別ページが無い: {sorted(missing)}")
    if extra: errs.append(f"データに無い古い個別ページ: {sorted(extra)}")
    missing, extra = set(slugs) - en_files, en_files - set(slugs)
    if missing: errs.append(f"英語の個別ページが無い: {sorted(missing)}")
    if extra: errs.append(f"データに無い古い英語の個別ページ: {sorted(extra)}")
    if not (DOCS / "en" / "index.html").exists():
        errs.append("英語版トップ docs/en/index.html が無い")

    # 2) sitemap
    sm = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    papers = sorted((DOCS / "papers").glob("*.html"))
    expect = 1 + len(slugs) + len(papers) + 1 + len(slugs)   # 日本語（トップ＋個別＋解説）＋英語（トップ＋個別）
    if len(locs) != expect or len(set(locs)) != len(locs):
        errs.append(f"sitemap の URL 数 {len(locs)}（重複除く {len(set(locs))}）≠ 期待 {expect}")
    for u in locs:
        t = resolve(DOCS / "index.html", u)
        if t is None or not t.exists():
            errs.append(f"sitemap の URL に対応するファイルが無い: {u}")
    # sitemap の hreflang（xhtml:link）：日英の対応ページは両方の <url> に同じ組が書かれていること
    sm_alt = {}
    for block in re.findall(r"<url>(.*?)</url>", sm):
        loc = re.search(r"<loc>([^<]+)</loc>", block).group(1)
        sm_alt[loc] = dict(re.findall(r'<xhtml:link rel="alternate" hreflang="([^"]+)" href="([^"]+)"/>', block))
    n_sm_pairs = 0
    for loc, alt in sm_alt.items():
        if not alt:
            continue
        n_sm_pairs += 1
        if set(alt) != {"ja", "en", "x-default"} or alt["x-default"] != alt["ja"] or loc not in (alt["ja"], alt["en"]):
            errs.append(f"sitemap の hreflang が不正: {loc} {alt}")
            continue
        other = alt["en"] if loc == alt["ja"] else alt["ja"]
        if sm_alt.get(other) != alt:
            errs.append(f"sitemap の hreflang が相互になっていない: {loc} ⇄ {other}")

    # 3) 内部リンク切れ（index・個別・解説）
    en_pages = [DOCS / "en" / "index.html"] + sorted((DOCS / "en" / "entries").glob("*.html"))
    pages = [DOCS / "index.html"] + sorted((DOCS / "entries").glob("*.html")) + papers + en_pages
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

    # 6) 英語版：index のカード → 英語の個別ページ
    en_idx = (DOCS / "en" / "index.html").read_text(encoding="utf-8") if (DOCS / "en" / "index.html").exists() else ""
    en_linked = set(re.findall(r'href="entries/([a-z0-9-]+)\.html"', en_idx))
    if en_linked != set(slugs):
        errs.append(f"英語版 index から個別ページへのリンク不一致: 不足 {sorted(set(slugs)-en_linked)}")
    if '<html lang="en">' not in en_idx:
        errs.append("英語版 index の lang 不正")

    # 7) 英語の個別ページの SEO 要素・信頼度表示・訳文
    for e in entries:
        p = DOCS / "en" / "entries" / f"{e['_slug']}.html"
        if not p.exists() or "_en" not in e:
            continue
        h = p.read_text(encoding="utf-8")
        url = f"{BASE}/en/entries/{e['_slug']}.html"
        if f'<link rel="canonical" href="{url}">' not in h: errs.append(f"canonical 不正: en/{p.name}")
        if '<html lang="en">' not in h: errs.append(f"lang 不正: en/{p.name}")
        if not re.search(r'<meta name="description" content="[^"]+">', h): errs.append(f"description 無し: en/{p.name}")
        for k in ("og:title", "og:image", "og:url"):
            if f'property="{k}"' not in h: errs.append(f"{k} 無し: en/{p.name}")
        if 'name="twitter:card"' not in h: errs.append(f"twitter:card 無し: en/{p.name}")
        try:
            ld = json.loads("".join(parse(p).ld).replace("<\\/", "</"))
            types = {g["@type"] for g in ld["@graph"]}
            wp = next(g for g in ld["@graph"] if g["@type"] == "WebPage")
            if not {"BreadcrumbList", "WebPage"} <= types or not wp.get("citation") or wp.get("inLanguage") != "en":
                errs.append(f"JSON-LD 不足: en/{p.name}")
        except Exception as ex:
            errs.append(f"JSON-LD 解析失敗: en/{p.name}: {ex}")
        conf = e.get("confidence")
        if conf in ("medium", "low") and 'class="conf-box"' not in h:
            errs.append(f"信頼度 {conf} の注記が無い: en/{p.name}")
        if build.esc(build.tx(e, "name", L_EN)) not in h:
            errs.append(f"本文に英語の術式名が静的出力されていない: en/{p.name}")

    # 8) hreflang の相互リンク（日英のトップ・個別ページ）。各ページの canonical が自分自身で、
    #    ja/en/x-default がそろい、相手ページにも同じ組が書かれていること
    alt_pages = [DOCS / "index.html", DOCS / "en" / "index.html"] + sorted((DOCS / "entries").glob("*.html")) + en_pages[1:]
    parsed = {p: parse(p) for p in alt_pages if p.exists()}
    by_url = {lp.canonical: lp for lp in parsed.values()}
    n_pairs = 0
    for p, lp in parsed.items():
        alt = lp.alternates
        name = p.relative_to(DOCS)
        if set(alt) != {"ja", "en", "x-default"}:
            errs.append(f"hreflang がそろっていない: {name} {sorted(alt)}")
            continue
        if alt["x-default"] != alt["ja"]:
            errs.append(f"x-default が日本語版でない: {name}")
        lang = "en" if p.parts[len(DOCS.parts)] == "en" else "ja"
        if lp.canonical != alt[lang]:
            errs.append(f"canonical と自己参照 hreflang が不一致: {name}")
        other = alt["en" if lang == "ja" else "ja"]
        t = resolve(p, other)
        if t is None or not t.exists():
            errs.append(f"hreflang の相手ページが無い: {name} → {other}")
            continue
        olp = by_url.get(other)
        if olp is None or olp.alternates != alt:
            errs.append(f"hreflang が相互になっていない: {name} ⇄ {other}")
            continue
        if lp.canonical in sm_alt and sm_alt[lp.canonical] != alt:
            errs.append(f"ページと sitemap で hreflang が違う: {name}")
        n_pairs += 1

    # 9) 英語ページに日本語（かな・和文記号）が残っていないか（CSS・JS のコードは対象外）
    for p in en_pages:
        if not p.exists():
            continue
        bad = sorted({m for t in parse(p).texts for m in JA_CHARS.findall(t)})
        if bad:
            errs.append(f"英語ページに日本語の文字が残っている: {p.relative_to(DOCS)} {''.join(bad)}")

    print(f"個別ページ {len(files)} / 項目 {len(slugs)}  解説ページ {len(papers)}")
    print(f"英語の個別ページ {len(en_files)} / 項目 {len(slugs)}  英語版トップ {'あり' if en_idx else '無し'}  英語index→個別リンク {len(en_linked)}")
    print(f"hreflang 相互リンク確認 {n_pairs} ページ  sitemap の hreflang 付き URL {n_sm_pairs}")
    print(f"sitemap URL {len(locs)}（期待 {expect}）  内部リンク検査 {n_links} 本  index→個別リンク {len(linked)}")
    if errs:
        print(f"NG {len(errs)} 件:")
        for x in errs:
            print("  -", x)
        sys.exit(1)
    print("OK: 問題なし")

if __name__ == "__main__":
    main()
