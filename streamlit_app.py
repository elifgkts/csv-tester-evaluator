# -*- coding: utf-8 -*-

# 📌 Test Case Evaluator — v1.3.0
# - Tablo (A/B/C/D) İHTİYAÇ analizi
# - Key prefix filtresi ( '-' öncesi )
# - Automated alanına göre Otomasyon/Manuel ayrımı + filtre
# - KPI, dağılım grafiği, detay kartları, CSV indirme
# - ✅ En düşük 5 ve en yüksek 5 case detayları
# - ✅ Hata yakalama & görünür durum mesajları

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
_EXPECT_PAST_WORDS = (
    r"(oldu|olmadı|gerçekleşti|gerçekleşmedi|yapıldı|yapılmadı|edildi|edilmedi|"
    r"sağlandı|sağlanmadı|tamamlandı|tamamlanmadı|görüldü|görülmedi|döndü|"
    r"başarılı oldu|başarısız oldu|hata verdi|gösterildi|gösterilmedi)"
)
_EXPECT_PAST_REGEXES = [
    re.compile(rf"\b{_EXPECT_PAST_WORDS}\b", re.I),
    re.compile(r"\b\w+(ildi|ıldı|uldu|üldü|ndi|ndı|ndu|ndü)\b", re.I),
    re.compile(r"\b\w+(medi|madı)\b", re.I),
]
def expected_style_hits(text: str) -> int:
    t = _cleanup_html(text or "").lower()
    hits = 0
    for rx in _EXPECT_PAST_REGEXES:
        hits += len(rx.findall(t))
    return hits
def expected_style_penalty(blocks: list[str]) -> tuple[int, int]:
    txt = " . ".join(blocks or [])
    hits = expected_style_hits(txt)
    if hits <= 0: return 0, 0
    if hits == 1: pen = 1
    elif hits == 2: pen = 2
    elif hits == 3: pen = 3
    elif hits <= 5: pen = 4
    else: pen = 5
    return hits, pen

# ---- Stepler kuralı ----
PASSIVE_PATTERNS = re.compile(
    r'\b(yapıldı|edildi|gerçekleştirildi|sağlandı|tamamlandı|kontrol edildi|yapılır|edilir|gerçekleştirilir|sağlanır|tamamlanır|kontrol edilir)\b',
    re.I
)
def block_has_many_substeps(text: str) -> bool:
    t = _cleanup_html(text or "")
    if re.search(r'(^|\n)\s*(\d+[\).\-\:]|\-|\*|\•)\s+\S+', t): return True
    lines = [ln.strip() for ln in re.split(r'(?:\n)+', t) if ln.strip()]
    if len(lines) >= 3: return True
    if t.count(';') >= 2: return True
    joiners = re.findall(r'(?:,|\bve\b|\bsonra\b|\bardından\b)', t, re.I)
    if len(joiners) >= 3: return True
    return False

# ---- Test Tipi (Backend/UI) Heuristics ----
def detect_test_type(summary: str, labels_text: str, action_texts: list, expected_texts: list) -> str:
    s_all = " \n ".join([summary or "", labels_text or ""] + action_texts + expected_texts).lower()
    backend_hits = 0
    ui_hits = 0
    for pat in [r'\bbackend\b', r'\bapi\b', r'\b(json|payload|request|response|headers)\b',
                r'\b(get|post|put|patch|delete)\b', r'/[\w\-/]+', r'\bselect|insert|update|delete\b']:
        if re.search(pat, s_all): backend_hits += 1
    for pat in [r'\bui\b', r'\bbuton|button|tıklanır|ekran|modal|form\b',
                r'\btextfield|input|dropdown|seçilir|yazılır|girilir\b',
                r'\bandroid|ios|web|chrome|safari|firefox|edge\b']:
        if re.search(pat, s_all): ui_hits += 1
    if backend_hits > ui_hits and backend_hits >= 1: return "Backend"
    if ui_hits > backend_hits and ui_hits >= 1: return "UI"
    if "backend" in (labels_text or "").lower(): return "Backend"
    return "—"

# ---------- Skorlama ----------
def score_one(row, df_cols, debug=False):
    key = _text(row.get('Issue key') or row.get('Issue Key') or row.get('Key') or row.get('IssueKey'))
    summary = _text(row.get('Summary') or row.get('Issue Summary') or row.get('Title'))
    priority = _text(row.get('Priority'))

    steps_col_name = pick_first_existing(
        ['Custom field (Manual Test Steps)', 'Manual Test Steps', 'Steps', 'Custom Steps'],
        df_cols
    )
    steps_list = parse_steps(row.get(steps_col_name)) if steps_col_name else []

    action_blocks = get_action_blocks(steps_list)
    expected_blocks = get_expected_blocks(steps_list)
    data_blocks = get_data_blocks(steps_list)

    data_present_for_scoring = has_data_written_from_steps(steps_list)
    precond_provided_csv     = precondition_provided_from_csv(row, df_cols)
    expected_present         = has_expected_present_from_steps(steps_list)
    pre_assoc_text           = get_pre_assoc_text(row, df_cols)

    if debug:
        table, base, active, data_sigs, pre_sigs, data_needed, pre_needed, data_strong = choose_table(
            summary, action_blocks, expected_blocks, pre_assoc_text,
            data_written=data_present_for_scoring,
            pre_written_csv=precond_provided_csv,
            debug=True
        )
    else:
        table, base, active = choose_table(
            summary, action_blocks, expected_blocks, pre_assoc_text,
            data_written=data_present_for_scoring,
            pre_written_csv=precond_provided_csv,
            debug=False
        )
        data_sigs = pre_sigs = []
        data_needed = pre_needed = None
        data_strong = None

    label_cols = [c for c in df_cols if c.lower().startswith("labels")]
    labels_text = " ".join([_text(row.get(c)) for c in label_cols])
    test_type = detect_test_type(summary, labels_text, action_blocks, expected_blocks)

    pts, notes, total = {}, [], 0

    # 1) Başlık
    if 1 in active:
        if not summary or len(summary) < 10:
            pts['Başlık'] = 0; notes.append("❌ Başlık çok kısa")
        elif any(w in summary.lower() for w in ["test edilir", "kontrol edilir"]):
            pts['Başlık'] = max(base-3, 1); notes.append(f"🔸 Başlık zayıf ifade ({pts['Başlık']})"); total += pts['Başlık']
        else:
            pts['Başlık'] = base; notes.append("✅ Başlık anlaşılır"); total += base

    # 2) Öncelik
    if 2 in active:
        if priority.strip().lower() in ["", "null", "none", "nan"]:
            pts['Öncelik'] = 0; notes.append("❌ Öncelik eksik")
        else:
            pts['Öncelik'] = base; notes.append("✅ Öncelik var"); total += base

    # 3) Data
    if 3 in active:
        if data_present_for_scoring:
            pts['Data'] = base; notes.append("✅ Data mevcut (steps JSON)")
            total += base
        else:
            pts['Data'] = 0; notes.append("❌ Data bulunamadı")

    # 4) Ön Koşul (YALNIZCA CSV)
    if 4 in active:
        if precond_provided_csv:
            pts['Ön Koşul'] = base; notes.append("✅ Pre-Condition association var (CSV)")
            total += base
        else:
            pts['Ön Koşul'] = 0; notes.append("❌ Pre-Condition association eksik (CSV)")

    # 5) Stepler
    if 5 in active:
        n_blocks = len(action_blocks)
        if n_blocks == 0:
            pts['Stepler'] = 0; notes.append("❌ Stepler boş")
        elif n_blocks >= 2:
            pts['Stepler'] = base; notes.append(f"✅ Stepler ayrı ve düzgün ({n_blocks} adım)"); total += base
        else:
            t = (action_blocks[0] or "")
            if block_has_many_substeps(t) or PASSIVE_PATTERNS.search(t):
                pts['Stepler'] = 1; notes.append("❌ Tek blokta çok adım veya edilgen ifade (1 puan)"); total += 1
            else:
                pts['Stepler'] = base; notes.append("✅ Tek step ama net/tek eylem"); total += base

    # 6) Client
    if 6 in active:
        ck = ["android","ios","web","mac","windows","chrome","safari","firefox","edge"]
        all_text = " ".join([summary] + action_blocks)
        if any(c in all_text.lower() for c in ck) or any(c in labels_text.lower() for c in ck):
            pts['Client'] = base; notes.append("✅ Client bilgisi var"); total += base
        else:
            pts['Client'] = 0; notes.append("❌ Client bilgisi eksik")

    # 7) Expected (+ yazım cezası)
    if 7 in active:
        if expected_present:
            pts['Expected'] = base
            hits, pen = expected_style_penalty(expected_blocks)
            if pen > 0:
                pts['Expected'] = max(0, pts['Expected'] - pen)
                notes.append(f"✏️ Expected yazımı (geçmiş zaman) -{pen} (isabet: {hits})")
            else:
                notes.append("✅ Expected mevcut (en az bir adım)")
            total += pts['Expected']
        else:
            pts['Expected'] = 0; notes.append("❌ Expected result eksik")

    result = {
        "Key": key, "Summary": summary, "Tablo": table, "Toplam Puan": total,
        **pts, "Açıklama": " | ".join(notes),
        "_type": test_type
    }
    if debug:
        hits_dbg, pen_dbg = expected_style_penalty(expected_blocks)
        result.update({
            "_data_sigs": ", ".join(sorted(data_sigs)) or "-",
            "_pre_sigs":  ", ".join(sorted(pre_sigs)) or "-",
            "_data_needed": data_needed,
            "_pre_needed":  pre_needed,
            "_data_strong": data_strong,
            "_data_written": data_present_for_scoring,
            "_pre_written_csv": precond_provided_csv,
            "_exp_hits": hits_dbg,
            "_exp_penalty": pen_dbg,
            "_actions_join": " ⏵ ".join(action_blocks)[:1200],
            "_expected_join": " ⏵ ".join(expected_blocks)[:1200],
            "_data_join": " ⏵ ".join(data_blocks)[:1200],
        })
    return result

# ---------- Görselleştirme yardımcıları ----------
def render_case_card(r, max_by_table_map, show_debug=False):
    badge_map = {"A":"badge badge-a","B":"badge badge-b","C":"badge badge-c","D":"badge badge-d"}
    max_pt = max_by_table_map.get(r["Tablo"], 100)
    pct = float(r["Toplam Puan"]) / max_pt if max_pt else 0.0
    badge_class = badge_map.get(r["Tablo"], "badge")
    ttype = r.get("_type","—")

    st.markdown('<div class="case-card">', unsafe_allow_html=True)
    st.markdown(f'''
        <div class="case-head">
          <div class="case-title">🔍 {r["Key"]} — {r["Summary"]}</div>
          <div class="case-meta">
            <span class="{badge_class}">Tablo {r["Tablo"]}</span>
            <span class="type-pill"><span class="dot"></span>{ttype}</span>
          </div>
        </div>
    ''', unsafe_allow_html=True)

    cL, cR = st.columns([3,1])
    with cL:
        st.markdown(f"**Toplam Puan:** `{int(r['Toplam Puan'])}` / `{int(max_pt)}`")
        st.progress(min(max(pct, 0.0), 1.0))
    with cR:
        st.markdown(f"**Skor %:** **{round(pct*100, 1)}%**")

    st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)
    for k in ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']:
        if k in r and pd.notna(r[k]):
            st.markdown(f"- **{k}**: {int(r[k])} puan")

    if show_debug:
        with st.expander(f"🔎 Debug — {r['Key']}"):
            st.markdown(f"- need:data: `{r.get('_data_needed')}`, strong_combo: `{r.get('_data_strong')}` — sinyaller: {r.get('_data_sigs')}")
            st.markdown(f"- need:pre : `{r.get('_pre_needed')}` — sinyaller: {r.get('_pre_sigs')}")
            st.markdown(f"- has:data(stepsJSON): `{r.get('_data_written')}` • has:pre(CSV): `{r.get('_pre_written_csv')}`")
            st.markdown(f"- ✏️ Expected yazım isabet: `{r.get('_exp_hits')}`, ceza: `{r.get('_exp_penalty')}`")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Çalıştır ----------
if uploaded:
    with st.status("📥 CSV yükleniyor...", expanded=False) as s:
        try:
            try:
                df = pd.read_csv(uploaded, sep=';')
            except Exception:
                df = pd.read_csv(uploaded)
            s.update(label=f"✅ CSV okundu — {df.shape[0]} satır, {df.shape[1]} sütun", state="complete")
        except Exception as e:
            st.exception(e)
            st.stop()

    try:
        # ✅ Prefix sütunu üret ve sidebar filtre ekle (örneklemeden ÖNCE)
        key_col_name = pick_first_existing(['Issue key', 'Issue Key', 'Key', 'IssueKey'], df.columns)
        if key_col_name:
            df['_KeyRaw'] = df[key_col_name].astype(str)
            df['_Prefix'] = df['_KeyRaw'].apply(_key_prefix)

            prefix_options = sorted([p for p in df['_Prefix'].unique() if p])
            selected_prefixes = st.sidebar.multiselect(
                "🔎 Projeye göre filtrele (Key prefix)",
                options=prefix_options,
                help="Key değerindeki '-' öncesi kısma göre filtreler (örn. QB284050, QM284050). Boş bırakılırsa tümü."
            )
            if selected_prefixes:
                df = df[df['_Prefix'].isin(selected_prefixes)]

        # ✅ Automated sütunu tespit et + durum sütunu üret + sidebar filtresi
        auto_col = None
        for c in df.columns:
            cl = str(c).strip().lower()
            if cl == "automated" or "automated" in cl:
                auto_col = c
                break
        if auto_col:
            df["_Automation"] = df[auto_col].apply(_detect_automation)
        else:
            df["_Automation"] = "Manuel"

        auto_choice = st.sidebar.radio(
            "🧪 Çalıştırma tipi",
            options=["Tümü", "Sadece Otomasyon", "Sadece Manuel"],
            index=0,
            help="CSV'deki 'Automated' alanına göre filtreler."
        )
        if auto_choice == "Sadece Otomasyon":
            df = df[df["_Automation"] == "Otomasyon"]
        elif auto_choice == "Sadece Manuel":
            df = df[df["_Automation"] == "Manuel"]

        # Filtre sonrası boşsa uyarı ver ve dur
        if len(df) == 0:
            st.warning("Filtreler sonrası kaynak veri **boş**. Prefix veya Çalıştırma tipi filtresini gevşetmeyi deneyin.")
            st.stop()

        # Örnekle
        n = min(sample_size, len(df))
        rstate = (123 + st.session_state.reroll) if fix_seed else None
        sample = df.sample(n=n, random_state=rstate) if len(df) > 0 else df

        # Skorla
        results = sample.apply(lambda r: score_one(r, df.columns, debug=show_debug), axis=1, result_type='expand')
        if results is None or len(results) == 0:
            st.error("Skorlama sonucu boş döndü.")
            st.stop()

        # KPI
        total_cases = len(results)
        avg_score  = round(results["Toplam Puan"].mean() if total_cases else 0, 1)
        min_score  = int(results["Toplam Puan"].min()) if total_cases else 0
        max_score  = int(results["Toplam Puan"].max()) if total_cases else 0
        dist = results['Tablo'].value_counts().reindex(["A","B","C","D"]).fillna(0).astype(int)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="kpi"><div class="kpi-title">Toplam Örnek</div><div class="kpi-value">{total_cases}</div><div class="kpi-sub">Değerlendirilen</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="kpi"><div class="kpi-title">Dağılım (A/B/C/D)</div><div class="kpi-value">{int(dist.get("A",0))}/{int(dist.get("B",0))}/{int(dist.get("C",0))}/{int(dist.get("D",0))}</div><div class="kpi-sub">Tablo adetleri</div></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="kpi"><div class="kpi-title">Ortalama Skor</div><div class="kpi-value">{avg_score}</div><div class="kpi-sub">Min: {min_score} • Max: {max_score}</div></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="kpi"><div class="kpi-title">Rapor Zamanı</div><div class="kpi-value">{datetime.now().strftime("%H:%M")}</div><div class="kpi-sub">Yerel saat</div></div>', unsafe_allow_html=True)

        # Otomasyon/Manuel sayacı (bilgi amaçlı)
        auto_counts_all = df["_Automation"].value_counts()
        auto_ot = int(auto_counts_all.get("Otomasyon", 0))
        auto_man = int(auto_counts_all.get("Manuel", 0))
        st.caption(f"🧪 Çalıştırma tipi dağılımı (filtre sonrası kaynak veri): **Otomasyon:** {auto_ot} • **Manuel:** {auto_man}")

        st.markdown("### 📈 Tablo Dağılımı")
        try:
            st.bar_chart(dist)
        except Exception as e:
            st.info("Dağılım grafiği çizilemedi, tablo boş olabilir.")
            if show_debug: st.exception(e)

        # Skor % ve tablo
        MAX_BY_TABLE = {"A": 100, "B": 102, "C": 102, "D": 98}
        results["Maks Puan"] = results["Tablo"].map(MAX_BY_TABLE).fillna(100)
        results["Skor %"] = (results["Toplam Puan"] / results["Maks Puan"]).clip(0, 1) * 100
        results["Skor %"] = results["Skor %"].round(1)

        # Görünüm kolonu: Prefix + Automation
        results["Prefix"] = results["Key"].str.extract(r'^([^\-\s]+)')
        results["Automation"] = df.loc[sample.index, "_Automation"].values

        show_cols = ["Prefix", "Key", "Summary", "Tablo", "Toplam Puan", "Skor %", "Automation", "Açıklama", "_type"]
        if show_debug:
            show_cols += ["_data_needed", "_pre_needed", "_data_strong", "_data_written", "_pre_written_csv",
                          "_data_sigs", "_pre_sigs", "_exp_hits", "_exp_penalty"]

        st.markdown("## 📊 Değerlendirme Tablosu")
        st.dataframe(
            results[show_cols].copy(),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prefix": st.column_config.TextColumn("Prefix", help="Key ön eki (proje/ürün kodu)"),
                "Key": st.column_config.TextColumn("Key", help="Issue key"),
                "Summary": st.column_config.TextColumn("Summary", width="medium"),
                "Tablo": st.column_config.TextColumn("Tablo"),
                "Toplam Puan": st.column_config.NumberColumn("Toplam Puan", format="%d"),
                "Skor %": st.column_config.ProgressColumn("Skor %", min_value=0, max_value=100, help="Toplam puanın tablo maksimumuna oranı"),
                "Automation": st.column_config.TextColumn("Çalıştırma Tipi", help="Otomasyon / Manuel"),
                "Açıklama": st.column_config.TextColumn("Açıklama", width="large"),
                "_type": st.column_config.TextColumn("Tip", help="Backend/UI tahmini"),
                "_data_needed": st.column_config.TextColumn("need:data"),
                "_pre_needed": st.column_config.TextColumn("need:pre"),
                "_data_strong": st.column_config.TextColumn("data:strong_combo"),
                "_data_written": st.column_config.TextColumn("has:data(stepsJSON)"),
                "_pre_written_csv": st.column_config.TextColumn("has:pre(CSV)"),
                "_data_sigs": st.column_config.TextColumn("Data sinyalleri"),
                "_pre_sigs": st.column_config.TextColumn("Pre sinyalleri"),
                "_exp_hits": st.column_config.NumberColumn("Exp yazım isabet"),
                "_exp_penalty": st.column_config.NumberColumn("Exp ceza (1-5)"),
            }
        )

        st.download_button(
            "📥 Sonuçları CSV olarak indir",
            data=results[show_cols].to_csv(index=False, sep=';', encoding='utf-8'),
            file_name=f"testcase_skorlari_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            type="primary"
        )

        # ---------- En Düşük 5 & En Yüksek 5 ----------
        st.markdown("## 🧩 En Düşük 5 Skor")
        bottom5 = results.sort_values(by=["Toplam Puan","Skor %","Key"], ascending=[True, True, True]).head(5)
        if len(bottom5) == 0:
            st.info("Gösterilecek kayıt yok.")
        else:
            for _, rr in bottom5.iterrows():
                render_case_card(rr, MAX_BY_TABLE, show_debug=show_debug)

        st.markdown("## 🏅 En Yüksek 5 Skor")
        top5 = results.sort_values(by=["Toplam Puan","Skor %","Key"], ascending=[False, False, True]).head(5)
        if len(top5) == 0:
            st.info("Gösterilecek kayıt yok.")
        else:
            for _, rr in top5.iterrows():
                render_case_card(rr, MAX_BY_TABLE, show_debug=show_debug)

        # ---------- Detay kartları (tüm örneklem) ----------
        st.markdown("## 📝 Tüm Detaylar")
        for _, r in results.iterrows():
            render_case_card(r, MAX_BY_TABLE, show_debug=show_debug)

    except Exception as e:
        st.exception(e)
        st.stop()
else:
    st.info("Başlamak için `;` ayraçlı CSV dosyanızı yükleyin.")
