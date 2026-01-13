import streamlit as st
import PyPDF2
import edge_tts
import asyncio
import base64
import streamlit.components.v1 as components

# --- 1. App Configuration ---
st.set_page_config(page_title="Turbo Reader", layout="centered")

# Custom CSS for Mobile
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        padding: 16px;
        font-size: 20px;
        border-radius: 12px;
        margin-bottom: 8px;
        background-color: #f0f2f6; 
        border: 1px solid #d1d5db;
    }
    div.stButton > button:active {
        background-color: #e5e7eb;
        border-color: #6366f1;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Turbo eBook Reader")

# --- 2. Session State Management ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'audio_cache' not in st.session_state:
    st.session_state.audio_cache = {}  # Stores audio so we don't re-download
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = []     # Stores all text so we don't re-read PDF

# --- 3. Settings ---
col1, col2 = st.columns(2)
with col1:
    speed_mode = st.selectbox("Speed", ["Normal", "Fast (+20%)", "Turbo (+50%)"], index=1)
with col2:
    auto_play = st.checkbox("Auto-Turn Page", value=True)

rate_str = "+0%"
if speed_mode == "Fast (+20%)": rate_str = "+20%"
elif speed_mode == "Turbo (+50%)": rate_str = "+50%"

# --- 4. Async Audio Engine ---
async def get_audio_base64(text, rate):
    # Generates audio and returns it as a base64 string (memory only, no files)
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate=rate)
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
    return base64.b64encode(audio_bytes).decode()

# --- 5. File Upload & Processing ---
uploaded_file = st.file_uploader("📂 Upload PDF (Loads once, stays fast)", type="pdf")

if uploaded_file is not None:
    # A. One-time processing (Fixes the "4 page limit" bug)
    if not st.session_state.pdf_text:
        with st.spinner("Processing PDF..."):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            # Store ALL pages in memory immediately
            for page in pdf_reader.pages:
                txt = page.extract_text()
                st.session_state.pdf_text.append(txt if txt else "")
    
    total_pages = len(st.session_state.pdf_text)
    current_page = st.session_state.current_page
    
    # --- 6. Navigation Logic ---
    def go_next():
        if st.session_state.current_page < total_pages - 1:
            st.session_state.current_page += 1
    def go_prev():
        if st.session_state.current_page > 0:
            st.session_state.current_page -= 1
            
    # Page Slider (Jump to any page)
    st.session_state.current_page = st.slider("Go to Page", 1, total_pages, st.session_state.current_page + 1) - 1

    # --- 7. Main Audio Logic (The "Cache Ahead" Trick) ---
    
    # Get Current Page Text
    text_current = st.session_state.pdf_text[current_page]
    
    if text_current:
        # Step A: Get Current Audio (Check cache first)
        cache_key = f"{current_page}_{rate_str}"
        
        if cache_key not in st.session_state.audio_cache:
            with st.spinner(f"Generating Page {current_page + 1}..."):
                st.session_state.audio_cache[cache_key] = asyncio.run(get_audio_base64(text_current, rate_str))
        
        b64_audio = st.session_state.audio_cache[cache_key]

        # Step B: Render Player
        # We embed the next_page logic directly into the audio player
        player_html = f"""
            <audio id="player" controls autoplay style="width: 100%;">
                <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
            </audio>
            <script>
                var audio = document.getElementById("player");
                audio.onended = function() {{
                    const nextBtn = window.parent.document.querySelector('button[aria-label="Next Page"]');
                    if (nextBtn) {{ nextBtn.click(); }}
                    else {{
                        // Fallback search for button text
                        var buttons = window.parent.document.getElementsByTagName('button');
                        for (var i = 0; i < buttons.length; i++) {{
                            if (buttons[i].innerText.includes("Next")) {{ buttons[i].click(); break; }}
                        }}
                    }}
                }};
            </script>
        """
        components.html(player_html, height=50)

        # Step C: PRE-FETCH NEXT PAGE (The Secret Sauce)
        # While you are listening to Page N, we download Page N+1 silently.
        if current_page < total_pages - 1:
            next_p = current_page + 1
            text_next = st.session_state.pdf_text[next_p]
            next_key = f"{next_p}_{rate_str}"
            
            if next_key not in st.session_state.audio_cache and text_next:
                # We run this SILENTLY (no spinner)
                try:
                    st.session_state.audio_cache[next_key] = asyncio.run(get_audio_base64(text_next, rate_str))
                    # print(f"Buffered Page {next_p}") # Debug
                except:
                    pass

    # --- 8. Navigation Buttons ---
    c1, c2 = st.columns(2)
    with c1: st.button("⬅️ Prev", on_click=go_prev)
    with c2: st.button("Next ➡️", on_click=go_next, args=(), key="next_btn", help="Next Page")

    st.markdown("---")
    st.markdown(text_current if text_current else "*No text found on this page.*")

else:
    # Reset buffer on new load
    if st.session_state.pdf_text:
        st.session_state.pdf_text = []
        st.session_state.audio_cache = {}
