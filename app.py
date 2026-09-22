import os
import io
import csv
import json
import time
import random
import re
import textwrap
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
# API KEYS
# ============================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
CEREBRAS_API_KEY = st.secrets.get("CEREBRAS_API_KEY") or os.getenv("CEREBRAS_API_KEY")

if not GROQ_API_KEY:
    st.error("⚠️ API Key Groq belum dikonfigurasi!")
    st.stop()

groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "openai/gpt-oss-120b"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gpt-oss-120b"


def clean_html(html_str):
    """Hilangkan indentasi leading agar Markdown tidak render sebagai code block."""
    return "\n".join(line.lstrip() if line.strip() else "" for line in html_str.split("\n"))

st.title("🏥 AI Medical Content Planner RSPUR")

# ============================================================
# CSS GLOBAL — biar mirip PDF RSPUR
# ============================================================
st.markdown("""
<style>
.rspur-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    font-family: -apple-system, "Segoe UI", Arial, sans-serif;
    margin: 10px 0;
}
.rspur-table th {
    background: #0d9488;
    color: white;
    padding: 10px 8px;
    text-align: left;
    border: 1px solid #0f766e;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
.rspur-table td {
    padding: 10px 8px;
    border: 1px solid #cbd5e1;
    vertical-align: top;
    line-height: 1.5;
}
.rspur-table tr:nth-child(even) td { background: #f8fafc; }
.rspur-table tr:hover td { background: #f0fdfa; }
.rspur-table .tanggal { font-weight: 700; color: #0f172a; }
.rspur-table .funnel {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 700;
    color: white;
    margin-top: 4px;
}
.funnel-tofu { background: #0284c7; }
.funnel-mofu { background: #d97706; }
.funnel-bofu { background: #dc2626; }
.funnel-combo { background: #7c3aed; }
.rspur-table .topik { font-weight: 700; color: #0f172a; }
.rspur-table .format { color: #475569; font-style: italic; font-size: 12px; }
.rspur-table .kanal { color: #0d9488; font-size: 12px; font-weight: 600; }
.rspur-table .label { font-weight: 700; color: #0f766e; }
.rspur-table .nakes { font-weight: 600; color: #0f172a; }
.rspur-table .tim { color: #64748b; font-size: 12px; }
.rspur-table .rujukan { font-size: 12px; color: #475569; }

.brief-card {
    border: 1px solid #cbd5e1;
    border-left: 4px solid #0d9488;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 12px 0;
    background: white;
}
.brief-card h4 { margin-top: 0; color: #0f766e; }
.brief-meta {
    background: #f0fdfa;
    padding: 14px 18px;
    border-radius: 6px;
    border-left: 4px solid #14b8a6;
    margin: 12px 0;
}
.brief-meta table { width: 100%; border-collapse: collapse; }
.brief-meta td { padding: 5px 8px; vertical-align: top; }
.brief-meta td:first-child { font-weight: 700; color: #0f766e; width: 200px; }
.slide-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}
.slide-num {
    background: #0d9488;
    color: white;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
    flex-shrink: 0;
}
.visual-dir {
    background: #fef3c7;
    border-left: 3px solid #f59e0b;
    padding: 10px 14px;
    border-radius: 4px;
    font-size: 13px;
    color: #78350f;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SCHEMAS
# ============================================================
SCHEMA_EDITORIAL = """
{
  "kampanye": "Pusat Jantung & Pembuluh Darah RSPUR",
  "periode": "28 September - 04 Oktober 2026",
  "ref": "EP-RSPUR-2026-W39",
  "total_konten": 7,
  "funnel_strategy": "3 TOFU | 3 MOFU | 1 BOFU",
  "kanal": "IG, FB, YT, TikTok, X, LinkedIn, WA",
  "verifikasi": "PERKI, AHA, WHO, POGI, Kemenkes",
  "konten": [
    {
      "tanggal": "Senin, 28 Sep 2026",
      "funnel": "TOFU",
      "topik": "Judul topik konten",
      "format": "Infografis Karosel",
      "kanal": "IG & FB",
      "hook": "Kalimat hook pembuka...",
      "fakta": "Data medis pendukung...",
      "isi": "Penjelasan utama konten...",
      "cta": "Call to action spesifik...",
      "narasumber": "Dr. dr. Nama Lengkap, MAppSc, Sp.JP, Subsp.P.R.KU(K), FIHA, FasCC",
      "tim": "Copywriter & Desainer",
      "rujukan": "PERKI, AHA"
    }
  ],
  "disiapkan_oleh": "Tim Copywriter & Humas",
  "verifikasi_oleh": "Tim Desain & Videografer",
  "disetujui_oleh": "dr. Nama Direktur Medis, Sp.JP"
}
"""

SCHEMA_BRIEF = """
{
  "judul": "Judul lengkap konten",
  "format_platform": "Carousel / Feeds - Instagram & Facebook",
  "funnel_target": "MOFU - Middle of Funnel (Edukasi & Pertimbangan) | BOFU - Bottom of Funnel (Konversi Layanan)",
  "kategori": "Edukasi Medis & Preventif / Informasi Layanan",
  "narasumber": "dr. Nama Lengkap, Sp.KFR & Tim Fisioterapis RSPUR",
  "rencana_tayang": "27 Sep 2026",
  "tujuan_strategis": "Paragraf tujuan strategis kampanye 2-3 kalimat...",
  "total_slide": 6,
  "slides": [
    {
      "nomor": 1,
      "label_slide": "SLIDE 1 - HEADLINE UTAMA (HOOK)",
      "judul": "Headline Utama (Hook)",
      "headline": "Kalimat headline utama...",
      "subcopy": "Sub-copy pendukung... [Swipe >>]",
      "isi": "",
      "visual": "Deskripsi visual direction..."
    },
    {
      "nomor": 2,
      "label_slide": "SLIDE 2 - TANTANGAN",
      "judul": "Tantangan Pasca Tindakan Medis",
      "headline": "",
      "subcopy": "",
      "isi": "Paragraf isi penjelasan...",
      "visual": "Deskripsi visual direction..."
    }
  ],
  "catatan_desain": [
    "Gunakan warna latar belakang putih/light teal (#f0fdfa) untuk kesan bersih dan higienis medis.",
    "Pastikan ukuran teks headline tidak kurang dari 32pt pada artboard Instagram (1080x1350px).",
    "Cantumkan watermark logo resmi RSPUR di sudut kanan atas setiap slide secara konsisten."
  ],
  "diajukan_oleh": "Tim Marketing Digital & Humas RSPUR",
  "disetujui_oleh": "dr. Nama Lengkap, Sp.KFR"
}
"""

# ============================================================
# AI CALLS
# ============================================================
def call_groq(prompt, system_msg, max_tokens=8000):
    last_error = None
    for attempt in range(1, 3):
        try:
            r = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return r.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Groq gagal: {last_error}")


def call_cerebras(prompt, system_msg, max_tokens=8000):
    if not CEREBRAS_API_KEY:
        raise RuntimeError("CEREBRAS_API_KEY tidak tersedia.")
    last_error = None
    for attempt in range(1, 3):
        try:
            r = requests.post(
                CEREBRAS_URL,
                headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                },
                timeout=180,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            if r.status_code in (429, 503):
                time.sleep(2 ** attempt)
                last_error = f"HTTP {r.status_code}"
                continue
            r.raise_for_status()
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Cerebras gagal: {last_error}")


def call_ai_json(prompt, system_msg, max_tokens=8000):
    try:
        st.write("🟢 Memproses via Groq...")
        raw = call_groq(prompt, system_msg, max_tokens)
    except Exception as e:
        st.write(f"⚠️ Groq gagal: {e}")
        st.write("🟡 Beralih ke Cerebras...")
        raw = call_cerebras(prompt, system_msg, max_tokens)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ============================================================
# HTML BUILDERS
# ============================================================
def funnel_badge(f):
    f = (f or "").upper()
    cls = {"TOFU": "funnel-tofu", "MOFU": "funnel-mofu",
           "BOFU": "funnel-bofu", "COMBO": "funnel-combo"}.get(f, "funnel-tofu")
    return f'<span class="funnel {cls}">{f}</span>'


def editorial_to_html(data):
    rows = ""
    for k in data.get("konten", []):
        rows += f"""
        <tr>
            <td>
                <div class="tanggal">{k.get('tanggal','')}</div>
                {funnel_badge(k.get('funnel',''))}
            </td>
            <td>
                <div class="topik">{k.get('topik','')}</div>
                <div class="format">Format: {k.get('format','')}</div>
                <div class="kanal">Kanal: {k.get('kanal','')}</div>
            </td>
            <td>
                <span class="label">HOOK</span> {k.get('hook','')}<br/>
                <span class="label">FAKTA</span> {k.get('fakta','')}<br/>
                <span class="label">ISI</span> {k.get('isi','')}<br/>
                <span class="label">CTA</span> {k.get('cta','')}
            </td>
            <td>
                <div class="nakes">Nakes:<br/>{k.get('narasumber','')}</div>
                <div class="tim">Tim: {k.get('tim','')}</div>
            </td>
            <td class="rujukan">{k.get('rujukan','')}</td>
        </tr>"""

    return f"""
    <h2 style="color:#0f766e;margin-bottom:4px;">PERENCANAAN KONTEN & JADWAL PUBLIKASI (EDITORIAL PLAN)</h2>
    <p style="font-size:16px;color:#0f172a;margin-top:0;"><b>{data.get('kampanye','')}</b> – Periode: {data.get('periode','')}</p>
    <p style="font-size:12px;color:#475569;">
        <b>DOKUMEN MASTER PDF</b> | Status: Approved / Siap Share | Ref: {data.get('ref','')}<br/>
        <b>TOTAL KONTEN:</b> {data.get('total_konten','-')} POSTINGAN &nbsp;|&nbsp;
        <b>FUNNEL STRATEGY:</b> {data.get('funnel_strategy','-')}<br/>
        <b>KANAL DISTRIBUSI:</b> {data.get('kanal','-')} &nbsp;|&nbsp;
        <b>VERIFIKASI MEDIS:</b> {data.get('verifikasi','-')}
    </p>

    <table class="rspur-table">
        <thead>
            <tr>
                <th style="width:14%;">TANGGAL & FUNNEL</th>
                <th style="width:20%;">TOPIK & FORMAT</th>
                <th style="width:36%;">KONSEP COPYWRITING (HOOK, FAKTA, ISI, CTA)</th>
                <th style="width:18%;">NARASUMBER & TIM</th>
                <th style="width:12%;">RUJUKAN</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>

    <h3 style="color:#0f766e;margin-top:28px;">LEMBAR VERIFIKASI & PERSETUJUAN PUBLIKASI (SIGN-OFF BLOCK)</h3>
    <table class="rspur-table">
        <thead>
            <tr><th>DISIAPKAN OLEH</th><th>VERIFIKASI MEDIS</th><th>DISETUJUI OLEH</th></tr>
        </thead>
        <tbody>
            <tr>
                <td>{data.get('disiapkan_oleh','-')}</td>
                <td>{data.get('verifikasi_oleh','-')}</td>
                <td>{data.get('disetujui_oleh','-')}</td>
            </tr>
        </tbody>
    </table>
    """


def brief_to_html(data):
    # Meta info
    meta = f"""
    <div class="brief-meta">
        <table>
            <tr><td>Judul / Topik</td><td><b>{data.get('judul','')}</b></td></tr>
            <tr><td>Format & Platform</td><td>{data.get('format_platform','')}</td></tr>
            <tr><td>Funnel Target</td><td>{data.get('funnel_target','')}</td></tr>
            <tr><td>Kategori Konten</td><td>{data.get('kategori','')}</td></tr>
            <tr><td>Narasumber / Reviewer</td><td>{data.get('narasumber','')}</td></tr>
            <tr><td>Rencana Tayang</td><td>{data.get('rencana_tayang','')}</td></tr>
        </table>
    </div>
    """

    # Slides
    slides_html = ""
    for s in data.get("slides", []):
        isi_block = ""
        if s.get("headline"):
            isi_block += f'<p style="font-size:15px;"><b>Headline:</b> "{s["headline"]}"</p>'
        if s.get("subcopy"):
            isi_block += f'<p><b>Sub-copy:</b> {s["subcopy"]}</p>'
        if s.get("isi"):
            isi_block += f'<p style="line-height:1.7;">{s["isi"]}</p>'

        slides_html += f"""
        <div class="brief-card">
            <div class="slide-header">
                <span class="slide-num">{s.get('nomor','')}</span>
                <h4 style="margin:0;">{s.get('label_slide', s.get('judul',''))}</h4>
            </div>
            {isi_block}
            {f'<div class="visual-dir"><b>🎨 Visual Direction:</b> {s["visual"]}</div>' if s.get('visual') else ''}
        </div>"""

    # Catatan desain
    catatan = ""
    if data.get("catatan_desain"):
        items = "".join([f"<li>{c}</li>" for c in data["catatan_desain"]])
        catatan = f"""
        <div style="background:#f8fafc;padding:14px 18px;border-radius:6px;margin-top:20px;">
            <h4 style="margin-top:0;color:#0f766e;">CATATAN DESAIN & PANDUAN VISUAL TIM KREATIF</h4>
            <ul style="margin:0;padding-left:20px;">{items}</ul>
        </div>"""

    # Approval
    approval = f"""
    <div style="background:#f0fdfa;padding:14px 18px;border-radius:6px;margin-top:20px;border-left:4px solid #0d9488;">
        <h4 style="margin-top:0;color:#0f766e;">LEMBAR REVIEW & PERSETUJUAN MEDIS (APPROVAL FORM)</h4>
        <p>☐ Setuju Tanpa Revisi &nbsp;&nbsp; ☐ Setuju Dengan Catatan Minor &nbsp;&nbsp; ☐ Perlu Perbaikan Naskah/Visual</p>
        <p><b>Catatan Tambahan / Masukan Dokter Spesialis:</b><br/>
        <em>[ Area untuk catatan / koreksi istilah medis ]</em></p>
        <table style="width:100%;margin-top:10px;">
            <tr>
                <td><b>Diajukan Oleh:</b><br/>{data.get('diajukan_oleh','-')}</td>
                <td><b>Ditinjau & Disetujui Oleh:</b><br/>{data.get('disetujui_oleh','-')}</td>
            </tr>
        </table>
    </div>"""

    return f"""
    <h2 style="color:#0f766e;margin-bottom:4px;">RSPUR — BRIEF KONTEN EDUKASI MEDIS</h2>
    <p style="font-size:14px;color:#475569;margin-top:0;">Lembar Pengajuan & Review Materi Media Sosial</p>
    <p style="font-size:12px;color:#0f766e;font-weight:700;">MARKETING DIGITAL & HUMAS &nbsp;|&nbsp; Rencana Tayang: {data.get('rencana_tayang','')}</p>

    {meta}

    <h3 style="color:#0f766e;margin-top:24px;">Tujuan Strategis & Kampanye Konten</h3>
    <p style="line-height:1.7;">{data.get('tujuan_strategis','')}</p>

    <h3 style="color:#0f766e;margin-top:24px;">RANCANGAN NASKAH & SLIDE CAROUSEL</h3>
    <p style="font-size:13px;color:#475569;"><b>Target Total:</b> {data.get('total_slide','')} Slide Carousel</p>

    {slides_html}
    {catatan}
    {approval}
    """


def editorial_to_csv(data):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Tanggal", "Funnel", "Topik", "Format", "Kanal",
                "Hook", "Fakta", "Isi", "CTA", "Narasumber", "Tim", "Rujukan"])
    for k in data.get("konten", []):
        w.writerow([
            k.get("tanggal", ""), k.get("funnel", ""), k.get("topik", ""),
            k.get("format", ""), k.get("kanal", ""),
            k.get("hook", ""), k.get("fakta", ""), k.get("isi", ""), k.get("cta", ""),
            k.get("narasumber", ""), k.get("tim", ""), k.get("rujukan", ""),
        ])
    return buf.getvalue()


def wrap_html_document(title, body_html):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; padding: 24px; color: #0f172a; }}
table.rspur-table {{ width:100%; border-collapse:collapse; font-size:12px; margin:10px 0; }}
table.rspur-table th {{ background:#0d9488; color:white; padding:8px; border:1px solid #0f766e; text-align:left; font-size:11px; }}
table.rspur-table td {{ padding:8px; border:1px solid #cbd5e1; vertical-align:top; }}
.funnel {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:10px; color:white; font-weight:700; }}
.funnel-tofu {{ background:#0284c7; }} .funnel-mofu {{ background:#d97706; }}
.funnel-bofu {{ background:#dc2626; }} .funnel-combo {{ background:#7c3aed; }}
.brief-card {{ border:1px solid #cbd5e1; border-left:4px solid #0d9488; border-radius:6px; padding:14px 18px; margin:12px 0; page-break-inside: avoid; }}
.brief-meta {{ background:#f0fdfa; padding:12px; border-radius:6px; border-left:4px solid #14b8a6; }}
.brief-meta td {{ padding:5px 8px; }} .brief-meta td:first-child {{ font-weight:700; color:#0f766e; width:180px; }}
.visual-dir {{ background:#fef3c7; border-left:3px solid #f59e0b; padding:10px; border-radius:4px; font-size:12px; }}
.slide-num {{ background:#0d9488; color:white; padding:4px 10px; border-radius:50%; font-weight:700; margin-right:10px; }}
.label {{ font-weight:700; color:#0f766e; }}
</style></head><body>{body_html}</body></html>"""


# ============================================================
# UI
# ============================================================
with st.form("content_form"):
    st.subheader("⚙️ Pengaturan Konten")

    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox(
            "📋 Jenis Output:",
            ["📊 Editorial Plan", "📝 Brief Konten", "📚 Keduanya (Editorial + Brief)"]
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
        st.stop()

    with st.status("🧠 Memproses Data AI...", expanded=True) as status:
        try:
            st.write("🔍 Analisa tren medis...")
            analisis = call_ai_json(
                prompt=f"Analisis singkat tren medis untuk: {topik}.",
                system_msg='Analis medis RSPUR. Output JSON: {"ringkasan":"...","poin":["..."]}',
                max_tokens=1200,
            )

            editorial_data = None
            brief_data = None

            if mode.startswith("📊") or mode.startswith("📚"):
                st.write("📊 Menyusun Editorial Plan...")
                editorial_data = call_ai_json(
                    prompt=f"""
Buat Editorial Plan RSPUR untuk topik: "{topik}", durasi {durasi}.

Konteks tren: {json.dumps(analisis, ensure_ascii=False)}

Output JSON valid PERSIS sesuai skema ini:
{SCHEMA_EDITORIAL}

Aturan WAJIB:
- Setiap konten punya 4 field: hook, fakta, isi, cta (semua tidak boleh kosong).
- hook = kalimat pembuka memancing, fakta = data medis, isi = penjelasan, cta = ajakan aksi.
- Nama dokter pakai gelar lengkap (Sp.JP, Sp.KFR, Sp.OG, dll).
- Funnel bervariasi: TOFU (awareness), MOFU (edukasi), BOFU (konversi).
- Rujukan: PERKI, AHA, WHO, POGI, atau Kemenkes.
""",
                    system_msg="Senior Content Planner RSPUR. Output JSON valid.",
                    max_tokens=8000,
                )

            if mode.startswith("📝") or mode.startswith("📚"):
                st.write("📝 Menyusun Brief Konten...")
                brief_data = call_ai_json(
                    prompt=f"""
Buat Brief Konten detail RSPUR untuk topik: "{topik}".

Konteks tren: {json.dumps(analisis, ensure_ascii=False)}

Output JSON valid PERSIS sesuai skema ini:
{SCHEMA_BRIEF}

Aturan WAJIB:
- Minimal 6 slide untuk carousel.
- Slide 1: Hook, Slide terakhir: CTA/Closing.
- Setiap slide punya visual direction yang detail.
- label_slide berformat "SLIDE N - NAMA SECTION".
- Nama dokter pakai gelar lengkap.
- Tujuan strategis 2-3 kalimat lengkap.
""",
                    system_msg="Senior Copywriter Medis RSPUR. Output JSON valid.",
                    max_tokens=8000,
                )

            status.update(label="✅ Konten Berhasil Dibuat!", state="complete", expanded=False)

        except Exception as e:
            status.update(label="❌ Error!", state="error", expanded=True)
            st.error(f"Detail: {str(e)}")
            st.stop()

    # ============================================================
    # RENDER TAB
    # ============================================================
    st.markdown("---")

    if editorial_data and brief_data:
        tab1, tab2 = st.tabs(["📊 Editorial Plan", "📝 Brief Konten"])
        with tab1:
            st.markdown(clean_html(editorial_to_html(editorial_data)), unsafe_allow_html=True)
        with tab2:
            st.markdown(clean_html(brief_to_html(brief_data)), unsafe_allow_html=True)
    elif editorial_data:
        st.markdown(clean_html(editorial_to_html(editorial_data)), unsafe_allow_html=True)
    elif brief_data:
        st.markdown(clean_html(brief_to_html(brief_data)), unsafe_allow_html=True)

    # ============================================================
    # EXPORT
    # ============================================================
    st.markdown("---")
    st.subheader("📥 Export & Share")

    c1, c2, c3 = st.columns(3)

    if editorial_data:
        with c1:
            st.download_button(
                "📊 Editorial (CSV / Excel)",
                data=editorial_to_csv(editorial_data),
                file_name="editorial_plan_rspur.csv",
                mime="text/csv",
                use_container_width=True,
                help="Buka di Excel/Google Sheets, bisa edit & share link"
            )
        with c2:
            st.download_button(
                "📄 Editorial (Word/HTML)",
                data=wrap_html_document("Editorial Plan RSPUR", editorial_to_html(editorial_data)),
                file_name="editorial_plan_rspur.html",
                mime="text/html",
                use_container_width=True,
                help="Buka di Word/Google Docs, layout persis seperti preview"
            )

    if brief_data:
        with c3:
            st.download_button(
                "📝 Brief (Word/HTML)",
                data=wrap_html_document("Brief Konten RSPUR", brief_to_html(brief_data)),
                file_name="brief_konten_rspur.html",
                mime="text/html",
                use_container_width=True,
                help="Buka di Word/Google Docs, layout persis seperti preview"
            )
