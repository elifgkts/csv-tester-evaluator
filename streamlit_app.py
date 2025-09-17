# -*- coding: utf-8 -*-

# 📌 Test Case Evaluator — v1.1.0 (Key Prefix Filter eklendi)
# - Tablo (A/B/C/D) İHTİYAÇ analiziyle belirlenir
# - Key prefix (örn. QB284050, QM284050) sidebar’dan filtrelenebilir

import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

# ---------- Sayfa & Stil ----------
st.set_page_config(page_title="Test Case SLA", layout="wide")

CUSTOM_CSS = """..."""  # senin CSS bloğun aynı kalıyor
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(f"""
<div class="app-hero">
  <h1>📋 Test Case Kalite Değerlendirmesi</h1>
  <p><span style="opacity:0.8">Rapor zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span></p>
</div>
""", unsafe_allow_html=True)

with st.expander("📌 Kurallar", expanded=False):
    st.markdown("""
- **CSV ayraç:** `;`  
- **Gerekli sütunlar:** `Issue key/Issue Key`, `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`  
- **Precondition sütunları (CSV):**  
  - `Custom field (Tests association with a Pre-Condition)`  
  - `Custom field (Pre-Conditions association with a Test)`  
- **Tablo mantığı (ihtiyaca göre):** **A** Data/Pre olmasa da olabilir • **B** Pre gerekli • **C** Data gerekli • **D** Data+Pre gerekli  
- **D override:** Hem Data (steps JSON’unda **“Data”** alanı) hem Pre (CSV) mevcutsa → **D**  
- **✏️ Expected yazım puan kırma:** Expected Result geçmiş/olup-bitti anlatımı içerirse 1–5 puan kesilir.
""")

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
def _cell(x): ...
def _is_blank_after_strip(val: str) -> bool: ...
def _normalize_newlines(s: str) -> str: ...
def _cleanup_html(s: str) -> str: ...
def _is_meaningless(val: str) -> bool: ...
def pick_first_existing(colnames, df_cols): ...

# ✅ Key prefix çıkarıcı
def _key_prefix(val: str) -> str:
    v = _text(val)
    m = re.match(r'^\s*([^\-\s]+)', v)
    return m.group(1) if m else ""

# ---- Steps JSON parse & field extract ----
def parse_steps(steps_cell): ...
def get_action_blocks(steps_list): ...
def get_data_blocks(steps_list): ...
def get_expected_blocks(steps_list): ...
def has_data_written_from_steps(steps_list) -> bool: ...
def has_expected_present_from_steps(steps_list) -> bool: ...

# ---- PRECONDITION (CSV doluluğu) ----
PRECOND_EXACT_COLS = [...]
def precondition_provided_from_csv(row, df_cols) -> bool: ...
def get_pre_assoc_text(row, df_cols) -> str: ...

# ---- İçerik sinyalleri ----
def _match(pattern, text): ...
def scan_precond_signals(text: str): ...
def scan_data_signals_from_text(text: str): ...
def decide_data_needed(summary, action_texts, expected_texts): ...
def decide_precond_needed(summary, action_texts, pre_assoc_text): ...

# ---- Tablo kararı ----
def choose_table(...): ...

# ---- Expected yazım cezası ----
_EXPECT_PAST_WORDS = r"..."
_EXPECT_PAST_REGEXES = [...]
def expected_style_hits(text: str) -> int: ...
def expected_style_penalty(blocks: list[str]) -> tuple[int, int]: ...

# ---- Stepler kuralı ----
PASSIVE_PATTERNS = re.compile(r"...", re.I)
def block_has_many_substeps(text: str) -> bool: ...

# ---- Test Tipi (Backend/UI) ----
def detect_test_type(...): ...

# ---------- Skorlama ----------
def score_one(row, df_cols, debug=False): ...
# (senin score_one fonksiyonun aynen duruyor)

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

    # KPI, tablo, grafik, detay kartları (senin mevcut bloklar aynen devam ediyor)
    # ...
