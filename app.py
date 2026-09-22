import os
import requests
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Medical Content Planner RSPUR",
    page_icon="🏥",
    layout="wide"
)

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY or not GEMINI_API_KEY:
    st.error("⚠️ API Key untuk Groq atau Gemini belum dikonfigurasi!")
    st.stop()

groq_client = Groq(api_key=GROQ_API_KEY)

GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_MODEL = "gemini-3.6-flash"

st.title("🏥 AI Medical Content Planner RSPUR")
st.markdown(
    f"Ditenagai Groq (`{GROQ_MODEL}`) & Gemini (`{GEMINI_MODEL}`) via REST API"
)

def call_gemini(prompt: str) -> str:
    """Panggil Gemini via REST API (tanpa SDK google-genai)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )
    r = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
            },
        },
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

with st.form("content_form"):
    st.subheader("⚙️ Pengaturan Konten")
    topik = st.text_area(
        "🎯 Topik / Kampanye Medis:",
        placeholder="Contoh: Buat konten kalender fokus pada jantung, dari 28 sep - 4 okt 2026..."
    )
    submitted = st.form_submit_button("🚀 Buat Konten Sekarang")

if submitted:
    if not topik.strip():
        st.warning("⚠️ Mohon masukkan topik terlebih dahulu!")
    else:
        with st.status("🧠 Memproses Data AI...", expanded=True) as status:
            try:
                st.write(f"🔍 Analisa tren medis via Groq (`{GROQ_MODEL}`)...")
                groq_response = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "Anda adalah analis riset medis dan humas rumah sakit berpengalaman."
                        },
                        {
                            "role": "user",
                            "content": f"Analisis tren dan berikan poin-poin kampanye kesehatan profesional untuk topik berikut: {topik}"
                        }
                    ],
                    temperature=0.7,
                )
                analisis_tren = groq_response.choices[0].message.content

                st.write(f"✍️ Menyusun naskah via Gemini (`{GEMINI_MODEL}`)...")
                prompt = f"""
Berdasarkan analisis tren berikut:
{analisis_tren}

Buatlah rencana konten atau naskah profesional rumah sakit untuk topik: "{topik}".
Sajikan dengan struktur yang jelas, rapi, dan informatif ala standar humas medis RSPUR.
"""
                hasil_konten = call_gemini(prompt)

                status.update(label="✅ Konten Berhasil Dibuat!", state="complete", expanded=False)

                st.markdown("---")
                st.subheader("📄 Hasil Generasi Konten:")
                st.markdown(hasil_konten)

            except Exception as e:
                status.update(label="❌ Terjadi Kesalahan Sistem!", state="error", expanded=True)
                st.error(f"Detail Error: {str(e)}")
