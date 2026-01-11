import streamlit as st
import PyPDF2
from gtts import gTTS
import io

# --- 1. App Setup ---
st.set_page_config(page_title="Simple eBook Reader")
st.title("📖 Simple eBook Reader")

# --- 2. Initialize State (The Memory) ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

# --- 3. File Uploader ---
uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file is not None:
    # Read the PDF
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    total_pages = len(pdf_reader.pages)
    
    # --- 4. Navigation Buttons ---
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous"):
            if st.session_state.current_page > 0:
                st.session_state.current_page -= 1
                st.rerun()

    with col3:
        if st.button("Next ➡️"):
            if st.session_state.current_page < total_pages - 1:
                st.session_state.current_page += 1
                st.rerun()

    # --- 5. Display Content ---
    st.markdown(f"### Page {st.session_state.current_page + 1} of {total_pages}")
    
    # Extract text for the current page
    page = pdf_reader.pages[st.session_state.current_page]
    text = page.extract_text()
    
    if text:
        # A. Create Audio
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        
        # B. Play Audio (This player resets every time text changes)
        st.audio(fp, format='audio/mp3', start_time=0)
        
        # C. Show Text
        st.info(text)
    else:
        st.warning("No readable text found on this page.")

else:
    st.write("Please upload a PDF to start.")
