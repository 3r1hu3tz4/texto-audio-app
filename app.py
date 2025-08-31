import io, os, tempfile, time, uuid, threading
import streamlit as st

from gtts import gTTS
from pypdf import PdfReader
from docx import Document
from pydub import AudioSegment
from pydub.utils import which

# Asegurar que pydub encuentre ffmpeg y ffprobe
AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe = which("ffprobe")

# =========================
# PRESENCIA / USUARIOS ACTIVOS (LOCAL)
# =========================
@st.cache_resource
def get_presence_registry():
    # Persistente mientras el proceso vive (sirve en local y en 1 réplica)
    return {"sessions": {}}, threading.Lock()

# Identificador de sesión del visitante
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

def update_presence(timeout_sec: int = 120) -> int:
    """Registra un 'latido' de esta sesión y limpia sesiones inactivas."""
    registry, lock = get_presence_registry()
    sid = st.session_state.session_id
    now = time.time()
    with lock:
        registry["sessions"][sid] = now
        # Elimina sesiones sin actividad en los últimos N segundos
        for s, ts in list(registry["sessions"].items()):
            if now - ts > timeout_sec:
                del registry["sessions"][s]
        active = len(registry["sessions"])
    return active

active_users = update_presence()  # actualiza y devuelve activos

# =========================
# UI: Banner + contador global (externo) + contador local (activo ahora)
# =========================
st.markdown(
    """
    <div style="text-align:center;">
        <h2>🔊 Texto → Audio (Multi-idioma, textos largos)</h2>
        <p>Convierte texto o archivos en audio MP3 compatible con iOS, Android, Huawei y navegadores web.</p>
        <h3>👥 Contador de visitas (global)</h3>
        <a href="https://www.hitwebcounter.com" target="_blank">
            <img src="https://hitwebcounter.com/counter/counter.php?page=1234567&style=0006&nbdigits=5&type=page&initCount=0" 
                 title="Visitas" alt="contador" border="0" />
        </a>
        <hr>
    </div>
    """,
    unsafe_allow_html=True
)

# Badge de usuarios activos locales (últimos 2 minutos)
st.markdown(
    f"""
    <div style="text-align:center; margin:10px 0 20px 0;">
      <span style="display:inline-block; background:#e8f5e9; color:#1b5e20; 
                   padding:6px 12px; border-radius:999px; font-weight:600;">
        Usuarios activos ahora: {active_users}
      </span>
    </div>
    """,
    unsafe_allow_html=True
)

# Botón para refrescar el contador manualmente (vuelve a ejecutar el script)
if st.button("🔄 Actualizar contador de usuarios activos"):
    active_users = update_presence()
    st.experimental_rerun()

# =========================
# Lógica de Texto → Audio
# =========================
LANG_OPTS = {
    "Español": "es",
    "Inglés": "en",
    "Francés": "fr",
    "Italiano": "it",
    "Portugués": "pt",
    "Ruso": "ru",
    "Chino (Mandarín)": "zh-CN",
    "Coreano": "ko",
}

SAFE_CHUNK = 9000
HARD_MAX_CHARS = 200_000  # soporta textos largos

def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    return "\n".join([page.extract_text() or "" for page in reader.pages]).strip()

def extract_text_from_docx(file) -> str:
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs).strip()

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join([ln.strip() for ln in text.split("\n") if ln.strip()])

def chunk_text(text, size=SAFE_CHUNK):
    return [text[i:i+size] for i in range(0, len(text), size)]

def synthesize_long_text_to_mp3(text, lang_code, slow=False) -> bytes:
    if len(text) > HARD_MAX_CHARS:
        text = text[:HARD_MAX_CHARS]

    chunks = chunk_text(text, SAFE_CHUNK)

    with tempfile.TemporaryDirectory() as tmpdir:
        parts = []
        for idx, ch in enumerate(chunks, start=1):
            tts = gTTS(text=ch, lang=lang_code, slow=slow)
            part_path = os.path.join(tmpdir, f"part_{idx:04d}.mp3")
            tts.save(part_path)
            parts.append(part_path)
            st.write(f"✔️ Fragmento {idx}/{len(chunks)} generado")

        combined = AudioSegment.silent(duration=0)
        for p in parts:
            combined += AudioSegment.from_mp3(p)

        out = io.BytesIO()
        combined.export(out, format="mp3", bitrate="192k")
        out.seek(0)
        return out.read()

uploaded = st.file_uploader("📂 Sube un archivo (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])

text_default = ""
if uploaded:
    suffix = uploaded.name.split(".")[-1].lower()
    if suffix == "pdf":
        text_default = extract_text_from_pdf(uploaded)
    elif suffix == "docx":
        text_default = extract_text_from_docx(uploaded)
    else:
        text_default = uploaded.read().decode("utf-8", errors="ignore")

text_input = st.text_area(
    "✍️ Texto a convertir",
    value=text_default,
    height=220,
    placeholder="Pega aquí tu texto…"
)

col1, col2 = st.columns([2,1])
with col1:
    lang_name = st.selectbox("Idioma", list(LANG_OPTS.keys()), index=0)
with col2:
    slow = st.toggle("Voz lenta", value=False)

if len(text_input) > HARD_MAX_CHARS:
    st.warning(f"⚠️ El texto supera {HARD_MAX_CHARS} caracteres. Se recortará automáticamente.")

if st.button("🎧 Generar audio MP3", type="primary", use_container_width=True):
    text_input = clean_text(text_input or "")
    if not text_input:
        st.error("Por favor ingresa o sube texto.")
    else:
        try:
            code = LANG_OPTS[lang_name]
            out_bytes = synthesize_long_text_to_mp3(text_input, code, slow=slow)
            st.success("✅ ¡Audio generado!")
            st.audio(out_bytes, format="audio/mp3")
            st.download_button(
                label="⬇️ Descargar MP3",
                data=out_bytes,
                file_name="audio_tts.mp3",
                mime="audio/mpeg",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

# =========================
# Botón de Mercado Libre
# =========================
st.markdown(
    """
    <div style="text-align:center; margin-top:30px;">
        <a href="https://mercadolibre.com/sec/2TWNb1N" 
           target="_blank" 
           style="background-color:#ffe600; color:black; padding:10px 20px; text-decoration:none; font-weight:bold; border-radius:5px;">
           🛒 Ir a Mercado Libre
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

