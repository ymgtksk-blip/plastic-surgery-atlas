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
    return re.sub(r"\s+", " ", " ".join(parts)).lower()

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
    return (
        f'<article class="card conf-{esc(conf)}" data-cat="{esc(key)}" data-first="{1 if first else 0}" '
        f'data-year="{ys}" data-search="{esc(blob)}" id="e{idx}">'
        f'<header class="card-h"><time class="yr"{dt_attr}>{esc(e.get("year_display",""))}</time>'
        f'<span class="chip" style="--c:{color}">{esc(label)}</span>{first_html}</header>'
        f'<h2 class="nm">{esc(e.get("name_ja",""))}</h2>'
        f'<p class="og">{esc(e.get("name_original",""))}</p>'
        f'<p class="au">{esc(e.get("author",""))}</p>'
        f'<p class="pp"><cite>{esc(e.get("paper_title",""))}</cite></p>'
        f'<p class="jr">{esc(e.get("journal",""))}</p>'
        f'<p class="sig">{esc(e.get("significance_ja",""))}</p>'
        f'{conf_html}{note_html}'
        f'<a class="src" href="{esc(e.get("url",""))}" target="_blank" rel="noopener noreferrer">原著・出典を見る<span aria-hidden="true"> ↗</span></a>'
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
                f'<span class="dot" style="--c:{color}"></span>{esc(label)} <span class="n">{counts[k]}</span></button>'
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

def build_body(entries):
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
    search_svg = ('<svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round">'
                  '<circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>')
    body = f"""<header class="mast"><div class="wrap mast-in">
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://example.com")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    entries, raw_n = load_entries()
    DIST.mkdir(exist_ok=True)
    body = build_body(entries)
    jsonld = render_jsonld(entries, base)
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
<meta property="og:type" content="website">
<meta property="og:site_name" content="術式の系譜">
<meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{base}/">
<meta property="og:image" content="{base}/og.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{base}/og.svg">
<meta name="theme-color" content="#EFEBE2">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%237E2B26'/%3E%3Ctext x='16' y='23' font-size='20' text-anchor='middle' fill='%23EFEBE2' font-family='Georgia,serif'%3E系%3C/text%3E%3C/svg%3E">
<style>.sr-only{{position:absolute;left:-9999px}}{CSS}</style>
<script type="application/ld+json">{jsonld}</script>
</head>
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

    print(f"built {len(entries)} entries (raw {raw_n}, collapsed {raw_n-len(entries)})")
    print("dist:", *(p.name for p in sorted(DIST.iterdir())))
    print("index.html bytes:", (DIST/'index.html').stat().st_size)

if __name__ == "__main__":
    main()
