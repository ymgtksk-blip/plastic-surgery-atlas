#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/commentaries/<slug>.json を、entries.json の該当項目に papers[].commentary として配線する。
解説ページを作っただけでは一覧から辿れない（孤立ページになる）ため、必ずこれを通す。"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).parent
# slug -> その解説を出す entries.json の name_ja（複数項目から同じ論文を参照することがある）
LINKS = {
    "song-1984":          ["前外側大腿皮弁（ALT皮弁）"],
    "yang-1981":          ["橈側前腕皮弁（中国皮弁／チャイニーズフラップ）"],
    "koshima-soeda-1989": ["DIEP皮弁（深下腹壁動脈穿通枝皮弁）の原型", "穿通枝皮弁の概念 ― DIEP皮弁の原型"],
    "mcgregor-jackson-1972": ["鼠径皮弁（グロインフラップ／McGregor皮弁）", "鼠径皮弁 ― 軸走型皮弁の確立"],
    "olivari-1976":       ["広背筋皮弁（ラチシマス皮弁）"],
    "bakamjian-1965":     ["デルトペクトラル皮弁（三角胸筋皮弁）"],
    "orticochea-1972":    ["薄筋皮弁（グラシリス皮弁）"],
    "taylor-1975":        ["遊離血管柄付き腓骨（腓骨皮弁）"],
    "ariyan-1979":        ["大胸筋皮弁（ペクトラリス皮弁）"],
    "hartrampf-1982":     ["TRAM皮弁（横軸腹直筋皮弁）"],
}

def main():
    ep = ROOT / "data" / "entries.json"
    items = json.loads(ep.read_text(encoding="utf-8"))
    by_name = {e["name_ja"]: e for e in items}
    changed = []
    for slug, names in LINKS.items():
        cf = ROOT / "data" / "commentaries" / f"{slug}.json"
        if not cf.exists():
            print(f"skip (解説未作成): {slug}")
            continue
        c = json.loads(cf.read_text(encoding="utf-8"))
        pp = c.get("paper", {})
        for nm in names:
            e = by_name.get(nm)
            if e is None:
                print(f"!! entries.json に見つからない: {nm}")
                continue
            papers = e.get("papers") or []
            # 既に同じ解説が配線済みならスキップ
            if any(p.get("commentary") == f"papers/{slug}.html" for p in papers):
                continue
            hit = next((p for p in papers if p.get("url") == pp.get("url")), None)
            if hit:
                hit["commentary"] = f"papers/{slug}.html"
            else:
                papers.append({
                    "kind": "原著",
                    "year": str(e.get("year_display", "")),
                    "author": pp.get("author", e.get("author", "")),
                    "title": pp.get("title", e.get("paper_title", "")),
                    "journal": pp.get("journal", e.get("journal", "")),
                    "url": pp.get("url", e.get("url", "")),
                    "link_label": "原著・抄録",
                    "commentary": f"papers/{slug}.html",
                })
                e["papers"] = papers
            changed.append(f"{nm} → papers/{slug}.html")
    ep.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in changed:
        print("配線:", c)
    print(f"計 {len(changed)} 件")

if __name__ == "__main__":
    main()
