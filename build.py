#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
形成外科 原典データベース「術式の系譜」 静的サイト・ジェネレータ
data/entries.json（検証済みデータセット）→ dist/index.html（SEO最適化・本文は静的HTML）
                                          → dist/artifact.html（claude.ai Artifactプレビュー用・body only）
                                          → dist/sitemap.xml / robots.txt / og.svg
LLMを使わない決定的ビルド（実行=枠ゼロ）。
"""
import json, html, pathlib, argparse, datetime, re, collections

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"

CAT = {
    "skin_graft":  ("植皮",                 "#9A7B33"),
    "local_flap":  ("局所皮弁・皮弁の原理", "#4E7A6A"),
    "named_flap":  ("名前のついた皮弁",     "#B0524A"),
    "micro":       ("マイクロ・再接着・穿通枝", "#3D5A80"),
    "craniofacial":("頭蓋顔面・その他再建", "#6D4C7D"),
    "history":     ("歴史・基礎・偉人",     "#86735A"),
    "extra":       ("基礎・その他",         "#5F6B63"),
}
CAT_ORDER = ["skin_graft", "local_flap", "named_flap", "micro", "craniofacial", "history", "extra"]

ERAS = [
    (-100000, 999,  "古代・中世"),
    (1000, 1799,    "近世（16–18世紀）"),
    (1800, 1899,    "19世紀"),
    (1900, 1949,    "20世紀前半"),
    (1950, 1979,    "戦後 ― マイクロサージャリーの幕開け"),
    (1980, 1999,    "皮弁・穿通枝の時代"),
    (2000, 3000,    "現代"),
]

# 解剖図譜調のSVGライン画（カテゴリ別・stroke=currentColorで色を継承）
ICON_PATHS = {
    "skin_graft":   '<rect x="4" y="6.5" width="16" height="11" rx="2"/><path d="M8 10l1.6 2M12 10l1.6 2M16 10l1.6 2M8 13.5l1.6 2M12 13.5l1.6 2M16 13.5l1.6 2"/>',
    "local_flap":   '<line x1="12" y1="4" x2="12" y2="20"/><path d="M12 8 L6 6.2 L8.2 12 Z"/><path d="M12 16 L18 17.8 L15.8 12 Z"/>',
    "named_flap":   '<ellipse cx="13" cy="10" rx="6" ry="4.4" transform="rotate(-18 13 10)"/><path d="M8.6 13C6.7 15.4 6.2 18 6.7 20"/><path d="M13 7.6 L12 13"/>',
    "micro":        '<path d="M5 16C9 8 15 6 19 8"/><circle cx="5" cy="16" r="1.1"/><path d="M19 8c-2 2-3 4-2 6" stroke-dasharray="2 2"/>',
    "craniofacial": '<path d="M5 11.5C5 6.5 9 4.2 13 5.2C18 6.2 19 11 17 13L17 16c0 1-1 2-2 2h-2v2h-3v-3c-3-1-5-3-5-5.5Z"/><circle cx="9.2" cy="11.2" r="1.3"/>',
    "history":      '<path d="M12 6.2C10 5.2 6 5.2 4 6.2V18c2-1 6-1 8 0 2-1 6-1 8 0V6.2c-2-1-6-1-8 0Z"/><line x1="12" y1="6.2" x2="12" y2="18"/>',
    "extra":        '<path d="M9.5 4h5M10.5 4v5.5L5.6 18c-.6 1.3.4 2.5 1.9 2.5h9c1.5 0 2.5-1.2 1.9-2.5L13.5 9.5V4"/><line x1="8.4" y1="15" x2="15.6" y2="15"/>',
}

def icon(key, cls=""):
    p = ICON_PATHS.get(key, "")
    return (f'<svg class="ic {cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{p}</svg>')

# ヘッダーの装飾エンブレム（回転皮弁の弧＋縫合線＝外科モチーフ）
HERO_SVG = ('<svg class="hero-emblem" viewBox="0 0 120 120" fill="none" stroke="currentColor" '
            'stroke-width="1.4" stroke-linecap="round" aria-hidden="true">'
            '<path class="arc" d="M18 96 A78 78 0 0 1 96 18"/>'
            '<path class="arc" d="M30 96 A66 66 0 0 1 96 30"/>'
            '<path class="arc" d="M42 96 A54 54 0 0 1 96 42"/>'
            '<line x1="22" y1="60" x2="98" y2="60" stroke-dasharray="1 7"/>'
            '<line x1="60" y1="22" x2="60" y2="98" stroke-dasharray="1 7"/></svg>')

def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)

def author_key(a):
    m = re.search(r"[A-Za-z]{2,}", a or "")
    return m.group(0).lower() if m else re.sub(r"\s+", "", (a or ""))

def richness(e):
    return len(e.get("significance_ja", "") or "") + len(e.get("history_note_ja", "") or "")

def load_entries():
    raw = json.loads((ROOT / "data" / "entries.json").read_text(encoding="utf-8"))
    # カテゴリ横断の重複（同年・同著者頭）を、情報量の多い方に集約
    best = {}
    order = []
    for e in raw:
        k = (e.get("year_sort", 0), author_key(e.get("author", "")))
        if k in best:
            if richness(e) > richness(best[k]):
                best[k] = e
        else:
            best[k] = e
            order.append(k)
    entries = [best[k] for k in order]
    entries.sort(key=lambda e: (e.get("year_sort", 0), CAT_ORDER.index(e["category_key"]) if e.get("category_key") in CAT_ORDER else 99))
    return entries, len(raw)

def search_blob(e):
    parts = [e.get("name_ja",""), e.get("name_original",""), e.get("author",""),
             e.get("journal",""), e.get("paper_title",""), e.get("significance_ja",""),
             CAT.get(e.get("category_key",""), ("",""))[0]]
    for p in e.get("papers", []) or []:
        parts += [p.get("author",""), p.get("title",""), p.get("journal","")]
    return re.sub(r"\s+", " ", " ".join(parts)).lower()

def render_sources(e):
    """単一urlの従来項目 → 1リンク。papers[]付き項目 → 複数論文リスト（原著/PDF/日本語解説リンク）。"""
    papers = e.get("papers")
    if not papers:
        return (f'<a class="src" href="{esc(e.get("url",""))}" target="_blank" rel="noopener noreferrer">'
                f'原著・出典を見る<span aria-hidden="true"> ↗</span></a>')
    rows = []
    for p in papers:
        links = [f'<a href="{esc(p.get("url",""))}" target="_blank" rel="noopener noreferrer">'
                 f'{esc(p.get("link_label","原著・抄録"))}<span aria-hidden="true"> ↗</span></a>']
        if p.get("pdf"):
            links.append(f'<a class="pdf" href="{esc(p["pdf"])}" target="_blank" rel="noopener noreferrer">'
                         f'PDF<span aria-hidden="true"> ↓</span></a>')
        if p.get("commentary"):
            links.append(f'<a class="jp" href="{esc(p["commentary"])}">'
                         f'日本語解説<span aria-hidden="true"> →</span></a>')
        kind = p.get("kind", "")
        kind_html = f'<span class="p-kind">{esc(kind)}</span>' if kind else ""
        rows.append(
            '<li class="paper">'
            f'<span class="p-yr">{esc(p.get("year",""))}</span>'
            '<span class="p-body">'
            f'<span class="p-head">{kind_html}<span class="p-au">{esc(p.get("author",""))}</span></span>'
            f'<cite class="p-ti">{esc(p.get("title",""))}</cite>'
            f'<span class="p-jr">{esc(p.get("journal",""))}</span>'
            f'<span class="p-links">{" ".join(links)}</span>'
            '</span></li>'
        )
    return ('<div class="papers"><p class="papers-h">原著・関連論文</p>'
            f'<ol class="paper-list">{"".join(rows)}</ol></div>')

def cat_label_color(e):
    return CAT.get(e.get("category_key", "extra"), ("基礎・その他", "#5F6B63"))

def render_card(e, idx):
    key = e.get("category_key", "extra")
    label, color = cat_label_color(e)
    ys = e.get("year_sort", 0)
    conf = e.get("confidence", "high")
    dt_attr = f' datetime="{ys:04d}"' if isinstance(ys, int) and ys > 0 else ""
    first = e.get("is_first")
    blob = search_blob(e)
    note = (e.get("history_note_ja") or "").strip()
    note_html = ""
    if note:
        note_html = (
            '<details class="note"><summary>歴史注・「世界初」の背景</summary>'
            f'<p>{esc(note)}</p></details>'
        )
    conf_html = ""
    if conf == "medium":
        conf_html = '<p class="conf-tag" title="年代・出典に史料的な幅があります">※ 史料に諸説あり</p>'
    elif conf == "low":
        conf_html = '<p class="conf-tag conf-low-tag">※ 出典は要確認</p>'
    first_html = '<span class="first" title="世界で初めて行われた（とされる）里程標">初</span>' if first else ""
    has_papers = bool(e.get("papers"))
    meta_html = "" if has_papers else (
        f'<p class="au">{esc(e.get("author",""))}</p>'
        f'<p class="pp"><cite>{esc(e.get("paper_title",""))}</cite></p>'
        f'<p class="jr">{esc(e.get("journal",""))}</p>'
    )
    return (
        f'<article class="card conf-{esc(conf)}" data-cat="{esc(key)}" data-first="{1 if first else 0}" '
        f'data-year="{ys}" data-search="{esc(blob)}" id="e{idx}">'
        f'<header class="card-h"><time class="yr"{dt_attr}>{esc(e.get("year_display",""))}</time>'
        f'<span class="chip" style="--c:{color}">{icon(key, "chip-ic")}{esc(label)}</span>{first_html}</header>'
        f'<h2 class="nm">{esc(e.get("name_ja",""))}</h2>'
        f'<p class="og">{esc(e.get("name_original",""))}</p>'
        f'{meta_html}'
        f'<p class="sig">{esc(e.get("significance_ja",""))}</p>'
        f'{conf_html}{note_html}'
        f'{render_sources(e)}'
        f'</article>'
    )

def render_chips(entries):
    counts = collections.Counter(e.get("category_key", "extra") for e in entries)
    chips = [f'<button class="chip-f" type="button" data-cat="all" aria-pressed="true">'
             f'<span class="dot" style="--c:var(--ink)"></span>すべて <span class="n">{len(entries)}</span></button>']
    for k in CAT_ORDER:
        if counts.get(k):
            label, color = CAT[k]
            chips.append(
                f'<button class="chip-f" type="button" data-cat="{k}" aria-pressed="false">'
                f'<span class="ci" style="color:{color}">{icon(k)}</span>{esc(label)} <span class="n">{counts[k]}</span></button>'
            )
    return "\n".join(chips)

def render_jsonld(entries, base):
    items = []
    for i, e in enumerate(entries, 1):
        yd = e.get("year_display", "")
        year_m = re.search(r"\d{3,4}", yd)
        node = {
            "@type": "ScholarlyArticle",
            "name": e.get("paper_title", "") or e.get("name_ja", ""),
            "headline": e.get("name_ja", ""),
            "author": {"@type": "Person", "name": e.get("author", "")},
            "url": e.get("url", ""),
            "about": e.get("significance_ja", ""),
            "isPartOf": e.get("journal", ""),
        }
        if year_m and e.get("year_sort", 0) > 0:
            node["datePublished"] = year_m.group(0)
        items.append({"@type": "ListItem", "position": i, "item": node})
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": base + "#website", "url": base,
             "name": "術式の系譜 — 形成外科 原典データベース",
             "inLanguage": "ja",
             "description": "形成外科の術式・皮弁・植皮・マイクロサージャリーの原著論文と『世界で初めて行った人』を一次資料リンク付きで年代順にまとめた検索データベース。"},
            {"@type": "Dataset", "@id": base + "#dataset",
             "name": "形成外科 術式原典データベース",
             "description": "紀元前600年のスシュルタから現代まで、形成外科の里程標となる術式・原著論文を出典付きで収録。",
             "inLanguage": "ja", "isAccessibleForFree": True, "url": base,
             "keywords": ["形成外科", "再建外科", "皮弁", "植皮", "マイクロサージャリー", "原著論文", "医学史"],
             "creator": {"@type": "Person", "name": "山形孝介"}},
            {"@type": "ItemList", "name": "形成外科の術式・原著 年代順一覧",
             "numberOfItems": len(entries), "itemListOrder": "https://schema.org/ItemListOrderAscending",
             "itemListElement": items},
        ],
    }
    return json.dumps(graph, ensure_ascii=False)

HEADPHONE = ('<svg class="pod-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/>'
             '<rect x="3" y="13.5" width="4.2" height="6.5" rx="1.3"/>'
             '<rect x="16.8" y="13.5" width="4.2" height="6.5" rx="1.3"/></svg>')

def render_pod(ep):
    if not ep:
        return ""
    turns = ep.get("turns", [])
    tr = "".join(
        f'<p class="ln"><span class="sp sp-{"navi" if t["speaker"]=="ナビ" else "sensei"}">'
        f'{esc(t["speaker"])}</span>{esc(t["text"])}</p>' for t in turns)
    mins = round(ep.get("duration_s", 0) / 60)
    return (
        '<section class="pod" id="podcast"><div class="wrap pod-in">'
        f'<div class="pod-head">{HEADPHONE}<div class="pod-h-t">'
        '<p class="pod-eyebrow">聴いて楽しむ ・ ポッドキャスト 第1回</p>'
        f'<h2 class="pod-title">{esc(ep.get("title",""))}</h2></div></div>'
        f'<p class="pod-sum">{esc(ep.get("summary",""))}</p>'
        '<audio class="pod-audio" controls preload="none" src="audio/ep1.mp3">'
        'お使いのブラウザは音声再生に対応していません。<a href="audio/ep1.mp3">MP3を開く</a>。</audio>'
        f'<p class="pod-links"><a href="audio/ep1.mp3" download>⬇ MP3をダウンロード（約{mins}分）</a>'
        '<a href="feed.xml">🎧 Podcastアプリで購読（RSS）</a></p>'
        '<details class="pod-tr"><summary>台本を読む（全文）</summary>'
        f'<div class="tr">{tr}</div></details>'
        '</div></section>')

def render_rss(ep, base):
    import email.utils
    pub = email.utils.format_datetime(datetime.datetime.now().astimezone())
    dur = int(ep.get("duration_s", 0))
    hms = f"{dur//3600:02d}:{(dur%3600)//60:02d}:{dur%60:02d}"
    cover = f"{base}/audio/cover.png"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">\n<channel>\n'
        '<title>からだを、つくり直す ― 形成外科2600年の物語</title>\n'
        f'<link>{base}/</link>\n<language>ja</language>\n'
        '<description>形成外科の術式・原著と「世界初」を、二人のかけあいでたどる歴史ポッドキャスト。データベース「術式の系譜」より。</description>\n'
        '<itunes:author>術式の系譜</itunes:author>\n'
        '<itunes:summary>形成外科2600年の里程標を、物語で。</itunes:summary>\n'
        '<itunes:owner><itunes:name>術式の系譜</itunes:name></itunes:owner>\n'
        '<itunes:category text="Science"><itunes:category text="Medicine"/></itunes:category>\n'
        '<itunes:explicit>false</itunes:explicit>\n<itunes:type>episodic</itunes:type>\n'
        f'<itunes:image href="{cover}"/>\n'
        f'<image><url>{cover}</url><title>からだを、つくり直す</title><link>{base}/</link></image>\n'
        '<item>\n'
        f'<title>{esc(ep.get("title",""))}</title>\n'
        f'<description>{esc(ep.get("summary",""))}</description>\n'
        f'<pubDate>{pub}</pubDate>\n'
        f'<enclosure url="{base}/audio/ep1.mp3" length="{ep.get("bytes",0)}" type="audio/mpeg"/>\n'
        '<guid isPermaLink="false">keisei-atlas-ep1</guid>\n'
        f'<itunes:duration>{hms}</itunes:duration>\n'
        '<itunes:episode>1</itunes:episode>\n<itunes:explicit>false</itunes:explicit>\n'
        '</item>\n</channel>\n</rss>\n')

CSS = r"""
:root{
  --ink:#22201C; --paper:#EFEBE2; --surface:#FBF9F4; --surface2:#F5F1E8;
  --muted:#6E655A; --faint:#8C8377; --rule:#DED6C7;
  --accent:#7E2B26; --accent-deep:#5C1D1A; --accent-tint:rgba(126,43,38,.09);
  --serif:"Hoefler Text","Iowan Old Style","Hiragino Mincho ProN","YuMincho","Yu Mincho",Palatino,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,"Cascadia Code",monospace;
  --maxw:1180px;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.72;font-size:16px;letter-spacing:.01em}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 22px}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
h1,h2,p{margin:0}

.mast{position:sticky;top:0;z-index:20;background:rgba(239,235,226,.90);-webkit-backdrop-filter:saturate(1.3) blur(9px);backdrop-filter:saturate(1.3) blur(9px);border-bottom:1px solid var(--rule)}
.mast-in{padding:20px 0 6px}
.eyebrow{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:8px}
.title{font-family:var(--serif);font-weight:600;font-size:clamp(28px,4.4vw,44px);line-height:1.04;letter-spacing:.01em;text-wrap:balance}
.title .en{display:block;font-size:.4em;letter-spacing:.16em;color:var(--muted);font-weight:500;margin-top:9px;text-transform:uppercase}
.thesis{max-width:64ch;color:var(--muted);margin-top:12px;font-size:15px}
.stat{font-family:var(--mono);font-size:12.5px;color:var(--faint);margin-top:9px;font-variant-numeric:tabular-nums}
.stat b{color:var(--ink);font-weight:600}
.controls{display:flex;flex-wrap:wrap;gap:12px 14px;align-items:center;padding:16px 0 12px}
.search{position:relative;flex:1 1 300px;min-width:210px}
.search input{width:100%;font:inherit;font-size:15px;padding:11px 14px 11px 40px;border:1px solid var(--rule);border-radius:11px;background:var(--surface);color:var(--ink)}
.search input::placeholder{color:var(--faint)}
.search svg{position:absolute;left:13px;top:50%;transform:translateY(-50%);width:16px;height:16px;stroke:var(--faint);fill:none}
.views{display:inline-flex;border:1px solid var(--rule);border-radius:11px;overflow:hidden;background:var(--surface)}
.views button{font:inherit;font-size:14px;padding:9px 17px;border:0;background:transparent;color:var(--muted);cursor:pointer}
.views button[aria-pressed=true]{background:var(--accent);color:#fff}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding-bottom:16px}
.chip-f{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--rule);border-radius:999px;background:var(--surface);color:var(--muted);cursor:pointer;display:inline-flex;align-items:center;gap:7px;line-height:1.4}
.chip-f .dot{width:9px;height:9px;border-radius:50%;background:var(--c,#999);flex:none}
.chip-f .n{font-family:var(--mono);font-size:11px;color:var(--faint)}
.chip-f[aria-pressed=true]{border-color:var(--ink);color:var(--ink);background:var(--surface2);font-weight:600}
.chip-f[aria-pressed=true] .n{color:var(--muted)}

main{padding:26px 0 40px;min-height:50vh}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(298px,1fr));gap:18px}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:14px;padding:17px 18px 15px;display:flex;flex-direction:column;gap:5px;transition:border-color .18s,box-shadow .18s,transform .18s}
.card:hover{border-color:#cbbca3;box-shadow:0 7px 22px rgba(60,42,22,.08)}
.card-h{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.yr{font-family:var(--mono);font-size:20px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.chip{font-size:11px;letter-spacing:.03em;padding:3px 9px;border-radius:999px;color:#fff;background:var(--c);white-space:nowrap}
.first{margin-left:auto;font-family:var(--serif);font-size:12px;font-weight:700;color:var(--accent);border:1.5px solid var(--accent);border-radius:50%;width:23px;height:23px;display:inline-grid;place-items:center}
.nm{font-family:var(--serif);font-size:19px;line-height:1.32;margin-top:5px;font-weight:600;text-wrap:balance}
.og{font-family:var(--serif);font-style:italic;color:var(--muted);font-size:14px}
.au{font-size:14px;color:var(--ink);margin-top:6px;font-weight:600}
.pp{font-size:13.5px;margin-top:2px}
.pp cite{font-style:italic}
.jr{font-family:var(--mono);font-size:11.5px;color:var(--faint);line-height:1.5}
.sig{font-size:14px;color:var(--ink);margin-top:9px}
.conf-tag{font-size:11px;color:var(--faint);font-family:var(--mono);margin-top:6px}
.conf-low-tag{color:var(--accent)}
.note{margin-top:9px}
.note summary{font-size:12.5px;color:var(--accent);cursor:pointer;list-style:none}
.note summary::-webkit-details-marker{display:none}
.note summary::before{content:"＋ "}
.note[open] summary::before{content:"− "}
.note p{font-size:13px;color:var(--muted);margin-top:6px;padding:2px 0 2px 11px;border-left:2px solid var(--rule)}
.src{margin-top:13px;font-size:13px;font-weight:600;align-self:flex-start;text-decoration:none;border-bottom:1px solid var(--accent);padding-bottom:1px}
.src:hover{color:var(--accent-deep);border-color:var(--accent-deep)}
.papers{margin-top:13px}
.papers-h{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--faint);text-transform:uppercase;margin-bottom:8px}
.paper-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:11px}
.paper{display:grid;grid-template-columns:46px 1fr;gap:10px;padding-top:10px;border-top:1px dotted var(--rule)}
.paper:first-child{border-top:0;padding-top:0}
.p-yr{font-family:var(--mono);font-size:14px;color:var(--accent);font-weight:700;font-variant-numeric:tabular-nums;padding-top:1px}
.p-body{display:flex;flex-direction:column;gap:3px;min-width:0}
.p-head{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.p-kind{font-size:10px;font-weight:700;letter-spacing:.03em;color:var(--muted);background:var(--surface2);border:1px solid var(--rule);border-radius:4px;padding:1px 6px;white-space:nowrap}
.p-au{font-size:12.5px;color:var(--ink);font-weight:600}
.p-ti{font-size:13.5px;font-style:italic;color:var(--ink);line-height:1.4}
.p-jr{font-family:var(--mono);font-size:11px;color:var(--faint);line-height:1.5}
.p-links{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:4px;font-size:12.5px;font-weight:600}
.p-links a{text-decoration:none;border-bottom:1px solid var(--accent);padding-bottom:1px;color:var(--accent)}
.p-links a.pdf{color:#3D5A80;border-color:#3D5A80}
.p-links a.pdf:hover{color:#26374d;border-color:#26374d}
.p-links a.jp{color:#4E7A6A;border-color:#4E7A6A}
.p-links a.jp:hover{color:#3a5c50;border-color:#3a5c50}
/* 論文解説ページ */
.paper-page{max-width:760px;padding-top:26px;padding-bottom:56px}
.paper-page .cite-box{background:var(--surface);border:1px solid var(--rule);border-left:3px solid var(--accent);border-radius:10px;padding:15px 17px;margin-bottom:22px}
.paper-page .cite-box .c-au{font-weight:600;font-size:14px}
.paper-page .cite-box .c-ti{font-style:italic;font-size:15px;margin-top:3px;display:block}
.paper-page .cite-box .c-jr{font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:4px}
.paper-page .cite-box .c-links{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:11px;font-size:13px;font-weight:600}
.paper-page .cite-box .c-links a{text-decoration:none;border-bottom:1px solid var(--accent);padding-bottom:1px}
.paper-page .cite-box .c-links a.pdf{color:#3D5A80;border-color:#3D5A80}
.paper-page .lead{font-size:16.5px;line-height:1.85;color:var(--ink);margin-bottom:10px;font-weight:500}
.paper-page section{margin-top:26px}
.paper-page section h2{font-family:var(--serif);font-size:21px;font-weight:600;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--rule)}
.paper-page section p{margin:10px 0;font-size:15px;line-height:1.9}
.paper-page .takeaways{margin-top:28px;background:var(--surface2);border-radius:12px;padding:18px 20px}
.paper-page .takeaways h2{font-family:var(--serif);font-size:18px;font-weight:600;margin-bottom:10px;border:0;padding:0}
.paper-page .takeaways ul{margin:0;padding-left:20px}
.paper-page .takeaways li{margin:7px 0;font-size:14.5px;line-height:1.7}
.paper-page .glossary{margin-top:26px}
.paper-page .glossary h2{font-family:var(--serif);font-size:18px;font-weight:600;margin-bottom:10px}
.paper-page .glossary dl{margin:0}
.paper-page .glossary dt{font-weight:700;font-size:14px;color:var(--accent-deep);margin-top:12px}
.paper-page .glossary dd{margin:3px 0 0;font-size:14px;color:var(--muted);line-height:1.7}
.paper-page .disclaimer{margin-top:30px;padding-top:16px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--faint);line-height:1.7}
.paper-page .backlink{display:inline-block;margin-top:18px;font-size:14px;font-weight:600;text-decoration:none;border-bottom:1px solid var(--accent);padding-bottom:1px}
.crumb{font-size:13px;color:var(--muted);margin-bottom:6px}
.crumb a{font-weight:600;text-decoration:none}
.empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:64px 0;font-size:15px}

.tl{display:none}
body.view-tl .grid{display:none}
body.view-tl .tl{display:block}
.era-h{font-family:var(--serif);font-size:22px;font-weight:600;margin:34px 0 2px;padding-bottom:7px;border-bottom:1px solid var(--rule)}
.era-h .c{font-family:var(--mono);font-size:12px;color:var(--faint);font-weight:400;margin-left:8px}
.tl-row{display:grid;grid-template-columns:92px 1fr;gap:16px;padding:11px 2px;border-bottom:1px dotted var(--rule);text-decoration:none;color:inherit}
.tl-row:hover{background:var(--surface2)}
.tl-yr{font-family:var(--mono);font-size:15px;color:var(--accent);font-weight:600;text-align:right;font-variant-numeric:tabular-nums;padding-top:1px}
.tl-body .n{font-family:var(--serif);font-size:16px;font-weight:600}
.tl-body .o{font-style:italic;color:var(--muted);font-size:13px}
.tl-body .a{display:block;font-size:12.5px;color:var(--muted);margin-top:1px}
.tl-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:middle}
.tl-first{font-family:var(--serif);font-size:11px;color:var(--accent);border:1px solid var(--accent);border-radius:50%;width:17px;height:17px;display:inline-grid;place-items:center;margin-left:6px;vertical-align:middle}

footer{border-top:1px solid var(--rule);margin-top:30px;padding:28px 0 64px;color:var(--muted);font-size:13px}
footer p{margin:6px 0;max-width:72ch}
footer b{color:var(--ink)}

@media (max-width:560px){
  .grid{grid-template-columns:1fr}
  .tl-row{grid-template-columns:70px 1fr;gap:12px}
}
.pod{background:linear-gradient(180deg,var(--surface2),var(--surface));border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.pod-in{padding:26px 22px 30px}
.pod-head{display:flex;gap:14px;align-items:flex-start}
.pod-ic{width:30px;height:30px;color:var(--accent);flex:none;margin-top:4px}
.pod-eyebrow{font-size:12px;letter-spacing:.16em;color:var(--accent);font-weight:700}
.pod-title{font-family:var(--serif);font-size:clamp(20px,3vw,27px);font-weight:600;line-height:1.22;margin-top:3px;text-wrap:balance}
.pod-sum{color:var(--muted);font-size:14.5px;margin-top:10px;max-width:72ch}
.pod-audio{width:100%;max-width:640px;margin-top:16px;display:block}
.pod-links{display:flex;flex-wrap:wrap;gap:9px 20px;margin-top:13px;font-size:13.5px;font-weight:600}
.pod-links a{text-decoration:none;border-bottom:1px solid var(--accent);padding-bottom:1px}
.pod-tr{margin-top:16px;max-width:80ch}
.pod-tr summary{font-size:13px;color:var(--accent);cursor:pointer;font-weight:600}
.pod-tr .tr{margin-top:12px;border-left:2px solid var(--rule);padding-left:14px;max-height:440px;overflow:auto}
.pod-tr .ln{font-size:14px;margin:9px 0;line-height:1.72}
.pod-tr .sp{font-weight:700;margin-right:8px;font-size:11.5px;padding:1px 7px;border-radius:4px;white-space:nowrap;color:#fff}
.pod-tr .sp-navi{background:var(--accent)}
.pod-tr .sp-sensei{background:#3D5A80}
.ic{width:1em;height:1em;display:inline-block;vertical-align:-.12em;flex:none}
.chip{display:inline-flex;align-items:center;gap:5px}
.chip .ic{width:13px;height:13px}
.chip-f .ci{display:inline-flex;width:15px;height:15px;align-items:center}
.chip-f .ci .ic{width:15px;height:15px}
.mast-in{position:relative}
.hero-emblem{position:absolute;right:2px;top:14px;width:120px;height:120px;color:var(--accent);opacity:.14;pointer-events:none}
@media (max-width:640px){.hero-emblem{display:none}}
@media (prefers-reduced-motion:no-preference){.hero-emblem .arc{stroke-dasharray:270;stroke-dashoffset:270;animation:draw 2.2s .25s ease forwards}@keyframes draw{to{stroke-dashoffset:0}}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
"""

JS = r"""
(function(){
  var q=document.getElementById('q');
  var cards=[].slice.call(document.querySelectorAll('.card'));
  var chips=[].slice.call(document.querySelectorAll('.chip-f'));
  var vcount=document.getElementById('vcount');
  var emptyEl=document.getElementById('empty');
  var activeCat='all';
  var ENTRIES=JSON.parse(document.getElementById('entries').textContent);
  var CATCOLOR=JSON.parse(document.getElementById('catcolor').textContent);
  var ERAS=[[-100000,999,"古代・中世"],[1000,1799,"近世（16–18世紀）"],[1800,1899,"19世紀"],[1900,1949,"20世紀前半"],[1950,1979,"戦後 ― マイクロサージャリーの幕開け"],[1980,1999,"皮弁・穿通枝の時代"],[2000,3000,"現代"]];

  // ---- timeline build ----
  var tl=document.getElementById('timeline');
  function el(t,c){var n=document.createElement(t); if(c)n.className=c; return n;}
  ERAS.forEach(function(era,ei){
    var inEra=ENTRIES.filter(function(e){return e.y>=era[0]&&e.y<=era[1];});
    if(!inEra.length) return;
    var sec=el('section','era'); sec.dataset.era=ei;
    var h=el('div','era-h'); h.innerHTML=era[2]+'<span class="c">'+inEra.length+'</span>'; sec.appendChild(h);
    inEra.forEach(function(e){
      var a=el('a','tl-row'); a.href=e.url; a.target='_blank'; a.rel='noopener noreferrer';
      a.dataset.cat=e.ck; a.dataset.q=e.q;
      var color=CATCOLOR[e.ck]||'#888';
      a.innerHTML='<span class="tl-yr">'+e.yd+'</span><span class="tl-body">'
        +'<span class="tl-dot" style="background:'+color+'"></span>'
        +'<span class="n">'+e.nm+'</span> <span class="o">'+e.og+'</span>'
        +(e.first?'<span class="tl-first" title="世界初">初</span>':'')
        +'<span class="a">'+e.au+'</span></span>';
      sec.appendChild(a);
    });
    tl.appendChild(sec);
  });
  var tlRows=[].slice.call(tl.querySelectorAll('.tl-row'));
  var tlSecs=[].slice.call(tl.querySelectorAll('.era'));

  // ---- filtering ----
  function apply(){
    var term=(q.value||'').trim().toLowerCase();
    var n=0;
    cards.forEach(function(c){
      var ok=(activeCat==='all'||c.dataset.cat===activeCat)&&(!term||c.dataset.search.indexOf(term)>-1);
      c.style.display=ok?'':'none'; if(ok)n++;
    });
    if(vcount)vcount.textContent=n;
    if(emptyEl)emptyEl.style.display=n?'none':'';
    tlRows.forEach(function(r){
      var ok=(activeCat==='all'||r.dataset.cat===activeCat)&&(!term||r.dataset.q.indexOf(term)>-1);
      r.style.display=ok?'':'none';
    });
    tlSecs.forEach(function(s){
      var vis=[].slice.call(s.querySelectorAll('.tl-row')).some(function(r){return r.style.display!=='none';});
      s.style.display=vis?'':'none';
    });
  }
  q.addEventListener('input',apply);
  chips.forEach(function(ch){ch.addEventListener('click',function(){
    chips.forEach(function(x){x.setAttribute('aria-pressed','false');});
    ch.setAttribute('aria-pressed','true'); activeCat=ch.dataset.cat; apply();
  });});
  var vList=document.getElementById('v-list'), vTl=document.getElementById('v-tl');
  vList.addEventListener('click',function(){document.body.classList.remove('view-tl');vList.setAttribute('aria-pressed','true');vTl.setAttribute('aria-pressed','false');});
  vTl.addEventListener('click',function(){document.body.classList.add('view-tl');vTl.setAttribute('aria-pressed','true');vList.setAttribute('aria-pressed','false');window.scrollTo(0,0);});
  apply();
})();
"""

def build_body(entries, episode=None):
    cards = "\n".join(render_card(e, i) for i, e in enumerate(entries))
    chips = render_chips(entries)
    firsts = sum(1 for e in entries if e.get("is_first"))
    tl_entries = [{
        "y": e.get("year_sort", 0), "yd": e.get("year_display", ""),
        "nm": e.get("name_ja", ""), "og": e.get("name_original", ""),
        "au": e.get("author", ""), "ck": e.get("category_key", "extra"),
        "url": e.get("url", ""), "first": bool(e.get("is_first")),
        "q": search_blob(e),
    } for e in entries]
    catcolor = {k: v[1] for k, v in CAT.items()}
    pod = render_pod(episode)
    search_svg = ('<svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round">'
                  '<circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>')
    body = f"""<header class="mast"><div class="wrap mast-in">
{HERO_SVG}
<p class="eyebrow">形成外科 原典データベース</p>
<h1 class="title">術式の系譜<span class="en">Genealogy of Reconstructive Operations</span></h1>
<p class="thesis">紀元前600年のスシュルタから現代まで ― 形成外科を形づくった術式・皮弁・植皮・マイクロサージャリーの<b>原著論文</b>と、それを<b>世界で初めて行った人</b>を、一次資料へのリンク付きで年代順にたどる。</p>
<p class="stat"><b>{len(entries)}</b> 術式・原著 ／ 前600年〜2005年 ／ うち <b>{firsts}</b> 件が「世界初」の里程標</p>
<div class="controls">
<div class="search"><label for="q" class="sr-only" style="position:absolute;left:-9999px">検索</label>{search_svg}
<input id="q" type="search" autocomplete="off" placeholder="術式・人名・皮弁名で検索（例：皮弁, Koshima, TRAM, 鼻）"></div>
<div class="views" role="group" aria-label="表示切替">
<button id="v-list" type="button" aria-pressed="true">一覧</button>
<button id="v-tl" type="button" aria-pressed="false">年表</button></div>
</div>
<div class="chips" role="group" aria-label="カテゴリで絞り込み">
{chips}
</div>
</div></header>
{pod}
<main class="wrap">
<div class="grid" id="list">
{cards}
<p class="empty" id="empty" style="display:none">該当する術式が見つかりません。検索語やカテゴリを変えてお試しください。</p>
</div>
<div class="tl" id="timeline" aria-label="年表"></div>
</main>
<footer><div class="wrap">
<p><b>術式の系譜</b> ― 形成外科の術式・原著論文を一次資料の出典リンク付きで収録した非営利のデータベース。各項目は複数エージェントによるWeb検証を経ています。</p>
<p>年代・出典に史料的な幅がある項目には「※ 史料に諸説あり」を付しています。医学的判断・引用の際は必ずリンク先の原著・一次資料をご確認ください。誤り・追加のご指摘は歓迎します。</p>
<p>データ {len(entries)} 項目 ／ 最終更新 {datetime.date.today().isoformat()}</p>
</div></footer>
<script id="entries" type="application/json">{json.dumps(tl_entries, ensure_ascii=False)}</script>
<script id="catcolor" type="application/json">{json.dumps(catcolor, ensure_ascii=False)}</script>
<script>{JS}</script>"""
    return body

FIG_CSS = """
figure.paper-fig{margin:22px 0;padding:0}
figure.paper-fig img{width:100%;height:auto;display:block;border-radius:8px;border:1px solid rgba(0,0,0,.14);background:#fff}
figure.paper-fig figcaption{font-size:14px;line-height:1.7;color:#4a4640;margin-top:8px}
figure.paper-fig .fig-cap{display:block}
figure.paper-fig .fig-src{display:block;margin-top:5px;font-size:12.5px;color:#6d675e}
figure.paper-fig .fig-src a{color:#6d675e}
figure.paper-fig .fig-note{display:block;margin-top:4px;font-size:12.5px;color:#8a6a3a}
"""

def render_figures(figs):
    """CC BY 等・再利用が明示的に許諾された図のみを掲載する。
    クレジット（著者・誌名・出典リンク・ライセンス）は必須。原著の図は権利上ここに載せない。"""
    out = ""
    for f in figs:
        cr = f.get("credit", {})
        src_bits = []
        if cr.get("author"):
            src_bits.append(esc(cr["author"]))
        if cr.get("journal"):
            src_bits.append(esc(cr["journal"]))
        cite = "／".join(src_bits)
        link = (f'<a href="{esc(cr["url"])}" target="_blank" rel="noopener noreferrer">出典'
                f'<span aria-hidden="true"> ↗</span></a>') if cr.get("url") else ""
        lic = (f'<a href="{esc(cr["license_url"])}" target="_blank" rel="noopener noreferrer">'
               f'{esc(cr.get("license","CC BY"))}<span aria-hidden="true"> ↗</span></a>') if cr.get("license_url") else esc(cr.get("license",""))
        note = f'<span class="fig-note">{esc(f["note"])}</span>' if f.get("note") else ""
        out += (f'<figure class="paper-fig">'
                f'<img src="{esc(f["src"])}" alt="{esc(f.get("alt",""))}" loading="lazy" decoding="async">'
                f'<figcaption><span class="fig-cap">{esc(f.get("caption",""))}</span>'
                f'<span class="fig-src">図の出典：{cite}　{link}　ライセンス：{lic}</span>'
                f'{note}</figcaption></figure>')
    return out

def render_commentary_page(d, base):
    """英語原著の日本語解説ページ（教育目的のオリジナル解説。逐語訳ではない）。"""
    pp = d.get("paper", {})
    c_links = [f'<a href="{esc(pp.get("url",""))}" target="_blank" rel="noopener noreferrer">原著（PubMed）<span aria-hidden="true"> ↗</span></a>']
    if pp.get("pdf"):
        c_links.append(f'<a class="pdf" href="{esc(pp["pdf"])}" target="_blank" rel="noopener noreferrer">無料PDF<span aria-hidden="true"> ↓</span></a>')
    secs = ""
    for s in d.get("sections", []):
        ps = "".join(f"<p>{esc(x)}</p>" for x in s.get("p", []))
        secs += f'<section><h2>{esc(s.get("h",""))}</h2>{ps}{render_figures(s.get("figures", []))}</section>'
    takeaways = ""
    if d.get("takeaways"):
        lis = "".join(f"<li>{esc(x)}</li>" for x in d["takeaways"])
        takeaways = f'<div class="takeaways"><h2>この論文の要点</h2><ul>{lis}</ul></div>'
    glossary = ""
    if d.get("glossary"):
        items = "".join(f"<dt>{esc(g.get('term',''))}</dt><dd>{esc(g.get('def',''))}</dd>" for g in d["glossary"])
        glossary = f'<div class="glossary"><h2>用語ミニ辞典</h2><dl>{items}</dl></div>'
    title = f'{d.get("title_ja","")}｜術式の系譜'
    desc = (d.get("lead","") or "")[:110]
    body = f"""<header class="mast"><div class="wrap mast-in">
<p class="crumb"><a href="../">術式の系譜</a> ／ 論文 日本語解説</p>
<p class="eyebrow">{esc(d.get("flap_ja",""))}</p>
<h1 class="title" style="font-size:clamp(23px,3.6vw,34px)">{esc(d.get("title_ja",""))}</h1>
</div></header>
<main class="wrap paper-page">
<div class="cite-box">
<span class="c-au">{esc(pp.get("author",""))}</span>
<cite class="c-ti">{esc(pp.get("title",""))}</cite>
<span class="c-jr">{esc(pp.get("journal",""))}</span>
<span class="c-links">{" ".join(c_links)}</span>
</div>
<p class="lead">{esc(d.get("lead",""))}</p>
{secs}
{takeaways}
{glossary}
<p class="disclaimer">本ページは形成外科の学習・参照を目的とした<b>編集部によるオリジナルの日本語解説</b>で、原著（英語）の逐語訳・全文転載ではありません。正確な内容・数値・図は必ず上記リンク先の原著をご確認ください。<br>掲載している図は、<b>原著の図ではありません</b>。原著の図は出版社が著作権を持ち転載できないため、<b>同じ術式・同じ解剖を扱った無料公開（オープンアクセス／CC BY）論文の図</b>を、出典とライセンスを明記して引用しています。</p>
<a class="backlink" href="../">← 術式の系譜（一覧）に戻る</a>
</main>"""
    return f"""<!doctype html>
<html lang="ja"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="author" content="山形孝介">
<link rel="canonical" href="{base}/papers/{esc(d.get('slug',''))}.html">
<meta name="robots" content="index,follow">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{base}/papers/{esc(d.get('slug',''))}.html">
<meta property="og:image" content="{base}/og.svg">
<meta name="theme-color" content="#EFEBE2">
<style>.sr-only{{position:absolute;left:-9999px}}{CSS}{FIG_CSS}</style>
</head><body>
{body}
</body></html>"""

def build_commentaries(base):
    cdir = ROOT / "data" / "commentaries"
    if not cdir.exists():
        return []
    out = DIST / "papers"
    out.mkdir(parents=True, exist_ok=True)
    slugs = []
    for f in sorted(cdir.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        slug = d.get("slug") or f.stem
        (out / f"{slug}.html").write_text(render_commentary_page(d, base), encoding="utf-8")
        slugs.append(slug)
    return slugs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://example.com")
    ap.add_argument("--google-verify", default="")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    gverify = (f'<meta name="google-site-verification" content="{esc(args.google_verify)}">\n' if args.google_verify else "")
    entries, raw_n = load_entries()
    episode = None
    epf = ROOT / "data" / "podcast_ep1.json"
    mf = ROOT / "data" / "ep1_meta.json"
    if epf.exists():
        episode = json.loads(epf.read_text(encoding="utf-8"))
        if mf.exists():
            episode.update(json.loads(mf.read_text(encoding="utf-8")))
    DIST.mkdir(exist_ok=True)
    body = build_body(entries, episode)
    jsonld = render_jsonld(entries, base)
    _cover_png = ROOT / "docs" / "audio" / "cover.png"
    og_image = f"{base}/audio/cover.png" if (episode and _cover_png.exists()) else f"{base}/og.svg"
    rss_link = (f'<link rel="alternate" type="application/rss+xml" title="ポッドキャスト" href="{base}/feed.xml">\n'
                if episode else "")
    podld = ""
    if episode:
        _mins = round(episode.get("duration_s", 0) / 60)
        _pod = {"@context": "https://schema.org", "@type": "PodcastEpisode",
                "name": episode.get("title", ""), "episodeNumber": 1, "inLanguage": "ja",
                "timeRequired": f"PT{_mins}M", "abstract": episode.get("summary", ""),
                "url": f"{base}/#podcast",
                "associatedMedia": {"@type": "MediaObject", "contentUrl": f"{base}/audio/ep1.mp3",
                                     "encodingFormat": "audio/mpeg"},
                "partOfSeries": {"@type": "PodcastSeries", "name": "からだを、つくり直す ― 形成外科2600年の物語",
                                 "url": f"{base}/", "webFeed": f"{base}/feed.xml"}}
        podld = f'<script type="application/ld+json">{json.dumps(_pod, ensure_ascii=False)}</script>\n'
        (DIST / "feed.xml").write_text(render_rss(episode, base), encoding="utf-8")
    title = "術式の系譜 — 形成外科 原典データベース｜Genealogy of Operations"
    desc = ("スシュルタ（前600年）から現代まで、形成外科の術式・皮弁・植皮・マイクロサージャリーの原著論文と"
            "「世界で初めて行った人」を、一次資料の出典リンク付きで年代順にまとめた検索データベース。"
            f"{len(entries)}項目・年表表示対応。")

    head = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="author" content="山形孝介">
<meta name="keywords" content="形成外科,再建外科,皮弁,植皮,マイクロサージャリー,原著論文,術式,医学史,DIEP,穿通枝皮弁,鼻形成,口唇裂">
<link rel="canonical" href="{base}/">
<meta name="robots" content="index,follow,max-image-preview:large">
{gverify}<meta property="og:type" content="website">
<meta property="og:site_name" content="術式の系譜">
<meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{base}/">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_image}">
<meta name="theme-color" content="#EFEBE2">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%237E2B26'/%3E%3Ctext x='16' y='23' font-size='20' text-anchor='middle' fill='%23EFEBE2' font-family='Georgia,serif'%3E系%3C/text%3E%3C/svg%3E">
<style>.sr-only{{position:absolute;left:-9999px}}{CSS}</style>
<script type="application/ld+json">{jsonld}</script>
{rss_link}{podld}</head>
<body>
{body}
</body>
</html>"""
    (DIST / "index.html").write_text(head, encoding="utf-8")

    # Artifact preview (body-only, no doctype/head/body)
    artifact = f"""<title>{esc(title)}</title>
<style>.sr-only{{position:absolute;left:-9999px}}{CSS}</style>
{body}"""
    (DIST / "artifact.html").write_text(artifact, encoding="utf-8")

    # sitemap / robots
    today = datetime.date.today().isoformat()
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{base}/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>1.0</priority></url>\n'
        f'</urlset>\n', encoding="utf-8")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")

    # simple OG image (SVG)
    og = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#EFEBE2"/>
<rect x="0" y="0" width="1200" height="10" fill="#7E2B26"/>
<text x="80" y="150" font-family="Georgia,'Hoefler Text',serif" font-size="34" fill="#7E2B26" letter-spacing="6">形成外科 原典データベース</text>
<text x="80" y="300" font-family="Georgia,'Hoefler Text',serif" font-size="120" font-weight="600" fill="#22201C">術式の系譜</text>
<text x="80" y="380" font-family="Georgia,serif" font-size="30" fill="#6E655A" letter-spacing="8">GENEALOGY OF RECONSTRUCTIVE OPERATIONS</text>
<text x="80" y="500" font-family="Georgia,serif" font-size="34" fill="#22201C">前600年 スシュルタ 〜 現代 ｜ {len(entries)} の原著・里程標を出典付きで</text>
<text x="80" y="560" font-family="ui-monospace,monospace" font-size="24" fill="#8C8377">植皮 ・ 皮弁 ・ 穿通枝 ・ マイクロサージャリー ・ 頭蓋顔面</text>
</svg>"""
    (DIST / "og.svg").write_text(og, encoding="utf-8")

    commentary_slugs = build_commentaries(base)

    print(f"built {len(entries)} entries (raw {raw_n}, collapsed {raw_n-len(entries)})")
    print(f"commentary pages: {len(commentary_slugs)} -> {commentary_slugs}")
    print("dist:", *(p.name for p in sorted(DIST.iterdir())))
    print("index.html bytes:", (DIST/'index.html').stat().st_size)

if __name__ == "__main__":
    main()
