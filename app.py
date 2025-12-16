import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.preview.vision_models import ImageGenerationModel
from google.oauth2 import service_account
from PIL import Image
import json

# --- 1. SETUP ---
st.set_page_config(page_title="BrandScout Director", page_icon="🎨", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton>button { background-color: #FF4B4B; color: white; border-radius: 6px; height: 3em; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
try:
    # We load the secret from the GOOGLE_JSON block
    if "GOOGLE_JSON" in st.secrets:
        key_info = json.loads(st.secrets["GOOGLE_JSON"])
        creds = service_account.Credentials.from_service_account_info(key_info)
        vertexai.init(project=key_info["project_id"], location="us-central1", credentials=creds)
    else:
        st.error("⚠️ Secrets not found. Please add GOOGLE_JSON to Streamlit Secrets.")
        st.stop()
except Exception as e:
    st.error(f"Auth Error: {e}")
    st.stop()

# --- 3. AI FUNCTIONS ---

def analyze_style(reference_files):
    """Uses Gemini 1.5 Flash to 'see' the style of uploaded images."""
    model = GenerativeModel("gemini-1.5-flash-001")
    
    prompt = """
    You are an Art Director. Analyze these reference images.
    Describe the visual style in a way that can be used as a prompt for an image generator.
    Focus on: Lighting type (cinematic, natural, neon), Texture (matte, glossy, wood), 
    Composition (minimalist, cluttered, centered), and Color Palette.
    Output ONE concise paragraph describing this style. Start with "A photorealistic product shot..."
    """
    
    parts = [prompt]
    for uploaded_file in reference_files:
        parts.append(Part.from_data(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
    
    response = model.generate_content(parts)
    return response.text

def generate_mockup(style_description, logo_image):
    """Generates the final image using Imagen 3."""
    try:
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        
        final_prompt = f"""
        {style_description}
        The product features a clean, legible logo centered on the packaging.
        High resolution, 8k, highly detailed, professional photography.
        """
        
        response = model.generate_images(prompt=final_prompt, number_of_images=1, aspect_ratio="16:9")
        return response[0]._pil_image
    except Exception as e:
        st.error(f"Generation Error: {e}")
        return None

def composite_logo(background, logo):
    """Stamps the logo on top."""
    bg = background.convert("RGBA")
    logo = logo.convert("RGBA")
    
    # Resize logo to 25% of background width
    target_w = int(bg.width * 0.25)
    ratio = target_w / logo.width
    target_h = int(logo.height * ratio)
    logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Center
    x = (bg.width - logo.width) // 2
    y = (bg.height - logo.height) // 2
    bg.paste(logo, (x, y), logo)
    return bg

# --- 4. UI ---
st.title("🎨 BrandScout: Director Mode")
st.info("Upload your Logo and 1-3 Style References (Screenshots).")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Inputs")
    logo_file = st.file_uploader("1. Upload Logo (PNG)", type=["png", "jpg"], key="logo")
    ref_files = st.file_uploader("2. Style References", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="refs")
    
    generate_btn = st.button("🚀 Generate Mockup")

with col2:
    if generate_btn:
        if not logo_file or not ref_files:
            st.warning("⚠️ Please upload both a Logo and Reference Images.")
        else:
            user_logo = Image.open(logo_file)
            
            with st.status("👨‍🎨 AI Art Director working...", expanded=True) as status:
                status.write("🧠 Analyzing reference style...")
                style_desc = analyze_style(ref_files)
                st.caption(f"**Extracted Style:** {style_desc}")
                
                status.write("📸 Taking the photo (Imagen 3)...")
                bg = generate_mockup(style_desc, user_logo)
                
                if bg:
                    status.write("🔨 Applying final touches...")
                    final = composite_logo(bg, user_logo)
                    status.update(label="Design Complete!", state="complete", expanded=False)
                    st.image(final, use_column_width=True)
