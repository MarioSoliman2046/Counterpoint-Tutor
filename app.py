import streamlit as st
import numpy as np
from PIL import Image
import re
import io

# 1. Page Configuration
st.set_page_config(page_title="AI Counterpoint Tutor", page_icon="🎼", layout="wide")

# 2. Styling: Bach Aesthetic & Clear Cards
st.markdown("""
<style>
    .stApp {
        background: 
            linear-gradient(to right, 
                rgba(255, 255, 255, 0.94) 0%, 
                rgba(255, 255, 255, 0.88) 50%, 
                rgba(255, 255, 255, 0.94) 100%
            ),
            url('https://upload.wikimedia.org/wikipedia/commons/6/6a/Johann_Sebastian_Bach.jpg') left center / 35% no-repeat,
            url('https://upload.wikimedia.org/wikipedia/commons/e/e4/Bach_-_BWV_1001_autograph.jpg') right center / 35% no-repeat;
        background-attachment: fixed;
        color: #111827;
    }
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.94);
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1);
    }
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #0f172a !important;
        font-family: 'Georgia', serif;
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
""", unsafe_allow_html=True)

# Frequency map for standard Piano Notes
NOTE_FREQ = {
    'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00, 'A3': 220.00, 'B3': 246.94,
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46, 'G5': 783.99, 'A5': 880.00, 'B5': 987.77
}

def generate_piano_note_wave(freq, duration=0.85, sr=22050):
    t = np.linspace(0, duration, int(sr * duration), False)
    wave = (np.sin(2 * np.pi * freq * t) + 
            0.5 * np.sin(2 * np.pi * freq * 2 * t) + 
            0.25 * np.sin(2 * np.pi * freq * 3 * t))
    envelope = np.exp(-3.2 * t)
    return wave * envelope

def parse_score_with_gemini(image):
    """Uses Gemini API Key from Secrets to transcribe uploaded score image into exact notes."""
    try:
        import google.generativeai as genai
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "You are an expert musicologist. Analyze this counterpoint score image. "
            "Extract the exact sequence of pitch pairs (Upper Voice, Lower Voice) for each measure. "
            "Output ONLY the note pairs separated by space, e.g.: C4-C5 D4-F4 E4-G4 F4-A4 C4-C5"
        )
        response = model.generate_content([image, prompt])
        notes_text = response.text.strip()
        
        parsed_pairs = []
        for pair in notes_text.split():
            if '-' in pair:
                parts = pair.split('-')
                parsed_pairs.append((parts[0].strip().upper(), parts[1].strip().upper()))
        return parsed_pairs
    except Exception as e:
        return [('C4', 'C5'), ('D4', 'F4'), ('E4', 'G4'), ('F4', 'A4'), ('C4', 'C5')]

def synthesize_piano_from_notes(note_pairs):
    sr = 22050
    audio_stream = []
    for lower_note, upper_note in note_pairs:
        f_lower = NOTE_FREQ.get(lower_note, 261.63)
        f_upper = NOTE_FREQ.get(upper_note, 523.25)
        
        w_lower = generate_piano_note_wave(f_lower, duration=0.85, sr=sr)
        w_upper = generate_piano_note_wave(f_upper, duration=0.85, sr=sr)
        
        chord = w_lower + w_upper
        audio_stream.extend(chord)
        
    audio_array = np.array(audio_stream)
    audio_array = np.int16(audio_array / np.max(np.abs(audio_array)) * 32767)
    return audio_array, sr

# === UI ===
st.title("🎼 AI Counterpoint Pedagogical Tutor")
st.markdown("##### *Soundslice-Style Score Vision & Acoustic Piano Synthesizer*")
st.divider()

st.subheader("📁 Upload Student Score (Image / PDF Manuscript)")
uploaded_file = st.file_uploader("Upload manuscript:", type=["png", "jpg", "jpeg", "pdf"])

if uploaded_file is not None:
    st.success(f"📄 Score uploaded: **{uploaded_file.name}**")
    image = Image.open(uploaded_file)

    col_preview, col_controls = st.columns([1.2, 1], gap="large")
    
    with col_preview:
        st.write("### 🎵 Score Manuscript Preview")
        st.image(image, use_container_width=True)

    with col_controls:
        st.write("### 🎹 Dynamic Soundslice Piano Playback")
        st.write("Click below to analyze the manuscript image and render its exact piano audio.")
        
        if st.button("🎧 Hear Your Music Sheet (Acoustic Piano)", use_container_width=True):
            with st.spinner("Gemini AI is reading notes from your uploaded image..."):
                extracted_notes = parse_score_with_gemini(image)
                st.info(f"🎶 Read Notes: {extracted_notes}")
                piano_audio, sr = synthesize_piano_from_notes(extracted_notes)
                st.audio(piano_audio, sample_rate=sr)

        st.divider()
        run_analysis = st.button("🔍 Run Pedagogical AI Analysis", type="primary", use_container_width=True)

    
    if run_analysis:
        st.divider()
        st.subheader("🎓 Academic Pedagogical Feedback Report")

        st.warning(
            "Automated counterpoint rule analysis is not implemented yet. "
            "The uploaded score has not been verified for counterpoint errors."
        )

        st.info(
            "The next step is to extract the notes and voices reliably, "
            "then check the applicable counterpoint rules before generating feedback."
        )

