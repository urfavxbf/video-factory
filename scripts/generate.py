from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
import urllib.parse
from datetime import date
from pathlib import Path

from gtts import gTTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

FACTS = [
    {
        "title": "BAKIT ASUL ANG LANGIT?",
        "text": "Bakit asul ang langit kahit halos puti ang sikat ng araw? May halo itong iba't ibang kulay. Kapag dumaan ang liwanag sa atmospera, mas madaling ikalat ng maliliit na molekula ng hangin ang asul na liwanag kaysa pula. Kaya umaabot sa mata natin ang asul na liwanag mula sa maraming direksiyon. Sa paglubog ng araw, mas mahaba ang dinaanan ng sikat ng araw sa atmospera. Mas maraming asul ang naikalat palayo, kaya mas nangingibabaw ang pula at kahel. Ibig sabihin, ang kulay ng langit ay resulta ng pakikipag-ugnayan ng sikat ng araw at hangin."
    },
    {
        "title": "TUNOG SA KALAWAKAN",
        "text": "Sa pelikula, maingay ang mga pagsabog sa kalawakan. Pero sa totoong buhay, kailangan ng tunog ng materyal gaya ng hangin, tubig, o solidong bagay para maipasa ang vibration. Halos vacuum ang kalawakan, kaya hindi makakabiyahe roon ang ordinaryong sound waves tulad sa Earth. Hindi ibig sabihin na walang galaw o alon doon: kayang sukatin ng mga instrumento ang ilang signal at vibration. Pero hindi iyon basta naririnig ng tainga ng tao. Kaya kung may pagsabog sa malayong bahagi ng kalawakan, hindi ito maririnig ng astronaut sa pamamagitan lamang ng hangin."
    },
    {
        "title": "MAY TUBIG SA BUWAN",
        "text": "Hindi ganap na tuyot ang Buwan. May ebidensiya ng tubig na yelo sa ilang permanenteng anino malapit sa mga polo nito. Dahil halos hindi naaabot ng sikat ng araw ang mga lugar na iyon, napakalamig nila at maaaring mapanatili ang yelo sa mahabang panahon. May natukoy ding mga molekula ng tubig o hydroxyl sa ibang bahagi ng ibabaw. Pero huwag isipin na may mga ilog o lawa roon. Mahalaga ang yelong ito sa pag-aaral ng kasaysayan ng Buwan at sa pagpaplano ng mga susunod na misyon. Kung mapag-aaralan at makokolekta nang ligtas, maaari itong maging mapagkukunan ng tubig para sa mga astronaut."
    },
    {
        "title": "MAS MABAGAL ANG ORAS",
        "text": "Totoo bang hindi pare-pareho ang takbo ng oras? Ayon sa relativity ni Einstein, naaapektuhan ang pagsukat ng oras ng gravity at bilis. Mas mabagal nang kaunti ang oras sa lugar na mas malakas ang gravity. Nagkakaroon din ng pagkakaiba kapag gumagalaw nang napakabilis ang isang bagay. Napakaliit ng epektong ito sa pang-araw-araw na buhay, kaya hindi natin ito napapansin. Pero mahalaga ito sa GPS. Dahil mabilis gumalaw ang mga satellite at nasa ibang antas ng gravity kaysa sa atin, kailangang itama ang kanilang mga orasan. Kung hindi, unti-unting magkakamali ang mga lokasyong ipinapakita ng ating mga telepono."
    },
    {
        "title": "ANG PUSO NG OCTOPUS",
        "text": "May tatlong puso ang octopus. Dalawa ang nagbobomba ng dugo papunta sa hasang para kumuha ng oxygen mula sa tubig. Ang ikatlo naman ang nagdadala ng dugo sa buong katawan. Asul ang dugo nito dahil gumagamit ito ng hemocyanin, isang protinang may tanso na nagdadala ng oxygen. Sa tao, iron-based hemoglobin ang ginagamit natin kaya pula ang dugo. May isa pang kakaiba: bumabagal o pansamantalang humihinto ang pangunahing puso ng octopus habang lumalangoy ito. Posibleng isa ito sa mga dahilan kung bakit mas madalas itong gumapang kaysa lumangoy nang matagal. Kahit kakaiba, ang sistemang ito ay angkop sa pamumuhay nito sa dagat."
    },
    {
        "title": "HINDI BITUIN ANG VENUS",
        "text": "Tinatawag minsan na tala sa umaga o gabi ang Venus, pero planeta ito, hindi bituin. Hindi ito gumagawa ng sariling liwanag; nakikita natin ito dahil sinasalamin ng makakapal nitong ulap ang sikat ng araw. Napakaliwanag nito kaya isa ito sa pinakamatingkad na bagay sa kalangitan pagkatapos ng Araw at Buwan. Karaniwan itong nakikita malapit sa pagsikat o paglubog ng araw dahil nasa loob ng orbit ng Earth ang orbit nito. Kahit halos magkapareho ang laki ng Venus at Earth, napakainit ng ibabaw ng Venus dahil sa matinding greenhouse effect, at napakataas din ng presyon. Kaya hindi ito ligtas na tirahan tulad ng ating planeta."
    },
    {
        "title": "BAKIT LUMULUTANG ANG YELO?",
        "text": "Bakit lumulutang ang yelo sa tubig? Mas mababa ang density nito kaysa likidong tubig. Kapag nagyeyelo ang tubig, nag-aayos ang mga molekula nito sa isang mala-kristal na istrukturang mas maluwag. Dahil dito, mas malaki ang espasyong nasasakop ng yelo kaysa sa parehong dami ng likidong tubig. Mahalaga ito sa mga lawa: kapag nagyelo ang ibabaw, nananatiling likido ang tubig sa ilalim at may matitirhan pa ang mga isda at iba pang organismo. Nagsisilbi ring panangga ang yelo laban sa sobrang pagkawala ng init. Kaya ang yelong lumulutang sa baso ay nagpapakita ng katangiang may malaking epekto sa buhay sa malamig na kapaligiran."
    },
    {
        "title": "MAY AMOY ANG KALAWAKAN?",
        "text": "May amoy ba ang kalawakan? Hindi natin direktang maaamoy ang vacuum dahil kailangan ng ilong ng mga molekulang makikilala nito. Pero may mga astronaut na nagsabing may kakaibang amoy ang kanilang spacesuit at kagamitan pagkatapos ng spacewalk—parang metal, usok, o nasunog na materyal. Hindi ibig sabihin na may hangin sa kalawakan na may ganoong amoy. Maaaring galing ito sa mga residue o kemikal na naiwan sa kagamitan matapos malantad sa kapaligiran ng kalawakan. Dahil mapanganib ang vacuum, umaasa ang mga astronaut sa spacesuit at life-support system. Kaya mas tumpak sabihing may amoy ang ilang residue, hindi ang vacuum mismo."
    },
    {
        "title": "ANG HIGANTENG JUPITER",
        "text": "Ang Jupiter ang pinakamalaking planeta sa Solar System. Napakalaki nito na mahigit isang libong Earth ang kasya rito ayon sa volume. Isa itong gas giant na pangunahing binubuo ng hydrogen at helium, kaya wala itong matigas na ibabaw na puwedeng tayuan. Kilala ito sa makapal na ulap at malalakas na bagyo, kabilang ang Great Red Spot na namataan sa loob ng maraming siglo. Napakalakas din ng magnetic field nito at marami itong buwan. Ang Europa, isa sa mga buwan nito, ay pinag-aaralan dahil maaaring may karagatan sa ilalim ng nagyeyelong ibabaw. Kahit napakalaki ng Jupiter, mabilis itong umiikot: ang isang araw doon ay humigit-kumulang sampung oras lamang."
    },
    {
        "title": "HALOS WALANG TUNOG ANG BUWAN",
        "text": "Halos walang atmospera ang Buwan, kaya hindi kumakalat doon ang ordinaryong tunog tulad sa Earth. Kailangan ng tunog ng materyal gaya ng hangin, tubig, o solidong bagay para maipasa ang vibration. Kaya hindi maririnig ng dalawang astronaut na magkalayo ang boses ng isa't isa sa pamamagitan lamang ng hangin. Gumagamit sila ng radyo sa helmet at spacesuit para makapagsalita at makarinig. Maaari pa ring dumaan ang vibration sa solidong materyal kapag direktang magkadikit ang mga bagay, pero iba iyon sa tunog na naglalakbay sa hangin. Kaya tahimik ang ibabaw ng Buwan sa tainga ng tao kahit gumagalaw ang mga rover at kagamitan."
    },
]


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def make_caption_chunks(text: str, max_words: int = 6) -> list[str]:
    """Shorter caption chunks are easier to read on a phone."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        sentence_chunks = [
            " ".join(words[start:start + max_words])
            for start in range(0, len(words), max_words)
        ]
        # Avoid a tiny final fragment such as "sa atin" on its own.
        if len(sentence_chunks) > 1 and len(sentence_chunks[-1].split()) <= 2:
            sentence_chunks[-2] += " " + sentence_chunks.pop()
        chunks.extend(sentence_chunks)
    return chunks


def write_srt(text: str, duration: float, path: Path) -> None:
    chunks = make_caption_chunks(text)
    weights = [max(1, len(chunk.split())) for chunk in chunks]
    total_weight = sum(weights)
    usable_duration = max(1.0, duration - 0.15)
    cursor = 0.0
    rows = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        end = usable_duration if index == len(chunks) else cursor + usable_duration * weight / total_weight
        rows.extend([
            str(index),
            f"{srt_timestamp(cursor)} --> {srt_timestamp(end)}",
            chunk,
            "",
        ])
        cursor = end
    path.write_text("\n".join(rows), encoding="utf-8")


PIXABAY_QUERIES = {
    "BAKIT ASUL ANG LANGIT?": "blue sky clouds",
    "TUNOG SA KALAWAKAN": "astronaut space earth",
    "MAY TUBIG SA BUWAN": "moon lunar surface",
    "MAS MABAGAL ANG ORAS": "satellite earth orbit",
    "ANG PUSO NG OCTOPUS": "octopus underwater",
    "HINDI BITUIN ANG VENUS": "planet venus space",
    "BAKIT LUMULUTANG ANG YELO?": "ice water",
    "MAY AMOY ANG KALAWAKAN?": "astronaut spacewalk",
    "ANG HIGANTENG JUPITER": "Jupiter planet space",
    "HALOS WALANG TUNOG ANG BUWAN": "astronaut moon",
}


def fetch_pixabay_video(title: str) -> Path | None:
    """Fetch one relevant Pixabay stock clip; fail safely to existing visual fallbacks."""
    api_key = os.getenv("PIXABAY_API_KEY", "").strip()
    query = PIXABAY_QUERIES.get(title)
    if not api_key or not query:
        print("Pixabay is not configured; using the animated background fallback.")
        return None

    video_path = OUT / "pixabay" / "stock-background.mp4"
    try:
        params = urllib.parse.urlencode({
            "key": api_key, "q": query, "video_type": "film",
            "safesearch": "true", "per_page": 8, "order": "popular",
        })
        request = urllib.request.Request(
            f"https://pixabay.com/api/videos/?{params}",
            headers={"User-Agent": "video-factory/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        hits = payload.get("hits", [])
        chosen = None
        for hit in hits:
            variants = hit.get("videos", {})
            candidate = variants.get("medium") or variants.get("small") or variants.get("large")
            if candidate and candidate.get("url"):
                chosen = candidate
                break
        if not chosen:
            print(f"Pixabay returned no usable video for '{query}'.")
            return None

        video_path.parent.mkdir(exist_ok=True)
        download_request = urllib.request.Request(
            chosen["url"], headers={"User-Agent": "video-factory/1.0"}
        )
        total = 0
        max_bytes = 80 * 1024 * 1024
        with urllib.request.urlopen(download_request, timeout=30) as response:
            with video_path.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise RuntimeError("Pixabay clip exceeded the 80 MB safety limit.")
                    output.write(chunk)
        if total == 0:
            raise RuntimeError("Pixabay returned an empty video file.")
        print(f"Downloaded Pixabay stock video ({total // (1024 * 1024)} MB).")
        return video_path
    except Exception as exc:
        print(f"Pixabay video unavailable ({type(exc).__name__}: {exc}).")
        print("Falling back to the animated background.")
        video_path.unlink(missing_ok=True)
        return None


def render_pixabay_video(source_path: Path, duration: float, video_path: Path,
                         audio_path: Path, srt_path: Path, title: str) -> None:
    """Crop/loop stock footage vertically; narration and captions remain unchanged."""
    video_filter = (
        "drawtext=text='ALAM MO BA?':fontcolor=0x7DD3FC:fontsize=22:font='DejaVu Sans':"
        "borderw=2:bordercolor=black@0.75:x=(w-text_w)/2:y=58:enable='between(t,0,2.8)',"
        f"drawtext=text='{title}':fontcolor=white:fontsize=27:font='DejaVu Sans':"
        "borderw=3:bordercolor=black@0.85:x=(w-text_w)/2:y=96,"
        f"subtitles='{srt_path.as_posix()}':force_style="
        "'FontName=DejaVu Sans,FontSize=13,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,BorderStyle=1,BackColour=&H00000000,"
        "Outline=1,Shadow=0,Alignment=2,MarginL=90,MarginR=90,MarginV=105'"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(source_path),
        "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0",
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,"
               "crop=720:1280,fps=30,setsar=1," + video_filter,
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", str(video_path),
    ])


def main() -> None:
    # The workflow sets TZ=Asia/Manila; daily rotation is stable for reruns.
    fact = FACTS[date.today().toordinal() % len(FACTS)]
    narration = fact["text"]

    audio_path = OUT / "narration.mp3"
    srt_path = OUT / "captions.srt"
    video_path = OUT / f"factstory-{date.today().isoformat()}.mp4"
    metadata_path = OUT / "metadata.json"

    print(f"Selected fact: {fact['title']}")
    print("Generating Filipino narration...")
    raw_audio_path = OUT / "narration-raw.mp3"
    gTTS(text=narration, lang="tl", slow=False).save(str(raw_audio_path))

    # Slightly lower pitch and add body, compression, and consistent loudness.
    sample_rate = int(run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate",
        "-of", "default=noprint_wrappers=1:nokey=1", str(raw_audio_path),
    ]))
    pitch_rate = max(8000, int(sample_rate * 0.90))
    audio_filter = (
        f"asetrate={pitch_rate},aresample={sample_rate},atempo={sample_rate / pitch_rate},"
        "highpass=f=75,equalizer=f=150:t=q:w=1:g=2.5,"
        "equalizer=f=2800:t=q:w=1:g=1.2,"
        "acompressor=threshold=0.125:ratio=3:attack=20:release=200,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    run(["ffmpeg", "-y", "-i", str(raw_audio_path), "-af", audio_filter,
         "-codec:a", "libmp3lame", "-b:a", "128k", str(audio_path)])
    raw_audio_path.unlink(missing_ok=True)

    duration_text = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ])
    duration = float(duration_text)
    write_srt(narration, duration, srt_path)

    # Use moving Pixabay footage when available; never use still images as backgrounds.
    pixabay_video = fetch_pixabay_video(fact["title"])
    if pixabay_video:
        print("Rendering Pixabay stock video with expanded narration and captions...")
        render_pixabay_video(pixabay_video, duration, video_path, audio_path, srt_path, fact["title"])
        visual_style = "Pixabay stock footage cropped to vertical 9:16"
    else:
        # Free fallback: animated color shapes, not a still-image background.
        subtitle_filter = (
            "drawbox=x='mod(t*42\\,900)-180':y=150:w=260:h=430:color=0x2563EB@0.42:t=fill,"
            "drawbox=x=720-mod(t*27\\,1000):y=620:w=220:h=500:color=0x7C3AED@0.38:t=fill,"
            "drawbox=x='mod(t*18\\,1000)-250':y=980:w=320:h=180:color=0x06B6D4@0.32:t=fill,"
            "drawtext=text='ALAM MO BA?':fontcolor=0x7DD3FC:fontsize=22:font='DejaVu Sans':"
            "borderw=2:bordercolor=black@0.75:x=(w-text_w)/2:y=58:enable='between(t,0,2.8)',"
            f"drawtext=text='{fact['title']}':fontcolor=white:fontsize=27:font='DejaVu Sans':"
            "borderw=3:bordercolor=black@0.85:x=(w-text_w)/2:y=96,"
            f"subtitles='{srt_path.as_posix()}':force_style="
            "'FontName=DejaVu Sans,FontSize=13,Bold=1,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00101010,BorderStyle=1,BackColour=&H00000000,"
            "Outline=1,Shadow=0,Alignment=2,MarginL=90,MarginR=90,MarginV=105'"
        )
        print("Rendering animated-background fallback MP4...")
        run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x101B35:s=720x1280:r=30",
            "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", subtitle_filter,
            "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", str(video_path),
        ])
        visual_style = "animated geometric background (no stock clip available)"

    metadata_path.write_text(json.dumps({
        "date": date.today().isoformat(),
        "title": fact["title"],
        "narration": narration,
        "duration_seconds": round(duration, 2),
        "video_file": video_path.name,
        "visual_style": visual_style,
        "caption_style": "bold high-contrast mobile subtitles",
        "target_duration_seconds": 45,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"SUCCESS: {video_path}")
    print(f"Duration: {duration:.1f} seconds (target: about 45 seconds)")


if __name__ == "__main__":
    main()
