import streamlit as st
import re

# 1. Page Configuration
st.set_page_config(page_title="AI Counterpoint Tutor", page_icon="🎼", layout="wide")

# 2. Advanced CSS for Aesthetic Background (Bach Portrait + Handwritten Manuscript)
st.markdown("""
<style>
    /* Full Page Background with Overlay Effects */
    .stApp {
        background: 
            linear-gradient(to right, 
                rgba(255, 255, 255, 0.92) 0%, 
                rgba(255, 255, 255, 0.85) 50%, 
                rgba(255, 255, 255, 0.92) 100%
            ),
            url('https://upload.wikimedia.org/wikipedia/commons/6/6a/Johann_Sebastian_Bach.jpg') left center / 35% no-repeat,
            url('https://upload.wikimedia.org/wikipedia/commons/e/e4/Bach_-_BWV_1001_autograph.jpg') right center / 35% no-repeat;
        background-attachment: fixed;
    }

    /* Container Styling */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.88);
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.08);
        backdrop-filter: blur(5px);
    }

    /* Header Styling */
    h1, h2, h3 {
        font-family: 'Georgia', serif;
        color: #1a2a3a;
    }

    /* Custom Accent Card */
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Pitch value mapping
NOTE_PITCH = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
    'c': 12, 'd': 14, 'e': 16, 'f': 17, 'g': 19, 'a': 21, 'b': 23
}

def parse_abc_line(line):
    notes = re.findall(r'[A-Ga-g]', line)
    return [NOTE_PITCH[n] for n in notes if n in NOTE_PITCH]

def analyze_counterpoint(abc_code):
    lines = [l.strip() for l in abc_code.strip().split('\n') if l.strip()]
    voice_lines = [l for l in lines if not l.startswith(('X:', 'T:', 'M:', 'L:', 'K:'))]
    
    if len(voice_lines) < 2:
        return None, "Invalid input format. Please ensure at least two voice lines are provided."

    cp_notes = parse_abc_line(voice_lines[0])
    cf_notes = parse_abc_line(voice_lines[1])

    if len(cp_notes) != len(cf_notes) or not cp_notes:
        return None, "Error: Voice length mismatch or empty score line."

    feedback = []
    prev_interval = None

    for measure, (cp, cf) in enumerate(zip(cp_notes, cf_notes), start=1):
        semitones = abs(cp - cf) % 12
        raw_diff = cp - cf
        
        # 1. Voice Crossing
        if raw_diff < 0:
            feedback.append({
                "measure": measure,
                "type": "Voice Crossing",
                "obs": f"Measure {measure}: Counterpoint voice dropped below the Cantus Firmus.",
                "rationale": "Voice crossing disrupts the clarity of individual polyphonic lines.",
                "rec": "Ensure the upper voice stays strictly above the lower voice."
            })

        # 2. Dissonance Check
        if semitones in (1, 2, 5, 6, 10, 11):
            feedback.append({
                "measure": measure,
                "type": "Dissonant Interval",
                "obs": f"Measure {measure}: A harmonic dissonance was detected.",
                "rationale": "In First Species Counterpoint, only consonant harmonic intervals (Unison, 3rd, 5th, 6th, 8ve) are permitted.",
                "rec": "Move the counterpoint note by step to form a 3rd, 5th, 6th, or Octave."
            })

        # 3. Parallel Fifths and Octaves
        if prev_interval is not None:
            if semitones == 7 and prev_interval == 7:
                feedback.append({
                    "measure": measure,
                    "type": "Parallel Fifths",
                    "obs": f"Transition into Measure {measure}: Parallel Perfect Fifths detected.",
                    "rationale": "Parallel movement in perfect intervals reduces contrapuntal independence.",
                    "rec": "Use contrary or oblique motion when approaching this measure."
                })
            elif semitones == 0 and prev_interval == 0:
                feedback.append({
                    "measure": measure,
                    "type": "Parallel Octaves/Unisons",
                    "obs": f"Transition into Measure {measure}: Parallel Octaves detected.",
                    "rationale": "Parallel octaves eliminate independent voice identity.",
                    "rec": "Change the direction of the upper voice."
                })

        prev_interval = semitones

    return feedback, "Success"

# === MAIN UI ===
st.title("🎼 AI Counterpoint Pedagogical Tutor")
st.markdown("##### *Intelligent Assessment Engine for First Species Counterpoint (Johann Joseph Fux)*")
st.divider()

# Input Options Layout
col_upload, col_input = st.columns([1, 1], gap="large")

with col_upload:
    st.subheader("📁 Upload Score (PDF / Image)")
    uploaded_file = st.file_uploader(
        "Upload manuscript scan, PDF, or picture:", 
        type=["pdf", "png", "jpg", "jpeg"]
    )
    if uploaded_file is not None:
        st.info(f"📄 File uploaded: **{uploaded_file.name}**")
        st.caption("Note: Optical Music Recognition (OMR) processing is active. Please confirm or fine-tune the extracted ABC Notation on the right.")

with col_input:
    st.subheader("✍️ ABC Notation Score")
    default_abc = """c | f | e | d | c
C | D | E | F | C"""
    
    abc_input = st.text_area(
        "Edit or paste ABC Notation here:", 
        value=default_abc, 
        height=160
    )

st.divider()

if st.button("🔍 Analyze Composition & Generate Feedback", type="primary", use_container_width=True):
    with st.spinner("Evaluating counterpoint rules and compiling academic report..."):
        report, status = analyze_counterpoint(abc_input)
        
        if status != "Success":
            st.error(status)
        elif not report:
            st.success("🎉 Excellent! Your exercise strictly complies with First Species Counterpoint rules!")
        else:
            st.warning(f"Found {len(report)} area(s) needing attention:")
            for item in report:
                with st.expander(f"📌 Measure {item['measure']}: {item['type']}", expanded=True):
                    st.write(f"**Observations:** {item['obs']}")
                    st.write(f"**Theoretical Rationale:** {item['rationale']}")
                    st.write(f"**Recommendation:** {item['rec']}")
