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
    page_title="مدرس الكونتربوينت",
    page_icon="🎼",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp { background: #f4f6fa; color: #111827; }
      .main .block-container {
        background: rgba(255,255,255,.96); padding: 2rem;
        border-radius: 14px; max-width: 1400px;
      }
    </style>
    """,
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

sys.argv = ["homer", "--no-title", sys.argv[1]]
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
                "لم يستطع محرّك قراءة هذه الصورة. "
                + (details[-1000:] if details else "لم يُنتج ملف MusicXML.")
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
        raise ValueError("ملف النوتة الناتج لا يحتوي على مدرّج قابل للقراءة.")

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
        raise ValueError("لم أجد نغمات في النتيجة. جرّب صورة أوضح ومقصوصة حول المدرّجين.")

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


st.title("🎼 مدرس الكونتربوينت")
st.markdown("ارفع صورة نوتة مطبوعة بصيغة PNG أو JPG لقراءة الصوتين وتشغيلهما معًا.")
st.info(
    "لأفضل نتيجة: ارفع صورة واضحة ومستقيمة يظهر فيها المدرّجان كاملين، "
    "بما في ذلك المفتاح الموسيقي وعلامات التحويل."
)

uploaded = st.file_uploader("اختر صورة النوتة", type=["png", "jpg", "jpeg"])

if uploaded:
    file_bytes = uploaded.getvalue()
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        st.error("الصورة غير صالحة. اختر ملف PNG أو JPG.")
        st.stop()

    st.image(image, caption=uploaded.name, use_container_width=True)
    bpm = st.slider("سرعة التشغيل (نبضة في الدقيقة)", 40, 180, 100)

    digest = hashlib.sha256(file_bytes).hexdigest()
    if st.button("🎹 اقرأ النوتة وشغّل الصوتين", type="primary"):
        with st.spinner("تتم قراءة النوتة. قد يستغرق التحليل الأول وقتًا أطول..."):
            try:
                xml_text = homr_convert(file_bytes, Path(uploaded.name).suffix.lower())
                events, detected_tempo, meter, total_beats = parse_musicxml(xml_text)
                st.session_state["score_result"] = (digest, events, detected_tempo, meter)
            except subprocess.TimeoutExpired:
                st.error("انتهى وقت قراءة الصورة. جرّب صورة أصغر وواضحة.")
                st.session_state.pop("score_result", None)
            except Exception as error:
                st.error(f"تعذّرت قراءة النوتة: {error}")
                st.session_state.pop("score_result", None)

    saved = st.session_state.get("score_result")
    if saved and saved[0] == digest:
        _, events, detected_tempo, meter = saved
        st.success(f"تم استخراج {len(events)} موضعًا موسيقيًا.")
        if meter:
            st.caption(f"الميزان المكتشف: {meter[0]}/{meter[1]}")
        st.caption("النغمات المستخرجة: الصوت العلوي ثم الصوت السفلي")
        for event in events:
            upper = " + ".join(midi_name(n) for n in event["upper"]) or "سكتة"
            lower = " + ".join(midi_name(n) for n in event["lower"]) or "سكتة"
            st.write(f"العلوي: **{upper}**　|　السفلي: **{lower}**")
        st.audio(synthesize_score(events, bpm), format="audio/wav")

st.divider()
st.subheader("تحليل الكونتربوينت")
st.info("سيُضاف تحليل قواعد الكونتربوينت بعد تثبيت قراءة النوتة وتشغيلها.")
