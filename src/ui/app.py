"""
Streamlit frontend for the AI Resume Agent.
LinkedIn Aesthetic: Clean, Professional, High Readability
"""

import streamlit as st
import requests
import time
import base64

API_BASE = "http://localhost:8000/api"

st.set_page_config(
    page_title="AI Job Prep | LinkedIn Style",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "processing" not in st.session_state:
    st.session_state.processing = False
if "result" not in st.session_state:
    st.session_state.result = None
if "current_step" not in st.session_state:
    st.session_state.current_step = -1

STEPS = ["Format Analysis", "JD Extraction", "Content Tailoring", "PDF Injection", "Validation"]

def apply_pastel_css():
    st.markdown("""
        <style>
        /* Soft Pastel Design System */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        .stApp { background-color: #fdfbf7; color: #2d3748; font-family: 'Inter', sans-serif;}
        .block-container { padding-top: 1rem !important; max-width: 1200px !important; }
        #MainMenu, footer { display: none !important; }

        h1, h2, h3, h4, p, span, div, label { color: #2d3748 !important; }

        .card-heading {
            font-size: 20px; font-weight: 600; color: #2d3748;
            padding-bottom: 16px; margin-bottom: 24px;
            letter-spacing: -0.02em;
        }

        /* Buttons */
        .stButton button { border-radius: 12px !important; font-weight: 600 !important; color: #4a5568 !important; background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; }
        .stButton button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #ffc8dd, #bde0fe) !important;
            color: #2d3748 !important; border: none !important;
            box-shadow: 0 4px 12px rgba(189, 224, 254, 0.4) !important;
            transition: all 0.3s ease !important;
        }
        .stButton button[data-testid="baseButton-primary"]:hover {
            box-shadow: 0 6px 16px rgba(189, 224, 254, 0.6) !important;
            transform: translateY(-2px);
        }

        /* Inputs */
        .stTextArea textarea, .stTextInput input {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            color: #2d3748 !important; border-radius: 12px !important;
        }
        .stTextArea textarea:focus, .stTextInput input:focus {
            border-color: #bde0fe !important; box-shadow: 0 0 0 2px #bde0fe !important;
        }
        
        div[data-testid="stFileUploader"] > section {
            border: 2px dashed #cbd5e0 !important;
            background-color: #ffffff !important; border-radius: 12px !important;
        }

        /* Match Progess bar */
        .match-container { margin-bottom: 20px; }
        .match-label-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
        .match-title { font-size: 14px; font-weight: 600; color: #4a5568; }
        .match-pct { font-size: 14px; font-weight: 700; color: #a2d2ff; }
        .match-bar-bg { width: 100%; height: 8px; background-color: #edf2f7; border-radius: 6px; }
        .match-bar-fill { height: 100%; border-radius: 6px; transition: width 1s ease; }

        /* Stepper */
        .li-stepper { display: flex; gap: 16px; margin-bottom: 32px; }
        .li-step { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;}
        .li-step-icon {
            width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center;
            justify-content: center; font-size: 14px; font-weight: 600;
        }
        .li-step-icon.done { background-color: #cdb4db; color: white; }
        .li-step-icon.active { background: linear-gradient(135deg, #ffc8dd, #bde0fe); color: #2d3748; }
        .li-step-icon.pending { background-color: #edf2f7; color: #a0aec0; }
        
        .li-step-label { font-size: 12px; text-align: center; }
        .li-step-label.active { color: #2d3748; font-weight: 600; }
        .li-step-label.done { color: #4a5568; }
        .li-step-label.pending { color: #a0aec0; }

        /* Header */
        .li-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; padding: 12px 0;}
        .li-logo {
            background: linear-gradient(135deg, #a2d2ff, #cdb4db);
            color: #2d3748; font-weight: bold; width: 44px; height: 44px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center; font-size: 22px;
            box-shadow: 0 4px 10px rgba(162, 210, 255, 0.3);
        }
        .li-title { font-size: 24px; font-weight: 700; color: #2d3748; letter-spacing: -0.02em; }
        
        /* Empty */
        .li-empty { padding: 60px; text-align: center; display: flex; flex-direction: column; align-items: center; }
        .li-empty-circle { font-size: 40px; margin-bottom: 16px; }

        /* Streamlit overrides for light mode compatibility */
        .stMarkdown { color: #2d3748; }
        
        </style>
    """, unsafe_allow_html=True)

def render_match_bar(title: str, value_pct: float, color: str = "#aca3ff"):
    pct_int = int(value_pct * 100)
    st.markdown(f"""
<div class="match-container">
    <div class="match-label-row">
        <span class="match-title">{title}</span>
        <span class="match-pct" style="color: {color};">{pct_int}%</span>
    </div>
    <div class="match-bar-bg">
        <div class="match-bar-fill" style="width: {pct_int}%; background-color: {color};"></div>
    </div>
</div>
    """, unsafe_allow_html=True)


def main():
    apply_pastel_css()

    # Top Navigation Bar Simulation
    st.markdown("""
<div class="li-header">
    <div class="li-logo">in</div>
    <div class="li-title">AI Job Prepper</div>
</div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1.2], gap="large")

    with col1:
        # Input Card using Streamlit Native Container
        with st.container(border=True):
            st.markdown("<div class='card-heading'>Target Your Resume</div>", unsafe_allow_html=True)
            
            # File Uploader - SAFE, using built-in Streamlit labeling strictly
            uploaded_file = st.file_uploader("Resume Document (PDF)", type=["pdf"])
            
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            job_description = st.text_area(
                "Job Description", 
                height=250, 
                placeholder="Paste the target job description. We will optimize your resume layout while extracting and matching the core requested skills."
            )
            urls = st.text_input("External Links (Optional)", placeholder="https://github.com/YourName")
            
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            can_submit = uploaded_file is not None and len(job_description.strip()) > 50
            if st.button("Optimize Resume", type="primary", use_container_width=True, disabled=not can_submit or st.session_state.processing):
                st.session_state.processing = True
                st.session_state.processing_refine = False
                st.session_state.result = None
                st.session_state.current_step = 0
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("<div class='card-heading'>Optimization Engine</div>", unsafe_allow_html=True)
            
            # Render Stepper
            current = st.session_state.current_step
            stepper_html = '<div class="li-stepper">'
            for i, step in enumerate(STEPS):
                if i < current: state_class, icon = "done", "✓"
                elif i == current: state_class, icon = "active", str(i+1)
                else: state_class, icon = "pending", str(i+1)
                
                stepper_html += f"""
<div class="li-step">
    <div class="li-step-icon {state_class}">{icon}</div>
    <div class="li-step-label {state_class}">{step}</div>
</div>
"""
            stepper_html += '</div>'
            st.markdown(stepper_html, unsafe_allow_html=True)

            # Output States
            if not st.session_state.processing and st.session_state.result is None:
                st.markdown("""
<div class="li-empty">
    <div class="li-empty-circle">📄</div>
    <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">Waiting for Input</div>
    <div style="font-size: 14px; color: #666666; max-width: 250px;">Upload your original resume and provide a target job description to begin the tailoring process.</div>
</div>
                """, unsafe_allow_html=True)

            elif st.session_state.processing:
                st.markdown("""
<div class="li-empty">
    <div class="li-empty-circle" style="animation: pulse 1.5s infinite;">💎</div>
    <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">Architecting your resume...</div>
    <div style="font-size: 14px; color: #aaa8c3; max-width: 250px;">Merging your external skills into a perfectly formatted PDF.</div>
</div>
                """, unsafe_allow_html=True)

            elif st.session_state.result:
                res = st.session_state.result
                if res.get("success"):
                    st.success("Your resume is optimized and ready for download.")
                    
                    val = res.get("validation", {})
                    eval_data = res.get("evaluation", {})
                    
                    st.markdown("### Profile Strength Validation")
                    
                    # Instead of bare numbers, show nice progress bars like LinkedIn profile strength
                    kw_match = eval_data.get('keyword_match', 0)
                    render_match_bar("Keyword Skills Match", kw_match, color="#5ddbff" if kw_match > 0.5 else "#aca3ff")
                    
                    ats_match = eval_data.get('ats_similarity', 0)
                    render_match_bar("ATS Structural Similarity", ats_match, color="#5ddbff" if ats_match > 0.5 else "#aca3ff")
                    
                    if val.get("format_preserved"):
                        st.markdown("**✓ Original PDF Structure Safely Preserved**")
                    else:
                        st.markdown("**⚠ Structure Modifications Detected in PDF**")
                        
                    # LIVE PDF PREVIEW
                    if res.get("output_pdf_path"):
                        try:
                            with open(res.get("output_pdf_path"), "rb") as f:
                                pdf_bytes = f.read()
                            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                            
                            st.markdown("### Interactive Preview")
                            pdf_display = f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="450px" type="application/pdf"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                            
                            st.markdown("<br/>", unsafe_allow_html=True)
                            
                            st.markdown("#### Suggest Changes (Human-in-the-Loop)")
                            feedback = st.text_input("Notice anything you'd like changed? Tell the AI:", placeholder="E.g., 'Make my backend skills sound more senior'")
                            
                            col_dl, col_refine = st.columns(2)
                            with col_dl:
                                st.download_button(
                                    label="Save as PDF",
                                    data=pdf_bytes,
                                    file_name="luminescent_resume.pdf",
                                    mime="application/pdf",
                                    use_container_width=True,
                                    type="primary"
                                )
                            with col_refine:
                                if st.button("Apply Feedback", disabled=not feedback or st.session_state.processing, use_container_width=True):
                                    st.session_state.processing = True
                                    st.session_state.processing_refine = True
                                    st.session_state.refine_feedback = feedback
                                    st.rerun()
                                    
                        except Exception as e:
                            st.error(f"Error reading optimized PDF: {e}")
                else:
                    st.error(f"Processing failed: {res.get('error')}")

    # Async Processor Loop
    if st.session_state.processing:
        if getattr(st.session_state, "processing_refine", False):
            # Hit the refine endpoint
            try:
                data = {"prompt": st.session_state.refine_feedback}
                response = requests.post(f"{API_BASE}/refine/{st.session_state.result['session_id']}", data=data, timeout=300)
                if response.status_code == 200:
                    st.session_state.result = response.json()
                else:
                    st.session_state.result = {"success": False, "error": response.text}
            except Exception as e:
                st.session_state.result = {"success": False, "error": str(e)}
        else:
            try:
                for step_idx in range(5):
                    st.session_state.current_step = step_idx
                    if step_idx < 4:
                        time.sleep(0.5)
                
                files = {"resume": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                data = {"job_description": job_description, "urls": urls}
    
                response = requests.post(f"{API_BASE}/tailor", files=files, data=data, timeout=300)
                if response.status_code == 200:
                    st.session_state.result = response.json()
                else:
                    st.session_state.result = {"success": False, "error": response.text}
            except Exception as e:
                st.session_state.result = {"success": False, "error": str(e)}

        st.session_state.current_step = 5
        st.session_state.processing = False
        st.session_state.processing_refine = False
        st.rerun()

if __name__ == "__main__":
    main()
