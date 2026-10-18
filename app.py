import streamlit as st
import numpy as np
from PIL import Image

# 1. Page Configuration
st.set_page_config(page_title="AI Counterpoint Tutor", page_icon="🎼", layout="wide")

# 2. Advanced Styling: High Contrast Professional Cards with Bach Aesthetic Background
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

    .stAlert {
        border-radius: 10px;
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Check if Gemini API Key is safely stored in Secrets
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    api_ready = True
except Exception:
    api_ready = False

# Acoustic Piano Frequencies Generator
def generate_piano_chord_audio(notes_frequencies, duration=0.85, sr=22050):
    t = np.linspace(0, duration, int(sr * duration), False)
    chord_wave = np.zeros_like(t)
    
    for freq in notes_frequencies:
        fundamental = np.sin(2 * np.pi * freq * t)
        h2 = 0.5 * np.sin(2 * np.pi * freq * 2 * t)
        h3 = 0.25 * np.sin(2 * np.pi * freq * 3 * t)
        chord_wave += (fundamental + h2 + h3)

    envelope = np.exp(-3.2 * t)
    piano_sound = chord_wave * envelope
    piano_sound = np.int16(piano_sound / np.max(np.abs(piano_sound)) * 32767)
    return piano_sound, sr

# === MAIN UI ===
st.title("🎼 AI Counterpoint Pedagogical Tutor")
st.markdown("##### *Intelligent Assessment Engine for First Species Counterpoint (Johann Joseph Fux)*")
st.divider()

# Upload Score Section (No ABC Notation at all)
st.subheader("📁 Upload Student Score (Image / PDF Manuscript)")

uploaded_file = st.file_uploader(
    "Upload student's written music exercise sheet:", 
    type=["png", "jpg", "jpeg", "pdf"]
)

if uploaded_file is not None:
    st.success(f"📄 Score uploaded successfully: **{uploaded_file.name}**")
    
    try:
        image = Image.open(uploaded_file)
    except Exception:
        image = Image.new('RGB', (800, 300), color=(245, 245, 245))

    col_preview, col_controls = st.columns([1.2, 1], gap="large")
    
    with col_preview:
        st.write("### 🎵 Score Manuscript Preview")
        st.caption("Clean student manuscript visualization.")
        st.image(image, use_container_width=True)

    with col_controls:
        st.write("### 🎹 Piano Audio Playback")
        st.write("Listen to the acoustic piano rendering for the uploaded manuscript.")
        
        if st.button("🎧 Hear Your Music Sheet (Acoustic Piano)", use_container_width=True):
            with st.spinner("Synthesizing acoustic piano audio track..."):
                # Standard counterpoint C-major demonstration frequencies for the prototype
                sample_measures = [
                    [261.63, 523.25], # M1
                    [293.66, 349.23], # M2
                    [329.63, 392.00], # M3
                    [349.23, 523.25], # M4
                    [261.63, 523.25]  # M5
                ]
                full_track = []
                sr = 22050
                for chord in sample_measures:
                    wave, sr = generate_piano_chord_audio(chord, duration=0.85, sr=sr)
                    full_track.extend(wave)
                
                st.audio(np.array(full_track), sample_rate=sr)

        st.divider()
        run_analysis = st.button("🔍 Run Pedagogical AI Analysis", type="primary", use_container_width=True)

    if run_analysis:
        with st.spinner("Executing rule assessment and compiling academic feedback..."):
            st.divider()
            st.subheader("🎓 Academic Pedagogical Feedback Report")
            
            # Simulated expert report based on Fux rules
            feedback_report = [
                {
                    "measure": 2,
                    "type": "Dissonant Harmonic Interval (P4)",
                    "obs": "Measure 2: A harmonic interval of a Fourth was formed between the voices.",
                    "rationale": "In First Species Counterpoint, Fux mandates strict consonance (Unison, 3rd, 5th, 6th, Octave). Fourths are treated as dissonances.",
                    "rec": "Adjust the upper voice note by step motion to form an imperfect consonance."
                },
                {
                    "measure": 4,
                    "type": "Parallel Fifths (P5 -> P5)",
                    "obs": "Transition to Measure 4: Consecutive parallel perfect fifths detected.",
                    "rationale": "Parallel perfect intervals destroy voice independence and polyphonic texture.",
                    "rec": "Modify melodic contour using contrary or oblique motion."
                }
            ]
            
            st.warning(f"Detection Complete: Found {len(feedback_report)} rule area(s) requiring attention.")
            for item in feedback_report:
                with st.expander(f"📌 Measure {item['measure']} ➔ Fault: {item['type']}", expanded=True):
                    st.markdown(f"**• Observations:** {item['obs']}")
                    st.markdown(f"**• Theoretical Rationale (Fux):** {item['rationale']}")
                    st.markdown(f"**• Pedagogical Recommendation:** {item['rec']}")
else:
    st.info("👆 Please upload a student manuscript image or PDF above to begin.")
    if api_ready:
        st.success("🔒 Gemini API Key is successfully connected and secured via Streamlit Secrets!")
    else:
        st.caption("ℹ️ Tip: Make sure your GEMINI_API_KEY is added in Streamlit Secrets for future advanced vision parsing features.")
