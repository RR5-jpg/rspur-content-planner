import streamlit as st
import google.generativeai as genai
from groq import Groq
import os
from dotenv import load_dotenv
import json
import base64
from io import BytesIO
from PIL import Image
from weasyprint import HTML
from streamlit_drawable_canvas import st_canvas

# Konfigurasi Halaman
st.set_page_config(page_title="AI Medical Content Planner", page_icon="🏥", layout="wide")

# Muat Environment Variables (.env)
load_dotenv()
GROQ_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not GROQ_KEY or not GEMINI_KEY:
    st.error("⚠️ API Key tidak ditemukan. Pastikan file .env sudah dikonfigurasi.")
    st.stop()

# Inisialisasi Klien AI
try:
    groq_client = Groq(api_key=GROQ_KEY)
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-pro')
except Exception as e:
    st.error(f"Gagal memuat sistem AI: {e}")
    st.stop()

# Muat Database Lokal
@st.cache_data
def muat_data_lokal():
    try:
        with open("data_dokter.json", "r") as f: data_dokter = json.load(f)
        with open("data_fasilitas.json", "r") as f: data_fasilitas = json.load(f)
        return data_dokter, data_fasilitas
    except:
        return None, None

data_dokter, data_fasilitas = muat_data_lokal()

# Fungsi Analisa Tren via Groq (Llama-3)
def analisa_tren_groq(topik):
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Anda adalah analis riset medis. Berikan 3 poin singkat tren terkini, peringatan hari besar medis, atau sentimen masyarakat terkait topik yang diberikan."},
                {"role": "user", "content": f"Berikan analisa tren untuk topik: {topik}"}
            ],
            temperature=0.5,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Gagal menarik tren Groq: {e}"

# Fungsi Prompting Ketat Gemini
def rakit_system_prompt(topik, nakes, tone, fasilitas, tren):
    return f"""
Anda adalah Copywriter Medis Senior Humas Rumah Sakit Pertamedika Ummi Rosnati (RSPUR).
Buatkan naskah konten edukasi medis dengan detail berikut:

1. TOPIK: '{topik}'
2. GAYA BAHASA: {tone}
3. NARASUMBER MEDIS: {nakes} (Jadikan beliau sebagai peninjau/perekomendasi layanan).
4. BATASAN FASILITAS (ANTI-OVERCLAIM): {json.dumps(fasilitas['unit_layanan'])}. HANYA tawarkan layanan di daftar 'layanan_tersedia'.
5. INSIGHT TREN TERKINI DARI GROQ: {tren}
6. REFERENSI WAJIB: Kemenkes, PERKI, WHO, atau lembaga resmi terkait.

FORMAT WAJIB (Susun seperti Brief Editorial):
Judul Kampanye: [Judul Menarik]
Funnel: [TOFU / MOFU / BOFU]
Platform: Instagram/Facebook Carousel

--- RANCANGAN SLIDE ---
Slide 1: [Headline/Hook Utama] + [Sub-copy] + [Visual Direction]
Slide 2: [Fakta Medis/Masalah] + [Sub-copy] + [Visual Direction]
Slide 3: [Solusi & Layanan RSPUR] + [Sub-copy] + [Visual Direction]
Slide 4: [Call to Action / Info Pendaftaran via Aplikasi/WA RSPUR] + [Visual Direction]
"""

# UI Sidebar
st.sidebar.header("⚙️ Pengaturan Konten")
uploaded_logo = st.sidebar.file_uploader("🖼️ Unggah Logo RS (PNG/JPG):", type=["png", "jpg"])
logo_b64 = ""
if uploaded_logo:
    logo_b64 = base64.b64encode(uploaded_logo.getvalue()).decode()
    st.sidebar.success("Logo dimuat!")

tone_pilihan = st.sidebar.selectbox("🗣️ Tone of Voice:", ["Empati & Menenangkan", "Urgensi & Siaga", "Profesional & Informatif"])

daftar_spesialis = []
if data_dokter:
    for kat, dr_list in data_dokter["spesialisasi"].items():
        for dr in dr_list: daftar_spesialis.append(f"{dr['nama_lengkap']} ({dr['jabatan']})")
nakes = st.sidebar.selectbox("👨‍⚕️ Pilih Narasumber Medis:", daftar_spesialis)
nakes_manual = st.sidebar.text_input("✏️ Atau Input Manual:")
nakes_final = nakes_manual.strip() if nakes_manual else nakes

# UI Main Area
st.title("🏥 AI Medical Content Planner RSPUR")
st.caption("Ditenagai oleh Groq (Llama 3) untuk Analisa Tren & Gemini 1.5 Pro untuk Copywriting Medis")

topik_input = st.text_input("🎯 Topik / Kampanye Medis:", placeholder="Contoh: Pentingnya Fisioterapi Pasca Cedera Olahraga")

if st.button("🚀 Generate Konten Medis", type="primary"):
    if topik_input:
        with st.status("🧠 Memproses Data AI...", expanded=True) as status:
            st.write("🔍 Mengambil data tren medis via Groq (Llama-3)...")
            tren_data = analisa_tren_groq(topik_input)
            
            st.write("✍️ Menyusun naskah dan validasi fasilitas via Gemini...")
            prompt = rakit_system_prompt(topik_input, nakes_final, tone_pilihan, data_fasilitas, tren_data)
            
            response = gemini_model.generate_content(prompt)
            st.session_state["draf_mentah"] = response.text
            st.session_state["topik_aktif"] = topik_input
            status.update(label="✅ Selesai!", state="complete", expanded=False)
    else:
        st.warning("⚠️ Masukkan topik terlebih dahulu.")

# UI Editor & Ekspor PDF
if "draf_mentah" in st.session_state:
    st.markdown("---")
    st.subheader("📝 Block Editor (Periksa & Edit Naskah)")
    draf_teredit = st.text_area("Sesuaikan isi naskah sebelum finalisasi:", value=st.session_state["draf_mentah"], height=400)
    
    st.markdown("### ✍️ Approval Medis (Tanda Tangan Digital)")
    st.caption("Reviewer / Dokter Spesialis silakan tanda tangan di kotak bawah ini:")
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000",
        background_color="#f8f9fa", height=150, width=400, drawing_mode="freedraw", key="ttd"
    )
    
    ttd_b64 = ""
    if canvas_result.image_data is not None:
        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        ttd_b64 = base64.b64encode(buffered.getvalue()).decode()

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📋 Salin Teks Biasa (.TXT)", data=draf_teredit, file_name="Naskah_Medsos.txt", mime="text/plain")
        
    with col2:
        if st.button("📥 Ekspor Dokumen ke PDF (Tahoma 12pt)"):
            img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="max-height: 60px; float:right;" />' if logo_b64 else ''
            ttd_tag = f'<img src="data:image/png;base64,{ttd_b64}" style="max-height: 90px;" />' if ttd_b64 else '<br><br><br>'
            
            html_content = f"""
            <html><head><style>
                @page {{ size: A4; margin: 20mm; }}
                body {{ font-family: 'Tahoma', sans-serif; font-size: 12pt; line-height: 1.5; color: #111; text-align: justify; }}
                .header {{ border-bottom: 3px solid #0d9488; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }}
                h1 {{ font-size: 18pt; color: #0d9488; margin: 0; }}
                .meta-info {{ font-size: 10pt; color: #555; margin-top: 5px; }}
                .content {{ white-space: pre-wrap; }}
                .approval-box {{ margin-top: 50px; text-align: right; font-size: 11pt; }}
                .footer {{ margin-top: 40px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 9pt; text-align: center; color: #777; }}
            </style></head>
            <body>
                <div class="header">
                    <div>
                        <h1>RSPUR — Brief Konten Edukasi Medis</h1>
                        <div class="meta-info">Topik: {st.session_state['topik_aktif']}</div>
                    </div>
                    {img_tag}
                </div>
                <div class="content">{draf_teredit}</div>
                <div class="approval-box">
                    <p>Ditinjau & Disetujui Oleh:</p>
                    {ttd_tag}
                    <p><b>{nakes_final}</b></p>
                </div>
                <div class="footer">Dicetak dari Sistem AI Content Planner RSPUR</div>
            </body></html>
            """
            pdf_file = HTML(string=html_content).write_pdf()
            st.download_button(label="⬇️ Unduh PDF Resmi", data=pdf_file, file_name="RSPUR_Brief_Medis.pdf", mime="application/pdf")
