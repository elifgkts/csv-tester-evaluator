# -*- coding: utf-8 -*-

# 📌 Test Case Evaluator — v1.1.0 (Key Prefix Filter eklendi)

import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

# ---------- Sayfa & Stil ----------
st.set_page_config(page_title="Test Case SLA", layout="wide")

CUSTOM_CSS = """
<style>
/* senin CSS bloğun – olduğu gibi buraya yapıştırabilirsin */
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(f"""
<div class="app-hero">
  <h1>📋 Test Case Kalite Değerlendirmesi</h1>
  <p><span style="opacity:0.8">Rapor zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span></p>
</div>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
st.sidebar.header("⚙️ Ayarlar")
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 300, 5)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
show_debug = st.sidebar.toggle("🛠 Debug (sinyaller & kararlar)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x): return str(x or "")
def _cell(x):
    try:
        if pd.isna(x): return ""
    except Exception:
        pass
    return str(x or "")
def _is_blank_after_strip(val: str) -> bool:
    return len((val or "").strip()) == 0
def pick_first_existing(colnames, df_cols):
    for name in colnames:
        if name in df_cols: return name
    return None

# ✅ Key prefix çıkarıcı
def _key_prefix(val: str) -> str:
    v = _text(val)
    m = re.match(r'^\s*([^\-\s]+)', v)
    return m.group(1) if m else ""

# (tüm senin fonksiyonların buraya gelecek: parse_steps, get_action_blocks, 
# get_data_blocks, get_expected_blocks, precondition_provided_from_csv, 
# choose_table, expected_style_penalty, block_has_many_substeps, 
# detect_test_type, score_one, vs. — bunlarda hiç değişiklik yok)

# ---------- Çalıştır ----------
if uploaded:
    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    # ✅ Prefix sütunu üret ve sidebar filtre ekle
    key_col_name = pick_first_existing(['Issue key', 'Issue Key', 'Key', 'IssueKey'], df.columns)
    if key_col_name:
        df['_KeyRaw'] = df[key_col_name].astype(str)
        df['_Prefix'] = df['_KeyRaw'].apply(_key_prefix)

        prefix_options = sorted([p for p in df['_Prefix'].unique() if p])
        selected_prefixes = st.sidebar.multiselect(
            "🔎 Projeye göre filtrele (Key prefix)",
            options=prefix_options,
            help="Key değerindeki '-' öncesi kısma göre filtreler (örn. QB284050, QM284050)."
        )
        if selected_prefixes:
            df = df[df['_Prefix'].isin(selected_prefixes)]

    # Örnekleme
    n = min(sample_size, len(df))
    rstate = (123 + st.session_state.reroll) if fix_seed else None
    sample = df.sample(n=n, random_state=rstate) if len(df) > 0 else df

    # Skorla
    results = sample.apply(lambda r: score_one(r, df.columns, debug=show_debug), axis=1, result_type='expand')

    # (senin KPI / chart / tablo / detay kartları kodun burada aynı şekilde devam ediyor)
