import streamlit as st
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from vertexai.generative_models import GenerativeModel, Part
from google.oauth2 import service_account
from PIL import Image
import json

# --- 1. SETUP ---
st.set_page_config(page_title="BrandScout Director", page_icon="🎨", layout="wide")
st.markdown("""<style>.stApp { background-color: #0E1117; color: #FAFAFA; } .stButton>button { background-color: #FF4B4B; color: white; border-radius: 6px; width: 100%; }</style>""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION (The Fix) ---
try:
    # UPDATED: This now looks for the 'gcp_service_account' table you just saved
    if "gcp_service_account" in st.secrets:
        key_info = st.secrets["gcp_service_account"]
    
    # Fallback for the old method
    elif "GOOGLE_JSON" in st.secrets:
        key_info = json.loads(st.secrets["GOOGLE_JSON"])
        
    else:
        st.error("🚨 Critical Error: No secrets found. Please add [gcp_service_account] to your Streamlit Secrets.")
        st.stop()

    # Connect to Google
    creds = service_account.Credentials.from_service_account_info(key_info)
    vertexai.init(project=key_info["project_id"], location="us-central1", credentials=creds)

except Exception as e:
    st.error(f"Auth Connection Error: {e}")
    st.stop()

# --- 3. AI FUNCTIONS ---

def analyze_style(reference_files):
    """Gemini 1.5 Flash analyzes the uploaded style."""
    model = GenerativeModel("gemini-1.5-flash-001")
    prompt = """
    You are an Art Director. Analyze these reference images.
    Describe the visual style for a photographer.
    Focus on: Lighting (cinematic, soft, neon), Texture, Composition, and Colors.
    Output ONE concise paragraph starting with 'A photorealistic product shot...'
    """
    parts = [prompt]
    for uploaded_file in reference_files:
        parts.append(Part.from_data(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
    
    return model.generate_content(parts).text

def generate_mockup(style_desc, logo):
    """Imagen 3 generates the image."""
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
    prompt = f"{style_desc} The product features a clean logo centered on the packaging. 8k, photorealistic."
    return model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="16:9")[0]._pil_image

def composite_logo(bg, logo):
    """Simple overlay to ensure logo visibility."""
    bg = bg.convert("RGBA")
    logo = logo.convert("RGBA")
    target_w = int(bg.width * 0.25)
    ratio = target_w / logo.width
    logo = logo.resize((target_w, int(logo.height * ratio)), Image.Resampling.LANCZOS)
    bg.paste(logo, ((bg.width - logo.width)//2, (bg.height - logo.height)//2), logo)
    return bg

# --- 4. UI ---
st.title("🎨 BrandScout: Director Mode")
st.info("Upload your Logo + Style Screenshots.")

col1, col2 = st.columns([1, 2])
with col1:
    logo_file = st.file_uploader("1. Logo", type=["png", "jpg"])
    ref_files = st.file_uploader("2. Style Refs", type=["png", "jpg"], accept_multiple_files=True)
    go = st.button("Generate")

with col2:
    if go and logo_file and ref_files:
        with st.status("🎨 Designing...", expanded=True):
            user_logo = Image.open(logo_file)
            style = analyze_style(ref_files)
            st.write(f"**Style:** {style}")
            bg = generate_mockup(style, user_logo)
            final = composite_logo(bg, user_logo)
            st.image(final, use_column_width=True)
