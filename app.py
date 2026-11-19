import hashlib
import io
import os
import subprocess
import sys
import tempfile
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError


st.set_page_config(
    page_title="Counterpoint Tutor",
    page_icon="🎼",
    layout="wide",
)

if "ui_language" not in st.session_state:
    st.session_state.ui_language = "English"

if st.session_state.ui_language == "English":
    _, language_column = st.columns([8, 1])
else:
    language_column, _ = st.columns([1, 8])

with language_column:
    next_language = "العربية" if st.session_state.ui_language == "English" else "English"
    language_help = "تغيير لغة العرض" if st.session_state.ui_language == "العربية" else "Switch the display language"
    if st.button(next_language, key="language_toggle", help=language_help):
        st.session_state.ui_language = next_language
        st.rerun()

LANGUAGE = st.session_state.ui_language
IS_ARABIC = LANGUAGE == "العربية"

TEXT = {
    "en": {
        "title": "🎼 Counterpoint Tutor",
        "intro": "Upload a printed score image (PNG or JPG) to read and play both staves together.",
        "quality_tip": "For best results, use a clear, straight image showing both complete staves, including the clefs and key signature.",
        "upload": "Choose a score image",
        "invalid_image": "This file is not a valid image. Choose a PNG or JPG file.",
        "tempo": "Playback tempo (beats per minute)",
        "read_play": "🎹 Read the score and play both staves",
        "reading": "Reading the score. The first analysis may take longer...",
        "timeout": "Reading timed out. Try a smaller, clearer image.",
        "read_failed": "The score could not be read. Check the image and try again.",
        "technical_details": "Technical details",
        "success": "Read {count} musical positions.",
        "meter": "Detected meter: {beats}/{unit}",
        "extracted": "Extracted notes: upper staff, then lower staff",
        "upper": "Upper",
        "lower": "Lower",
        "rest": "Rest",
        "analysis": "Counterpoint analysis",
        "analysis_soon": "Counterpoint rule analysis will be added after score reading and playback are complete.",
    },
    "ar": {
        "title": "🎼 مدرس الكونتربوينت",
        "intro": "ارفع صورة نوتة مطبوعة (PNG أو JPG) لقراءة المدرّجين وتشغيلهما معًا.",
        "quality_tip": "لأفضل نتيجة، استخدم صورة واضحة ومستقيمة يظهر فيها المدرّجان كاملين، مع المفتاح الموسيقي وعلامة التحويل.",
        "upload": "اختر صورة النوتة",
        "invalid_image": "الملف ليس صورة صالحة. اختر ملف PNG أو JPG.",
        "tempo": "سرعة التشغيل (نبضة في الدقيقة)",
        "read_play": "🎹 اقرأ النوتة وشغّل المدرّجين",
        "reading": "تتم قراءة النوتة. قد يستغرق التحليل الأول وقتًا أطول...",
        "timeout": "انتهى وقت القراءة. جرّب صورة أصغر وأوضح.",
        "read_failed": "تعذّرت قراءة النوتة. تأكد من الصورة وحاول مرة أخرى.",
        "technical_details": "التفاصيل التقنية",
        "success": "تم استخراج {count} موضعًا موسيقيًا.",
        "meter": "الميزان المكتشف: {beats}/{unit}",
        "extracted": "النغمات المستخرجة: المدرّج العلوي ثم السفلي",
        "upper": "العلوي",
        "lower": "السفلي",
        "rest": "سكتة",
        "analysis": "تحليل الكونتربوينت",
        "analysis_soon": "ستُضاف قواعد التحليل بعد اكتمال قراءة النوتة وتشغيلها.",
    },
}


def tr(key, **values):
    language_key = "ar" if IS_ARABIC else "en"
    return TEXT[language_key][key].format(**values)

st.markdown(
    """
    <style>
      .stApp { background: #f4f6fa; color: #111827; }
      .main .block-container {
        background: rgba(255,255,255,.96); padding: 2rem;
        border-radius: 14px; max-width: 1400px;
      }
      body, [data-testid="stAppViewContainer"] { direction: __DIRECTION__; }
    </style>
    """.replace("__DIRECTION__", "rtl" if IS_ARABIC else "ltr"),
    unsafe_allow_html=True,
)

PITCH_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def midi_name(midi):
    return f"{PITCH_NAMES[midi % 12]}{midi // 12 - 1}"


def pitch_to_midi(pitch):
    step = pitch.findtext("step")
    octave = pitch.findtext("octave")
    alter = int(float(pitch.findtext("alter", "0")))
    base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[step]
    return (int(octave) + 1) * 12 + base + alter


def homr_convert(image_bytes, suffix):
    """Run HOMR on one uploaded image and return its MusicXML text."""
    with tempfile.TemporaryDirectory(prefix="counterpoint_") as temp_dir:
        image_path = Path(temp_dir) / f"student_score{suffix}"
        image_path.write_bytes(image_bytes)

        # HOMR normally saves downloaded neural-network weights beside its
        # installed package. Streamlit's package directory is read-only, so
        # redirect every model path to a writable temporary cache directory.
        model_dir = Path(tempfile.gettempdir()) / "counterpoint_homr_models"
        model_dir.mkdir(parents=True, exist_ok=True)
        bootstrap = r'''
import os
import sys
from pathlib import Path

import homr.main as homr_main
import onnxruntime
from homr.transformer.configs import default_config

model_dir = Path(os.environ["HOMR_WRITABLE_MODEL_DIR"])
model_dir.mkdir(parents=True, exist_ok=True)

import homr.segmentation.config as segmentation_config
segmentation_config.segnet_path_onnx = str(
    model_dir / Path(segmentation_config.segnet_path_onnx).name
)
segmentation_config.segnet_path_onnx_fp16 = str(
    model_dir / Path(segmentation_config.segnet_path_onnx_fp16).name
)
for module in tuple(sys.modules.values()):
    if module is not None and getattr(module, "__name__", "").startswith("homr."):
        if hasattr(module, "segnet_path_onnx"):
            module.segnet_path_onnx = segmentation_config.segnet_path_onnx
        if hasattr(module, "segnet_path_onnx_fp16"):
            module.segnet_path_onnx_fp16 = segmentation_config.segnet_path_onnx_fp16

for name in (
    "encoder_path",
    "decoder_path",
    "encoder_path_fp16",
    "decoder_path_fp16",
):
    old_path = getattr(default_config.filepaths, name)
    setattr(default_config.filepaths, name, str(model_dir / Path(old_path).name))

# Some HOMR releases copy ONNX paths into module-level variables at import
# time. Redirect those too, so inference uses the writable files downloaded above.
for module in tuple(sys.modules.values()):
    if module is None or not getattr(module, "__name__", "").startswith("homr."):
        continue
    for name, value in tuple(vars(module).items()):
        if name.endswith("path_onnx") or name.endswith("path_onnx_fp16"):
            if isinstance(value, (str, os.PathLike)):
                setattr(module, name, str(model_dir / Path(value).name))

# Last-resort compatibility for versions that pass an old package path
# directly to ONNX Runtime after HOMR has already downloaded the same model.
original_inference_session = onnxruntime.InferenceSession
def writable_inference_session(model_path, *args, **kwargs):
    if isinstance(model_path, (str, os.PathLike)):
        requested = Path(model_path)
        writable_copy = model_dir / requested.name
        if not requested.exists() and writable_copy.exists():
            model_path = str(writable_copy)
    return original_inference_session(model_path, *args, **kwargs)

for module in tuple(sys.modules.values()):
    if module is not None and getattr(module, "InferenceSession", None) is original_inference_session:
        module.InferenceSession = writable_inference_session
onnxruntime.InferenceSession = writable_inference_session

sys.argv = ["homer", sys.argv[1]]
homr_main.main()
'''
        env = os.environ.copy()
        env["HOMR_WRITABLE_MODEL_DIR"] = str(model_dir)

        result = subprocess.run(
            [sys.executable, "-c", bootstrap, str(image_path)],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
            env=env,
        )

        xml_path = image_path.with_suffix(".musicxml")
        if result.returncode != 0 or not xml_path.exists():
            details = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                "HOMR_FAILED: "
                + (details[-1000:] if details else "No MusicXML file was produced.")
            )
        return xml_path.read_text(encoding="utf-8")


def parse_musicxml(xml_text):
    """Read note pitches, staff numbers, durations, meter, and tempo."""
    root = ET.fromstring(xml_text)
    events = []
    divisions = 1
    tempo = 120.0
    score_beats = 0.0
    first_meter = None

    parts = root.findall(".//part")
    if not parts:
        raise ValueError("EMPTY_MUSICXML")

    for part in parts:
        part_offset = 0.0
        for measure in part.findall("measure"):
            cursor = 0.0
            previous_onset = 0.0
            for child in measure:
                tag = child.tag.split("}")[-1]
                if tag == "attributes":
                    div = child.findtext("divisions")
                    if div:
                        divisions = max(1, int(div))
                    time_node = child.find("time")
                    if time_node is not None:
                        beats = int(time_node.findtext("beats", "4").split("+")[0])
                        beat_type = int(time_node.findtext("beat-type", "4"))
                        meter_beats = beats * 4.0 / beat_type
                        if first_meter is None:
                            first_meter = (beats, beat_type)
                elif tag == "direction":
                    sound = child.find("sound")
                    if sound is not None and sound.get("tempo"):
                        tempo = float(sound.get("tempo"))
                    metronome = child.find(".//metronome/per-minute")
                    if metronome is not None and metronome.text:
                        tempo = float(metronome.text)
                elif tag == "note":
                    duration = int(child.findtext("duration", "0")) / divisions
                    # A chord note shares the onset of the preceding note.
                    is_chord = child.find("chord") is not None
                    if is_chord:
                        onset = previous_onset
                    else:
                        onset = cursor
                        previous_onset = onset

                    if child.find("rest") is None:
                        pitch = child.find("pitch")
                        if pitch is not None:
                            midi = pitch_to_midi(pitch)
                            staff = int(child.findtext("staff", "1"))
                            events.append({
                                "beat": part_offset + onset,
                                "duration_beats": max(duration, 0.25),
                                "staff": staff,
                                "midi": midi,
                                "name": midi_name(midi),
                            })
                    if not is_chord:
                        cursor += duration
                elif tag in ("backup", "forward"):
                    amount = int(child.findtext("duration", "0")) / divisions
                    if tag == "backup":
                        cursor = max(0.0, cursor - amount)
                    else:
                        cursor += amount

            # A measure normally has a fixed length from its time signature.
            # Keep the larger of the notated meter and the actual event extent.
            measure_length = max(
                locals().get("meter_beats", 4.0),
                locals().get("cursor", 0.0),
                1.0,
            )
            part_offset += measure_length
            score_beats = max(score_beats, part_offset)

    if not events:
        raise ValueError("NO_NOTES")

    # Group notes occurring at the same musical time; staff 1 is upper, staff 2 lower.
    grouped = {}
    for event in events:
        key = round(event["beat"], 4)
        grouped.setdefault(key, {"beat": event["beat"], "upper": [], "lower": [], "durations": []})
        voice = "upper" if event["staff"] == 1 else "lower"
        grouped[key][voice].append(event["midi"])
        grouped[key]["durations"].append(event["duration_beats"])

    output = []
    for _, event in sorted(grouped.items()):
        output.append({
            "beat": event["beat"],
            "upper": event["upper"],
            "lower": event["lower"],
            "duration_beats": max(event["durations"] or [1.0]),
        })
    return output, tempo, first_meter, score_beats


def piano_note(freq, duration, sample_rate):
    n = max(1, int(duration * sample_rate))
    t = np.arange(n, dtype=np.float32) / sample_rate
    fundamental = (
        np.sin(2 * np.pi * freq * t)
        + 0.48 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.22 * np.sin(2 * np.pi * freq * 3 * t)
        + 0.10 * np.sin(2 * np.pi * freq * 4 * t)
    )
    attack = np.minimum(1.0, t / 0.012)
    release = np.minimum(1.0, np.maximum(0.0, (duration - t) / 0.06))
    envelope = np.exp(-2.0 * t) * attack * release
    return fundamental * envelope


def synthesize_score(events, bpm):
    sample_rate = 22050
    seconds_per_beat = 60.0 / bpm
    end_beats = max(
        event["beat"] + event["duration_beats"] for event in events
    ) + 0.15
    audio = np.zeros(int(end_beats * seconds_per_beat * sample_rate), dtype=np.float32)

    for event in events:
        start = int(event["beat"] * seconds_per_beat * sample_rate)
        duration = max(0.12, event["duration_beats"] * seconds_per_beat * 0.92)
        for midi in event["upper"] + event["lower"]:
            freq = 440.0 * (2 ** ((midi - 69) / 12))
            note = piano_note(freq, duration, sample_rate) * 0.34
            stop = min(len(audio), start + len(note))
            if stop > start:
                audio[start:stop] += note[:stop - start]

    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak > 0:
        audio = audio / peak * 0.88

    buffer = io.BytesIO()
    pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())
    return buffer.getvalue()


st.title(tr("title"))
st.markdown(tr("intro"))
st.info(tr("quality_tip"))

uploaded = st.file_uploader(tr("upload"), type=["png", "jpg", "jpeg"])

if uploaded:
    file_bytes = uploaded.getvalue()
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        st.error(tr("invalid_image"))
        st.stop()

    st.image(image, caption=uploaded.name, use_container_width=True)
    bpm = st.slider(tr("tempo"), 40, 180, 100)

    digest = hashlib.sha256(file_bytes).hexdigest()
    if st.button(tr("read_play"), type="primary"):
        with st.spinner(tr("reading")):
            try:
                xml_text = homr_convert(file_bytes, Path(uploaded.name).suffix.lower())
                events, detected_tempo, meter, total_beats = parse_musicxml(xml_text)
                st.session_state["score_result"] = (digest, events, detected_tempo, meter)
            except subprocess.TimeoutExpired:
                st.error(tr("timeout"))
                st.session_state.pop("score_result", None)
            except Exception as error:
                st.error(tr("read_failed"))
                with st.expander(tr("technical_details")):
                    st.code(str(error)[-1200:])
                st.session_state.pop("score_result", None)

    saved = st.session_state.get("score_result")
    if saved and saved[0] == digest:
        _, events, detected_tempo, meter = saved
        st.success(tr("success", count=len(events)))
        if meter:
            st.caption(tr("meter", beats=meter[0], unit=meter[1]))
        st.caption(tr("extracted"))
        for event in events:
            upper = " + ".join(midi_name(n) for n in event["upper"]) or tr("rest")
            lower = " + ".join(midi_name(n) for n in event["lower"]) or tr("rest")
            st.write(f"{tr('upper')}: **{upper}**　|　{tr('lower')}: **{lower}**")
        st.audio(synthesize_score(events, bpm), format="audio/wav")

st.divider()
st.subheader(tr("analysis"))
st.info(tr("analysis_soon"))
