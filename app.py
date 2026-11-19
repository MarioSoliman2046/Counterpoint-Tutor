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
if "tutor_mode" not in st.session_state:
    st.session_state.tutor_mode = "Counterpoint"

if st.session_state.ui_language == "English":
    _, mode_column, language_column = st.columns([7, 2, 1])
else:
    language_column, mode_column, _ = st.columns([1, 2, 7])

with mode_column:
    next_mode = "Harmony" if st.session_state.tutor_mode == "Counterpoint" else "Counterpoint"
    mode_label = (
        ("Harmony mode" if next_mode == "Harmony" else "Counterpoint mode")
        if st.session_state.ui_language == "English"
        else ("وضع الهارموني" if next_mode == "Harmony" else "وضع الكونتربوينت")
    )
    if st.button(mode_label, key="tutor_mode_toggle"):
        st.session_state.tutor_mode = next_mode
        st.rerun()

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
        "harmony_title": "🎼 Harmony Tutor",
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
        "harmony_analysis": "Harmony analysis",
        "analysis_soon": "Upload a score, choose the species and cantus staff, then run the initial automatic checks.",
        "harmony_analysis_soon": "Harmony analysis will be added in a later update. Score reading and piano playback are available here.",
        "species_label": "Counterpoint species",
        "species_first": "First — note against note",
        "species_second": "Second — two notes against one",
        "species_third": "Third — four notes against one",
        "species_fourth": "Fourth — suspensions",
        "species_fifth": "Fifth — florid mixture",
        "cantus_label": "Cantus firmus staff",
        "upper_staff": "Upper staff",
        "lower_staff": "Lower staff",
        "analyze_button": "Analyze counterpoint",
        "analysis_found": "Analysis found {count} item(s) to review across {positions} aligned positions.",
        "analysis_clear": "No issues were found by the current automatic checks.",
        "review_note": "This is a learning aid. Confirm the recognized notes before relying on the analysis.",
        "finding_rhythm": "Expected {expected} counterpoint note(s) in this measure; found {actual}.",
        "finding_dissonance": "{interval} is dissonant at this position.",
        "finding_parallel": "Consecutive parallel {interval} intervals reduce independence between the voices.",
        "suggest_rhythm": "Check the selected species rhythm and confirm that the score was read correctly.",
        "suggest_dissonance": "Try a consonant third, fifth, sixth, or octave; in later species, check the allowed dissonance pattern and resolution.",
        "suggest_parallel": "Change one voice so the parts move in contrary or oblique motion, or use an imperfect consonance.",
        "bar_beat": "Measure {bar}, beat {beat}",
        "suggestion": "Possible next step",
        "cadence_rule": "Begin and end with a perfect consonance (unison, fifth, or octave).",
        "meter_missing": "The time signature could not be read, so rhythmic species checks are unavailable.",
        "footer": "© 2026 Mario Soliman · Created in the UAE",
    },
    "ar": {
        "title": "🎼 مدرس الكونتربوينت",
        "harmony_title": "🎼 مدرس الهارموني",
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
        "harmony_analysis": "تحليل الهارموني",
        "analysis_soon": "ارفع النوتة، واختر النوع والمدرّج الذي يحمل اللحن الثابت، ثم شغّل الفحوص الأولية.",
        "harmony_analysis_soon": "ستُضاف تفاصيل تحليل الهارموني في تحديث لاحق. قراءة النوتة وتشغيل البيانو متاحان هنا.",
        "species_label": "نوع الكونتربوينت",
        "species_first": "الأول — نغمة مقابل نغمة",
        "species_second": "الثاني — نغمتان مقابل نغمة",
        "species_third": "الثالث — أربع نغمات مقابل نغمة",
        "species_fourth": "الرابع — التعليق والحل",
        "species_fifth": "الخامس — مزيج حر من الأنواع",
        "cantus_label": "المدرّج الذي يحمل اللحن الثابت",
        "upper_staff": "المدرّج العلوي",
        "lower_staff": "المدرّج السفلي",
        "analyze_button": "حلّل الكونتربوينت",
        "analysis_found": "وجد التحليل {count} ملاحظة للمراجعة في {positions} موضعًا متوافقًا.",
        "analysis_clear": "لم تكشف الفحوص الآلية الحالية عن أخطاء.",
        "review_note": "هذا التحليل مساعد تعليمي؛ راجع النغمات التي قرأها التطبيق قبل الاعتماد على النتيجة.",
        "finding_rhythm": "المتوقع {expected} نغمة للكونتربوينت في هذا المازورة، والموجود {actual}.",
        "finding_dissonance": "الفاصل {interval} غير متوافق في هذا الموضع.",
        "finding_parallel": "تكرار فاصل {interval} بالحركة المتوازية يقلل استقلال الصوتين.",
        "suggest_rhythm": "راجع إيقاع النوع المختار وتأكد من صحة قراءة الصورة.",
        "suggest_dissonance": "جرّب فاصلًا متوافقًا مثل الثالثة أو الخامسة أو السادسة أو الأوكتاف؛ وفي الأنواع المتقدمة راجع طريقة معالجة النغمة غير المتوافقة.",
        "suggest_parallel": "غيّر حركة أحد الصوتين لتصبح عكسية أو ثابتة، أو استخدم فاصلًا متوافقًا غير تام.",
        "bar_beat": "المازورة {bar}، النبضة {beat}",
        "suggestion": "اقتراح للمراجعة",
        "cadence_rule": "ابدأ وأنهِ بفاصل تام متوافق (الأوكتاف أو الخامسة أو اليونيسون).",
        "meter_missing": "تعذّرت قراءة الميزان، لذلك لا يمكن فحص إيقاع النوع.",
        "footer": "© 2026 Mario Soliman · صُنع في الإمارات",
    },
}


def tr(key, **values):
    language_key = "ar" if IS_ARABIC else "en"
    return TEXT[language_key][key].format(**values)

st.markdown(
    """
    <style>
      .stApp {
        background:
          linear-gradient(90deg, rgba(248,250,252,.88), rgba(248,250,252,.45)),
          url('https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Johann_Sebastian_Bach.jpg/500px-Johann_Sebastian_Bach.jpg');
        background-size: cover, auto 100vh;
        background-position: center, right center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        color: #111827;
      }
      [data-testid="stAppViewContainer"] { color: #111827; }
      div[data-testid="stHeading"] { text-align: center !important; width: 100%; }
      div[data-testid="stHeading"] h1 { text-align: center !important; width: 100%; }
      .stButton > button,
      button[data-testid="stBaseButton-secondary"],
      [data-testid="stFileUploader"] button,
      [data-testid="stFileUploaderDropzone"] button {
        color: #102a43 !important; background-color: #e8f0fb !important;
        border: 1px solid #9bb6d3 !important; border-radius: 10px !important;
        font-weight: 600 !important;
      }
      [data-testid="stFileUploaderDropzone"] {
        background-color: rgba(247,251,255,.96) !important;
        border-color: #9bb6d3 !important;
      }
      [data-testid="stFileUploaderDropzone"] div,
      [data-testid="stFileUploaderDropzone"] span,
      [data-testid="stFileUploaderDropzone"] small {
        color: #243b53 !important;
      }
      .stButton > button:hover,
      [data-testid="stFileUploader"] button:hover {
        color: #ffffff !important; background-color: #285f8f !important;
      }
      .main .block-container {
        background: rgba(255,255,255,.82); padding: 2rem;
        border-radius: 14px; max-width: 1400px; padding-bottom: 5rem;
      }
      body, [data-testid="stAppViewContainer"] { direction: __DIRECTION__; }
      .app-footer {
        position: fixed; bottom: 0; left: 0; width: 100%; z-index: 999;
        padding: .7rem 1rem; text-align: center;
        color: #475569; background: rgba(255,255,255,.97);
        border-top: 1px solid #dbe3ee; font-size: .9rem;
        box-shadow: 0 -2px 12px rgba(15,23,42,.06);
      }
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
        grouped.setdefault(key, {
            "beat": event["beat"],
            "upper": [],
            "lower": [],
            "upper_durations": [],
            "lower_durations": [],
            "durations": [],
        })
        voice = "upper" if event["staff"] == 1 else "lower"
        grouped[key][voice].append(event["midi"])
        grouped[key][f"{voice}_durations"].append(event["duration_beats"])
        grouped[key]["durations"].append(event["duration_beats"])

    output = []
    for _, event in sorted(grouped.items()):
        output.append({
            "beat": event["beat"],
            "upper": event["upper"],
            "lower": event["lower"],
            "upper_durations": event["upper_durations"],
            "lower_durations": event["lower_durations"],
            "duration_beats": max(event["durations"] or [1.0]),
        })
    return output, tempo, first_meter, score_beats


def interval_label(midi_a, midi_b):
    semitones = abs(midi_a - midi_b)
    simple = semitones % 12
    labels_en = {0: "unison/octave", 1: "minor second", 2: "major second",
                 3: "minor third", 4: "major third", 5: "perfect fourth",
                 6: "tritone", 7: "perfect fifth", 8: "minor sixth",
                 9: "major sixth", 10: "minor seventh", 11: "major seventh"}
    labels_ar = {0: "يونيسون/أوكتاف", 1: "ثانية صغيرة", 2: "ثانية كبيرة",
                 3: "ثالثة صغيرة", 4: "ثالثة كبيرة", 5: "رابعة تامة",
                 6: "تريتون", 7: "خامسة تامة", 8: "سادسة صغيرة",
                 9: "سادسة كبيرة", 10: "سابعة صغيرة", 11: "سابعة كبيرة"}
    labels = labels_ar if IS_ARABIC else labels_en
    return labels[simple], simple


def analyze_species(events, meter, species, cantus_voice):
    """Apply an initial two-voice, tonal species-counterpoint rule set."""
    if not events or not meter:
        return [], 0

    beats_per_measure = meter[0] * 4.0 / meter[1]
    counter_voice = "lower" if cantus_voice == "upper" else "upper"
    lines = {"upper": [], "lower": []}
    for event in events:
        for voice in ("upper", "lower"):
            notes = event[voice]
            durations = event.get(f"{voice}_durations", [])
            for index, midi in enumerate(notes):
                duration = durations[index] if index < len(durations) else event["duration_beats"]
                lines[voice].append((event["beat"], midi, max(duration, 0.25)))
    for voice in lines:
        lines[voice].sort(key=lambda item: item[0])

    def active_note(voice, beat):
        candidates = [item for item in lines[voice] if item[0] <= beat < item[0] + item[2] - 1e-5]
        return candidates[-1][1] if candidates else None

    findings = []
    expected_per_measure = {"First": 1, "Second": 2, "Third": 4, "Fourth": 2}
    expected = expected_per_measure.get(species)
    if expected:
        counts = {}
        for beat, _, _ in lines[counter_voice]:
            bar = int(beat // beats_per_measure) + 1
            counts[bar] = counts.get(bar, 0) + 1
        for bar in sorted(counts):
            if counts[bar] != expected:
                findings.append({
                    "kind": "rhythm", "bar": bar, "beat": 1,
                    "expected": expected, "actual": counts[bar],
                    "severity": "check",
                })

    attacks = []
    for beat, midi, _ in lines[counter_voice]:
        cantus_midi = active_note(cantus_voice, beat)
        if cantus_midi is not None:
            label, simple = interval_label(cantus_midi, midi)
            attacks.append((beat, midi, cantus_midi, label, simple))

    if not attacks:
        return findings, 0

    consonant_classes = {0, 3, 4, 7, 8, 9}
    perfect_classes = {0, 7}
    for edge, attack in (("start", attacks[0]), ("end", attacks[-1])):
        if attack[4] not in perfect_classes:
            findings.append({
                "kind": "cadence", "bar": 1 if edge == "start" else int(attack[0] // beats_per_measure) + 1,
                "beat": 1 if edge == "start" else (attack[0] % beats_per_measure) + 1,
                "severity": "error",
            })
    for index, (beat, cp_midi, cf_midi, label, simple) in enumerate(attacks):
        if simple in consonant_classes:
            continue
        bar = int(beat // beats_per_measure) + 1
        beat_in_bar = (beat % beats_per_measure) + 1
        allowed = False
        note_index = next((i for i, item in enumerate(lines[counter_voice]) if abs(item[0] - beat) < 1e-5 and item[1] == cp_midi), -1)
        previous = lines[counter_voice][note_index - 1] if note_index > 0 else None
        following = lines[counter_voice][note_index + 1] if note_index >= 0 and note_index + 1 < len(lines[counter_voice]) else None
        if species in ("Second", "Third", "Fifth") and previous and following:
            before = cp_midi - previous[1]
            after = following[1] - cp_midi
            step = abs(before) in (1, 2) and abs(after) in (1, 2)
            passing = step and before * after > 0
            neighbor = step and previous[1] == following[1]
            if species == "Second":
                weak = abs((beat % beats_per_measure) - beats_per_measure / 2) < 0.08
                allowed = weak and passing
            elif species == "Third":
                strong = min(beat % beats_per_measure, abs((beat % beats_per_measure) - beats_per_measure / 2)) < 0.08
                allowed = not strong and (passing or neighbor)
            else:
                allowed = passing or neighbor
        if not allowed and species in ("Fourth", "Fifth") and previous and following:
            # Candidate suspension: same pitch is prepared, then resolves down by step.
            prepared = previous[1] == cp_midi and beat % beats_per_measure < 0.08
            resolves = cp_midi - following[1] in (1, 2)
            allowed = prepared and resolves

        if not allowed:
            findings.append({
                "kind": "dissonance", "bar": bar, "beat": beat_in_bar,
                "interval": label,
                "severity": "error",
            })

    for index in range(1, len(attacks)):
        prev = attacks[index - 1]
        current = attacks[index]
        prev_cp, prev_cf = prev[1], prev[2]
        cp_motion = current[1] - prev_cp
        cf_motion = current[2] - prev_cf
        if cp_motion * cf_motion > 0 and prev[4] in perfect_classes and current[4] == prev[4]:
            findings.append({
                "kind": "parallel", "bar": int(current[0] // beats_per_measure) + 1,
                "beat": (current[0] % beats_per_measure) + 1,
                "interval": current[3],
                "severity": "error",
            })

    return findings, len(attacks)


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


st.title(tr("harmony_title") if st.session_state.tutor_mode == "Harmony" else tr("title"))
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

        if st.session_state.tutor_mode == "Counterpoint":
            species_codes = ["First", "Second", "Third", "Fourth", "Fifth"]
            species_labels = [tr(f"species_{code.lower()}") for code in species_codes]
            selected_species_label = st.selectbox(tr("species_label"), species_labels)
            selected_species = species_codes[species_labels.index(selected_species_label)]
            cantus_label = st.radio(
                tr("cantus_label"),
                [tr("upper_staff"), tr("lower_staff")],
                horizontal=True,
            )
            cantus_voice = "upper" if cantus_label == tr("upper_staff") else "lower"

            if st.button(tr("analyze_button"), key="analyze_counterpoint"):
                if not meter:
                    st.error(tr("meter_missing"))
                else:
                    findings, aligned_positions = analyze_species(
                        events, meter, selected_species, cantus_voice
                    )
                    st.session_state["counterpoint_report"] = (
                        digest, selected_species, cantus_voice, findings, aligned_positions
                    )

            report = st.session_state.get("counterpoint_report")
            if report and report[:3] == (digest, selected_species, cantus_voice):
                _, _, _, findings, aligned_positions = report
                st.info(tr("review_note"))
                if findings:
                    st.warning(tr(
                        "analysis_found",
                        count=len(findings),
                        positions=aligned_positions,
                    ))
                    for finding in findings:
                        if finding["kind"] == "rhythm":
                            message = tr(
                                "finding_rhythm",
                                expected=finding["expected"],
                                actual=finding["actual"],
                            )
                            suggestion = tr("suggest_rhythm")
                        elif finding["kind"] == "cadence":
                            message = tr("cadence_rule")
                            suggestion = tr("suggest_dissonance")
                        elif finding["kind"] == "parallel":
                            message = tr("finding_parallel", interval=finding["interval"])
                            suggestion = tr("suggest_parallel")
                        else:
                            message = tr("finding_dissonance", interval=finding["interval"])
                            suggestion = tr("suggest_dissonance")
                        with st.container(border=True):
                            st.error(f"{tr('bar_beat', bar=finding['bar'], beat=finding['beat'])}: {message}")
                            st.caption(f"{tr('suggestion')}: {suggestion}")
                else:
                    st.success(tr("analysis_clear"))

st.divider()
st.subheader(
    tr("harmony_analysis")
    if st.session_state.tutor_mode == "Harmony"
    else tr("analysis")
)
st.info(
    tr("harmony_analysis_soon")
    if st.session_state.tutor_mode == "Harmony"
    else tr("analysis_soon")
)
st.markdown(f'<div class="app-footer">{tr("footer")}</div>', unsafe_allow_html=True)
