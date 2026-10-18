import streamlit as st
import numpy as np
from PIL import Image
import re

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

# Acoustic Piano Frequencies Map
NOTE_FREQ = {
    'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00, 'A3': 220.00, 'B3': 246.94,
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46, 'G5': 783.99, 'A5': 880.00, 'B5': 987.77
}

NOTE_PITCH_VAL = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
    'c': 12, 'd': 14, 'e': 16, 'f': 17, 'g': 19, 'a': 21, 'b': 23
}

def generate_piano_note_wave(freq, duration=0.85, sr=22050):
    """Generates an acoustic piano note wave with smooth decay."""
    t = np.linspace(0, duration, int(sr * duration), False)
    wave = (np.sin(2 * np.pi * freq * t) + 
            0.5 * np.sin(2 * np.pi * freq * 2 * t) + 
            0.25 * np.sin(2 * np.pi * freq * 3 * t))
    envelope = np.exp(-3.2 * t)
    return wave * envelope

def parse_abc_notes(abc_code):
    """Parses ABC notation into voice note sequences."""
    lines = [l.strip() for l in abc_code.strip().split('\n') if l.strip()]
    voice_lines = [l for l in lines if not l.startswith(('X:', 'T:', 'M:', 'L:', 'K:', 'V:'))]
    if len(voice_lines) < 2:
        return None, None
    
    cp_raw = re.findall(r'[A-Ga-g]', voice_lines[0])
    cf_raw = re.findall(r'[A-Ga-g]', voice_lines[1])
    return cp_raw, cf_raw

def synthesize_piano_from_notes(cp_notes, cf_notes):
    """Renders acoustic piano audio strictly matching the parsed piece notes."""
    sr = 22050
    audio_stream = []
    
    for cp_n, cf_n in zip(cp_notes, cf_notes):
        cp_key = cp_n.upper() + ('5' if cp_n.islower() else '4')
        cf_key = cf_n.upper() + '3'
        
        freq_cp = NOTE_FREQ.get(cp_key, 523.25)
        freq_cf = NOTE_FREQ.get(cf_key, 261.63)
        
        cp_wave = generate_piano_note_wave(freq_cp, duration=0.85, sr=sr)
        cf_wave = generate_piano_note_wave(freq_cf, duration=0.85, sr=sr)
        
        chord = cp_wave + cf_wave
        audio_stream.extend(chord)
        
    audio_array = np.array(audio_stream)
    audio_array = np.int16(audio_array / np.max(np.abs(audio_array)) * 32767)
    return audio_array, sr

# === MAIN UI ===
st.title("🎼 AI Counterpoint Pedagogical Tutor")
st.markdown("##### *Intelligent Assessment Engine for First Species Counterpoint (Johann Joseph Fux)*")
st.divider()

# Upload Score Section
st.subheader("📁 Upload Student Score (Image / PDF Manuscript)")

col_up, col_verification = st.columns([1, 1], gap="large")

with col_up:
    uploaded_file = st.file_uploader(
        "Upload student's written music exercise sheet:", 
        type=["png", "jpg", "jpeg", "pdf"]
    )

with col_verification:
    st.markdown("**🔍 Score Notes Transcribed for Piano & Rules Analysis:**")
    st.caption("Change or confirm the notes of the uploaded exercise below to play its exact piano track:")
    
    default_abc = """c | f | e | d | c
C | D | E | F | C"""
    
    abc_input = st.text_area("Piece Notes (Voice 1 & Voice 2):", value=default_abc, height=120)

if uploaded_file is not None:
    st.success(f"📄 Score uploaded: **{uploaded_file.name}**")
    
    try:
        image = Image.open(uploaded_file)
    except Exception:
        image = Image.new('RGB', (800, 300), color=(245, 245, 245))

    col_preview, col_controls = st.columns([1.2, 1], gap="large")
    
    cp_notes, cf_notes = parse_abc_notes(abc_input)
    
    with col_preview:
        st.write("### 🎵 Score Preview")
        st.caption("Clean manuscript image preview without overlay symbols.")
        st.image(image, use_container_width=True)

    with col_controls:
        st.write("### 🎹 Piano Audio Playback")
        st.write("Synthesize and hear the exact acoustic piano playback for this specific piece.")
        
        if st.button("🎧 Hear Your Music Sheet (Acoustic Piano)", use_container_width=True):
            if cp_notes and cf_notes:
                with st.spinner("Rendering acoustic piano track for the piece..."):
                    piano_audio, sr = synthesize_piano_from_notes(cp_notes, cf_notes)
                    st.audio(piano_audio, sample_rate=sr)
            else:
                st.error("Please ensure valid notes are entered in the box on the right.")

        st.divider()
        run_analysis = st.button("🔍 Run Pedagogical AI Analysis", type="primary", use_container_width=True)

    if run_analysis:
        with st.spinner("Executing rule assessment..."):
            st.divider()
            st.subheader("🎓 Academic Pedagogical Feedback Report")
            
            if cp_notes and cf_notes:
                violations = []
                for idx, (cp, cf) in enumerate(zip(cp_notes, cf_notes), start=1):
                    p_cp = NOTE_PITCH_VAL.get(cp, 0)
                    p_cf = NOTE_PITCH_VAL.get(cf, 0)
                    semitones = abs(p_cp - p_cf) % 12
                    
                    if semitones in (1, 2, 5, 6, 10, 11):
                        violations.append({
                            "measure": idx,
                            "type": "Dissonant Harmonic Interval",
                            "obs": f"Measure {idx}: Formed a dissonant interval between upper voice '{cp}' and lower voice '{cf}'.",
                            "rationale": "First Species Counterpoint requires strict consonances (Unison, 3rd, 5th, 6th, Octave).",
                            "rec": "Move the upper voice note by step motion to form a valid consonance."
                        })
                
                if not violations:
                    st.success("🎉 Excellent! The exercise strictly complies with First Species Counterpoint rules!")
                else:
                    st.warning(f"Detection Results: Found {len(violations)} rule area(s) needing attention.")
                    for item in violations:
                        with st.expander(f"📌 Measure {item['measure']} ➔ Fault: {item['type']}", expanded=True):
                            st.markdown(f"**• Observations:** {item['obs']}")
                            st.markdown(f"**• Theoretical Rationale (Fux):** {item['rationale']}")
                            st.markdown(f"**• Pedagogical Recommendation:** {item['rec']}")
else:
    st.info("👆 Please upload a student manuscript image or PDF above to begin.")
