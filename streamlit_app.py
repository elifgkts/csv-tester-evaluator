# -*- coding: utf-8 -*-

# 📌 Test Case Evaluator — v1.3.0
# - Tablo (A/B/C/D) İHTİYAÇ analizi
# - Key prefix filtresi ( '-' öncesi )
# - Automated alanına göre Otomasyon/Manuel ayrımı + filtre
# - KPI, dağılım grafiği, detay kartları, CSV indirme
# - 🆕 En düşük 5 ve en yüksek 5 case'i kart detaylarıyla göster

import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

# ---------- Sayfa & Stil ----------
st.set_page_config(page_title="Test Case SLA", layout="wide")

CUSTOM_CSS = """
<style>
:root{
  --bg-card:#ffffff; --text-strong:#0f172a; --text-soft:#475569; --text-sub:#64748b; --border:rgba(2,6,23,0.08);
  --badge-a-bg:#eef2ff; --badge-a-fg:#3730a3; --badge-a-bd:#c7d2fe;
  --badge-b-bg:#ecfeff; --badge-b-fg:#155e75; --badge-b-bd:#a5f3fc;
  --badge-c-bg:#fef9c3; --badge-c-fg:#854d0e; --badge-c-bd:#fde68a;
  --badge-d-bg:#fee2e2; --badge-d-fg:#991b1b; --badge-d-bd:#fecaca;
  --accent:#2563eb;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg-card:#0b1220; --text-strong:#e5ecff; --text-soft:#c7d2fe; --text-sub:#94a3b8; --border:rgba(148,163,184,0.25);
    --badge-a-bg:#1e1b4b; --badge-a-fg:#c7d2fe; --badge-a-bd:#3730a3;
    --badge-b-bg:#083344; --badge-b-fg:#99f6e4; --badge-b-bd:#155e75;
    --badge-c-bg:#3f3f1e; --badge-c-fg:#fde68a; --badge-c-bd:#854d0e;
    --badge-d-bg:#431313; --badge-d-fg:#fecaca; --badge-d-bd:#991b1b;
    --accent:#60a5fa;
  }
}
#MainMenu, footer {visibility:hidden;}
.app-hero{
  background: linear-gradient(135deg, #1f6feb 0%, #0ea5e9 100%);
  color:#fff; padding:18px 22px; border-radius:14px; margin-bottom:18px;
  box-shadow:0 8px 24px rgba(2, 6, 23, 0.18);
}
.app-hero h1{ font-size:24px; margin:0 0 6px 0; line-height:1.2; color:#fff; }
.app-hero p{ margin:0; opacity:.95; color:#fff; }

.kpi{
  border-radius:14px; padding:14px; background:var(--bg-card);
  border:1px solid var(--border); box-shadow:0 4px 16px rgba(2,6,23,0.06);
}
.kpi .kpi-title{ font-size:12px; color:var(--text-sub); margin-bottom:6px; }
.kpi .kpi-value{ font-size:20px; font-weight:700; color:var(--text-strong); }
.kpi .kpi-sub{ font-size:12px; color:var(--text-sub); }

.badge{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px;
  border:1px solid var(--border); background:#f8fafc; color:var(--text-strong); }
.badge-a{ background:var(--badge-a-bg); color:var(--badge-a-fg); border-color:var(--badge-a-bd);}
.badge-b{ background:var(--badge-b-bg); color:var(--badge-b-fg); border-color:var(--badge-b-bd);}
.badge-c{ background:var(--badge-c-bg); color:var(--badge-c-fg); border-color:var(--badge-c-bd);}
.badge-d{ background:var(--badge-d-bg); color:var(--badge-d-fg); border-color:var(--badge-d-bd);}

.type-pill{
  display:inline-flex; align-items:center; gap:6px; padding:2px 8px; border-radius:999px; font-size:12px;
  border:1px solid var(--border); background:rgba(37,99,235,0.08); color:var(--accent);
}
.type-pill .dot{ width:6px; height:6px; border-radius:999px; background:var(--accent); display:inline-block; }

.case-card{
  border-radius:14px; padding:14px 16px; background:var(--bg-card);
  border:1px solid var(--border); box-shadow:0 6px 24px rgba(2,6,23,0.06);
  margin-bottom:14px; transition: transform .08s ease, box-shadow .12s ease;
}
.case-card:hover{
  transform: translateY(-1px);
  box-shadow:0 10px 28px rgba(2,6,23,0.12);
}
.case-head{ display:flex; align-items:center; justify-content:space-between; gap:8px;
  border-bottom:1px dashed var(--border); padding-bottom:8px; margin-bottom:8px; }
.case-title{ font-weight:700; color:var(--text-strong); }
.case-meta{ display:flex; align-items:center; gap:8px; font-size:12px; color:var(--text-soft); }
.hr-soft{ border:none; border-top:1px dashed var(--border); margin:8px 0; }

.scrollbox{
  max-height: 220px; overflow:auto; border:1px dashed var(--border);
  padding:10px; border-radius:10px; background: rgba(2,6,23,0.02);
}

h1,h2,h3,h4,h5,h6, .stMarkdown p, .stMarkdown li{ color:var(--text-strong) !important; }
small, .help, .hint{ color:var(--text-sub) !important; }
.stProgress > div > div{ background:var(--accent) !important; }
</style>
"""
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
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 300, 5, help="Örnekleme sayısı")
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
show_debug = st.sidebar.toggle("🛠 Debug (sinyaller & kararlar)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x): return str(x or "")
def _cell(x) -> str:
    try:
        if pd.isna(x): return ""
    except Exception:
        pass
    return str(x or "")
def _is_blank_after_strip(val: str) -> bool:
    return len((val or "").strip()) == 0
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
    if re.fullmatch(r'[\s\[\]\{\}\(\)\.,;:\-_/\\]*', v or ""): return True
    return False
def pick_first_existing(colnames, df_cols):
    for name in colnames:
        if name in df_cols: return name
    return None

# ✅ Key prefix çıkarıcı ( '-' öncesi )
def _key_prefix(val: str) -> str:
    v = _text(val)
    m = re.match(r'^\s*([^\-\s]+)', v)
    return m.group(1) if m else ""

# ✅ Automated alanını yorumlayan yardımcı
def _detect_automation(val: str) -> str:
    """CSV'deki 'Automated' alanından 'Otomasyon' / 'Manuel' üretir."""
    v = (str(val or "")).strip().lower()
    automated_set = {
        "yes", "true", "1", "android-automated", "ios-automated",
        "automated", "auto", "automation", "android_automated", "ios_automated"
    }
    return "Otomasyon" if v in automated_set else "Manuel"

# ---- Steps JSON parse & field extract ----
def parse_steps(steps_cell):
    """Return list of steps with normalized fields dicts, else []."""
    steps = []
    raw = steps_cell if isinstance(steps_cell, str) else ""
    if not raw.strip():
        return steps
    txt = raw.strip()
    try:
        data = json.loads(txt)
        if isinstance(data, list):
            steps = data
        else:
            steps = []
    except Exception:
        try:
            if txt.startswith('"') and txt.endswith('"'):
                txt2 = txt[1:-1].replace('""','"')
                data = json.loads(txt2)
                if isinstance(data, list):
                    steps = data
        except Exception:
            steps = []
    norm = []
    for s in steps:
        fields = s.get("fields", {}) if isinstance(s, dict) else {}
        if not isinstance(fields, dict): fields = {}
        f2 = {}
        for k in ["Action","Data","Expected Result","Expected","Attachments","Step","Adım"]:
            v = fields.get(k, "")
            if isinstance(v, str):
                f2[k] = v
        norm.append({"fields": f2})
    return norm

def get_action_blocks(steps_list):
    out = []
    for s in steps_list:
        v = s.get("fields",{}).get("Action","")
        if isinstance(v,str) and v.strip():
            out.append(v.strip())
    if not out:
        for s in steps_list:
            f = s.get("fields",{})
            for alt in ("Adım","Step"):
                v = f.get(alt,"")
                if isinstance(v,str) and v.strip(): out.append(v.strip())
    return out

def get_data_blocks(steps_list):
    out = []
    for s in steps_list:
        v = s.get("fields",{}).get("Data","")
        if isinstance(v,str) and v.strip():
            out.append(v.strip())
    return out

def get_expected_blocks(steps_list):
    out = []
    for s in steps_list:
        f = s.get("fields",{})
        v = f.get("Expected Result", f.get("Expected",""))
        if isinstance(v,str) and v.strip():
            out.append(v.strip())
    return out

def has_data_written_from_steps(steps_list) -> bool:
    return any(not _is_meaningless(x) for x in get_data_blocks(steps_list))

def has_expected_present_from_steps(steps_list) -> bool:
    return any(not _is_meaningless(x) for x in get_expected_blocks(steps_list))

# ---- PRECONDITION (CSV doluluğu) ----
PRECOND_EXACT_COLS = [
    "Custom field (Tests association with a Pre-Condition)",
    "Custom field (Pre-Conditions association with a Test)",
]
def precondition_provided_from_csv(row, df_cols) -> bool:
    for col in PRECOND_EXACT_COLS:
        if col in df_cols:
            if not _is_blank_after_strip(_cell(row.get(col))):
                return True
    return False
def get_pre_assoc_text(row, df_cols) -> str:
    texts = []
    for col in PRECOND_EXACT_COLS:
        if col in df_cols:
            texts.append(_text(row.get(col)))
    return "\n".join(texts)

# ---- İçerik sinyalleri (ihtiyaç analizi) ----
def _match(pattern, text): return re.search(pattern, text or "", re.IGNORECASE)

def scan_precond_signals(text: str):
    t = (text or "").lower()
    s = []
    if _match(r'\b(pre[- ]?condition|ön\s*koşul|ön\s*şart)\b', t): s.append("Precondition ifadesi")
    if _match(r'\b(gerek(ir|li)|zorunlu|olmalı|required|must|should)\b.*\b(login|auth|role|permission|config|seed|setup)\b', t): s.append("Zorunluluk ifadesi")
    if _match(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth|session)\b', t): s.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): s.append("Abonelik aktif")
    if _match(r'\bexisting user|mevcut kullanıcı|mevcut hesap\b', t): s.append("Mevcut kullanıcı/hesap")
    if _match(r'\b(seed|setup|config(ure)?|feature flag|whitelist|allowlist|role|permission|yetki)\b', t): s.append("Ortam/Ayar/Yetki")
    return list(set(s))

def scan_data_signals_from_text(text: str):
    t = (text or "").lower()
    s = []
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t): s.append("JSON/HTTP")
    if _match(r'\b(post|put|patch|get|delete)\b', t) and _match(r'\b(/[\w\-/]+)\b', t): s.append("HTTP path")
    if _match(r'\bselect|insert|update|delete\b', t): s.append("SQL")
    if _match(r'\b(tıklanır|buton|button|ekran|modal|form|textfield|input|dropdown|seçilir|yazılır|girilir)\b', t): s.append("UI input")
    if _match(r'\bplaceholder\b', t): s.append("Placeholder")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\\-]?id|subscriber)\b', t): s.append("ID field")
    return list(set(s))

def decide_data_needed(summary: str, action_texts: list, expected_texts: list):
    combined = " \n ".join([summary] + action_texts + expected_texts)
    ds = scan_data_signals_from_text(combined)
    strong_combo = ("JSON/HTTP" in ds and ("HTTP path" in ds or "UI input" in ds)) or ("SQL" in ds and "ID field" in ds)
    needed = strong_combo or len(ds) >= 2
    return needed, ds, strong_combo

def decide_precond_needed(summary: str, action_texts: list, pre_assoc_text: str):
    combined = " \n ".join([summary] + action_texts + [pre_assoc_text or ""])
    ps = scan_precond_signals(combined)
    needed = len(ps) >= 1
    return needed, ps

# ---- TABLO KARARI (ihtiyaç + override) ----
def choose_table(summary: str, action_texts: list, expected_texts: list, pre_assoc_text: str,
                 *, data_written: bool, pre_written_csv: bool, debug: bool=False):
    data_needed, data_sigs, data_strong = decide_data_needed(summary, action_texts, expected_texts)
    pre_needed,  pre_sigs              = decide_precond_needed(summary, action_texts, pre_assoc_text)

    if data_written and pre_written_csv:
        decision = ("D", 14, [1,2,3,4,5,6,7])
    else:
        if data_needed and pre_needed:
            decision = ("D", 14, [1,2,3,4,5,6,7])
        elif data_needed:
            decision = ("C", 17, [1,2,3,5,6,7])
        elif pre_needed:
            decision = ("B", 17, [1,2,4,5,6,7])
        else:
            decision = ("A", 20, [1,2,5,6,7])

    if debug:
        return (*decision, data_sigs, pre_sigs, data_needed, pre_needed, data_strong)
    return decision

# ✏️ ---- EXPECTED YAZIM KALİTESİ CEZASI ----
_EXPECT_PAST_WORDS = r"(oldu|olmadı|gerçekleşti|gerçekleşmedi|yapıldı|yapılmadı|edildi|edilmedi|sağlandı|sağlanmadı|tamamlandı|tamamlanmadı|görüldü|görülmedi|döndü|başarılı
