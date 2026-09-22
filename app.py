import os, io, csv, json, time, re
import requests
import pandas as pd
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Content Planner RSPUR", page_icon="🏥", layout="wide")

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
CEREBRAS_API_KEY = st.secrets.get("CEREBRAS_API_KEY") or os.getenv("CEREBRAS_API_KEY")
if not GROQ_API_KEY:
    st.error("⚠️ GROQ_API_KEY belum dikonfigurasi!"); st.stop()

groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "openai/gpt-oss-120b"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gpt-oss-120b"

# ---------- SESSION STATE INIT ----------
for k, v in [("editorial_data", None), ("briefs", {}), ("generated", False), ("constraints", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ---------- CSS ----------
st.markdown("""<style>
.rspur-table{width:100%;border-collapse:collapse;font-size:13px;font-family:Arial,sans-serif;margin:10px 0;}
.rspur-table th{background:#0d9488;color:white;padding:10px 8px;text-align:left;border:1px solid #0f766e;font-weight:600;font-size:12px;text-transform:uppercase;}
.rspur-table td{padding:10px 8px;border:1px solid #cbd5e1;vertical-align:top;line-height:1.5;}
.rspur-table tr:nth-child(even) td{background:#f8fafc;}
.rspur-table .tanggal{font-weight:700;color:#0f172a;}
.rspur-table .funnel{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;color:white;margin-top:4px;}
.funnel-tofu{background:#0284c7;} .funnel-mofu{background:#d97706;} .funnel-bofu{background:#dc2626;} .funnel-combo{background:#7c3aed;}
.rspur-table .topik{font-weight:700;} .rspur-table .format{color:#475569;font-style:italic;font-size:12px;}
.rspur-table .kanal{color:#0d9488;font-size:12px;font-weight:600;}
.rspur-table .label{font-weight:700;color:#0f766e;}
.rspur-table .nakes{font-weight:600;} .rspur-table .tim{color:#64748b;font-size:12px;}
.brief-card{border:1px solid #cbd5e1;border-left:4px solid #0d9488;border-radius:6px;padding:16px 20px;margin:12px 0;background:white;}
.brief-card h4{margin-top:0;color:#0f766e;}
.brief-meta{background:#f0fdfa;padding:14px 18px;border-radius:6px;border-left:4px solid #14b8a6;margin:12px 0;}
.brief-meta table{width:100%;border-collapse:collapse;} .brief-meta td{padding:5px 8px;vertical-align:top;}
.brief-meta td:first-child{font-weight:700;color:#0f766e;width:200px;}
.slide-num{background:#0d9488;color:white;padding:4px 10px;border-radius:50%;font-weight:700;margin-right:10px;}
.visual-dir{background:#fef3c7;border-left:3px solid #f59e0b;padding:10px 14px;border-radius:4px;font-size:13px;color:#78350f;margin-top:10px;}
.badge-reel{background:#dc2626;color:white;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;}
.badge-carousel{background:#0284c7;color:white;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;}
.badge-brief-done{color:#16a34a;font-weight:700;font-size:11px;}
.badge-brief-none{color:#94a3b8;font-size:11px;}
</style>""", unsafe_allow_html=True)

st.title("🏥 AI Medical Content Planner RSPUR")

# ---------- SCHEMAS ----------
SCHEMA_EDITORIAL = """
{"kampanye":"...","periode":"...","ref":"EP-RSPUR-2026-WXX","total_konten":7,
"funnel_strategy":"3 TOFU | 3 MOFU | 1 BOFU","kanal":"IG, FB, YT, TikTok",
"verifikasi":"PERKI, AHA, Kemenkes","konten":[
{"tanggal":"Senin, 28 Sep 2026","funnel":"TOFU","topik":"...","format":"Carousel Infografis",
"kanal":"IG & FB","hook":"...","fakta":"...","isi":"...","cta":"...",
"narasumber":"dr. Nama, Sp.JP","tim":"Copywriter & Desainer","rujukan":"PERKI, AHA"}],
"disiapkan_oleh":"Tim Copywriter & Humas","verifikasi_oleh":"Tim Desain",
"disetujui_oleh":"dr. Nama, Sp.JP"}
"""

SCHEMA_BRIEF = """
{"judul":"...","format_platform":"Carousel - IG & FB","funnel_target":"MOFU - Edukasi",
"kategori":"Edukasi Medis & Preventif","narasumber":"dr. Nama, Sp.KFR","rencana_tayang":"27 Sep 2026",
"tujuan_strategis":"...","total_slide":6,"slides":[
{"nomor":1,"label_slide":"SLIDE 1 - HOOK","judul":"Headline Utama","headline":"...","subcopy":"...[Swipe >>]","isi":"","visual":"..."}],
"catatan_desain":["Warna latar putih/light teal (#f0fdfa)","Headline minimal 32pt pada 1080x1350px","Watermark logo RSPUR di sudut kanan atas"],
"diajukan_oleh":"Tim Marketing Digital & Humas RSPUR","disetujui_oleh":"dr. Nama, Sp.KFR"}
"""

# ---------- AI ----------
def call_groq(prompt, sys_msg, max_tokens=8000):
    for a in range(1, 3):
        try:
            r = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role":"system","content":sys_msg},{"role":"user","content":prompt}],
                temperature=0.3, max_tokens=max_tokens,
                response_format={"type":"json_object"})
            return r.choices[0].message.content
        except Exception as e:
            if a < 2: time.sleep(2)
            else: raise RuntimeError(f"Groq: {e}")

def call_cerebras(prompt, sys_msg, max_tokens=8000):
    if not CEREBRAS_API_KEY: raise RuntimeError("No CEREBRAS_API_KEY")
    for a in range(1, 3):
        try:
            r = requests.post(CEREBRAS_URL,
                headers={"Authorization":f"Bearer {CEREBRAS_API_KEY}","Content-Type":"application/json"},
                json={"model":CEREBRAS_MODEL,"messages":[{"role":"system","content":sys_msg},{"role":"user","content":prompt}],
                      "temperature":0.3,"max_tokens":max_tokens,"response_format":{"type":"json_object"}},
                timeout=180)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
            if r.status_code in (429,503): time.sleep(2**a)
            else: r.raise_for_status()
        except Exception as e:
            if a == 2: raise RuntimeError(f"Cerebras: {e}")

def call_ai_json(prompt, sys_msg, max_tokens=8000):
    try:
        st.write("🟢 Groq...")
        raw = call_groq(prompt, sys_msg, max_tokens)
    except Exception as e:
        st.write(f"⚠️ Groq gagal: {e}. Cerebras...")
        raw = call_cerebras(prompt, sys_msg, max_tokens)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)

# ---------- HELPERS ----------
def clean_html(h):
    return "\n".join(l.lstrip() if l.strip() else "" for l in h.split("\n"))

def funnel_badge(f):
    f = (f or "").upper()
    cls = {"TOFU":"funnel-tofu","MOFU":"funnel-mofu","BOFU":"funnel-bofu","COMBO":"funnel-combo"}.get(f,"funnel-tofu")
    return f'<span class="funnel {cls}">{f}</span>'

def format_badge(fmt):
    f = (fmt or "").lower()
    if "reel" in f or "video" in f or "tiktok" in f:
        return f'<span class="badge-reel">🎬 {fmt}</span>'
    return f'<span class="badge-carousel">🖼️ {fmt}</span>'

def editorial_to_html(data, briefs_map=None):
    rows = ""
    briefs_map = briefs_map or {}
    for i, k in enumerate(data.get("konten", [])):
        badge_brief = ('<span class="badge-brief-done">✅ Brief tersedia</span>'
                       if i in briefs_map else
                       '<span class="badge-brief-none">— Belum ada brief</span>')
        rows += f"""<tr>
        <td><div class="tanggal">{k.get('tanggal','')}</div>{funnel_badge(k.get('funnel',''))}</td>
        <td><div class="topik">{k.get('topik','')}</div>{format_badge(k.get('format',''))}<div class="kanal" style="margin-top:6px;">Kanal: {k.get('kanal','')}</div>{badge_brief}</td>
        <td><span class="label">HOOK</span> {k.get('hook','')}<br/><span class="label">FAKTA</span> {k.get('fakta','')}<br/><span class="label">ISI</span> {k.get('isi','')}<br/><span class="label">CTA</span> {k.get('cta','')}</td>
        <td><div class="nakes">Nakes:<br/>{k.get('narasumber','')}</div><div class="tim">Tim: {k.get('tim','')}</div></td>
        <td>{k.get('rujukan','')}</td></tr>"""
    return f"""<h2 style="color:#0f766e;">PERENCANAAN KONTEN & JADWAL PUBLIKASI (EDITORIAL PLAN)</h2>
    <p><b>{data.get('kampanye','')}</b> – Periode: {data.get('periode','')}</p>
    <p style="font-size:12px;color:#475569;"><b>Ref:</b> {data.get('ref','')} | <b>Total:</b> {data.get('total_konten','')} | <b>Funnel:</b> {data.get('funnel_strategy','')}<br/>
    <b>Kanal:</b> {data.get('kanal','')} | <b>Verifikasi:</b> {data.get('verifikasi','')}</p>
    <table class="rspur-table"><thead><tr>
    <th style="width:14%">TANGGAL & FUNNEL</th><th style="width:22%">TOPIK & FORMAT</th>
    <th style="width:34%">KONSEP COPYWRITING</th><th style="width:18%">NARASUMBER & TIM</th>
    <th style="width:12%">RUJUKAN</th></tr></thead><tbody>{rows}</tbody></table>
    <h3 style="color:#0f766e;">LEMBAR VERIFIKASI (SIGN-OFF BLOCK)</h3>
    <table class="rspur-table"><thead><tr><th>DISIAPKAN OLEH</th><th>VERIFIKASI MEDIS</th><th>DISETUJUI OLEH</th></tr></thead>
    <tbody><tr><td>{data.get('disiapkan_oleh','-')}</td><td>{data.get('verifikasi_oleh','-')}</td><td>{data.get('disetujui_oleh','-')}</td></tr></tbody></table>"""

def brief_to_html(data):
    meta = f"""<div class="brief-meta"><table>
    <tr><td>Judul / Topik</td><td><b>{data.get('judul','')}</b></td></tr>
    <tr><td>Format & Platform</td><td>{data.get('format_platform','')}</td></tr>
    <tr><td>Funnel Target</td><td>{data.get('funnel_target','')}</td></tr>
    <tr><td>Kategori Konten</td><td>{data.get('kategori','')}</td></tr>
    <tr><td>Narasumber / Reviewer</td><td>{data.get('narasumber','')}</td></tr>
    <tr><td>Rencana Tayang</td><td>{data.get('rencana_tayang','')}</td></tr>
    </table></div>"""
    slides_html = ""
    for s in data.get("slides", []):
        blk = ""
        if s.get("headline"): blk += f'<p><b>Headline:</b> "{s["headline"]}"</p>'
        if s.get("subcopy"):  blk += f'<p><b>Sub-copy:</b> {s["subcopy"]}</p>'
        if s.get("isi"):      blk += f'<p style="line-height:1.7;">{s["isi"]}</p>'
        slides_html += f"""<div class="brief-card">
        <div><span class="slide-num">{s.get('nomor','')}</span><b>{s.get('label_slide', s.get('judul',''))}</b></div>
        {blk}
        {f'<div class="visual-dir"><b>🎨 Visual Direction:</b> {s["visual"]}</div>' if s.get('visual') else ''}
        </div>"""
    catatan = ""
    if data.get("catatan_desain"):
        items = "".join([f"<li>{c}</li>" for c in data["catatan_desain"]])
        catatan = f'<div style="background:#f8fafc;padding:14px 18px;border-radius:6px;margin-top:20px;"><h4 style="color:#0f766e;margin-top:0;">CATATAN DESAIN</h4><ul>{items}</ul></div>'
    approval = f"""<div style="background:#f0fdfa;padding:14px 18px;border-radius:6px;margin-top:20px;border-left:4px solid #0d9488;">
    <h4 style="color:#0f766e;margin-top:0;">LEMBAR REVIEW & PERSETUJUAN MEDIS</h4>
    <p>☐ Setuju Tanpa Revisi &nbsp; ☐ Setuju Dengan Catatan Minor &nbsp; ☐ Perlu Perbaikan</p>
    <table style="width:100%"><tr><td><b>Diajukan:</b> {data.get('diajukan_oleh','-')}</td>
    <td><b>Disetujui:</b> {data.get('disetujui_oleh','-')}</td></tr></table></div>"""
    return f"""<h2 style="color:#0f766e;">RSPUR — BRIEF KONTEN EDUKASI MEDIS</h2>
    <p style="color:#475569;">Lembar Pengajuan & Review Materi Media Sosial</p>
    <p style="color:#0f766e;font-weight:700;font-size:12px;">MARKETING DIGITAL & HUMAS | Rencana Tayang: {data.get('rencana_tayang','')}</p>
    {meta}
    <h3 style="color:#0f766e;">Tujuan Strategis</h3><p style="line-height:1.7;">{data.get('tujuan_strategis','')}</p>
    <h3 style="color:#0f766e;">RANCANGAN NASKAH & SLIDE</h3>
    <p style="font-size:13px;color:#475569;"><b>Total:</b> {data.get('total_slide','')} Slide</p>
    {slides_html}{catatan}{approval}"""

def wrap_html(title, body):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title><style>
body{{font-family:Arial,sans-serif;padding:24px;color:#0f172a;}}
table.rspur-table{{width:100%;border-collapse:collapse;font-size:12px;}}
table.rspur-table th{{background:#0d9488;color:white;padding:8px;border:1px solid #0f766e;text-align:left;}}
table.rspur-table td{{padding:8px;border:1px solid #cbd5e1;vertical-align:top;}}
.funnel{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;color:white;font-weight:700;}}
.funnel-tofu{{background:#0284c7;}} .funnel-mofu{{background:#d97706;}}
.funnel-bofu{{background:#dc2626;}} .funnel-combo{{background:#7c3aed;}}
.brief-card{{border:1px solid #cbd5e1;border-left:4px solid #0d9488;padding:14px 18px;margin:12px 0;}}
.brief-meta{{background:#f0fdfa;padding:12px;border-radius:6px;}}
.brief-meta td{{padding:5px 8px;}} .brief-meta td:first-child{{font-weight:700;color:#0f766e;width:180px;}}
.visual-dir{{background:#fef3c7;border-left:3px solid #f59e0b;padding:10px;font-size:12px;}}
.slide-num{{background:#0d9488;color:white;padding:4px 10px;border-radius:50%;font-weight:700;margin-right:10px;}}
.label{{font-weight:700;color:#0f766e;}}
.badge-reel{{background:#dc2626;color:white;padding:2px 8px;border-radius:10px;font-size:10px;}}
.badge-carousel{{background:#0284c7;color:white;padding:2px 8px;border-radius:10px;font-size:10px;}}
</style></head><body>{body}</body></html>"""

def editorial_to_csv(data):
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["Tanggal","Funnel","Topik","Format","Kanal","Hook","Fakta","Isi","CTA","Narasumber","Tim","Rujukan"])
    for k in data.get("konten", []):
        w.writerow([k.get(x,"") for x in ["tanggal","funnel","topik","format","kanal","hook","fakta","isi","cta","narasumber","tim","rujukan"]])
    return buf.getvalue()

def brief_to_txt(data):
    """Export brief sebagai teks (untuk copy-paste cepat)."""
    lines = [f"BRIEF KONTEN: {data.get('judul','')}", "="*60,
             f"Format: {data.get('format_platform','')}",
             f"Funnel: {data.get('funnel_target','')}",
             f"Narasumber: {data.get('narasumber','')}",
             f"Tayang: {data.get('rencana_tayang','')}", "",
             f"TUJUAN: {data.get('tujuan_strategis','')}", "",
             f"RANCANGAN {data.get('total_slide','')} SLIDE:", "-"*60]
    for s in data.get("slides", []):
        lines.append(f"\n[Slide {s.get('nomor','')}] {s.get('label_slide', s.get('judul',''))}")
        if s.get("headline"): lines.append(f"  Headline : {s['headline']}")
        if s.get("subcopy"): lines.append(f"  Sub-copy : {s['subcopy']}")
        if s.get("isi"): lines.append(f"  Isi      : {s['isi']}")
        if s.get("visual"): lines.append(f"  Visual   : {s['visual']}")
    if data.get("catatan_desain"):
        lines.append("\nCATATAN DESAIN:")
        for c in data["catatan_desain"]: lines.append(f"  - {c}")
    return "\n".join(lines)

# ---------- FORM INPUT ----------
with st.form("form"):
    st.subheader("⚙️ Pengaturan Konten")
    c1, c2, c3 = st.columns(3)
    with c1:
        mode = st.selectbox("📋 Output Editorial:", ["Editorial Plan saja","Editorial + Brief (per konten)"])
    with c2:
        durasi = st.selectbox("📅 Rentang:", ["1 Minggu (7 hari)","3 Hari","2 Minggu (14 hari)"])
    with c3:
        format_mix = st.selectbox("🎬 Format Mix:", [
            "1 Reel + sisanya Carousel",
            "Semua Carousel",
            "2 Reel + sisanya Carousel",
            "1 Reel + 1 Video Panjang + sisanya Carousel",
            "Seimbang (AI bebas)"
        ])

    topik = st.text_area("🎯 Topik / Kampanye:",
        placeholder="Contoh: Kampanye Jantung Sehat 28 Sep - 4 Okt 2026, fokus deteksi dini & MCU",
        height=70)

    with st.expander("🏥 Batasan Kapasitas RS (opsional)", expanded=False):
        colA, colB = st.columns(2)
        with colA:
            fasilitas = st.text_area("Fasilitas & Alat:", placeholder="EKG, Echo, Cath Lab, treadmill, lab", height=68)
            dokter_ada = st.text_area("Dokter Spesialis:", placeholder="2 Sp.JP, 1 Sp.KFR, 1 Sp.OG", height=68)
        with colB:
            produksi = st.selectbox("Tingkat Produksi:",
                ["Rendah — Canva + HP","Sedang — video pendek + staf","Tinggi — videografer profesional","Maksimal — animasi/drone"])
            jam_ops = st.text_input("Jam Operasional:", placeholder="Poli 08.00-16.00, IGD 24 jam")
            limitasi = st.text_area("Limitasi:", placeholder="Tidak ada MRI, dokter anak terbatas", height=56)

    submitted = st.form_submit_button("🚀 Generate Editorial Plan", type="primary")

# ---------- GENERATE EDITORIAL ----------
if submitted:
    if not topik.strip():
        st.warning("⚠️ Topik wajib diisi!"); st.stop()

    constraints_list = []
    if fasilitas: constraints_list.append(f"- Fasilitas: {fasilitas}")
    if dokter_ada: constraints_list.append(f"- Dokter: {dokter_ada}")
    if produksi: constraints_list.append(f"- Produksi: {produksi}")
    if jam_ops: constraints_list.append(f"- Jam operasional: {jam_ops}")
    if limitasi: constraints_list.append(f"- Limitasi: {limitasi}")
    constraint_block = "\n".join(constraints_list) if constraints_list else "(tidak ada)"

    with st.status("🧠 Generate Editorial...", expanded=True) as status:
        try:
            st.write("🔍 Analisa tren...")
            analisis = call_ai_json(
                prompt=f"Analisis tren medis singkat untuk: {topik}.",
                sys_msg='Analis medis RSPUR. JSON: {"ringkasan":"...","poin":["..."]}',
                max_tokens=1200)

            st.write("📊 Menyusun Editorial Plan...")
            ed_data = call_ai_json(
                prompt=f"""Buat Editorial Plan RSPUR: "{topik}", durasi {durasi}.

FORMAT MIX WAJIB: {format_mix}
- Tentukan format tiap konten sesuai mix di atas.
- Field "format" harus spesifik: "Reel Video Vertikal 9:16", "Carousel Infografis 6 Slide", "Video Edukasi 3 Menit", "Foto Grafis", dll.

Konteks tren: {json.dumps(analisis, ensure_ascii=False)}

BATASAN RS (WAJIB DIPATUHI):
{constraint_block}

Skema JSON: {SCHEMA_EDITORIAL}

Aturan:
- Setiap konten: hook, fakta, isi, cta (semua wajib diisi).
- Nama dokter pakai gelar lengkap.
- Funnel bervariasi TOFU/MOFU/BOFU.
- Rujukan: PERKI, AHA, WHO, POGI, Kemenkes.
- Konten HANYA yang bisa dieksekusi dengan kapasitas RS di atas.""",
                sys_msg="Senior Content Planner RSPUR. Output JSON valid, realistis.",
                max_tokens=8000)

            st.session_state.editorial_data = ed_data
            st.session_state.briefs = {}  # reset briefs
            st.session_state.constraints = constraint_block
            st.session_state.generated = True
            status.update(label="✅ Editorial Plan selesai!", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ Error!", state="error", expanded=True)
            st.error(f"Detail: {str(e)}"); st.stop()

# ---------- RENDER HASIL ----------
if st.session_state.get("generated") and st.session_state.editorial_data:
    ed_data = st.session_state.editorial_data

    st.markdown("---")
    edit_mode = st.toggle("🔧 Mode Edit", value=False,
        help="Preview: tampilan final. Edit: ubah langsung di tabel/form.")

    tab1, tab2 = st.tabs(["📊 Editorial Plan", "📝 Brief per Konten"])

    # ===== TAB 1: EDITORIAL =====
    with tab1:
        if edit_mode:
            st.markdown("**Edit tabel — klik cell untuk ubah, `+` untuk tambah baris:**")
            df = pd.DataFrame(ed_data["konten"])
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=500,
                column_config={
                    "funnel": st.column_config.SelectboxColumn("Funnel", options=["TOFU","MOFU","BOFU","COMBO"], required=True),
                    "hook": st.column_config.TextColumn("Hook", width="large"),
                    "fakta": st.column_config.TextColumn("Fakta", width="large"),
                    "isi": st.column_config.TextColumn("Isi", width="large"),
                    "cta": st.column_config.TextColumn("CTA", width="large"),
                }, key="ed_editor")
            if st.button("💾 Simpan Editorial", type="primary"):
                st.session_state.editorial_data["konten"] = edited.to_dict("records")
                st.success("✅ Tersimpan!"); st.rerun()
        else:
            st.markdown(clean_html(editorial_to_html(ed_data, st.session_state.briefs)), unsafe_allow_html=True)

    # ===== TAB 2: BRIEF PER KONTEN =====
    with tab2:
        konten_list = ed_data.get("konten", [])
        if not konten_list:
            st.info("Editorial Plan masih kosong.")
        else:
            # Dropdown pilih konten
            options = [f"{i+1}. {k.get('tanggal','')} — {k.get('topik','')} [{k.get('format','')}]"
                       for i, k in enumerate(konten_list)]
            idx_sel = st.selectbox("📌 Pilih konten yang mau dibuat brief:",
                range(len(options)), format_func=lambda i: options[i], key="brief_selector")

            konten = konten_list[idx_sel]
            brief_key = idx_sel

            # Info konten terpilih
            with st.container(border=True):
                st.markdown(f"**{konten.get('topik','')}**")
                cc1, cc2, cc3 = st.columns(3)
                cc1.markdown(f"**📅 Tanggal:** {konten.get('tanggal','')}")
                cc2.markdown(f"**🎬 Format:** {konten.get('format','')}")
                cc3.markdown(f"**🎯 Funnel:** {konten.get('funnel','')}")
                st.markdown(f"**🪝 Hook:** {konten.get('hook','')}")
                st.markdown(f"**👨‍⚕️ Nakes:** {konten.get('narasumber','')}")

            # Cek apakah brief sudah ada
            brief_exists = brief_key in st.session_state.briefs

            col_btn1, col_btn2, col_status = st.columns([1, 1, 2])
            with col_btn1:
                if not brief_exists:
                    btn_generate = st.button("📝 Buat Brief untuk Konten Ini", type="primary", use_container_width=True)
                else:
                    btn_generate = st.button("🔄 Regenerate Brief", use_container_width=True)
            with col_btn2:
                if brief_exists:
                    if st.button("🗑️ Hapus Brief", use_container_width=True):
                        del st.session_state.briefs[brief_key]
                        st.rerun()
            with col_status:
                if brief_exists:
                    st.markdown("✅ **Brief sudah tersedia** — siap diedit atau di-export")
                else:
                    st.markdown("⏳ Belum ada brief untuk konten ini")

            # Generate brief
            if btn_generate:
                with st.status(f"✍️ Menyusun brief untuk: {konten.get('topik','')}", expanded=True) as status:
                    try:
                        brief = call_ai_json(
                            prompt=f"""Buat Brief Konten detail RSPUR untuk konten berikut:

JUDUL/TOPIK: {konten.get('topik','')}
FORMAT: {konten.get('format','')}
KANAL: {konten.get('kanal','')}
FUNNEL: {konten.get('funnel','')}
HOOK: {konten.get('hook','')}
FAKTA: {konten.get('fakta','')}
ISI: {konten.get('isi','')}
CTA: {konten.get('cta','')}
NARASUMBER: {konten.get('narasumber','')}
RUJUKAN: {konten.get('rujukan','')}

BATASAN RS: {st.session_state.get('constraints','')}

Skema JSON: {SCHEMA_BRIEF}

Aturan:
- Brief ini HARUS konsisten dengan editorial di atas (topik, format, CTA).
- Jika format = Reel/Video → buat script per detik (00:00-00:05 dst), bukan slide carousel.
- Jika format = Carousel → buat slide 1 sampai terakhir.
- Minimal 5-7 slide/scene.
- Slide/scene pertama = Hook, terakhir = CTA.
- Setiap slide/scene punya visual direction detail.
- Nama dokter pakai gelar lengkap.""",
                            sys_msg="Senior Copywriter Medis RSPUR. Output JSON valid, realistis.",
                            max_tokens=8000)

                        st.session_state.briefs[brief_key] = brief
                        status.update(label="✅ Brief selesai!", state="complete", expanded=False)
                        st.rerun()
                    except Exception as e:
                        status.update(label="❌ Error!", state="error", expanded=True)
                        st.error(f"Detail: {str(e)}")

            # Tampilkan brief jika ada
            if brief_exists:
                brief = st.session_state.briefs[brief_key]
                st.markdown("---")

                if edit_mode:
                    st.markdown("**Edit field brief di bawah:**")
                    brief["judul"] = st.text_input("Judul", brief.get("judul",""), key=f"bj_{brief_key}")
                    brief["tujuan_strategis"] = st.text_area("Tujuan Strategis", brief.get("tujuan_strategis",""), height=80, key=f"bt_{brief_key}")
                    brief["narasumber"] = st.text_input("Narasumber", brief.get("narasumber",""), key=f"bn_{brief_key}")
                    brief["format_platform"] = st.text_input("Format & Platform", brief.get("format_platform",""), key=f"bf_{brief_key}")
                    brief["funnel_target"] = st.text_input("Funnel Target", brief.get("funnel_target",""), key=f"bfn_{brief_key}")

                    st.markdown("---")
                    for i, s in enumerate(brief.get("slides", [])):
                        with st.expander(f"Slide {s.get('nomor','')} — {s.get('label_slide', s.get('judul',''))}", expanded=False):
                            s["label_slide"] = st.text_input("Label", s.get("label_slide",""), key=f"sl_{brief_key}_{i}")
                            s["headline"] = st.text_input("Headline", s.get("headline",""), key=f"sh_{brief_key}_{i}")
                            s["subcopy"] = st.text_area("Sub-copy", s.get("subcopy",""), height=68, key=f"ss_{brief_key}_{i}")
                            s["isi"] = st.text_area("Isi", s.get("isi",""), height=100, key=f"si_{brief_key}_{i}")
                            s["visual"] = st.text_area("Visual Direction", s.get("visual",""), height=68, key=f"sv_{brief_key}_{i}")

                    if st.button("💾 Simpan Brief", type="primary", key=f"save_b_{brief_key}"):
                        st.session_state.briefs[brief_key] = brief
                        st.success("✅ Brief tersimpan!"); st.rerun()
                else:
                    st.markdown(clean_html(brief_to_html(brief)), unsafe_allow_html=True)

                # Export brief ini
                st.markdown("---")
                ec1, ec2, ec3 = st.columns(3)
                safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", konten.get("topik","brief"))[:40]
                with ec1:
                    st.download_button("📝 Brief (Word/HTML)",
                        data=wrap_html("Brief Konten RSPUR", brief_to_html(brief)),
                        file_name=f"brief_{brief_key+1}_{safe_name}.html",
                        mime="text/html", use_container_width=True)
                with ec2:
                    st.download_button("📋 Brief (TXT)",
                        data=brief_to_txt(brief),
                        file_name=f"brief_{brief_key+1}_{safe_name}.txt",
                        mime="text/plain", use_container_width=True,
                        help="Copy-paste cepat ke WA/email")
                with ec3:
                    st.download_button("🗂️ Brief (JSON)",
                        data=json.dumps(brief, ensure_ascii=False, indent=2),
                        file_name=f"brief_{brief_key+1}_{safe_name}.json",
                        mime="application/json", use_container_width=True,
                        help="Backup — bisa di-import kembali")

    # ---------- EXPORT EDITORIAL ----------
    st.markdown("---")
    st.subheader("📥 Export Editorial Plan")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📊 Editorial (CSV/Excel)",
            data=editorial_to_csv(ed_data),
            file_name="editorial_plan_rspur.csv", mime="text/csv",
            use_container_width=True)
    with c2:
        st.download_button("📄 Editorial (Word/HTML)",
            data=wrap_html("Editorial Plan RSPUR", editorial_to_html(ed_data, st.session_state.briefs)),
            file_name="editorial_plan_rspur.html", mime="text/html",
            use_container_width=True)
    with c3:
        total_briefs = len(st.session_state.briefs)
        total_konten = len(ed_data.get("konten", []))
        st.metric("Brief Dibuat", f"{total_briefs} / {total_konten}")

    # ---------- RESET ----------
    st.markdown("---")
    if st.button("🔄 Reset & Buat Kampanye Baru"):
        for k in ["editorial_data","briefs","generated","constraints","brief_selector","ed_editor"]:
            st.session_state.pop(k, None)
        st.rerun()
