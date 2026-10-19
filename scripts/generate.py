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
        "text": "Alam mo ba kung bakit asul ang langit? Ang liwanag ng araw ay may iba't ibang kulay, kahit mukhang puti ito sa ating mga mata. Kapag pumapasok ang sikat ng araw sa atmospera, nakikipag-ugnayan ito sa maliliit na molekula ng hangin. Mas madaling ikalat ng mga molekulang ito ang asul na liwanag kaysa sa pulang liwanag. Dahil dito, nagmumula sa maraming direksiyon ang asul na liwanag na umaabot sa ating mga mata. Sa paglubog ng araw, mas mahaba ang dinaanan ng liwanag sa atmospera, kaya mas maraming asul ang naikalat palayo at mas kapansin-pansin ang pula at kahel. Kaya ang kulay ng langit ay may kinalaman sa liwanag at sa hangin sa paligid ng Earth."
    },
    {
        "title": "TUNOG SA KALAWAKAN",
        "text": "May pagsabog ba na maririnig sa kalawakan? Sa mga pelikula, madalas may malalakas na tunog ang pagsabog at paglipad ng mga spaceship. Pero sa totoong buhay, ang ordinaryong tunog ay nangangailangan ng medium gaya ng hangin, tubig, o solidong materyal para maipasa ang vibration. Halos vacuum ang kalawakan, kaya hindi makapaglalakbay doon ang sound waves tulad ng paglalakbay nila sa hangin sa Earth. Hindi ibig sabihin nito na walang anumang vibration sa kalawakan; may mga alon at signal na kayang sukatin ng mga instrumento, pero hindi iyon basta naririnig ng tainga ng tao. Kaya kung may pagsabog sa malayong bahagi ng vacuum, hindi ito maririnig ng astronaut sa pamamagitan lamang ng hangin."
    },
    {
        "title": "MAY TUBIG SA BUWAN",
        "text": "Hindi pala ganap na tuyot ang Buwan. Nakakita ang mga siyentipiko ng ebidensiya ng tubig na yelo sa ilang napakalamig at permanenteng anino malapit sa mga polo nito. Dahil hindi direktang naaabot ng sikat ng araw ang mga lugar na ito, nananatiling napakababa ng temperatura at maaaring mapreserba ang yelo sa mahabang panahon. May ebidensiya rin ng mga molekula ng tubig o hydroxyl sa iba pang bahagi ng ibabaw, pero hindi ibig sabihin na may mga ilog o lawa roon. Mahalaga ang pagtuklas na ito sa pag-unawa sa kasaysayan ng Buwan at sa pagpaplano ng mga susunod na misyon. Kung mapag-aaralan at magagamit nang ligtas, maaaring makatulong ang lunar ice bilang pinagkukunan ng tubig para sa mga astronaut."
    },
    {
        "title": "MAS MABAGAL ANG ORAS",
        "text": "Ayon sa teorya ng relativity ni Einstein, hindi pare-pareho ang takbo ng oras sa lahat ng sitwasyon. Ang gravity at bilis ay parehong maaaring makaapekto sa pagsukat ng oras. Kapag mas malakas ang gravity, bahagyang mas mabagal ang oras kumpara sa lugar na mas mahina ang gravity. Samantala, ang bagay na gumagalaw nang napakabilis ay maaari ring magkaroon ng ibang pagsukat ng oras kumpara sa isang nakapirming tagamasid. Napakaliit ng epektong ito sa pang-araw-araw na buhay kaya hindi natin ito napapansin. Pero mahalaga ito sa mga satellite navigation system gaya ng GPS. Dahil nasa orbit ang mga satellite at mabilis ang kanilang galaw, kailangang itama ang kanilang mga orasan upang manatiling tumpak ang mga lokasyong ibinibigay sa ating mga telepono."
    },
    {
        "title": "ANG PUSO NG OCTOPUS",
        "text": "Alam mo ba na may tatlong puso ang octopus? Dalawa sa mga puso nito ang nagbobomba ng dugo papunta sa hasang, kung saan kumukuha ng oxygen ang dugo mula sa tubig. Ang ikatlong puso naman ang nagpapadaloy ng dugo sa iba pang bahagi ng katawan. Kapansin-pansin din na kulay asul ang dugo nito dahil gumagamit ito ng protinang hemocyanin na may tanso upang magdala ng oxygen. Sa tao, hemoglobin na may iron ang ginagamit kaya pula ang dugo natin. May isa pang kakaibang detalye: ang pangunahing pusong nagpapadaloy ng dugo sa katawan ay pansamantalang bumabagal o humihinto sa pagbomba habang lumalangoy ang octopus. Kaya madalas gumapang ito sa halip na lumangoy nang matagal, dahil mas nakakatipid ito ng enerhiya."
    },
    {
        "title": "HINDI BITUIN ANG VENUS",
        "text": "Minsan tinatawag na tala sa umaga o tala sa gabi ang Venus, pero planeta ito at hindi bituin. Hindi ito gumagawa ng sariling liwanag tulad ng Araw; nakikita natin ito dahil nagbabalik ng sikat ng araw ang makapal na ulap sa atmospera nito. Napakaliwanag ng Venus kaya madalas itong isa sa pinakamatingkad na bagay sa kalangitan pagkatapos ng Araw at Buwan. Karaniwan itong nakikita malapit sa pagsikat o paglubog ng araw dahil ang orbit nito ay nasa loob ng orbit ng Earth. Hindi ito laging makikita sa buong gabi. Bagama't magkahawig ang laki ng Venus at Earth, ibang-iba ang kondisyon sa ibabaw nito: napakainit dahil sa matinding greenhouse effect at napakataas ng presyon. Kaya hindi ito katulad ng Earth kahit tinatawag minsan na planetang kapatid nito."
    },
    {
        "title": "BAKIT LUMULUTANG ANG YELO?",
        "text": "Kadalasan, lumulutang ang yelo sa tubig dahil mas mababa ang density nito kaysa likidong tubig. Kapag lumalamig at nagyeyelo ang tubig, nag-aayos ang mga molekula nito sa isang mala-kristal na istrukturang mas maluwag kaysa sa pagkakaayos nila sa likidong anyo. Dahil dito, mas malaki ang espasyong nasasakop ng parehong dami ng tubig kapag naging yelo ito. Kakaiba ito dahil maraming ibang materyal ang mas siksik sa solidong anyo. Mahalaga rin ang katangiang ito sa kalikasan. Kapag nagyeyelo ang ibabaw ng lawa, nananatili sa ilalim ang likidong tubig, kaya may lugar pa ring matitirhan ang mga isda at iba pang organismo. Nagsisilbi ring panangga ang yelo laban sa sobrang pagkawala ng init. Kaya ang simpleng yelong lumulutang sa baso ay may malaking papel sa buhay sa malamig na kapaligiran."
    },
    {
        "title": "MAY AMOY ANG KALAWAKAN?",
        "text": "Hindi natin direktang maaamoy ang vacuum ng kalawakan dahil kailangan ng ilong natin ng mga molekulang makararating dito upang makilala ang isang amoy. Sa kabila nito, may mga astronaut na naglarawan ng kakaibang amoy sa kanilang spacesuit at kagamitan pagkatapos ng spacewalk. Inihalintulad nila ito sa metal, usok, o nasunog na materyal. Hindi ibig sabihin na may hangin sa kalawakan na may ganoong amoy. Maaaring nagmula ang amoy sa mga residue o kemikal na naiwan sa suit at kagamitan matapos malantad sa kapaligiran ng kalawakan. Dahil mapanganib ang direktang paglanghap sa vacuum, umaasa ang mga astronaut sa spacesuit at life-support system. Kaya mas tamang sabihin na may amoy ang ilang residue pagkatapos ng spacewalk, hindi na naaamoy natin ang vacuum mismo."
    },
    {
        "title": "ANG HIGANTENG JUPITER",
        "text": "Ang Jupiter ang pinakamalaking planeta sa ating Solar System. Napakalaki nito na mahigit isang libong Earth ang maaaring magkasya sa loob nito ayon sa volume. Isa itong gas giant na pangunahing binubuo ng hydrogen at helium, kaya wala itong matigas na ibabaw na katulad ng sa Earth na puwedeng tayuan. May makapal itong ulap at malalakas na bagyo, kabilang ang Great Red Spot, isang napakalaking sistema ng bagyong namataan sa loob ng maraming siglo. Napakalakas din ng magnetic field nito at mayroon itong maraming buwan. Ang ilan sa mga buwan nito, gaya ng Europa, ay pinag-aaralan dahil maaaring may karagatan sa ilalim ng kanilang nagyeyelong ibabaw. Kahit napakalaki ng Jupiter, mabilis itong umiikot sa axis nito at natatapos ang isang araw sa loob ng humigit-kumulang sampung oras."
    },
    {
        "title": "HALOS WALANG TUNOG ANG BUWAN",
        "text": "Walang hangin sa ibabaw ng Buwan na sapat para magdala ng ordinaryong tunog tulad ng sa Earth. Ang tunog ay vibration na kailangang dumaan sa materyal gaya ng hangin, tubig, o solidong bagay. Dahil halos walang atmospera ang Buwan, hindi maririnig ng dalawang astronaut na magkalayo ang boses ng isa't isa sa pamamagitan lamang ng hangin. Kaya gumagamit sila ng radyo sa loob ng kanilang helmet at spacesuit upang makapagsalita at makarinig. Hindi ibig sabihin na walang vibration sa Buwan: kung may direktang kontak sa solidong materyal, maaaring dumaan ang vibration sa materyal na iyon. Pero hindi ito katulad ng tunog na naglalakbay sa hangin sa Earth. Isa ito sa mga dahilan kung bakit tahimik ang mga eksenang kinukunan sa ibabaw ng Buwan, kahit may gumagalaw na rover o kagamitan."
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


def make_caption_chunks(text: str, max_words: int = 4) -> list[str]:
    """Shorter caption chunks are easier to read on a phone."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        for start in range(0, len(words), max_words):
            chunks.append(" ".join(words[start:start + max_words]))
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
    gTTS(text=narration, lang="tl", slow=False).save(str(audio_path))

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
            "drawbox=x='mod(t*42\\,900)-180':y=0:w=220:h=1280:color=0x2563EB@0.16:t=fill,"
            "drawbox=x=720-mod(t*27\\,1000):y=0:w=160:h=1280:color=0x7C3AED@0.12:t=fill,"
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
