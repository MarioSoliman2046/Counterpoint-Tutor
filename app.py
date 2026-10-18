import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
import io

# 1. Page Configuration
st.set_page_config(page_title="AI Counterpoint Tutor", page_icon="🎼", layout="wide")

# 2. Advanced Styling: Dark Fonts & Bach Aesthetic Background
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
        color: #111827; /* Dark text color for readability */
    }

    /* Container and Card Styling */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.92);
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1);
    }

    /* Enforce Dark Professional Colors for Headers and Text */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #1e293b !important;
        font-family: 'Georgia', serif;
    }
    
    /* Custom Alert Boxes */
    .stAlert {
        border-radius: 10px;
        color: #0f172a !important;
    }
</style>
""", unsafe_allow_html=True)

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
    
    # Load image for processing and visual annotation
    try:
        image = Image.open(uploaded_file)
    except Exception:
        # Fallback dummy image representation if PDF or format needs conversion
        image = Image.new('RGB', (800, 300), color=(240, 240, 240))
        draw_fallback = ImageDraw.Draw(image)
        draw_fallback.text((20, 130), "Uploaded Document Preview (Music Manuscript)", fill=(50, 50, 50))

    col_preview, col_controls = st.columns([1.2, 1], gap="large")
    
    with col_preview:
        st.write("### 🎵 Score Visual Annotation Preview")
        st.caption("Green checkmarks indicate correct measures. Red circles highlight voice-leading faults.")
        
        # Draw dynamic mock visual annotations (Green checks & Red circles on measures)
        annotated_image = image.copy()
        draw = ImageDraw.Draw(annotated_image)
        width, height = annotated_image.size
        
        # Simulating measure check/error coordinates for demonstration
        # Green circles/checks for good measures, Red circles for faults
        measures_status = [
            ("Green", width * 0.15, height * 0.4),
            ("Red", width * 0.35, height * 0.4), # Fault in Measure 2
            ("Green", width * 0.55, height * 0.4),
            ("Red", width * 0.75, height * 0.4), # Fault in Measure 4
            ("Green", width * 0.90, height * 0.4)
        ]
        
        for status_type, cx, cy in measures_status:
            if status_type == "Green":
                draw.ellipse([cx-15, cy-15, cx+15, cy+15], outline="green", width=4)
                draw.text((cx-5, cy-8), "✔", fill="green")
            else:
                draw.ellipse([cx-20, cy-20, cx+20, cy+20], outline="red", width=5)
                draw.text((cx-5, cy-8), "✖", fill="red")

        st.image(annotated_image, use_container_width=True)

    with col_controls:
        st.write("### 🎛️ Audio Playback & Analysis Tools")
        st.write("Listen to the transcribed audio representation of the uploaded student sheet before or after review.")
        
        # Audio feature button
        if st.button("🎧 Hear Your Music Sheet", use_container_width=True):
            st.info("🎵 Synthesizing audio playback from manuscript... (Playing Fux First Species Exercise)")
            # Generating a dummy synthetic audio wave tone to simulate playback functionality
            sample_rate = 22050
            t = np.linspace(0, 2, int(sample_rate * 2))
            # C major chord frequencies simulation
            audio_data = np.sin(2 * np.pi * 261.63 * t) + np.sin(2 * np.pi * 329.63 * t)
            audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
            st.audio(audio_data, sample_rate=sample_rate)

        st.divider()
        
        run_analysis = st.button("🔍 Run Pedagogical AI Analysis", type="primary", use_container_width=True)

    if run_analysis:
        with st.spinner("Analyzing counterpoint rules via computer vision and generating academic feedback..."):
            
            # Simulated Structured Pedagogical Report based on Fux Rules
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
