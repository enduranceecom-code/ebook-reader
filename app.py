import streamlit as st
import PyPDF2
import edge_tts
import asyncio
import base64
import streamlit.components.v1 as components

# --- 1. App Setup ---
st.set_page_config(page_title="Lightweight Reader", layout="centered")

# Custom CSS
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

st.title("🪶 Lightweight eBook Reader")

# --- 2. Session State ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'audio_cache' not in st.session_state:
    st.session_state.audio_cache = {} # Cache audio, not text

# --- 3. Settings ---
col1, col2 = st.columns(2)
with col1:
    speed_mode = st.selectbox("Speed", ["Normal", "Fast (+20%)", "Turbo (+50%)"], index=1)
with col2:
    # Option to turn off auto-play if it glitches
    auto_play = st.checkbox("Auto-Turn Page", value=True)

rate_str = "+0%"
if speed_mode == "Fast (+20%)": rate_str = "+20%"
elif speed_mode == "Turbo (+50%)": rate_str = "+50%"

# --- 4. Async Audio Function ---
async def get_audio_base64(text, rate):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate=rate)
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
    return base64.b64encode(audio_bytes).decode()

# --- 5. File Upload ---
uploaded_file = st.file_uploader("📂 Upload PDF", type="pdf")

if uploaded_file is not None:
    # Create the reader Object (But DON'T read the text yet)
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    total_pages = len(pdf_reader.pages)
    
    # Show the total page count immediately to confirm file is good
    st.write(f"**Book Loaded:** {total_pages} pages detected.")

    # --- Navigation ---
    def go_next():
        if st.session_state.current_page < total_pages - 1:
            st.session_state.current_page += 1
            # Clear old audio cache to save memory
            st.session_state.audio_cache = {}

    def go_prev():
        if st.session_state.current_page > 0:
            st.session_state.current_page -= 1
            st.session_state.audio_cache = {}

    # Slider Jump
    st.session_state.current_page = st.slider(
        "Page Selector", 1, total_pages, st.session_state.current_page + 1
    ) - 1

    current_page_idx = st.session_state.current_page
    
    # --- 6. READ ONLY CURRENT PAGE ---
    # This is the fix. We only extract extracting text for NOW.
    page_obj = pdf_reader.pages[current_page_idx]
    text_current = page_obj.extract_text()
    
    if text_current:
        # A. Generate Audio for Current Page
        cache_key = f"{current_page_idx}_{rate_str}"
        
        if cache_key not in st.session_state.audio_cache:
            with st.spinner(f"Reading Page {current_page_idx + 1}..."):
                st.session_state.audio_cache[cache_key] = asyncio.run(get_audio_base64(text_current, rate_str))
        
        b64_audio = st.session_state.audio_cache[cache_key]

        # B. Render Player
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
                        var buttons = window.parent.document.getElementsByTagName('button');
                        for (var i = 0; i < buttons.length; i++) {{
                            if (buttons[i].innerText.includes("Next")) {{ buttons[i].click(); break; }}
                        }}
                    }}
                }};
            </script>
        """
        components.html(player_html, height=50)
        
        # C. PRE-FETCH NEXT PAGE (Secretly)
        # We only look ahead 1 page.
        if current_page_idx < total_pages - 1:
            try:
                next_page_idx = current_page_idx + 1
                next_cache_key = f"{next_page_idx}_{rate_str}"
                
                # Check if we already have it
                if next_cache_key not in st.session_state.audio_cache:
                    text_next = pdf_reader.pages[next_page_idx].extract_text()
                    if text_next:
                        # Silently generate audio
                        st.session_state.audio_cache[next_cache_key] = asyncio.run(get_audio_base64(text_next, rate_str))
            except:
                pass 

    # --- Controls ---
    c1, c2 = st.columns(2)
    with c1: st.button("⬅️ Prev", on_click=go_prev)
    with c2: st.button("Next ➡️", on_click=go_next, args=(), key="next_btn", help="Next Page")

    st.markdown("---")
    st.markdown(text_current if text_current else "No text found.")

else:
    st.info("👆 Upload PDF to start")
