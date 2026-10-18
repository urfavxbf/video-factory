from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from gtts import gTTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

FACTS = [
    {
        "title": "BAKIT ASUL ANG LANGIT?",
        "text": "Alam mo ba kung bakit asul ang langit? Ang liwanag ng araw ay may iba't ibang kulay. Mas madaling ikalat ng hangin ang asul na liwanag kaysa sa pulang liwanag. Kaya sa araw, mas marami tayong nakikitang asul mula sa kalangitan."
    },
    {
        "title": "TUNOG SA KALAWAKAN",
        "text": "May pagsabog ba na maririnig sa kalawakan? Ang ordinaryong tunog ay nangangailangan ng medium gaya ng hangin. Halos vacuum ang kalawakan, kaya hindi karaniwang makararating doon ang sound waves tulad ng paglalakbay nila sa hangin."
    },
    {
        "title": "MAY TUBIG SA BUWAN",
        "text": "Hindi pala ganap na tuyot ang Buwan. Nakakita ang mga siyentipiko ng ebidensiya ng tubig na yelo sa ilang malamig at permanenteng anino malapit sa mga polo nito. Mahalaga ito sa pag-aaral ng kasaysayan ng Buwan at mga susunod na misyon."
    },
    {
        "title": "MAS MABAGAL ANG ORAS",
        "text": "Ayon sa relativity, hindi pare-pareho ang takbo ng oras sa lahat ng sitwasyon. Ang gravity at bilis ay maaaring makaapekto sa pagsukat ng oras. Maliit ang epekto sa pang-araw-araw na buhay, pero kailangang isaalang-alang ito ng mga satellite navigation system."
    },
    {
        "title": "ANG PUSO NG OCTOPUS",
        "text": "Alam mo ba na may tatlong puso ang octopus? Dalawa ang nagbobomba ng dugo papunta sa hasang, at isa ang nagbobomba nito sa ibang bahagi ng katawan. Kapansin-pansin din na ang dugo nito ay kulay asul dahil sa copper-containing na protina na hemocyanin."
    },
    {
        "title": "HINDI BITUIN ANG VENUS",
        "text": "Minsan tinatawag na tala sa umaga o tala sa gabi ang Venus. Pero planeta ito, hindi bituin. Napakaliwanag nito sa ating kalangitan dahil sa lapit nito sa Earth at sa makapal na ulap na nagbabalik ng maraming sikat ng araw."
    },
    {
        "title": "BAKIT LUMULUTANG ANG YELO?",
        "text": "Kadalasan, lumulutang ang yelo sa tubig dahil mas mababa ang density nito kaysa likidong tubig. Kapag nagyeyelo ang tubig, nag-aayos ang mga molekula sa isang istrukturang mas maluwag. Dahil dito, mahalaga ang yelo sa pagprotekta sa buhay sa malamig na lawa."
    },
    {
        "title": "MAY AMOY ANG KALAWAKAN?",
        "text": "Hindi natin direktang maaamoy ang vacuum ng kalawakan dahil kailangan ng ilong natin ng mga molekulang makararating dito. May mga astronaut na naglarawan ng amoy sa kanilang spacesuit pagkatapos ng spacewalk, pero ang paglalarawang iyon ay mula sa mga residue sa suit, hindi sa vacuum mismo."
    },
    {
        "title": "ANG HIGANTENG JUPITER",
        "text": "Ang Jupiter ang pinakamalaking planeta sa ating Solar System. Napakalaki nito na mahigit isang libong Earth ang maaaring magkasya rito ayon sa volume. Isa rin itong gas giant, kaya wala itong matigas na ibabaw na katulad ng sa Earth."
    },
    {
        "title": "HALOS WALANG TUNOG ANG BUWAN",
        "text": "Walang hangin sa ibabaw ng Buwan na sapat para magdala ng ordinaryong tunog tulad ng sa Earth. Kaya kung may dalawang astronaut na magkalayo at walang radyo, hindi nila maririnig ang boses ng isa't isa sa pamamagitan lamang ng hangin."
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


def make_caption_chunks(text: str, max_words: int = 5) -> list[str]:
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

    # Animated geometric accents create motion without external stock footage.
    # The opening kicker is visible for the first 2.8 seconds as a clear hook.
    subtitle_filter = (
        "drawbox=x='mod(t*42\\,900)-180':y=0:w=220:h=1280:color=0x2563EB@0.16:t=fill,"
        "drawbox=x='720-mod(t*27\\,1000)':y=0:w=160:h=1280:color=0x7C3AED@0.12:t=fill,"
        "drawbox=x=0:y=0:w=720:h=12:color=0x38BDF8@0.95:t=fill,"
        "drawbox=x=54:y=258:w=612:h=3:color=0x38BDF8@0.85:t=fill,"
        "drawtext=text='ALAM MO BA?':fontcolor=0x7DD3FC:fontsize=30:font='DejaVu Sans':"
        "x=(w-text_w)/2:y=112:enable='between(t,0,2.8)',"
        f"drawtext=text='{fact['title']}':fontcolor=white:fontsize=36:font='DejaVu Sans':"
        "x=(w-text_w)/2:y=160:box=1:boxcolor=0x101B35@0.72:boxborderw=18,"
        f"subtitles='{srt_path.as_posix()}':force_style="
        "'FontName=DejaVu Sans,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00202038,BorderStyle=3,BackColour=&HAA101B35,"
        "Outline=2,Shadow=0,Alignment=2,MarginL=58,MarginR=58,MarginV=170'"
    )

    print("Rendering upgraded vertical MP4...")
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x101B35:s=720x1280:r=30",
        "-i", str(audio_path),
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        str(video_path),
    ])

    metadata_path.write_text(json.dumps({
        "date": date.today().isoformat(),
        "title": fact["title"],
        "narration": narration,
        "duration_seconds": round(duration, 2),
        "video_file": video_path.name,
        "visual_style": "animated geometric background",
        "caption_style": "bold high-contrast mobile subtitles",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"SUCCESS: {video_path}")
    print(f"Duration: {duration:.1f} seconds")


if __name__ == "__main__":
    main()
