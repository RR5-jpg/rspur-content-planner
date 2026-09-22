import os
import streamlit as st
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="AI Medical Content Planner RSPUR",
    page_icon="🏥",
    layout="wide"
)

# Ambil API Key dari st.secrets atau environment lokal
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

# Validasi API Key
if not GROQ_API_KEY or not GEMINI_API_KEY:
    st.error("⚠️ API Key untuk Groq atau Gemini belum dikonfigurasi dengan benar!")
    st.stop()

# Inisialisasi Client AI
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# Menggunakan model aktif yang stabil
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🏥 AI Medical Content Planner RSPUR")
st.markdown("Ditenagai oleh Groq (Llama 3.3) untuk Analisa Tren & Gemini 1.5 untuk Copywriting Medis")

with st.form("content_form"):
    st.subheader("⚙️ Pengaturan Konten")
    topik = st.text_area("🎯 Topik / Kampanye Medis:", placeholder="Contoh: Buat konten kalender fokus pada jantung, dari 28 sep - 4 okt 2026...")
    submitted = st.form_submit_button("🚀 Buat Konten Sekarang")

if submitted:
    if not topik.strip():
        st.warning("⚠️ Mohon masukkan topik atau kampanye terlebih dahulu!")
    else:
        with st.status("🧠 Memproses Data AI...", expanded=True) as status:
            try:
                st.write("🔍 Mengambil data tren medis via Groq (Llama-3.3)...")
                groq_response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Anda adalah analis riset medis dan humas rumah sakit berpengalaman."},
                        {"role": "user", "content": f"Analisis tren dan berikan poin-poin kampanye kesehatan profesional untuk topik berikut: {topik}"}
                    ],
                    temperature=0.7,
                )
                analisis_tren = groq_response.choices[0].message.content

                st.write("✍️ Menyusun naskah dan validasi fasilitas via Gemini...")
                prompt = f"""
                Berdasarkan analisis tren berikut:
                {analisis_tren}
                
                Buatlah rencana konten atau naskah profesional rumah sakit untuk topik: "{topik}".
                Sajikan dengan struktur yang jelas, rapi, dan informatif ala standar humas medis RSPUR.
                """
                
                response = gemini_model.generate_content(prompt)
                hasil_konten = response.text

                status.update(label="✅ Konten Berhasil Dibuat!", state="complete", expanded=False)
                
                st.markdown("---")
                st.subheader("📄 Hasil Generasi Konten:")
                st.markdown(hasil_konten)

            except Exception as e:
                status.update(label="❌ Terjadi Kesalahan Sistem!", state="error", expanded=True)
                st.error(f"Detail Error: {str(e)}")

