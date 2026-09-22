import os
import time
import random
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

# --- KONFIGURASI API KEY ---
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
# Tambahkan OpenRouter API Key (opsional, untuk fallback)
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")

if not GROQ_API_KEY or not GEMINI_API_KEY:
    st.error("⚠️ API Key untuk Groq atau Gemini belum dikonfigurasi!")
    st.stop()

# --- INISIALISASI CLIENT ---
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "openai/gpt-oss-120b"

# Daftar model Gemini (Fallback chain internal Google)
# Gunakan model yang stabil (GA) sebagai utama
GEMINI_MODEL_PRIMARY = "gemini-3.5-flash" # Stabil & GA[reference:5]
GEMINI_MODEL_FALLBACK = "gemini-3.1-flash-lite" # Alternatif ringan

# Konfigurasi OpenRouter sebagai fallback terakhir
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Model yang tersedia di OpenRouter (contoh: Qwen atau model Gemini lainnya)
OPENROUTER_MODEL = "google/gemini-3.5-flash" 

st.title("🏥 AI Medical Content Planner RSPUR")
st.markdown(f"Ditenagai Groq (`{GROQ_MODEL}`) & Gemini (Fallback Chain)")

# --- FUNGSI PEMANGGILAN API GEMINI DENGAN RETRY & FALLBACK ---
def call_gemini(prompt: str) -> str:
    """Memanggil Gemini dengan strategi retry dan fallback berlapis."""
    
    # 1. Coba Model Utama (Gemini 3.5 Flash) dengan Retry
    for attempt in range(1, 4): # Maksimal 3 kali percobaan
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_PRIMARY}:generateContent"
            r = requests.post(
                url,
                headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}},
                timeout=120,
            )
            
            if r.status_code == 200:
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            
            if r.status_code in (503, 429): # Jika server sibuk atau limit
                wait = (2 ** attempt) + random.uniform(0, 1) # Exponential backoff + jitter[reference:6]
                st.write(f"⏳ Model `{GEMINI_MODEL_PRIMARY}` sibuk (HTTP {r.status_code}). Mencoba lagi dalam {wait:.1f}s... (Percobaan {attempt}/3)")
                time.sleep(wait)
                continue
            
            r.raise_for_status() # Error lain (misal 400, 401) langsung diangkat

        except Exception as e:
            st.write(f"⚠️ Terjadi kesalahan pada model `{GEMINI_MODEL_PRIMARY}`: {e}. Mencoba fallback...")
            break # Keluar dari loop retry, lanjut ke fallback

    # 2. Jika Model Utama Gagal, Coba Model Fallback Internal Google
    st.write(f"🔄 Beralih ke model fallback: `{GEMINI_MODEL_FALLBACK}`...")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_FALLBACK}:generateContent"
        r = requests.post(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}},
            timeout=120,
        )
        if r.status_code == 200:
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        r.raise_for_status()
    except Exception as e:
        st.write(f"⚠️ Model fallback internal gagal: {e}")

    # 3. Jika Semua Gagal, Coba OpenRouter (Jika API Key Tersedia)
    if OPENROUTER_API_KEY:
        st.write("🔄 Mencoba jalur terakhir via OpenRouter...")
        try:
            r = requests.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}]},
                timeout=120,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            r.raise_for_status()
        except Exception as e:
            st.error(f"❌ Semua jalur gagal. Error terakhir dari OpenRouter: {e}")
            raise RuntimeError("Semua penyedia AI sedang sibuk. Silakan coba lagi nanti.")
    else:
        st.warning("⚠️ OpenRouter API Key tidak diatur. Tidak ada fallback eksternal.")
        raise RuntimeError("Model Gemini utama dan fallback internal gagal.")

# --- FORM & LOGIKA UTAMA ---
with st.form("content_form"):
    st.subheader("⚙️ Pengaturan Konten")
    topik = st.text_area("🎯 Topik / Kampanye Medis:", placeholder="Contoh: Buat konten kalender fokus pada jantung, dari 28 sep - 4 okt 2026...")
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
                        {"role": "system", "content": "Anda adalah analis riset medis dan humas rumah sakit berpengalaman."},
                        {"role": "user", "content": f"Analisis tren dan berikan poin-poin kampanye kesehatan profesional untuk topik berikut: {topik}"}
                    ],
                    temperature=0.7,
                )
                analisis_tren = groq_response.choices[0].message.content

                st.write("✍️ Menyusun naskah via Gemini (dengan strategi fallback)...")
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
