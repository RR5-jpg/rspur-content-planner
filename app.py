import os, io, csv, json, time, random, re
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
</style>""", unsafe_allow_html=True)

st.title("🏥 AI Medical Content Planner RSPUR")

# ---------- SCHEMAS ----------
SCHEMA_EDITORIAL = """
{"kampanye":"...","periode":"...","ref":"EP-RSPUR-2026-WXX","total_konten":7,
"funnel_strategy":"3 TOFU | 3 MOFU | 1 BOFU","kanal":"IG, FB, YT, TikTok",
"verifikasi":"PERKI, AHA, Kemenkes","konten":[
{"tanggal":"Senin, 28 Sep 2026","funnel":"TOFU","topik":"...","format":"Karosel Infografis",
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

# ---------- AI CALLS ----------
def call_groq(prompt, sys_msg, max_tokens=8000):
    for attempt in range(1, 3):
        try:
            r = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role":"system","content":sys_msg},{"role":"user","content":prompt}],
                temperature=0.3, max_tokens=max_tokens,
                response_format={"type":"json_object"})
            return r.choices[0].message.content
        except Exception as e:
            if attempt < 2: time.sleep(2)
            else: raise RuntimeError(f"Groq gagal: {e}")

def call_cerebras(prompt, sys_msg, max_tokens=8000):
    if not CEREBRAS_API_KEY: raise RuntimeError("CEREBRAS_API_KEY tidak ada.")
    for attempt in range(1, 3):
        try:
            r = requests.post(CEREBRAS_URL,
                headers={"Authorization":f"Bearer {CEREBRAS_API_KEY}","Content-Type":"application/json"},
                json={"model":CEREBRAS_MODEL,"messages":[{"role":"system","content":sys_msg},{"role":"user","content":prompt}],
                      "temperature":0.3,"max_tokens":max_tokens,"response_format":{"type":"json_object"}},
                timeout=180)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
            if r.status_code in (429,503): time.sleep(2**attempt)
            else: r.raise_for_status()
        except Exception as e:
            if attempt == 2: raise RuntimeError(f"Cerebras gagal: {e}")

def call_ai_json(prompt, sys_msg, max_tokens=8000):
    try:
        st.write("🟢 Memproses via Groq...")
        raw = call_groq(prompt, sys_msg, max_tokens)
    except Exception as e:
        st.write(f"⚠️ Groq gagal: {e}. Beralih ke Cerebras...")
        raw = call_cerebras(prompt, sys_msg, max_tokens)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)

# ---------- HELPERS ----------
def clean_html(h):
    return "\n".join(line.lstrip() if line.strip() else "" for line in h.split("\n"))

def funnel_badge(f):
    f = (f or "").upper()
    cls = {"TOFU":"funnel-tofu","MOFU":"funnel-mofu","BOFU":"funnel-bofu","COMBO":"funnel-combo"}.get(f,"funnel-tofu")
    return f'<span class="funnel {cls}">{f}</span>'

def editorial_to_html(data):
    rows = ""
    for k in data.get("konten", []):
        rows += f"""<tr>
        <td><div class="tanggal">{k.get('tanggal','')}</div>{funnel_badge(k.get('funnel',''))}</td>
        <td><div class="topik">{k.get('topik','')}</div><div class="format">Format: {k.get('format','')}</div><div class="kanal">Kanal: {k.get('kanal','')}</div></td>
        <td><span class="label">HOOK</span> {k.get('hook','')}<br/><span class="label">FAKTA</span> {k.get('fakta','')}<br/><span class="label">ISI</span> {k.get('isi','')}<br/><span class="label">CTA</span> {k.get('cta','')}</td>
        <td><div class="nakes">Nakes:<br/>{k.get('narasumber','')}</div><div class="tim">Tim: {k.get('tim','')}</div></td>
        <td>{k.get('rujukan','')}</td></tr>"""
    return f"""<h2 style="color:#0f766e;">PERENCANAAN KONTEN & JADWAL PUBLIKASI (EDITORIAL PLAN)</h2>
    <p><b>{data.get('kampanye','')}</b> – Periode: {data.get('periode','')}</p>
    <p style="font-size:12px;color:#475569;"><b>Ref:</b> {data.get('ref','')} | <b>Total:</b> {data.get('total_konten','')} | <b>Funnel:</b> {data.get('funnel_strategy','')}<br/>
    <b>Kanal:</b> {data.get('kanal','')} | <b>Verifikasi:</b> {data.get('verifikasi','')}</p>
    <table class="rspur-table"><thead><tr>
    <th style="width:14%">TANGGAL & FUNNEL</th><th style="width:20%">TOPIK & FORMAT</th>
    <th style="width:36%">KONSEP COPYWRITING</th><th style="width:18%">NARASUMBER & TIM</th>
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
    <h3 style="color:#0f766e;">RANCANGAN NASKAH & SLIDE CAROUSEL</h3>
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
.label{{font-weight:700;color:#0f766e;}}</style></head><body>{body}</body></html>"""

def editorial_to_csv(data):
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["Tanggal","Funnel","Topik","Format","Kanal","Hook","Fakta","Isi","CTA","Narasumber","Tim","Rujukan"])
    for k in data.get("konten", []):
        w.writerow([k.get(x,"") for x in ["tanggal","funnel","topik","format","kanal","hook","fakta","isi","cta","narasumber","tim","rujukan"]])
    return buf.getvalue()

# ---------- UI FORM ----------
with st.form("form"):
    st.subheader("⚙️ Pengaturan Konten")
    c1, c2 = st.columns(2)
    with c1:
        mode = st.selectbox("📋 Jenis Output:", ["📊 Editorial Plan","📝 Brief Konten","📚 Keduanya"])
    with c2:
        durasi = st.selectbox("📅 Rentang:", ["1 Hari","3 Hari","1 Minggu (7 hari)","2 Minggu (14 hari)"])

    topik = st.text_area("🎯 Topik / Kampanye:",
        placeholder="Contoh: Kampanye Jantung Sehat 28 Sep - 4 Okt 2026, fokus deteksi dini & MCU",
        height=80)

    # ================= BATASAN KAPASITAS RS =================
    with st.expander("🏥 Batasan Kapasitas RS (opsional — agar ide realistis & bisa dieksekusi)", expanded=False):
        st.caption("Isi yang Anda tahu. AI akan menyesuaikan konten dengan kapasitas nyata RSPUR.")
        colA, colB = st.columns(2)
        with colA:
            fasilitas = st.text_area("Fasilitas & Alat Tersedia:",
                placeholder="Contoh: EKG, Echo, Cath Lab, treadmill, USG, X-Ray, lab lengkap",
                height=80)
            dokter_ada = st.text_area("Dokter Spesialis yang Ada:",
                placeholder="Contoh: 2 Sp.JP, 1 Sp.KFR, 1 Sp.OG, 3 dokter umum",
                height=80)
        with colB:
            budget = st.selectbox("Tingkat Produksi Konten:",
                ["Rendah — Canva + foto HP",
                 "Sedang — video pendek + talent staf",
                 "Tinggi — live streaming + videografer profesional",
                 "Maksimal — animasi, drone, talent eksternal"])
            jam_ops = st.text_input("Jam Operasional Layanan:",
                placeholder="Contoh: Poli 08.00-16.00, IGD 24 jam")
            limitasi = st.text_area("Limitasi / Catatan Khusus:",
                placeholder="Contoh: tidak ada alat MRI, dokter anak terbatas",
                height=68)

    submitted = st.form_submit_button("🚀 Buat Konten Sekarang")

# ---------- GENERATE ----------
if submitted:
    if not topik.strip():
        st.warning("⚠️ Topik wajib diisi!"); st.stop()

    # Bangun constraint context
    constraints = []
    if fasilitas: constraints.append(f"- Fasilitas/alat tersedia: {fasilitas}")
    if dokter_ada: constraints.append(f"- Dokter spesialis: {dokter_ada}")
    if budget: constraints.append(f"- Tingkat produksi: {budget}")
    if jam_ops: constraints.append(f"- Jam operasional: {jam_ops}")
    if limitasi: constraints.append(f"- Limitasi: {limitasi}")
    constraint_block = "\n".join(constraints) if constraints else "(tidak ada batasan khusus)"

    with st.status("🧠 Memproses...", expanded=True) as status:
        try:
            st.write("🔍 Analisa tren...")
            analisis = call_ai_json(
                prompt=f"Analisis tren medis singkat untuk: {topik}.",
                sys_msg='Analis medis RSPUR. JSON: {"ringkasan":"...","poin":["..."]}',
                max_tokens=1200)

            ed_data, br_data = None, None

            if mode.startswith("📊") or mode.startswith("📚"):
                st.write("📊 Menyusun Editorial Plan...")
                ed_data = call_ai_json(
                    prompt=f"""Buat Editorial Plan RSPUR: "{topik}", durasi {durasi}.

Konteks tren: {json.dumps(analisis, ensure_ascii=False)}

BATASAN KAPASITAS RS (WAJIB DIPATUHI):
{constraint_block}

Skema JSON: {SCHEMA_EDITORIAL}

Aturan:
- Setiap konten punya hook, fakta, isi, cta (semua tidak boleh kosong).
- Nama dokter pakai gelar lengkap.
- Funnel bervariasi: TOFU/MOFU/BOFU.
- Rujukan: PERKI, AHA, WHO, POGI, Kemenkes.
- Konten HANYA yang bisa dieksekusi dengan fasilitas/dokter/budget di atas.
- Jangan pakai alat atau layanan yang tidak tersedia di RS.""",
                    sys_msg="Senior Content Planner RSPUR. Output JSON valid, realistis sesuai kapasitas RS.",
                    max_tokens=8000)

            if mode.startswith("📝") or mode.startswith("📚"):
                st.write("📝 Menyusun Brief Konten...")
                br_data = call_ai_json(
                    prompt=f"""Buat Brief Konten RSPUR: "{topik}".

Konteks tren: {json.dumps(analisis, ensure_ascii=False)}

BATASAN KAPASITAS RS (WAJIB DIPATUHI):
{constraint_block}

Skema JSON: {SCHEMA_BRIEF}

Aturan:
- Minimal 6 slide carousel.
- Slide 1 = Hook, terakhir = CTA/Closing.
- Setiap slide punya visual direction yang detail.
- Visual HANYA yang bisa dibuat dengan tingkat produksi di atas.
- Nama dokter pakai gelar lengkap.""",
                    sys_msg="Senior Copywriter Medis RSPUR. Output JSON valid, realistis.",
                    max_tokens=8000)

            # Simpan ke session_state
            st.session_state.editorial_data = ed_data
            st.session_state.brief_data = br_data
            st.session_state.generated = True

            status.update(label="✅ Konten Berhasil Dibuat!", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ Error!", state="error", expanded=True)
            st.error(f"Detail: {str(e)}"); st.stop()

# ---------- RENDER (di luar form) ----------
if st.session_state.get("generated"):
    ed_data = st.session_state.get("editorial_data")
    br_data = st.session_state.get("brief_data")

    st.markdown("---")

    # Toggle mode edit
    col_tgl, col_info = st.columns([1, 3])
    with col_tgl:
        edit_mode = st.toggle("🔧 Mode Edit", value=False)
    with col_info:
        if edit_mode:
            st.caption("✏️ **Mode Edit aktif** — ubah langsung di tabel/form. Perubahan otomatis tersimpan.")
        else:
            st.caption("👁️ **Mode Preview** — tampilan final. Aktifkan Mode Edit untuk mengubah.")

    if ed_data and br_data:
        tab1, tab2 = st.tabs(["📊 Editorial Plan", "📝 Brief Konten"])
    elif ed_data:
        tab1 = st.container(); tab2 = None
    else:
        tab1 = None; tab2 = st.container()

    # ===== EDITORIAL TAB =====
    if ed_data:
        with (tab1 if ed_data and br_data else tab1):
            if edit_mode:
                st.markdown("**Edit tabel di bawah — seperti Excel:**")
                df = pd.DataFrame(ed_data["konten"])
                edited = st.data_editor(
                    df, num_rows="dynamic", use_container_width=True, height=500,
                    column_config={
                        "funnel": st.column_config.SelectboxColumn("Funnel", options=["TOFU","MOFU","BOFU","COMBO"], required=True),
                        "hook": st.column_config.TextColumn("Hook", width="large"),
                        "fakta": st.column_config.TextColumn("Fakta", width="large"),
                        "isi": st.column_config.TextColumn("Isi", width="large"),
                        "cta": st.column_config.TextColumn("CTA", width="large"),
                    },
                    key="ed_edit")
                if st.button("💾 Simpan Perubahan Editorial", type="primary"):
                    st.session_state.editorial_data["konten"] = edited.to_dict("records")
                    st.success("✅ Editorial tersimpan!")
                    st.rerun()
            else:
                st.markdown(clean_html(editorial_to_html(ed_data)), unsafe_allow_html=True)

    # ===== BRIEF TAB =====
    if br_data:
        with (tab2 if ed_data and br_data else tab2):
            if edit_mode:
                st.markdown("**Edit field per slide di bawah:**")
                # Field utama
                br_data["judul"] = st.text_input("Judul", br_data.get("judul",""), key="b_judul")
                br_data["tujuan_strategis"] = st.text_area("Tujuan Strategis", br_data.get("tujuan_strategis",""), height=80, key="b_tujuan")
                br_data["narasumber"] = st.text_input("Narasumber", br_data.get("narasumber",""), key="b_nakes")
                br_data["format_platform"] = st.text_input("Format & Platform", br_data.get("format_platform",""), key="b_fmt")
                br_data["funnel_target"] = st.text_input("Funnel Target", br_data.get("funnel_target",""), key="b_fn")

                st.markdown("---")
                st.markdown("**Slides:**")
                for i, s in enumerate(br_data.get("slides", [])):
                    with st.expander(f"Slide {s.get('nomor','')} — {s.get('label_slide', s.get('judul',''))}", expanded=False):
                        s["label_slide"] = st.text_input("Label Slide", s.get("label_slide",""), key=f"s_label_{i}")
                        s["headline"] = st.text_input("Headline", s.get("headline",""), key=f"s_head_{i}")
                        s["subcopy"] = st.text_area("Sub-copy", s.get("subcopy",""), height=68, key=f"s_sub_{i}")
                        s["isi"] = st.text_area("Isi", s.get("isi",""), height=100, key=f"s_isi_{i}")
                        s["visual"] = st.text_area("Visual Direction", s.get("visual",""), height=68, key=f"s_vis_{i}")

                if st.button("💾 Simpan Perubahan Brief", type="primary"):
                    st.session_state.brief_data = br_data
                    st.success("✅ Brief tersimpan!")
                    st.rerun()
            else:
                st.markdown(clean_html(brief_to_html(br_data)), unsafe_allow_html=True)

    # ---------- EXPORT ----------
    st.markdown("---")
    st.subheader("📥 Export & Share")

    ed_data = st.session_state.get("editorial_data")
    br_data = st.session_state.get("brief_data")
    c1, c2, c3 = st.columns(3)

    if ed_data:
        with c1:
            st.download_button("📊 Editorial (CSV/Excel)",
                data=editorial_to_csv(ed_data),
                file_name="editorial_plan_rspur.csv", mime="text/csv",
                use_container_width=True,
                help="Buka di Excel/Google Sheets, edit & share link")
        with c2:
            st.download_button("📄 Editorial (Word/HTML)",
                data=wrap_html("Editorial Plan RSPUR", editorial_to_html(ed_data)),
                file_name="editorial_plan_rspur.html", mime="text/html",
                use_container_width=True,
                help="Buka di Word/Google Docs → layout persis")
    if br_data:
        with c3:
            st.download_button("📝 Brief (Word/HTML)",
                data=wrap_html("Brief Konten RSPUR", brief_to_html(br_data)),
                file_name="brief_konten_rspur.html", mime="text/html",
                use_container_width=True,
                help="Buka di Word/Google Docs → layout persis")

    # Reset
    st.markdown("---")
    if st.button("🔄 Reset & Buat Konten Baru"):
        for k in ["editorial_data","brief_data","generated"]:
            st.session_state.pop(k, None)
        st.rerun()
