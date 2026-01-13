import streamlit as st
import PyPDF2
import edge_tts
import asyncio
import base64
import os
import streamlit.components.v1 as components

# --- 1. App Setup ---
st.set_page_config(page_title="Continuous Reader", layout="centered")

# Custom CSS for bigger buttons on mobile
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        padding: 20px;
        font-size: 20px;
        border-radius: 12px;
        margin-bottom: 10px;
        background-color: #f0f2f6; 
        border: 1px solid #d1d5db;
    }
    div.stButton > button:active {
        background-color: #e5e7eb;
        border-color: #6366f1;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🔄 Continuous Play Reader")

# --- 2. Initialize State ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'auto_play' not in st.session_state:
    st.session_state.auto_play = True  # Default to ON

# --- 3. Settings ---
col_set1, col_set2 = st.columns(2)
with col_set1:
    speed_mode = st.selectbox(
        "Reading Speed", 
        ["Normal", "Fast (+20%)", "Super Fast (+50%)"],
        index=1
    )
with col_set2:
    st.session_state.auto_play = st.checkbox("Auto-Play Next Page", value=True)

# Map selection to rate
rate_str = "+0%"
if speed_mode == "Fast (+20%)":
    rate_str = "+20%"
elif speed_mode == "Super Fast (+50%)":
    rate_str = "+50%"

# --- 4. File Upload ---
uploaded_file = st.file_uploader("📂 Tap here to upload PDF", type="pdf")

# --- 5. Async Audio Generator ---
async def generate_audio_file(text, rate):
    # Uses Microsoft Edge's high-quality neural voice
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate=rate)
    filename = f"audio_{st.session_state.current_page}.mp3"
    await communicate.save(filename)
    return filename

# --- 6. The "Auto-Next" Audio Player Logic ---
def get_autoplay_html(audio_file_path):
    # Convert audio to base64 to embed it directly in HTML
    with open(audio_file_path, "rb") as f:
        audio_bytes = f.read()
    b64 = base64.b64encode(audio_bytes).decode()
    
    # HTML that plays audio and clicks 'Next' when done
    return f"""
        <audio id="audio_player" controls autoplay style="width: 100%;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        
        <script>
            var audio = document.getElementById("audio_player");
            
            // When audio finishes...
            audio.onended = function() {{
                console.log("Audio ended. Triggering next page...");
                
                // Find buttons on the page
                var buttons = window.parent.document.getElementsByTagName('button');
                
                // Click the one that says "Next"
                for (var i = 0; i < buttons.length; i++) {{
                    if (buttons[i].innerText.includes("Next")) {{
                        buttons[i].click();
                        break;
                    }}
                }}
            }};
        </script>
    """

if uploaded_file is not None:
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    total_pages = len(pdf_reader.pages)
    
    # --- Navigation Logic ---
    def go_next():
        if st.session_state.current_page < total_pages - 1:
            st.session_state.current_page += 1

    def go_prev():
        if st.session_state.current_page > 0:
            st.session_state.current_page -= 1

    # Buttons
    c1, c2 = st.columns(2)
    with c1:
        st.button("⬅️ Prev", on_click=go_prev)
    with c2:
        # We give this button a specific label so our JavaScript can find it
        st.button("Next ➡️", on_click=go_next)

    st.divider()

    # --- Page Content ---
    st.caption(f"Page {st.session_state.current_page + 1} of {total_pages}")
    
    page = pdf_reader.pages[st.session_state.current_page]
    text = page.extract_text()
    
    if text:
        # Generate Audio
        try:
            # Generate the file using asyncio
            audio_path = asyncio.run(generate_audio_file(text, rate_str))
            
            # Render the Custom Player
            st.components.v1.html(get_autoplay_html(audio_path), height=60)
            
            # Cleanup temp file
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
        except Exception as e:
            st.error(f"Error: {e}")

        # Show Text
        st.markdown(text)
    else:
        st.warning("No readable text on this page.")

else:
    st.info("👆 Upload PDF to start")
