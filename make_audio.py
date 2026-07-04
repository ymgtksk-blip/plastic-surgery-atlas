#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台本(data/podcast_ep1.json) → 音源(docs/audio/ep1.mp3)。
macOS `say`（ナビ=Flo / 先生=Eddy）でターン毎に合成→ffmpegで無音を挟んで結合→mp3。
読みの二重化（漢字（かな））や（笑）はTTS前に整形。LLM不使用＝枠ゼロ。"""
import json, re, subprocess, pathlib

ROOT = pathlib.Path(__file__).parent
VOICE = {"ナビ": "Flo", "先生": "Eddy"}
# 誤読しやすい専門用語は読みを強制（グローバル置換）
FORCE = {"穿通枝": "せんつうし", "皮弁": "ひべん", "植皮": "しょくひ",
         "遊離": "ゆうり", "管状": "かんじょう", "茎": "くき"}

def clean(t):
    for k, v in FORCE.items():
        t = t.replace(k, v)
    # 漢字（かな） → かな（ふりがなの二重読みを解消・人名の読みを優先）
    t = re.sub(r'[一-龥々〆ヶ]+（([ぁ-んァ-ヶー]+)）', r'\1', t)
    # 残った全角括弧（（笑）等）を除去
    t = re.sub(r'（[^）]*）', '', t)
    return t.strip()

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    ep = json.loads((ROOT / "data" / "podcast_ep1.json").read_text(encoding="utf-8"))
    turns = ep["turns"]
    work = ROOT / "dist" / "_audio_seg"
    work.mkdir(parents=True, exist_ok=True)
    sil = work / "sil.wav"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", "0.35", "-c:a", "pcm_s16le", str(sil)])
    segs = []
    for i, t in enumerate(turns):
        txt = clean(t["text"])
        if not txt:
            continue
        v = VOICE.get(t["speaker"], "Kyoko")
        tf = work / f"t{i}.txt"; tf.write_text(txt, encoding="utf-8")
        aiff = work / f"s{i}.aiff"; wav = work / f"s{i}.wav"
        run(["say", "-v", v, "-f", str(tf), "-o", str(aiff)])
        run(["ffmpeg", "-y", "-i", str(aiff), "-ar", "24000", "-ac", "1",
             "-c:a", "pcm_s16le", str(wav)])
        segs.append(wav)
    listf = work / "list.txt"
    with open(listf, "w") as f:
        for j, w in enumerate(segs):
            f.write(f"file '{w.name}'\n")
            if j != len(segs) - 1:
                f.write("file 'sil.wav'\n")
    out = ROOT / "docs" / "audio"; out.mkdir(parents=True, exist_ok=True)
    mp3 = out / "ep1.mp3"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
         "-c:a", "libmp3lame", "-q:a", "4",
         "-metadata", f"title={ep['title']}",
         "-metadata", "artist=術式の系譜",
         "-metadata", "album=からだを、つくり直す ― 形成外科2600年の物語",
         str(mp3)])
    dur = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", str(mp3)]).decode().strip()
    meta = {"duration_s": float(dur), "bytes": mp3.stat().st_size, "segments": len(segs)}
    (ROOT / "data" / "ep1_meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    print(f"EP1 mp3: {mp3}  {meta['bytes']//1024}KB  {int(float(dur))}s ({float(dur)/60:.1f}min)  segs={len(segs)}")

if __name__ == "__main__":
    main()
