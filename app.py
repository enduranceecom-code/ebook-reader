import streamlit as st
import PyPDF2
from gtts import gTTS
import io
import base64

# --- 1. Page Config ---
st.set_page_config(page_title="Free eBook Reader", layout="wide")

# --- 2. CSS for clean layout ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .main-text {
        font-size: 18px;
        line-height: 1.6;
        font-family: 'Georgia', serif;
        padding: 20px;
        background-color: #f9f9f9;
        border-radius: 10px;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Session State Initialization ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = []

# --- 4. Helper Functions ---

@st.cache_resource
def parse_pdf(file):
    """Extracts text from the entire PDF at once and caches it."""
    pdf_reader = PyPDF2.PdfReader(file)
    text_list = []
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            text_list.append(text)
        else:
            text_list.append("(No readable text on this page - likely an image)")
    return text_list

def generate_audio_bytes(text):
    """Generates audio using free Google TTS."""
    if not text.strip() or len(text) < 5:
        return None
    
    # Generate MP3 data in memory
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()

def get_audio_player_html(audio_bytes, speed=1.0):
    """Creates a custom HTML audio player that supports speed control."""
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio controls autoplay id="audio_player" style="width: 100%;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        <script>
            var audio = document.getElementById("audio_player");
            audio.playbackRate = {speed};
        </script>
    """
    return md

# --- 5. Main App Layout ---

st.title("📖 Free eBook Audio Reader")

# Sidebar
with st.sidebar:
    st.header("Settings")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    
    st.divider()
    
    st.subheader("Playback Speed")
    speed = st.select_slider(
        "Voice Speed",
        options=[0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        value=1.0
    )
    
    st.info("Tip: Use the slider to read faster!")

# Main Logic
if uploaded_file is not None:
    # Load PDF (Cached)
    with st.spinner("Processing PDF..."):
        text_list = parse_pdf(uploaded_file)
        st.session_state.pdf_text = text_list

    total_pages = len(st.session_state.pdf_text)

    # --- Navigation Logic ---
    col1, col2, col3 = st.columns([1, 2, 1])

    # Slider callback to sync state
    def update_slider():
        st.session_state.current_page = st.session_state.page_slider

    with col2:
        # The slider is bound to the session state
        st.slider(
            "Go to Page", 
            0, 
            total_pages - 1, 
            key="page_slider", 
            value=st.session_state.current_page,
            on_change=update_slider
        )

    # Prev/Next Buttons
    c_prev, c_info, c_next = st.columns([1, 2, 1])
    
    with c_prev:
        if st.button("⬅️ Previous"):
            if st.session_state.current_page > 0:
                st.session_state.current_page -= 1
                st.rerun()
                
    with c_next:
        if st.button("Next ➡️"):
            if st.session_state.current_page < total_pages - 1:
                st.session_state.current_page += 1
                st.rerun()

    # --- Content Display ---
    
    # Get current text
    current_text = st.session_state.pdf_text[st.session_state.current_page]
    
    st.markdown(f"### Page {st.session_state.current_page + 1} of {total_pages}")
    
    # Audio Player
    audio_bytes = generate_audio_bytes(current_text)
    if audio_bytes:
        # Render custom player with speed control
        st.markdown(get_audio_player_html(audio_bytes, speed), unsafe_allow_html=True)
    else:
        st.warning("No text to read on this page.")

    # Text Display
    st.markdown(f'<div class="main-text">{current_text}</div>', unsafe_allow_html=True)

else:
    st.markdown("### 👋 Welcome! Upload a PDF in the sidebar to start reading.")
