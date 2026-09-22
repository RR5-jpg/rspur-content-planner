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

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY or not GEMINI_API_KEY:
    st.error("⚠️ API Key untuk Groq atau Gemini belum dikonfigurasi!")
    st.stop()

groq_client = Groq(api_key=GROQ_API_KEY)

GROQ_MODEL = "openai/gpt-oss-120b"

GEMINI_FALLBACK_CHAIN = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
]

st.title("🏥 AI Medical Content Planner RSPUR")
st.markdown("Generator Konten Medis sesuai **Template Resmi RSPUR** (Editorial Plan + Brief Konten)")

# ============================================================
# TEMPLATE MASTER RSPUR (dipakai sebagai acuan AI)
# ============================================================
TEMPLATE_EDITORIAL_PLAN = """
STRUKTUR EDITORIAL PLAN RSPUR (WAJIB DIIKUTI PERSIS):

# PERENCANAAN KONTEN & JADWAL PUBLIKASI (EDITORIAL PLAN)
## [Nama Unit/Kampanye] RSPUR – Periode: [Tanggal Awal – Tanggal Akhir]

**DOKUMEN MASTER PDF** | Status: Draft | Ref: EP-RSPUR-[TAHUN]-W[NO-MINGGU]

**TOTAL KONTEN:** X POSTINGAN
**FUNNEL STRATEGY:** X TOFU | X MOFU | X BOFU | X COMBO
**KANAL DISTRIBUSI:** IG, FB, YT, TikTok, X, LinkedIn, WA
**VERIFIKASI MEDIS:** [Sebutkan guideline: PERKI/AHA/WHO/POGI/Kemenkes]

---

### TABEL BRIEF EKSEKUSI EDITORIAL

| TANGGAL & FUNNEL | TOPIK & FORMAT | KONSEP COPYWRITING (HOOK, FAKTA, ISI, CTA) | NARASUMBER & TIM | RUJUKAN |
|---|---|---|---|---|
| [Hari, Tgl Bulan Tahun]<br/>[TOFU/MOFU/BOFU] | [Judul Topik]<br/>Format: [Karosel/Video/Reels/Story/Poster/Artikel]<br/>Kanal: [IG/FB/YT/TikTok/X/LinkedIn/WA] | **HOOK** [Kalimat pembuka yang memancing]<br/>**FAKTA** [Data medis pendukung]<br/>**ISI** [Penjelasan utama]<br/>**CTA** [Call to action] | Nakes: [Nama lengkap + gelar]<br/>Tim: [Copywriter/Desainer/Videografer/Admin Medsos] | [Referensi guideline] |

[Ulangi untuk setiap hari]

---

### LEMBAR VERIFIKASI & PERSETUJUAN PUBLIKASI (SIGN-OFF BLOCK)

| DISIAPKAN OLEH | VERIFIKASI MEDIS | DISETUJUI OLEH |
|---|---|---|
| (Tim Copywriter & Humas) | (Tim Desain & Videografer) | [Nama Dokter Spesialis] |
"""

TEMPLATE_BRIEF_KONTEN = """
STRUKTUR BRIEF KONTEN EDUKASI MEDIS RSPUR (WAJIB DIIKUTI PERSIS):

# RSPUR — BRIEF KONTEN EDUKASI MEDIS
## Lembar Pengajuan & Review Materi Media Sosial

**MARKETING DIGITAL & HUMAS** | Rencana Tayang: [Tanggal]

| FIELD | ISI |
|---|---|
| **Judul / Topik** | [Judul lengkap] |
| **Format & Platform** | [Carousel/Video/dll] / [IG & FB/YT/TikTok] |
| **Funnel Target** | [TOFU: Awareness / MOFU: Edukasi & Pertimbangan / BOFU: Konversi Layanan] |
| **Kategori Konten** | [Edukasi Medis & Preventif / Informasi Layanan] |
| **Narasumber / Reviewer** | [Nama dokter + gelar lengkap] |

**Tujuan Strategis & Kampanye Konten:**
[Paragraf tujuan, 2-3 kalimat]

---

### RANCANGAN NASKAH & SLIDE

**Headline Utama (Hook):**
"[Kalimat hook]"
Sub-copy: [Kalimat pendukung] [Swipe >>]
Visual Direction: [Deskripsi visual]

**Slide 2 — [Nama Slide]:**
[Judul/Sub-headline]
[Isi konten]
Visual Direction: [Deskripsi visual]

**Slide 3 — [Nama Slide]:**
[Isi]
Visual Direction: [Deskripsi]

[Lanjutkan sampai slide terakhir]

---

**CATATAN DESAIN & PANDUAN VISUAL TIM KREATIF:**
- Warna: [Panduan warna hex]
- Ukuran teks headline minimal 32pt pada artboard 1080x1350px
- Watermark logo RSPUR di sudut kanan atas setiap slide

---

### LEMBAR REVIEW & PERSETUJUAN MEDIS (APPROVAL FORM)

☐ Setuju Tanpa Revisi  ☐ Setuju Dengan Catatan Minor  ☐ Perlu Perbaikan Naskah/Visual

Catatan Tambahan / Masukan Dokter Spesialis:
[Area untuk catatan]

Diajukan Oleh: Tim Marketing Digital & Humas RSPUR
Ditinjau & Disetujui Oleh: [Nama Dokter + Gelar]
"""


def call_gemini_with_retry(prompt: str, max_retries: int = 2) -> str:
    last_error = None
    for model in GEMINI_FALLBACK_CHAIN:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": GEMINI_API_KEY,
                    },
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.5,
                            "maxOutputTokens": 16000,
                        },
                    },
                    timeout=240,
                )
                if r.status_code == 200:
                    data = r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                if r.status_code in (503, 429):
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    st.write(f"⏳ `{model}` sibuk ({r.status_code}). Retry {attempt}/{max_retries} dalam {wait:.1f}s...")
                    time.sleep(wait)
                    last_error = f"{model}: HTTP {r.status_code}"
                    continue
                r.raise_for_status()
            except requests.exceptions.Timeout:
                wait = (2 ** attempt) + random.uniform(0, 1)
                st.write(f"⏳ Timeout pada `{model}`. Retry {attempt}/{max_retries}...")
                time.sleep(wait)
                last_error = f"{model}: timeout"
                continue
        st.write(f"⚠️ `{model}` gagal, lanjut ke fallback berikutnya...")
    raise RuntimeError(f"Semua model Gemini gagal. Error: {last_error}")


# ============================================================
# UI
# ============================================================
with st.form("content_form"):
    st.subheader("⚙️ Pengaturan Konten")

    col1, col2 = st.columns(2)
    with col1:
        template_pilihan = st.selectbox(
            "📋 Format Output (Sesuai Template RSPUR):",
            [
                "📊 Editorial Plan Mingguan (Tabel)",
                "📝 Brief Konten Detail (Naskah per Slide)",
                "📚 Kombinasi Lengkap (Editorial Plan + Brief per Konten)",
            ]
        )
    with col2:
        durasi = st.selectbox(
            "📅 Rentang Waktu:",
            ["1 Hari", "3 Hari", "1 Minggu (7 hari)", "2 Minggu (14 hari)"]
        )

    topik = st.text_area(
        "🎯 Topik / Kampanye Medis:",
        placeholder="Contoh: Kampanye Jantung Sehat periode 28 Sep - 4 Okt 2026, fokus deteksi dini & MCU Jantung",
        height=100,
    )

    submitted = st.form_submit_button("🚀 Buat Konten Sekarang")

if submitted:
    if not topik.strip():
        st.warning("⚠️ Mohon masukkan topik terlebih dahulu!")
    else:
        with st.status("🧠 Memproses Data AI...", expanded=True) as status:
            try:
                # STEP 1: Analisa tren via Groq
                st.write(f"🔍 Analisa tren medis via Groq (`{GROQ_MODEL}`)...")
                groq_response = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Anda adalah analis riset medis dan humas rumah sakit RSPUR berpengalaman. "
                                "Berikan analisa tren yang ringkas, berbasis data, dan relevan untuk konten media sosial rumah sakit."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Analisis tren medis & poin-poin kampanye kesehatan untuk topik: {topik}. Durasi: {durasi}."
                        }
                    ],
                    temperature=0.7,
                )
                analisis_tren = groq_response.choices[0].message.content

                # STEP 2: Tentukan template
                if template_pilihan.startswith("📊"):
                    template_used = TEMPLATE_EDITORIAL_PLAN
                    instruksi_format = "Gunakan HANYA format Editorial Plan (tabel harian)."
                elif template_pilihan.startswith("📝"):
                    template_used = TEMPLATE_BRIEF_KONTEN
                    instruksi_format = "Gunakan HANYA format Brief Konten (naskah per slide untuk SATU konten utama)."
                else:
                    template_used = TEMPLATE_EDITORIAL_PLAN + "\n\n" + TEMPLATE_BRIEF_KONTEN
                    instruksi_format = (
                        "Hasilkan DUA bagian: (1) Editorial Plan lengkap dalam tabel, "
                        "(2) Brief Konten detail untuk SETIAP topik di editorial plan."
                    )

                # STEP 3: Generate via Gemini sesuai template
                st.write(f"✍️ Menyusun naskah sesuai template RSPUR via Gemini...")
                prompt = f"""
Anda adalah **Senior Copywriter & Medical Content Planner RSPUR** (Rumah Sakit Rujukan). 
Tugas Anda: membuat perencanaan konten media sosial sesuai **template resmi RSPUR** di bawah ini.

═══════════════════════════════════════════
📌 TOPIK / KAMPANYE: {topik}
📅 DURASI: {durasi}
📋 FORMAT OUTPUT: {instruksi_format}
═══════════════════════════════════════════

📊 ANALISIS TREN DARI TIM RISET:
{analisis_tren}

═══════════════════════════════════════════
📐 TEMPLATE WAJIB (IKUTI STRUKTUR PERSIS):
═══════════════════════════════════════════
{template_used}

═══════════════════════════════════════════
✅ ATURAN KETAT:
═══════════════════════════════════════════
1. IKUTI struktur template PERSIS — jangan improvisasi format baru.
2. Gunakan bahasa Indonesia profesional ala humas rumah sakit.
3. Setiap konten WAJIB punya: HOOK, FAKTA, ISI, CTA.
4. Cantumkan nama dokter spesialis lengkap dengan gelar (Sp.JP, Sp.KFR, Sp.OG, dll).
5. Sertakan referensi medis (PERKI, AHA, WHO, POGI, Kemenkes).
6. Gunakan formatting Markdown: tabel pakai `|`, header pakai `#`, bullet pakai `-`.
7. Jangan tambahkan komentar pembuka/penutup di luar template.
8. Pastikan CTA jelas dan actionable (booking, WA, link, dll).
9. Untuk carousel, buat minimal 5-7 slide dengan Visual Direction di setiap slide.
10. Sesuaikan funnel: TOFU (awareness), MOFU (edukasi), BOFU (konversi layanan).

Mulai sekarang. Output langsung ke struktur template tanpa basa-basi.
"""

                hasil_konten = call_gemini_with_retry(prompt)

                status.update(label="✅ Konten Berhasil Dibuat!", state="complete", expanded=False)

                st.markdown("---")
                st.subheader("📄 Hasil Generasi Konten (Sesuai Template RSPUR):")
                st.markdown(hasil_konten)

                # Tombol download
                st.download_button(
                    label="⬇️ Download sebagai Markdown (.md)",
                    data=hasil_konten,
                    file_name="konten_rspur.md",
                    mime="text/markdown",
                )

            except Exception as e:
                status.update(label="❌ Terjadi Kesalahan Sistem!", state="error", expanded=True)
                st.error(f"Detail Error: {str(e)}")
