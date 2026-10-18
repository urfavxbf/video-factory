from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
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


VISUAL_SCENES = {
    "BAKIT ASUL ANG LANGIT?": [
        "Cinematic view from high above Earth, vivid blue atmosphere glowing along the curved horizon, sunlight from space, scientifically inspired realistic photography, vertical composition, no text, no labels",
        "Sunlight passing through Earth's atmosphere with tiny air molecules scattering blue light in every direction, elegant realistic science visualization, deep navy background and blue rays, vertical composition, no text",
        "Beautiful real-world view looking up at a brilliant blue sky with soft white clouds above a tropical Philippine landscape, natural sunlight, cinematic realistic photography, vertical composition, no text",
    ],
    "TUNOG SA KALAWAKAN": [
        "A lone astronaut floating outside a spacecraft in the silent black vacuum of space, Earth in the background, cinematic photorealism, vertical composition, no text",
        "A spacecraft drifting in deep space with stars and distant nebula, visual feeling of absolute silence and emptiness, cinematic realistic science imagery, vertical composition, no text",
        "Close-up of an astronaut helmet reflecting Earth and stars, dramatic rim lighting, photorealistic, vertical composition, no text",
    ],
    "MAY TUBIG SA BUWAN": [
        "Detailed cinematic lunar surface near the Moon's south pole, rugged gray craters and sharp sunlight, realistic space photography, vertical composition, no text",
        "Deep shadow inside a permanently shadowed lunar crater with subtle crystalline water ice glinting on the cold surface, scientifically grounded realistic visualization, vertical composition, no text",
        "A modern lunar exploration rover moving across the Moon with Earth visible low on the horizon, cinematic photorealism, vertical composition, no text",
    ],
    "MAS MABAGAL ANG ORAS": [
        "A GPS navigation satellite orbiting Earth with blue atmospheric glow and solar panels, realistic space photography, vertical composition, no text",
        "Elegant visualization of curved spacetime around Earth shown as subtle luminous grid lines bending near the planet, science documentary style, vertical composition, no text",
        "A satellite above Earth with city lights visible at night, crisp cinematic realism, vertical composition, no text",
    ],
    "ANG PUSO NG OCTOPUS": [
        "A realistic octopus swimming gracefully underwater among coral and rocks, detailed skin texture, natural ocean light, vertical composition, no text",
        "Scientific documentary-style close-up of an octopus with its arms spread, subtle educational anatomical visualization without labels or gore, realistic underwater lighting, vertical composition, no text",
        "Macro view of an octopus moving across a reef, blue water and sunbeams, photorealistic marine wildlife photography, vertical composition, no text",
    ],
    "HINDI BITUIN ANG VENUS": [
        "The bright planet Venus glowing in a deep twilight sky above a Philippine horizon, realistic astronomy photography, vertical composition, no text",
        "Planet Venus seen from space as a brilliant sphere wrapped in thick golden-white clouds, photorealistic planetary science image, vertical composition, no text",
        "A starry twilight sky over Earth with Venus shining brightly above the horizon, cinematic realistic astrophotography, vertical composition, no text",
    ],
    "BAKIT LUMULUTANG ANG YELO?": [
        "Clear ice cubes floating in a glass of water, close-up with realistic refraction and condensation, cinematic macro photography, vertical composition, no text",
        "Scientific visualization of water molecules forming an open crystalline ice lattice, translucent blue molecular structure, accurate educational 3D render, vertical composition, no text",
        "A frozen freshwater lake in winter with a visible layer of ice and calm water at the edge, peaceful realistic nature photography, vertical composition, no text",
    ],
    "MAY AMOY ANG KALAWAKAN?": [
        "Astronaut outside a spacecraft during a spacewalk, Earth filling the background, realistic NASA-inspired documentary photography, vertical composition, no text",
        "Close-up of a space suit glove and helmet after a spacewalk, metallic spacecraft surfaces and reflected sunlight, cinematic realism, vertical composition, no text",
        "A spacecraft airlock with an astronaut returning from a spacewalk, Earth visible beyond, realistic science documentary style, vertical composition, no text",
    ],
    "ANG HIGANTENG JUPITER": [
        "Jupiter filling most of the frame, swirling cream and rust-colored cloud bands and the Great Red Spot, realistic planetary photography, vertical composition, no text",
        "A spacecraft flying near Jupiter with the planet's enormous cloud bands and moons in the distance, cinematic realistic space art, vertical composition, no text",
        "Jupiter and several small moons against a deep black star field, scientifically inspired realistic astronomy image, vertical composition, no text",
    ],
    "HALOS WALANG TUNOG ANG BUWAN": [
        "Two astronauts in bulky white spacesuits standing far apart on the gray lunar surface, Earth above the horizon, realistic cinematic space photography, vertical composition, no text",
        "Close-up of an astronaut's helmet on the Moon, lunar dust and harsh sunlight, deep black sky, photorealistic, vertical composition, no text",
        "Wide view of the quiet lunar landscape with footprints leading toward a lunar lander, Earth in the sky, realistic space photography, vertical composition, no text",
    ],
}


def generate_ai_images(title: str) -> list[Path]:
    """Generate three story-matched images when Cloudflare credentials are configured."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    prompts = VISUAL_SCENES.get(title)
    if not account_id or not api_token or not prompts:
        print("AI scene images are not configured; using animated-background fallback.")
        return []

    scene_dir = OUT / "scenes"
    scene_dir.mkdir(exist_ok=True)
    generated: list[Path] = []
    endpoint = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    try:
        for index, prompt in enumerate(prompts, start=1):
            print(f"Generating contextual AI image {index}/{len(prompts)}...")
            payload = json.dumps({"prompt": prompt, "steps": 4}).encode("utf-8")
            request = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
            image_data = result.get("result", {}).get("image")
            if not result.get("success") or not image_data:
                raise RuntimeError("Cloudflare AI did not return an image.")
            image_path = scene_dir / f"scene-{index:02}.png"
            image_path.write_bytes(base64.b64decode(image_data))
            generated.append(image_path)
        return generated
    except Exception as exc:
        print(f"AI image generation failed ({type(exc).__name__}: {exc}).")
        print("Falling back to the animated background so the workflow can still finish.")
        for path in generated:
            path.unlink(missing_ok=True)
        return []


def render_ai_scene_video(images: list[Path], duration: float, video_path: Path,
                          audio_path: Path, srt_path: Path, title: str) -> None:
    """Create gentle Ken Burns motion on each generated image, then add narration/captions."""
    scene_dir = OUT / "scenes"
    clip_paths: list[Path] = []
    durations = [duration / len(images)] * len(images)
    durations[-1] = max(0.5, duration - sum(durations[:-1]))
    for index, (image_path, clip_duration) in enumerate(zip(images, durations), start=1):
        clip_path = scene_dir / f"clip-{index:02}.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(image_path),
            "-t", f"{clip_duration:.3f}",
            "-vf", "scale=900:1600:force_original_aspect_ratio=increase,"
                   "crop=900:1600,zoompan=z='min(zoom+0.0008,1.08)':d=1:"
                   "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=30,setsar=1",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", str(clip_path),
        ])
        clip_paths.append(clip_path)

    concat_file = scene_dir / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{path.resolve().as_posix()}'\n" for path in clip_paths),
        encoding="utf-8",
    )
    stitched_path = scene_dir / "stitched.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(stitched_path),
    ])

    # The AI images supply the context; title and subtitles remain legible over them.
    ai_filter = (
        "drawtext=text='ALAM MO BA?':fontcolor=0x7DD3FC:fontsize=22:font='DejaVu Sans':"
        "borderw=2:bordercolor=black@0.75:x=(w-text_w)/2:y=58:enable='between(t,0,2.8)',"
        f"drawtext=text='{title}':fontcolor=white:fontsize=27:font='DejaVu Sans':"
        "borderw=3:bordercolor=black@0.85:x=(w-text_w)/2:y=96,"
        f"subtitles='{srt_path.as_posix()}':force_style="
        "'FontName=DejaVu Sans,FontSize=17,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,BorderStyle=1,BackColour=&H00000000,"
        "Outline=2,Shadow=1,Alignment=2,MarginL=72,MarginR=72,MarginV=230'"

    )
    run([
        "ffmpeg", "-y", "-i", str(stitched_path), "-i", str(audio_path),
        "-map", "0:v:0", "-map", "1:a:0", "-vf", ai_filter,
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

    ai_images = generate_ai_images(fact["title"])
    if ai_images:
        print("Rendering contextual AI-scene video...")
        render_ai_scene_video(ai_images, duration, video_path, audio_path, srt_path, fact["title"])
        visual_style = "three contextual AI-generated images with gentle camera motion"
    else:
        # Fallback: animated geometric accents work even without API credentials.
        subtitle_filter = (
            "drawbox=x='mod(t*42\\,900)-180':y=0:w=220:h=1280:color=0x2563EB@0.16:t=fill,"
            "drawbox=x=720-mod(t*27\\,1000):y=0:w=160:h=1280:color=0x7C3AED@0.12:t=fill,"
            "drawtext=text='ALAM MO BA?':fontcolor=0x7DD3FC:fontsize=22:font='DejaVu Sans':"
            "borderw=2:bordercolor=black@0.75:x=(w-text_w)/2:y=58:enable='between(t,0,2.8)',"
            f"drawtext=text='{fact['title']}':fontcolor=white:fontsize=27:font='DejaVu Sans':"
            "borderw=3:bordercolor=black@0.85:x=(w-text_w)/2:y=96,"
            f"subtitles='{srt_path.as_posix()}':force_style="
            "'FontName=DejaVu Sans,FontSize=17,Bold=1,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00101010,BorderStyle=1,BackColour=&H00000000,"
            "Outline=2,Shadow=1,Alignment=2,MarginL=72,MarginR=72,MarginV=230'"

        )
        print("Rendering animated-background fallback MP4...")
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
        visual_style = "animated geometric background (AI images not configured or unavailable)"

    metadata_path.write_text(json.dumps({
        "date": date.today().isoformat(),
        "title": fact["title"],
        "narration": narration,
        "duration_seconds": round(duration, 2),
        "video_file": video_path.name,
        "visual_style": visual_style,
        "caption_style": "bold high-contrast mobile subtitles",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"SUCCESS: {video_path}")
    print(f"Duration: {duration:.1f} seconds")


if __name__ == "__main__":
    main()
