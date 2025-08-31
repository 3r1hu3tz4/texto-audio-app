
import io
import os
import streamlit as st

from gtts import gTTS
from pypdf import PdfReader
from docx import Document

# -----------------------------
# Configuración básica de la app
# -----------------------------
st.set_page_config(page_title="Texto → Audio (Multi-idioma)", page_icon="🔊", layout="centered")
st.title("🔊 Texto → Audio (Multi‑idioma)")
st.caption("Sube un archivo (.txt, .pdf, .docx) o pega texto. Elige el idioma y genera un audio .mp3 reproducible en web y móviles (iOS/Android/Huawei).")

# -----------------------------
# Utilidades
# -----------------------------
LANG_OPTS = {
    "Español": "es",
    "Inglés": "en",
    "Francés": "fr",
    "Italiano": "it",
    "Portugués": "pt",
    "Ruso": "ru",
    "Chino (Mandarín, China)": "zh-CN",
    "Coreano": "ko",
}

MAX_CHARS = 10000  # límite de seguridad para textos muy largos

def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            pass
    return "\n".join(parts).strip()

def extract_text_from_docx(file) -> str:
    # file puede ser un buffer en memoria
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs).strip()

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # colapsa espacios excesivos
    lines = [ln.strip() for ln in text.split("\n")]
    text = "\n".join([ln for ln in lines if ln != ""])
    return text.strip()

def synthesize_mp3(text: str, lang_code: str) -> bytes:
    # gTTS requiere conexión a internet.
    # Para textos muy largos, gTTS puede tardar. Limitamos longitud.
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
    tts = gTTS(text=text, lang=lang_code, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()

# -----------------------------
# UI
# -----------------------------
with st.expander("➕ Subir archivo (.txt, .pdf, .docx)", expanded=True):
    uploaded = st.file_uploader(
        "Elige un archivo",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=False
    )

text_area_help = "También puedes pegar texto aquí. Si subes un archivo, intentaremos rellenar este cuadro automáticamente con su contenido."
text_default = ""

if uploaded:
    try:
        suffix = (uploaded.name.split(".")[-1] or "").lower()
        if suffix == "pdf":
            text_default = extract_text_from_pdf(uploaded)
        elif suffix == "docx":
            text_default = extract_text_from_docx(uploaded)
        else:  # txt
            text_default = uploaded.read().decode("utf-8", errors="ignore")
        text_default = clean_text(text_default)
        if not text_default:
            st.warning("No se pudo extraer texto del archivo. Puedes copiar/pegar el contenido manualmente.")
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")

text_input = st.text_area(
    "Texto a convertir",
    value=text_default,
    height=220,
    help=text_area_help,
    placeholder="Pega aquí el texto si no subiste archivo…"
)

col1, col2 = st.columns([2,1])
with col1:
    lang_name = st.selectbox(
        "Idioma del audio",
        list(LANG_OPTS.keys()),
        index=0
    )
with col2:
    st.write("")
    st.write("")
    slow = st.toggle("Voz lenta", value=False, help="Activa una voz más lenta.")

# Aviso si está largo
if len(text_input) > MAX_CHARS:
    st.info(f"El texto supera {MAX_CHARS} caracteres. Se recortará automáticamente para evitar errores.")

# -----------------------------
# Acción: Generar audio
# -----------------------------
btn = st.button("🎧 Generar audio (.mp3)", type="primary", use_container_width=True)

if btn:
    text_input = clean_text(text_input or "")
    if not text_input:
        st.error("Por favor ingresa o sube texto para convertir.")
    else:
        try:
            code = LANG_OPTS[lang_name]
            # gTTS no soporta 'slow' continuo muy largo. Para simplificar, usamos una sola llamada.
            # (Si fuera necesario, podríamos trocear por párrafos y unir con pydub/ffmpeg).
            if len(text_input) > MAX_CHARS:
                text_input = text_input[:MAX_CHARS]
            tts = gTTS(text=text_input, lang=code, slow=slow)
            out_bytes = io.BytesIO()
            tts.write_to_fp(out_bytes)
            out_bytes.seek(0)

            file_name = "audio_tts.mp3"
            st.success("¡Audio generado!")
            st.audio(out_bytes.getvalue(), format="audio/mp3")

            st.download_button(
                label="⬇️ Descargar MP3",
                data=out_bytes.getvalue(),
                file_name=file_name,
                mime="audio/mpeg",
                use_container_width=True
            )
            st.caption("El archivo .mp3 es compatible con iOS, Android, Huawei y navegadores web.")
        except Exception as e:
            st.error(f"Ocurrió un error al generar el audio: {e}")

st.markdown("---")
st.markdown("**Sugerencias:** Si tu PDF es escaneado (imagen), conviértelo a texto con OCR antes (por ejemplo, con Google Drive o Adobe Scan).")
