# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v2.9.8-fix
# - Tablo (A/B/C/D) İHTİYAÇ analiziyle belirlenir (summary + steps + pre-association metni)
#   A: Data/Pre gerekmez • B: Pre gerekli • C: Data gerekli • D: Data+Pre gerekli
# - OVERRIDE: Hem Data (steps’te anlamlı) hem Pre (CSV’de iki sütundan biri dolu) yazılmışsa → D
# - PUANLAMA:
#   • Pre puanı: yalnızca CSV’deki iki sütundan biri doluysa
#   • Data/Expected puanı: steps/expected’ta gerçek/anlamlı varlığa göre
#   • ✏️ Expected yazım cezası: Expected’ta “-di’li geçmiş zaman” tespit edilirse 1–5 puan kesinti
# - Stepler: tek blok + çok adım/edilgen ise 1 puan
# - Debug: tetiklenen sinyaller + güçlü data kombinasyonu + Expected yazım isabet/ceza bilgisi

import streamlit as st
import pandas as pd
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
.app-hero{background:linear-gradient(135deg,#1f6feb 0%, #0ea5e9 100%);color:#fff;padding:18px 22px;border-radius:14px;margin-bottom:18px;box-shadow:0 8px 24px rgba(2, 6, 23, 0.18)}
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
  <p>
  <span style="opacity:0.8">Rapor zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span></p>
</div>
""", unsafe_allow_html=True)

with st.expander("📌 Kurallar"):
    st.markdown("""
- **CSV ayraç:** `;`  
- **Gerekli sütunlar:** `Issue key`/`Issue Key`, `Summary`, `Priority`, `Labels`, `Tests association with a Pre-Condition	`,`Pre-Conditions association with a Test	`,`Custom field (Manual Test Steps)`  
- **Tablo mantığı (ihtiyaca göre):** **A** Data/Pre gerekmez • **B** Pre gerekli • **C** Data gerekli • **D** Data+Pre gerekli  
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14  
- **Pre puanı:** **Sadece** şu iki CSV alanından biri **boşluk-harici doluysa** verilir:  
  `Custom field (Tests association with a Pre-Condition)` veya `Custom field (Pre-Conditions association with a Test)`  
- **D override:** Hem Data (steps) hem Pre (CSV) mevcutta yazılıysa → **D**.  
- **✏️ Expected yazım puan kırma:** Expected Result geçmiş/olup-bitti anlatımı içerirse 1–5 puan kesilir.
""")

# ---------- Sidebar ----------
st.sidebar.header("⚙️ Ayarlar")
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
show_debug = st.sidebar.toggle("🛠 Debug (sinyaller & kararlar)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x):
    return str(x or "")

def _cell(x) -> str:
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x or "")

def _is_blank_after_strip(val: str) -> bool:
    return len((val or "").strip()) == 0

def _match(pattern, text):
    return re.search(pattern, text or "", re.IGNORECASE)

def _normalize_newlines(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n")

def _cleanup_html(s: str) -> str:
    s = _normalize_newlines(s or "")
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</?(p|div|li|tr|td|th|ul|ol|span|b|strong)>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return s

def _is_meaningless(val: str) -> bool:
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    v = re.sub(r'\s+', ' ', (val or '')).strip().lower()
    if v in meaningless:
        return True
    if re.fullmatch(r'[\s\[\]\{\}\(\)\.,;:\-_/\\]*', v or ""):
        return True
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
    # JSON "Data":"..."
    for m in re.finditer(r'"Data"\s*:\s*"((?:\\.|[^"])*)"', txt_raw, re.I | re.DOTALL):
        val = m.group(1).replace('\\"', '"').strip()
        if val:
            blocks.append(val)
    # Metin/HTML başlığı: Data / Data 1 vs
    txt = _cleanup_html(txt_raw)
    pattern = re.compile(
        r'(?:^|\n)\s*Data(?:\s*\d+)?\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Expected\s*Result|Action|Adım|Step|Attachments?)\b|$)',
        re.I | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = (m.group(1) or '').strip()
        if val:
            blocks.append(val)
    return [b for b in blocks if b.strip()]

def is_meaningful_data(value: str) -> bool:
    if _is_meaningless(value):
        return False
    v = value.strip()
    if re.search(r'https?://', v, re.I):
        return True
    if re.search(r'\b(select|insert|update|delete)\b', v, re.I):
        return True
    if re.search(r'\b[a-z_]+\.[a-z_]+\b', v, re.I):
        return True
    if len(re.sub(r'\s+', '', v)) >= 2:
        return True
    return False

def has_data_present_for_scoring(steps_text: str) -> bool:
    blocks = extract_data_blocks(steps_text)
    if any(is_meaningful_data(b) for b in blocks):
        return True
    if re.search(r'\b(select|insert|update|delete)\b', steps_text or "", re.I):
        return True
    return False

# ---- PRECONDITION (CSV doluluğu) ----
PRECOND_EXACT_COLS = [
    "Custom field (Tests association with a Pre-Condition)",
    "Custom field (Pre-Conditions association with a Test)",
]

def precondition_provided_from_csv(row, df_cols) -> bool:
    for col in PRECOND_EXACT_COLS:
        if col in df_cols:
            val = _cell(row.get(col))
            if not _is_blank_after_strip(val):
                return True
    return False

def get_pre_assoc_text(row, df_cols) -> str:
    texts = []
    for col in PRECOND_EXACT_COLS:
        if col in df_cols:
            texts.append(_text(row.get(col)))
    return "\n".join(texts)

# ---- İçerik sinyalleri (ihtiyaç analizi) ----
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

def scan_data_signals(text: str):
    t = (text or "").lower()
    s = []
    # mevcut sinyaller
    if _match(r'\b(select|insert|update|delete)\b', t): s.append("SQL")
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t) and _match(r'"\w+"\s*:\s*".+?"', t):
        s.append("JSON body")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\-]?id|subscriber)\b', t):
        s.append("ID field")
    if _match(r'\b(post|put|patch)\b', t) and _match(r'\b(body|payload)\b', t):
        s.append("POST payload")
    if _match(r'<\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*>', t) or \
       _match(r'\{\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*\}', t):
        s.append("Placeholder(ID)")
    # 🔎 yeni sinyaller
    if _match(r'/(?:[a-z0-9_\-]+)(?:/[a-z0-9_\-]+){2,}', t): s.append("HTTP path")
    if _match(r"\bid[’'\s]?li\b", t) or _match(r"\b(episode|content|asset)[_\- ]?id\b", t) or _match(r"\bid\b", t):
        s.append("ID token")
    if _match(r"\b\d{6,}\b", t): s.append("Long numeric ID")
    if _match(r"\b(response|cevap|yanıt)\b", t): s.append("Response mention")
    if _match(r"\b(tablosu|tablosundaki|table|collection|index)\b", t): s.append("Table mention")
    return list(set(s))

# ---- İhtiyaç analizi ----
def decide_data_needed(summary: str, steps_text: str):
    """Return (needed: bool, data_signals: list[str], strong_combo: bool)."""
    combined = (summary or "") + "\n" + (steps_text or "")
    ds = scan_data_signals(combined)
    strong_combo = (
        ("ID token" in ds and "Response mention" in ds) or
        ("HTTP path" in ds and "ID token" in ds) or
        ("Table mention" in ds and "Long numeric ID" in ds)
    )
    needed = strong_combo or len(ds) >= 2 or bool(extract_data_blocks(steps_text))
    return needed, ds, strong_combo

def decide_precond_needed(summary: str, steps_text: str, pre_assoc_text: str):
    combined = (summary or "") + "\n" + (steps_text or "") + "\n" + (pre_assoc_text or "")
    ps = scan_precond_signals(combined)
    needed = len(ps) >= 1
    return needed, ps

# ---- TABLO KARARI (ihtiyaç + override) ----
def choose_table(summary: str, steps_text: str, pre_assoc_text: str, *, data_written: bool, pre_written_csv: bool, debug: bool=False):
    data_needed, data_sigs, data_strong = decide_data_needed(summary, steps_text)
    pre_needed,  pre_sigs              = decide_precond_needed(summary, steps_text, pre_assoc_text)

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

# ---- ACTION/STEPLER ----
def extract_action_blocks(steps_text: str) -> list[str]:
    blocks = []
    txt_raw = _normalize_newlines(steps_text or "")
    # JSON "Action":"..."
    for m in re.finditer(r'"Action"\s*:\s*"((?:\\.|[^"])*)"', txt_raw, re.I | re.DOTALL):
        val = m.group(1).replace('\\"', '"').strip()
        if val:
            blocks.append(val)
    # HTML/metin başlıkları
    txt = _cleanup_html(txt_raw)
    pattern = re.compile(
        r'(?:^|\n)\s*(?:Action|Adım|Step)(?:\s*\d+)?\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Data|Expected\s*Result|Attachments?|Action|Adım|Step)\b|$)',
        re.I | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = (m.group(1) or '').strip()
        if val:
            blocks.append(val)
    # "Step 1:" vb. ayırıcılarla böl
    if len(blocks) <= 1:
        split_blocks = re.split(r'(?:^|\n)\s*Step\s*\d+\s*:\s*', txt, flags=re.I)
        split_blocks = [b.strip() for b in split_blocks if b.strip()]
        if len(split_blocks) > 1:
            blocks = split_blocks
    return [b for b in blocks if b.strip()]

def extract_expected_blocks(steps_text: str) -> list[str]:
    blocks = []
    txt_raw = _normalize_newlines(steps_text or "")
    for m in re.finditer(r'"Expected\s*Result"\s*:\s*"((?:\\.|[^"])*)"', txt_raw, re.I | re.DOTALL):
        val = m.group(1).replace('\\"', '"').strip()
        if val:
            blocks.append(val)
    txt = _cleanup_html(txt_raw)
    pattern = re.compile(
        r'(?:^|\n)\s*Expected\s*Result\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Action|Data|Attachments?)\b|$)',
        re.I | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = (m.group(1) or '').strip()
        if val:
            blocks.append(val)
    return [b for b in blocks if b.strip()]

def is_meaningful_expected(value: str) -> bool:
    if _is_meaningless(value):
        return False
    v = value.strip()
    return len(re.sub(r'\s+', '', v)) >= 2

def has_expected_present(steps_text: str) -> bool:
    blocks = extract_expected_blocks(steps_text)
    return any(is_meaningful_expected(b) for b in blocks)

# ✏️ ---- EXPECTED YAZIM KALİTESİ CEZASI ----
_EXPECT_PAST_WORDS = r"(oldu|olmadı|gerçekleşti|gerçekleşmedi|yapıldı|yapılmadı|edildi|edilmedi|sağlandı|sağlanmadı|tamamlandı|tamamlanmadı|görüldü|görülmedi|döndü|başarılı oldu|başarısız oldu|hata verdi|gösterildi|gösterilmedi)"
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
    if hits <= 0:
        return 0, 0
    if hits == 1:
        pen = 1
    elif hits == 2:
        pen = 2
    elif hits == 3:
        pen = 3
    elif hits <= 5:
        pen = 4
    else:
        pen = 5
    return hits, pen

# ---- Stepler kuralı ----
PASSIVE_PATTERNS = re.compile(
    r'\b(yapıldı|edildi|gerçekleştirildi|sağlandı|tamamlandı|kontrol edildi|yapılır|edilir|gerçekleştirilir|sağlanır|tamamlanır|kontrol edilir)\b',
    re.I
)

def block_has_many_substeps(text: str) -> bool:
    t = _cleanup_html(text or "")
    if re.search(r'(^|\n)\s*(\d+[\).\-\:]|\-|\*|\•)\s+\S+', t):
        return True
    lines = [ln.strip() for ln in re.split(r'(?:\n)+', t) if ln.strip()]
    if len(lines) >= 3:
        return True
    if t.count(';') >= 2:
        return True
    joiners = re.findall(r'(?:,|\bve\b|\bsonra\b|\bardından\b)', t, re.I)
    if len(joiners) >= 3:
        return True
    return False

# ---------- Skorlama ----------
def score_one(row, df_cols, debug=False):
    key = _text(row.get('Issue key') or row.get('Issue Key') or row.get('Key') or row.get('IssueKey'))
    summary = _text(row.get('Summary') or row.get('Issue Summary') or row.get('Title'))
    priority = _text(row.get('Priority')).lower()

    # Steps sütunu
    steps_col_name = pick_first_existing(
        ['Custom field (Manual Test Steps)', 'Manual Test Steps', 'Steps', 'Custom Steps'],
        df_cols
    )
    steps_text = _text(row.get(steps_col_name)) if steps_col_name else ""

    # GERÇEK varlıklar (puanlama & override için)
    data_present_for_scoring = has_data_present_for_scoring(steps_text)
    precond_provided_csv     = precondition_provided_from_csv(row, df_cols)   # sadece CSV doluluğu
    expected_present         = has_expected_present(steps_text)
    pre_assoc_text           = get_pre_assoc_text(row, df_cols)

    # İçerik analizi + override → TABLO
    if debug:
        table, base, active, data_sigs, pre_sigs, data_needed, pre_needed, data_strong = choose_table(
            summary, steps_text, pre_assoc_text,
            data_written=data_present_for_scoring,
            pre_written_csv=precond_provided_csv,
            debug=True
        )
    else:
        table, base, active = choose_table(
            summary, steps_text, pre_assoc_text,
            data_written=data_present_for_scoring,
            pre_written_csv=precond_provided_csv,
            debug=False
        )
        data_sigs = pre_sigs = []
        data_needed = pre_needed = None
        data_strong = None

    # Actions
    action_blocks = extract_action_blocks(steps_text)
    all_actions_text = " \n ".join(action_blocks)

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
        if priority in ["", "null", "none"]:
            pts['Öncelik'] = 0; notes.append("❌ Öncelik eksik")
        else:
            pts['Öncelik'] = base; notes.append("✅ Öncelik var"); total += base

    # 3) Data
    if 3 in active:
        if data_present_for_scoring:
            pts['Data'] = base; notes.append("✅ Data mevcut (steps)"); total += base
        else:
            pts['Data'] = 0; notes.append("❌ Data bulunamadı")

    # 4) Ön Koşul (YALNIZCA CSV)
    if 4 in active:
        if precond_provided_csv:
            pts['Ön Koşul'] = base; notes.append("✅ Pre-Condition association var (CSV)"); total += base
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
        if any(c in (summary or "").lower() for c in ck) or any(c in (all_actions_text or "").lower() for c in ck):
            pts['Client'] = base; notes.append("✅ Client bilgisi var"); total += base
        else:
            pts['Client'] = 0; notes.append("❌ Client bilgisi eksik")

    # 7) Expected (+ yazım cezası)
    exp_blocks = extract_expected_blocks(steps_text)
    if 7 in active:
        if expected_present:
            pts['Expected'] = base
            hits, pen = expected_style_penalty(exp_blocks)
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
        **pts, "Açıklama": " | ".join(notes)
    }
    if debug:
        hits_dbg, pen_dbg = expected_style_penalty(exp_blocks)
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
        })
    return result

# ---------- Çalıştır ----------
if uploaded:
    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    n = min(sample_size, len(df))
    sample = df.sample(n=n, random_state=(123 + st.session_state.reroll) if fix_seed else None) if len(df) > 0 else df

    results = sample.apply(lambda r: score_one(r, df.columns, debug=show_debug), axis=1, result_type='expand')

    # KPI
    total_cases = len(results)
    avg_score  = round(results["Toplam Puan"].mean() if total_cases else 0, 1)
    min_score  = int(results["Toplam Puan"].min()) if total_cases else 0
    max_score  = int(results["Toplam Puan"].max()) if total_cases else 0
    dist = results['Tablo'].value_counts().reindex(["A","B","C","D"]).fillna(0).astype(int)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="kpi"><div class="kpi-title">Toplam Örnek</div><div class="kpi-value">{total_cases}</div><div class="kpi-sub">Değerlendirilen</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi"><div class="kpi-title">Dağılım (A/B/C/D)</div><div class="kpi-value">{dist["A"]}/{dist["B"]}/{dist["C"]}/{dist["D"]}</div><div class="kpi-sub">Tablo adetleri</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi"><div class="kpi-title">Ortalama Skor</div><div class="kpi-value">{avg_score}</div><div class="kpi-sub">Min: {min_score} • Max: {max_score}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi"><div class="kpi-title">Rapor Zamanı</div><div class="kpi-value">{datetime.now().strftime("%H:%M")}</div><div class="kpi-sub">Yerel saat</div></div>', unsafe_allow_html=True)

    st.markdown("### 📈 Tablo Dağılımı")
    st.bar_chart(dist)

    # Skor % ve tablo
    MAX_BY_TABLE = {"A": 100, "B": 102, "C": 102, "D": 98}
    results["Maks Puan"] = results["Tablo"].map(MAX_BY_TABLE).fillna(100)
    results["Skor %"] = (results["Toplam Puan"] / results["Maks Puan"]).clip(0, 1) * 100
    results["Skor %"] = results["Skor %"].round(1)

    show_cols = ["Key", "Summary", "Tablo", "Toplam Puan", "Skor %", "Açıklama"]
    if show_debug:
        show_cols += ["_data_needed", "_pre_needed", "_data_strong", "_data_written", "_pre_written_csv", "_data_sigs", "_pre_sigs", "_exp_hits", "_exp_penalty"]

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(
        results[show_cols].copy(),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Key": st.column_config.TextColumn("Key", help="Issue key"),
            "Summary": st.column_config.TextColumn("Summary", width="medium"),
            "Tablo": st.column_config.TextColumn("Tablo"),
            "Toplam Puan": st.column_config.NumberColumn("Toplam Puan", format="%d"),
            "Skor %": st.column_config.ProgressColumn("Skor %", min_value=0, max_value=100, help="Toplam puanın tablo maksimumuna oranı"),
            "Açıklama": st.column_config.TextColumn("Açıklama", width="large"),
            "_data_needed": st.column_config.TextColumn("need:data"),
            "_pre_needed": st.column_config.TextColumn("need:pre"),
            "_data_strong": st.column_config.TextColumn("data:strong_combo"),
            "_data_written": st.column_config.TextColumn("has:data(steps)"),
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
        mime="text/csv"
    )

    st.markdown("## 📝 Detaylar")
    badge_map = {"A": "badge badge-a", "B": "badge badge-b", "C": "badge badge-c", "D": "badge badge-d"}

    for _, r in results.iterrows():
        max_pt = MAX_BY_TABLE.get(r["Tablo"], 100)
        pct = float(r["Toplam Puan"]) / max_pt if max_pt else 0.0
        badge_class = badge_map.get(r["Tablo"], "badge")

        st.markdown('<div class="case-card">', unsafe_allow_html=True)
        st.markdown(f'''
            <div class="case-head">
              <div class="case-title">🔍 {r["Key"]} — {r["Summary"]}</div>
              <div class="case-meta"><span class="{badge_class}">Tablo {r["Tablo"]}</span></div>
            </div>
        ''', unsafe_allow_html=True)

        cL, cR = st.columns([3, 1])
        with cL:
            st.markdown(f"**Toplam Puan:** `{int(r['Toplam Puan'])}` / `{int(max_pt)}`")
            st.progress(min(max(pct, 0.0), 1.0))
        with cR:
            st.markdown(f"**Skor %:** **{round(pct*100, 1)}%**")

        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)
        for k in ['Başlık', 'Öncelik', 'Data', 'Ön Koşul', 'Stepler', 'Client', 'Expected']:
            if k in r and pd.notna(r[k]):
                st.markdown(f"- **{k}**: {int(r[k])} puan")

        if show_debug:
            with st.expander(f"🔎 Debug — {r['Key']}"):
                st.markdown(f"- need:data: `{r.get('_data_needed')}` • strong_combo: `{r.get('_data_strong')}` — sinyaller: {r.get('_data_sigs')}")
                st.markdown(f"- need:pre : `{r.get('_pre_needed')}` — sinyaller: {r.get('_pre_sigs')}")
                st.markdown(f"- has:data(steps): `{r.get('_data_written')}` • has:pre(CSV): `{r.get('_pre_written_csv')}`")
                st.markdown(f"- ✏️ Expected yazım isabet: `{r.get('_exp_hits')}`, ceza: `{r.get('_exp_penalty')}`")
