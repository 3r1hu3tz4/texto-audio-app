
# Texto → Audio (Multi-idioma) — Streamlit

Convierte texto (pegado o desde archivos `.txt`, `.pdf`, `.docx`) a audio `.mp3` en varios idiomas (es, en, fr, it, pt, ru, zh-CN, ko).

## Requisitos
- Python 3.10+
- Conexión a internet (gTTS)

## Instalación
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar
```bash
streamlit run app.py
```

Se abrirá en tu navegador (generalmente http://localhost:8501).

## Uso
1. Sube un archivo `.txt`, `.pdf` o `.docx`, o pega texto en el cuadro.
2. Elige el idioma.
3. Haz clic en **Generar audio (.mp3)**.
4. Reproduce el audio en la página o descárgalo.

## Notas
- Si el PDF es escaneado (solo imagen), primero aplica OCR.
- El MP3 funciona en iOS, Android, Huawei y navegadores web.
