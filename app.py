import io
import re
import wave

import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError
from google import genai
from google.genai import types


# إعداد الصفحة
st.set_page_config(
    page_title="AI Counterpoint Tutor",
    page_icon="🎼",
    layout="wide",
)

# التنسيق
st.markdown(
    """
    <style>
        .stApp {
            background:
                linear-gradient(
                    to right,
                    rgba(255, 255, 255, 0.94) 0%,
                    rgba(255, 255, 255, 0.88) 50%,
                    rgba(255, 255, 255, 0.94) 100%
                ),
                url('https://upload.wikimedia.org/wikipedia/commons/6/6a/Johann_Sebastian_Bach.jpg')
                    left center / 35% no-repeat,
                url('https://upload.wikimedia.org/wikipedia/commons/e/e4/Bach_-_BWV_1001_autograph.jpg')
                    right center / 35% no-repeat;
            background-attachment: fixed;
            color: #111827;
        }

        .main .block-container {
            background-color: rgba(255, 255, 255, 0.94);
            padding: 2.5rem;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }

        h1, h2, h3, h4, h5, h6, p, span, label {
            color: #0f172a !important;
            font-family: Georgia, serif;
        }

        div[data-testid="stExpander"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            margin-bottom: 10px !important;
        }

        div[data-testid="stExpander"] * {
            color: #0f172a !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def note_frequency(note_name):
    """تحويل اسم نغمة مثل C4 أو F#4 أو Bb3 إلى تردد."""
    match = re.fullmatch(r"([A-Ga-g])([#b]?)([0-8])", note_name.strip())
    if not match:
        raise ValueError(f"اسم النغمة غير صالح: {note_name}")

    letter, accidental, octave_text = match.groups()
    letter = letter.upper()
    octave = int(octave_text)

    semitones = {
        "C": 0,
        "D": 2,
        "E": 4,
        "F": 5,
        "G": 7,
        "A": 9,
        "B": 11,
    }

    midi_number = (octave + 1) * 12 + semitones[letter]

    if accidental == "#":
        midi_number += 1
    elif accidental == "b":
        midi_number -= 1

    return 440.0 * (2 ** ((midi_number - 69) / 12))


def generate_piano_note_wave(freq, duration=0.85, sample_rate=22050):
    """توليد موجة صوتية بسيطة لنغمة واحدة."""
    time_values = np.linspace(
        0,
        duration,
        int(sample_rate * duration),
        endpoint=False,
    )

    signal = (
        np.sin(2 * np.pi * freq * time_values)
        + 0.5 * np.sin(2 * np.pi * freq * 2 * time_values)
        + 0.25 * np.sin(2 * np.pi * freq * 3 * time_values)
    )

    envelope = np.exp(-3.2 * time_values)
    return signal * envelope


def parse_score_with_gemini(image):
    """قراءة أزواج النغمات من صورة التمرين: العلوي ثم السفلي."""
    api_key = st.secrets.get("GEMINI_API_KEY")

    if not api_key:
        st.error("مفتاح Gemini غير موجود في إعدادات التطبيق.")
        return None

    prompt = (
        "Read every note in this two-staff musical score from left to right. "
        "Identify the clef and key signature on each staff, and apply the key "
        "signature and any local accidentals when naming each pitch. Ignore "
        "the numbers and text printed below the notes. For each vertically "
        "aligned position, return the upper-staff pitch first and the "
        "lower-staff pitch second. Use scientific pitch notation such as "
        "C4, F#4, or Bb3. Return only pairs separated by spaces, for example: "
        "C4-G3 D4-A3 E4-B3. Do not reuse notes from any previous image. "
        "If a note is unclear, return exactly UNREADABLE."
    )

    try:
        # تصغير الصورة لتقليل وقت رفعها ومعالجتها.
        image_to_send = image.convert("RGB")
        image_to_send.thumbnail((1400, 1400))

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=120_000),
        )

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[prompt, image_to_send],
        )

        notes_text = (response.text or "").strip()

        if not notes_text or "UNREADABLE" in notes_text.upper():
            st.error("لم أتمكن من قراءة النوتة بوضوح. جرّب صورة أوضح.")
            return None

        pitch_pattern = re.compile(r"^[A-Ga-g](?:#|b)?[0-8]$")
        parsed_pairs = []

        for token in notes_text.split():
            token = token.strip("`.,;:")
            pair_match = re.fullmatch(r"([^-\s]+)-([^-\s]+)", token)

            if not pair_match:
                continue

            upper_note, lower_note = pair_match.groups()

            if (
                pitch_pattern.fullmatch(upper_note)
                and pitch_pattern.fullmatch(lower_note)
            ):
                parsed_pairs.append((upper_note, lower_note))

        if not parsed_pairs:
            st.error("وصل رد من Gemini، لكن لم أستطع استخراج أزواج نغمات منه.")
            return None

        return parsed_pairs

    except Exception as error:
        st.error(
            f"تعذّرت قراءة التمرين. نوع الخطأ: {type(error).__name__}. "
            "جرّب صورة أصغر، ثم أعد المحاولة."
        )
        return None

def synthesize_piano_from_notes(note_pairs):
    """توليد ملف WAV من أزواج النغمات المستخرجة."""
    sample_rate = 22050
    audio_parts = []

    for upper_note, lower_note in note_pairs:
        # الزوج المستخرج ترتيبه: الصوت العلوي ثم الصوت السفلي.
        upper_wave = generate_piano_note_wave(
            note_frequency(upper_note),
            sample_rate=sample_rate,
        )
        lower_wave = generate_piano_note_wave(
            note_frequency(lower_note),
            sample_rate=sample_rate,
        )

        chord = upper_wave + lower_wave
        peak = np.max(np.abs(chord))

        if peak > 0:
            chord = chord / peak * 0.8

        audio_parts.append(chord)

    audio_array = np.concatenate(audio_parts)
    pcm_audio = np.int16(np.clip(audio_array, -1.0, 1.0) * 32767)

    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_audio.tobytes())

    return wav_buffer.getvalue()


# واجهة التطبيق
st.title("🎼 مدرس الهارموني والكونتربوينت بالذكاء الاصطناعي")
st.markdown("##### *قراءة النوتة وتشغيل النغمات المستخرجة*")
st.divider()

st.subheader("📁 ارفع صورة النوتة")
uploaded_file = st.file_uploader(
    "اختر صورة بصيغة PNG أو JPG:",
    type=["png", "jpg", "jpeg"],
)

if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file).convert("RGB")
    except (UnidentifiedImageError, OSError):
        st.error("الملف المرفوع ليس صورة صالحة. اختر ملف PNG أو JPG.")
        st.stop()

    st.success(f"تم رفع الملف: **{uploaded_file.name}**")

    col_preview, col_controls = st.columns([1.2, 1], gap="large")

    with col_preview:
        st.write("### 🎵 معاينة النوتة")
        st.image(image, use_container_width=True)

    with col_controls:
        st.write("### 🎹 تشغيل النغمات")
        st.write("اضغط الزر لتحليل الصورة وتشغيل النغمات التي يتعرف عليها Gemini.")

        if st.button(
            "🎧 اقرأ النوتة وشغّلها",
            use_container_width=True,
        ):
            with st.spinner("Gemini يقرأ النوتة الآن..."):
                extracted_notes = parse_score_with_gemini(image)

            if extracted_notes:
                st.info(f"النغمات المستخرجة (الصوت العلوي، ثم السفلي): {extracted_notes}")
                audio_bytes = synthesize_piano_from_notes(extracted_notes)
                st.audio(audio_bytes, format="audio/wav")

        st.divider()

        run_analysis = st.button(
            "🔍 تحليل تربوي",
            type="primary",
            use_container_width=True,
        )

    if run_analysis:
        st.divider()
        st.subheader("🎓 ملاحظات تعليمية")

        st.warning(
            "تحليل قواعد الكونتربوينت غير مطبّق بعد؛ "
            "لم يتم التحقق من وجود أخطاء في النوتة."
        )

        st.info(
            "الخطوة التالية هي استخراج النغمات والأصوات بدقة، "
            "ثم التحقق من قواعد الكونتربوينت المناسبة قبل إنشاء الملاحظات."
        )
else:
    st.info("ارفع صورة للنوتة حتى تبدأ.")
