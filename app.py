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

# ============================================================
# KONFIGURASI API KEY
# ============================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
CEREBRAS_API_KEY = st.secrets.get("CEREBRAS_API_KEY") or os.getenv("CEREBRAS_API_KEY")

if not GROQ_API_KEY:
    st.error("⚠️ API Key Groq belum dikonfigurasi!")
    st.stop()

groq_client = Groq(api_key=GROQ_API_KEY)

# ============================================================
# KONFIGURASI MODEL
# ============================================================
GROQ_MODEL = "openai/gpt-oss-120b"

# Cerebras - OpenAI-compatible endpoint (model sama dengan Groq)
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gpt-oss-120b"

st.title("🏥 AI Medical Content Planner RSPUR")
st.markdown("Groq (utama) + Cerebras (fallback) — 2 penyedia independen")

# ============================================================
# TEMPLATE MASTER RSPUR
# ============================================================
TEMPLATE_EDITORIAL_PLAN = """
STRUKTUR EDITORIAL PLAN RSPUR (WAJIB DIIKUTI PERSIS):

# PERENCANAAN KONTEN & JADWAL PUBLIKASI (EDITORIAL PLAN)
## [Nama Unit/Kampanye] RSPUR – Periode: [Tanggal Awal – Tanggal Akhir]

**DOKUMEN MASTER PDF** | Status: Draft | Ref: EP-RSPUR-[TAHUN]-W[NO-MINGGU]

**TOTAL KONTEN:** X POSTINGAN
**FUNNEL STRATEGY:** X TOFU | X MOFU | X BOFU | X COMBO
**KANAL DISTRIBUSI:** IG, FB, YT, TikTok, X, LinkedIn, WA
**VERIFIKASI MEDIS:** [Guideline: PERKI/AHA/WHO/POGI/Kemenkes]

---

### TABEL BRIEF EKSEKUSI EDITORIAL

| TANGGAL & FUNNEL | TOPIK & FORMAT | KONSEP COPYWRITING (HOOK, FAKTA, ISI, CTA) | NARASUMBER & TIM | RUJUKAN |
|---|---|---|---|---|
| [Hari, Tgl Bulan Tahun]<br/>[TOFU/MOFU/BOFU] | [Judul Topik]<br/>Format: [Karosel/Video/Reels/Story/Poster/Artikel]<br/>Kanal: [IG/FB/YT/TikTok/X/LinkedIn/WA] | **HOOK** [Kalimat pembuka]<br/>**FAKTA** [Data medis]<br/>**ISI** [Penjelasan]<br/>**CTA** [Call to action] | Nakes: [Nama lengkap + gelar]<br/>Tim: [Copywriter/Desainer/Videografer/Admin] | [Referensi guideline] |

[Ulangi untuk setiap hari]

---

### LEMBAR VERIFIKASI & PERSETUJUAN PUBLIKASI

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
| **Funnel Target** | [TOFU/MOFU/BOFU] |
| **Kategori Konten** | [Edukasi Medis & Preventif / Informasi Layanan] |
| **Narasumber / Reviewer** | [Nama dokter + gelar lengkap] |

**Tujuan Strategis & Kampanye Konten:**
[Paragraf tujuan]

---

### RANCANGAN NASKAH & SLIDE

**Headline Utama (Hook):**
"[Kalimat hook]"
Sub-copy: [Kalimat pendukung] [Swipe >>]
Visual Direction: [Deskripsi visual]

**Slide 2 — [Nama Slide]:**
[Isi konten]
Visual Direction: [Deskripsi visual]

[Lanjutkan sampai slide terakhir]

---

**CATATAN DESAIN:**
- Warna: [Panduan warna hex]
- Ukuran teks headline minimal 32pt pada artboard 1080x1350px
- Watermark logo RSPUR di sudut kanan atas setiap slide

---

### LEMBAR REVIEW & PERSETUJUAN MEDIS

☐ Setuju Tanpa Revisi  ☐ Setuju Dengan Catatan Minor  ☐ Perlu Perbaikan

Diajukan Oleh: Tim Marketing Digital & Humas RSPUR
Ditinjau & Disetujui Oleh: [Nama Dokter + Gelar]
"""


# ============================================================
# FUNGSI PEMANGGILAN AI
# ============================================================
def call_groq(prompt: str, system_msg: str = "Anda adalah asisten humas medis RSPUR.") -> str:
    """Panggil Groq dengan retry."""
    last_error = None
    for attempt in range(1, 4):
        try:
            r = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=8000,
            )
            return r.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt < 3:
                wait = (2 ** attempt) + random.uniform(0, 1)
                st.write(f"⏳ Groq sibuk ({e}). Retry {attempt}/3 dalam {wait:.1f}s...")
                time.sleep(wait)
    raise RuntimeError(f"Groq gagal setelah 3x: {last_error}")


def call_cerebras(prompt: str, system_msg: str = "Anda adalah asisten humas medis RSPUR.") -> str:
    """Fallback ke Cerebras (OpenAI-compatible)."""
    if not CEREBRAS_API_KEY:
        raise RuntimeError("CEREBRAS_API_KEY tidak tersedia. Groq juga gagal.")

    last_error = None
    for attempt in range(1, 4):
        try:
            r = requests.post(
                CEREBRAS_URL,
                headers={
                    "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.5,
                    "max_tokens": 8000,
                },
                timeout=180,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]

            if r.status_code in (429, 503):
                wait = (2 ** attempt) + random.uniform(0, 1)
                st.write(f"⏳ Cerebras sibuk (HTTP {r.status_code}). Retry {attempt}/3 dalam {wait:.1f}s...")
                time.sleep(wait)
                last_error = f"HTTP {r.status_code}"
                continue

            r.raise_for_status()
        except requests.exceptions.Timeout:
            wait = (2 ** attempt) + random.uniform(0, 1)
            st.write(f"⏳ Cerebras timeout. Retry {attempt}/3...")
            time.sleep(wait)
            last_error = "timeout"
            continue
        except Exception as e:
            last_error = e

    raise RuntimeError(f"Cerebras gagal setelah 3x: {last_error}")


def generate_content(prompt: str, system_msg: str = "Anda adalah asisten humas medis RSPUR.") -> str:
    """Coba Groq dulu, kalau gagal fallback ke Cerebras."""
    try:
        st.write("🟢 Menulis via Groq...")
        return call_groq(prompt, system_msg)
    except Exception as e:
        st.write(f"⚠️ Groq gagal: {e}")
        st.write("🟡 Beralih ke Cerebras (fallback)...")
        return call_cerebras(prompt, system_msg)


# ============================================================
# UI
# ============================================================
with st.form("content_form"):
    st.subheader("⚙️ Pengaturan Konten")

    col1, col2 = st.columns(2)
    with col1:
        template_pilihan = st.selectbox(
            "📋 Format Output:",
            [
                "📊 Editorial Plan Mingguan (Tabel)",
                "📝 Brief Konten Detail (Naskah per Slide)",
                "📚 Kombinasi Lengkap",
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
                # STEP 1: Analisa tren
                st.write(f"🔍 Analisa tren medis via Groq (`{GROQ_MODEL}`)...")
                analisis_tren = generate_content(
                    prompt=f"Analisis tren medis & poin-poin kampanye kesehatan untuk topik: {topik}. Durasi: {durasi}.",
                    system_msg="Anda adalah analis riset medis dan humas rumah sakit RSPUR berpengalaman."
                )

                # STEP 2: Pilih template
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

                # STEP 3: Generate naskah
                st.write("✍️ Menyusun naskah sesuai template RSPUR...")
                prompt = f"""
Anda adalah **Senior Copywriter & Medical Content Planner RSPUR** (Rumah Sakit Rujukan).
Tugas: membuat perencanaan konten media sosial sesuai template resmi RSPUR.

═══════════════════════════════════════════
📌 TOPIK: {topik}
📅 DURASI: {durasi}
📋 FORMAT: {instruksi_format}
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
2. Bahasa Indonesia profesional ala humas rumah sakit.
3. Setiap konten WAJIB punya: HOOK, FAKTA, ISI, CTA.
4. Cantumkan nama dokter spesialis lengkap dengan gelar (Sp.JP, Sp.KFR, Sp.OG, dll).
5. Sertakan referensi medis (PERKI, AHA, WHO, POGI, Kemenkes).
6. Gunakan formatting Markdown: tabel pakai `|`, header pakai `#`, bullet pakai `-`.
7. Jangan tambahkan komentar pembuka/penutup di luar template.
8. CTA harus jelas dan actionable (booking, WA, link, dll).
9. Untuk carousel, minimal 5-7 slide dengan Visual Direction.
10. Sesuaikan funnel: TOFU (awareness), MOFU (edukasi), BOFU (konversi).

Mulai sekarang. Output langsung ke struktur template tanpa basa-basi.
"""

                hasil_konten = generate_content(
                    prompt=prompt,
                    system_msg="Anda adalah Senior Copywriter & Medical Content Planner RSPUR yang patuh template."
                )

                status.update(label="✅ Konten Berhasil Dibuat!", state="complete", expanded=False)

                st.markdown("---")
                st.subheader("📄 Hasil Generasi Konten (Sesuai Template RSPUR):")
                st.markdown(hasil_konten)

                st.download_button(
                    label="⬇️ Download sebagai Markdown (.md)",
                    data=hasil_konten,
                    file_name="konten_rspur.md",
                    mime="text/markdown",
                )

            except Exception as e:
                status.update(label="❌ Terjadi Kesalahan Sistem!", state="error", expanded=True)
                st.error(f"Detail Error: {str(e)}")
