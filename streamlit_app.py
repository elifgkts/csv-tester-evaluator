# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v2.9.3
# - Precondition SADECE şu iki CSV sütunundan anlamlı içerik varsa var sayılır:
#   • Custom field (Tests association with a Pre-Condition)
#   • Custom field (Pre-Conditions association with a Test)
# - Boş/işlevsiz değerler ([], {}, -, none, null, yok, yalnızca noktalama/boşluk) PUAN getirmez.
# - Tablo tayini: içerik analizi (ihtiyaç) + override (hem data hem pre CSV doluysa → D)
# - Data/Expected puanlaması steps’te gerçek varlığa göre; Pre yalnız CSV’den.

import streamlit as st
import pandas as pd
import re
import html
from datetime import datetime

st.set_page_config(page_title="Test Case SLA", layout="wide")

CUSTOM_CSS = """
<style>
:root{
  --bg-card:#ffffff; --text-strong:#0f172a; --text-soft:#475569; --text-sub:#64748b; --border:rgba(2,6,23,0.08);
  --badge-a-bg:#eef2ff; --badge-a-fg:#3730a3; --badge-a-bd:#c7d2fe;
  --badge-b-bg:#ecfeff; --badge-b-fg:#155e75; --badge-b-bd:#a5f3fc;
  --badge-c-bg:#fef9c3; --badge-c-fg:#854d0e; --badge-c-bd:#fde68a;
  --badge-d-bg:#fee2e2; --badge-d-fg:#991b1b; --badge-d-bd:#fecaca;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg-card:#0b1220; --text-strong:#e5ecff; --text-soft:#c7d2fe; --text-sub:#94a3b8; --border:rgba(148,163,184,0.25);
    --badge-a-bg:#1e1b4b; --badge-a-fg:#c7d2fe; --badge-a-bd:#3730a3;
    --badge-b-bg:#083344; --badge-b-fg:#99f6e4; --badge-b-bd:#155e75;
    --badge-c-bg:#3f3f1e; --badge-c-fg:#fde68a; --badge-c-bd:#854d0e;
    --badge-d-bg:#431313; --badge-d-fg:#fecaca; --badge-d-bd:#991b1b;
  }
}
#MainMenu, footer {visibility:hidden;}
.app-hero{background:linear-gradient(135deg,#1f6feb 0%,#0ea5e9 100%);color:#fff;padding:18px 22px;border-radius:14px;margin-bottom:18px;box-shadow:0 8px 24px rgba(2,6,23,0.18)}
.app-hero h1{font-size:24px;margin:0 0 6px 0;line-height:1.2;color:#fff}
.app-hero p{margin:0;opacity:.95;color:#fff}
.kpi{border-radius:14px;padding:14px;background:var(--bg-card);border:1px solid var(--border);box-shadow:0 4px 16px rgba(2,6,23,0.06)}
.kpi .kpi-title{font-size:12px;color:var(--text-sub);margin-bottom:6px}
.kpi .kpi-value{font-size:20px;font-weight:700;color:var(--text-strong)}
.kpi .kpi-sub{font-size:12px;color:var(--text-sub)}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid var(--border);background:#f8fafc;color:var(--text-strong)}
.badge-a{background:var(--badge-a-bg);color:var(--badge-a-fg);border-color:var(--badge-a-bd)}
.badge-b{background:var(--badge-b-bg);color:var(--badge-b-fg);border-color:var(--badge-b-bd)}
.badge-c{background:var(--badge-c-bg);color:var(--badge-c-fg);border-color:var(--badge-c-bd)}
.badge-d{background:var(--badge-d-bg);color:var(--badge-d-fg);border-color:var(--badge-d-bd)}
.case-card{border-radius:14px;padding:14px 16px;background:var(--bg-card);border:1px solid var(--border);box-shadow:0 6px 24px rgba(2,6,23,0.06);margin-bottom:14px}
.case-head{display:flex;align-items:center;justify-content:space-between;gap:8px;border-bottom:1px dashed var(--border);padding-bottom:8px;margin-bottom:8px}
.case-title{font-weight:700;color:var(--text-strong)}
.case-meta{font-size:12px;color:var(--text-soft)}
.hr-soft{border:none;border-top:1px dashed var(--border);margin:8px 0}
h1,h2,h3,h4,h5,h6,.stMarkdown p,.stMarkdown li{color:var(--text-strong)!important}
small,.help,.hint{color:var(--text-sub)!important}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(f"""
<div class="app-hero">
  <h1>📋 Test Case Kalite Değerlendirmesi</h1>
  <p>Tablo belirleme: içerik analizi • Puanlama: gerçek alan varlığına göre.
  <span style="opacity:0.8">Rapor zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span></p>
</div>
""", unsafe_allow_html=True)

with st.expander("📌 Kurallar (özet)"):
    st.markdown("""
- **CSV ayraç:** `;`  
- **Gerekli sütunlar:** `Issue key`/`Issue Key`, `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`  
- **Tablo mantığı (senaryoya göre, içerik analizi):** A: Data/Pre yok • B: Pre gerekli • C: Data gerekli • D: Data+Pre gerekli  
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14  
- **Pre-Condition puanı:** **Sadece** şu CSV alanlardan **anlamlı içerik** varsa verilir:  
  `Custom field (Tests association with a Pre-Condition)` **veya** `Custom field (Pre-Conditions association with a Test)`.
""")

# ---------- Sidebar ----------
st.sidebar.header("⚙️ Ayarlar")
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
show_debug = st.sidebar.toggle("🛠 Debug (Data/Action/Expected)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x): return str(x or "")
def _match(pattern, text): return re.search(pattern, text or "", re.IGNORECASE)

def _normalize_newlines(s: str) -> str:
    return (s or "").replace("\r\n","\n").replace("\r","\n")

def _cleanup_html(s: str) -> str:
    s = _normalize_newlines(s or "")
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</?(p|div|li|tr|td|th|ul|ol|span|b|strong)>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return s

def _is_meaningless(val: str) -> bool:
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    v = re.sub(r'\s+', ' ', (val or '')).strip().lower()
    if v in meaningless: return True
    # sadece boşluk/noktalama/parantez vs ⇒ anlamsız
    if re.fullmatch(r'[\s\[\]\{\}\(\)\.,;:\-_/\\]*', v or ""): return True
    return False

# ---- CSV sütun adı toleransı ----
def pick_first_existing(colnames, df_cols):
    for name in colnames:
        if name in df_cols:
            return name
    return None

# ---- DATA ALGILAMA (puan/override) ----
def extract_data_blocks(steps_text: str) -> list[str]:
    blocks = []
    txt_raw = _normalize_newlines(steps_text or "")
    for m in re.finditer(r'["\']Data["\']\s*:\s*["\']((?:\\.|[^"\'])*)["\']', txt_raw, re.I | re.DOTALL):
        val = m.group(1).replace('\\"','"').replace("\\'", "'").strip()
        if val: blocks.append(val)
    txt = _cleanup_html(txt_raw)
    pattern = re.compile(
        r'(?:^|\n)\s*Data(?:\s*\d+)?\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Expected\s*Result|Action|Adım|Step|Attachments?)\b|$)',
        re.I | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = (m.group(1) or '').strip()
        if val: blocks.append(val)
    return [b for b in blocks if b.strip()]

def is_meaningful_data(value: str) -> bool:
    if _is_meaningless(value): return False
    v = value.strip()
    if re.search(r'https?://', v, re.I): return True
    if re.search(r'\b(select|insert|update|delete)\b', v, re.I): return True
    if re.search(r'\b[a-z_]+\.[a-z_]+\b', v, re.I): return True
    if len(re.sub(r'\s+', '', v)) >= 2: return True
    return False

def has_data_present_for_scoring(steps_text: str) -> bool:
    blocks = extract_data_blocks(steps_text)
    if any(is_meaningful_data(b) for b in blocks): return True
    if re.search(r'\b(select|insert|update|delete)\b', steps_text or "", re.I): return True
    return False

# ---- PRECONDITION (YALNIZCA CSV’den, anlamlı içerik kontrolüyle) ----
PRECOND_EXACT_COLS = [
    "Custom field (Tests association with a Pre-Condition)",
    "Custom field (Pre-Conditions association with a Test)",
]

def _pre_csv_has_meaningful(val: str) -> bool:
    # HTML çöz, boşlukları normalize et
    s = html.unescape(_text(val)).replace("\u00a0", " ")
    s = _cleanup_html(s).strip()
    if _is_meaningless(s): return False
    # “[]”, “{}”, “()”, sadece virgül/noktalama → boş
    if re.fullmatch(r'[\[\]\{\}\(\)\s\.,;:/\\\-_]*', s): return False
    # Sık görülen issue key deseni (Jira): ABC-123
    if re.search(r'\b[A-Z][A-Z0-9_]+-\d+\b', s): return True
    # En az iki alfasayısal karakter (örn. gerçek bir ad/ID)
    if re.search(r'[A-Za-zÇĞİÖŞÜçğıöşü0-9]{2,}', s): return True
    return False

def precondition_provided_from_csv(row, df_cols) -> bool:
    found = False
    for col in PRECOND_EXACT_COLS:
        if col in df_cols and _pre_csv_has_meaningful(row.get(col)):
            found = True
            break
    return found

# ---- İçerik sinyalleri (İHTİYAÇ analizi için) ----
def scan_precond_signals(text: str):
    t = (text or "").lower()
    s = []
    if _match(r'\bprecondition\b|ön\s*koşul|given .*already', t): s.append("Precondition ifadesi")
    if _match(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth)\b', t): s.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): s.append("Abonelik aktif")
    if _match(r'\bexisting user|mevcut kullanıcı\b', t): s.append("Mevcut kullanıcı/hesap")
    if _match(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission)\b', t): s.append("Ortam/Ayar/Yetki")
    return list(set(s))

def scan_data_signals(text: str):
    t = (text or "").lower()
    s = []
    if _match(r'\b(select|insert|update|delete)\b', t): s.append("SQL")
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t) and _match(r'"\w+"\s*:\s*".+?"', t): s.append("JSON body")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\\-]?id|subscriber)\b', t): s.append("ID field")
    if _match(r'\b(post|put|patch)\b', t) and _match(r'\b(body|payload)\b', t): s.append("POST payload")
    if _match(r'<\\s*(msisdn|token|iban|imei|email|username|password|user[_\\-]?id)\\s*>', t) or \
       _match(r'\\{\\s*(msisdn|token|iban|imei|email|username|password|user[_\\-]?id)\\s*\\}', t): s.append("Placeholder(ID)")
    return list(set(s))

def decide_data_needed(summary: str, steps_text: str) -> bool:
    combined = (summary or "") + "\n" + (steps_text or "")
    if len(scan_data_signals(combined)) >= 2: return True
    if extract_data_blocks(steps_text): return True
    return False

def decide_precond_needed(summary: str, steps_text: str) -> bool:
    combined = (summary or "") + "\n" + (steps_text or "")
    return len(scan_precond_signals(combined)) >= 1

# ---- TABLO KARARI (override + içerik) ----
def choose_table(summary: str, steps_text: str, *, data_written: bool, pre_written_csv: bool):
    if data_written and pre_written_csv:
        return "D", 14, [1,2,3,4,5,6,7]
