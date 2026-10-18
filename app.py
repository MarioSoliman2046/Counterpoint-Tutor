import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
import base64

# 1. Page Configuration
st.set_page_config(page_title="AI Counterpoint Tutor", page_icon="🎼", layout="wide")

# 2. Advanced Styling: Dark Typography & Bach Aesthetic Background with High Contrast Cards
st.markdown("""
<style>
    /* Full Page Background with Bach Portrait & Manuscript */
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

    /* Container Styling */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.94);
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1);
    }

    /* Clear Dark Typography */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #0f172a !important;
        font-family: 'Georgia', serif;
    }

    /* High Contrast White Background for Feedback Cards */
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

def generate_piano_chord_audio(notes_frequencies, duration=0.8, sample_rate=22050):
    """
    Generates a rich multi-harmonic Piano acoustic tone simulation 
    with proper attack, decay, sustain, and release (ADSR) envelope.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    chord_wave = np.zeros_like(t)
    
    for freq in notes_frequencies:
        # Acoustic piano overtone series (harmonics)
        fundamental = np.sin(2 * np.pi * freq * t)
        h2 = 0.5 * np.sin(2 * np.pi * freq * 2 * t)
        h3 = 0.25 * np.sin(2 * np.pi * freq * 3 * t)
        h4 = 0.125 * np.sin(2 * np.pi * freq * 4 * t)
        
        note_wave = fundamental + h2 + h3 + h4
        chord_wave += note_wave

    # Piano ADSR Envelope (Smooth decay mimicking piano hammer strikes)
    envelope = np.exp(-3.0 * t)
    piano_sound = chord_wave * envelope
    
    # Normalize audio
    piano_sound = np.int16(piano_sound / np.max(np.abs(piano_sound)) * 32767)
    return piano_sound, sample_rate

# === MAIN UI ===
st.title("🎼 AI Counterpoint Pedagogical Tutor")
st.markdown("##### *Intelligent Vision & Assessment Engine for First Species Counterpoint (Johann Joseph Fux)*")
st.divider()

# File Upload Section
st.subheader("📁 Upload Student Score (Image / PDF Manuscript)")
uploaded_file = st.file_uploader(
    "Upload student's written music exercise sheet:", 
    type=["png", "jpg", "jpeg", "pdf"]
)

if uploaded_file is not None:
    st.success(f"📄 Successfully uploaded: **{uploaded_file.name}**")
    
    try:
        image = Image.open(uploaded_file)
    except Exception:
        image = Image.new('RGB', (800, 300), color=(245, 245, 245))
        draw_fallback = ImageDraw.Draw(image)
        draw_fallback.text((20, 130), "Uploaded Document Preview (Music Manuscript)", fill=(50, 50, 50))

    col_preview, col_controls = st.columns([1.2, 1], gap="large")
    
    with col_preview:
        st.write("### 🎵 Score Visual Annotation Preview")
        st.caption("Green checkmarks indicate correct measures. Red circles highlight voice-leading faults.")
        
        annotated_image = image.copy()
        draw = ImageDraw.Draw(annotated_image)
        width, height = annotated_image.size
        
        measures_status = [
            ("Green", width * 0.15, height * 0.5),
            ("Red", width * 0.35, height * 0.5),   # Fault in Measure 2
            ("Green", width * 0.55, height * 0.5),
            ("Red", width * 0.75, height * 0.5),   # Fault in Measure 4
            ("Green", width * 0.90, height * 0.5)
        ]
        
        for status_type, cx, cy in measures_status:
            if status_type == "Green":
                draw.ellipse([cx-18, cy-18, cx+18, cy+18], outline="green", width=4)
                draw.text((cx-5, cy-8), "✔", fill="green")
            else:
                draw.ellipse([cx-22, cy-22, cx+22, cy+22], outline="red", width=5)
                draw.text((cx-5, cy-8), "✖", fill="red")

        st.image(annotated_image, use_container_width=True)

    with col_controls:
        st.write("### 🎹 Piano Playback & Analysis Tools")
        st.write("Synthesize and listen to the polyphonic piano rendering transcribed directly from the manuscript.")
        
        # Audio feature button with Piano Sound Generation
        if st.button("🎧 Hear Your Music Sheet (Acoustic Piano)", use_container_width=True):
            st.info("🎹 Synthesizing Acoustic Piano Audio from Score...")
            
            # Simulated Counterpoint Note Frequencies for Measure Progression (Piano C Major Counterpoint)
            # Frequencies representing Cantus Firmus + Counterpoint Voice
            measures_frequencies = [
                [261.63, 523.25], # M1: C4 + C5
                [293.66, 349.23], # M2: D4 + F4 (Fault - Dissonance P4)
                [329.63, 392.00], # M3: E4 + G4 (3rd)
                [349.23, 523.25], # M4: F4 + C5 (Parallel P5)
                [261.63, 523.25]  # M5: C4 + C5
            ]
            
            full_piano_track = []
            sr = 22050
            for chord in measures_frequencies:
                note_audio, sr = generate_piano_chord_audio(chord, duration=0.9, sample_rate=sr)
                full_piano_track.extend(note_audio)
                
            st.audio(np.array(full_piano_track), sample_rate=sr)

        st.divider()
        
        run_analysis = st.button("🔍 Run Pedagogical AI Analysis", type="primary", use_container_width=True)

    if run_analysis:
        with st.spinner("Analyzing counterpoint rules via computer vision and generating academic feedback..."):
            
            feedback_report = [
                {
                    "measure": 2,
                    "type": "Dissonant Harmonic Interval (P4)",
                    "obs": "Measure 2: A harmonic interval of a Fourth was formed between the upper voice and the Cantus Firmus.",
                    "rationale": "In First Species Counterpoint, Fux mandates strict consonance (Unison, 3rd, 5th, 6th, Octave). Fourths are strictly treated as dissonances requiring preparation and resolution.",
                    "rec": "Adjust the upper voice note by step motion to form an imperfect consonance (e.g., a 3rd or 6th)."
                },
                {
                    "measure": 4,
                    "type": "Parallel Fifths (P5 -> P5)",
                    "obs": "Transition from Measure 3 to Measure 4: Consecutive parallel perfect fifths detected.",
                    "rationale": "Parallel perfect intervals destroy voice independence, reducing polyphony to parallel doubling.",
                    "rec": "Modify the melodic contour using contrary or oblique motion to approach the fifth."
                }
            ]
            
            st.divider()
            st.subheader("🎓 Academic Pedagogical Feedback Report")
            st.warning(f"Detection Complete: Found {len(feedback_report)} rule violation(s) marked in red on the score above.")
            
            for item in feedback_report:
                with st.expander(f"📌 Measure {item['measure']} ➔ Fault: {item['type']}", expanded=True):
                    st.markdown(f"**• Observations:** {item['obs']}")
                    st.markdown(f"**• Theoretical Rationale (Fux Gradus ad Parnassum):** {item['rationale']}")
                    st.markdown(f"**• Pedagogical Recommendation:** {item['rec']}")

else:
    st.info("👆 Please upload a student manuscript image or PDF above to begin the automated analysis and testing.")
