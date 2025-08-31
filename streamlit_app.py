# -*- coding: utf-8 -*-
"""
Test Case Evaluator v2.0
This Streamlit application scores manual test cases based on the presence of
critical metadata (summary, priority, data, precondition, steps, client and expected result)
and classifies each case into table A/B/C/D.  The application implements refined
logic for detecting when a case truly contains data or preconditions and when
those elements are merely empty markers left unfilled by the tester.

Key improvements over v1.9:
    * A Data: tag or JSON "Data" field must have a non-empty value to be counted.
      An empty tag/field no longer counts as having data.
    * A precondition must contain real content to award points.  An empty label
      does not satisfy the requirement.
    * Even when data or precondition fields are empty, the scoring logic still
      looks for signals in the summary/steps to determine whether such elements
      are needed.  This ensures that cases requiring data or preconditions are
      placed into the correct table (C, B or D) even if the tester omitted them.
    * Dedicated functions `has_data_present_for_scoring` and
      `has_precond_present_for_scoring` distinguish between detecting presence
      of content versus inferring the need for content.
"""

import streamlit as st
import pandas as pd
import re
import time
import random
from datetime import datetime

###############################################################################
#                               Page & Style                                  #
###############################################################################
st.set_page_config(page_title="Test Case SLA", layout="wide")

CUSTOM_CSS = """
<style>
:root{
  --bg-card:#ffffff;
  --text-strong:#0f172a;   /* başlık/metin koyu tema yokken */
  --text-soft:#475569;
  --text-sub:#64748b;
  --border:rgba(2,6,23,0.08);

  --badge-a-bg:#eef2ff; --badge-a-fg:#3730a3; --badge-a-bd:#c7d2fe;
  --badge-b-bg:#ecfeff; --badge-b-fg:#155e75; --badge-b-bd:#a5f3fc;
  --badge-c-bg:#fef9c3; --badge-c-fg:#854d0e; --badge-c-bd:#fde68a;
  --badge-d-bg:#fee2e2; --badge-d-fg:#991b1b; --badge-d-bd:#fecaca;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg-card:#0b1220;
    --text-strong:#e5ecff; /* başlık/metin koyu temada açık olsun */
    --text-soft:#c7d2fe;
    --text-sub:#94a3b8;
    --border:rgba(148,163,184,0.25);

    --badge-a-bg:#1e1b4b; --badge-a-fg:#c7d2fe; --badge-a-bd:#3730a3;
    --badge-b-bg:#083344; --badge-b-fg:#99f6e4; --badge-b-bd:#155e75;
    --badge-c-bg:#3f3f1e; --badge-c-fg:#fde68a; --badge-c-bd:#854d0e;
    --badge-d-bg:#431313; --badge-d-fg:#fecaca; --badge-d-bd:#991b1b;
  }
}

/* Streamlit header/text vars */
#MainMenu, footer {visibility:hidden;}
.app-hero{
  background: linear-gradient(135deg, #1f6feb 0%, #0ea5e9 100%);
  color: white; padding:18px 22px; border-radius:14px; margin-bottom:18px;
  box-shadow:0 8px 24px rgba(2, 6, 23, 0.18);
}
.app-hero h1{ font-size:24px; margin:0 0 6px 0; line-height:1.2; color:white; }
.app-hero p{ margin:0; opacity:.95; color:white; }

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

.case-card{
  border-radius:14px; padding:14px 16px; background:var(--bg-card);
  border:1px solid var(--border); box-shadow:0 6px 24px rgba(2,6,23,0.06);
  margin-bottom:14px;
}
.case-head{ display:flex; align-items:center; justify-content:space-between; gap:8px;
  border-bottom:1px dashed var(--border); padding-bottom:8px; margin-bottom:8px; }
.case-title{ font-weight:700; color:var(--text-strong); }
.case-meta{ font-size:12px; color:var(--text-soft); }
.hr-soft{ border:none; border-top:1px dashed var(--border); margin:8px 0; }

/* Genel başlık/metin renkleri */
h1,h2,h3,h4,h5,h6, .stMarkdown p, .stMarkdown li{ color:var(--text-strong) !important; }
small, .help, .hint{ color:var(--text-sub) !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(f"""
<div class="app-hero">
  <h1>📋 Test Case Kalite Değerlendirmesi</h1>
  <p>Test caseleri A/B/C/D tablosuna göre senaryo içeriğini analiz ederek puanlar.
  <span style="opacity:0.8">Rapor zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span></p>
</div>
""", unsafe_allow_html=True)

with st.expander("📌 Kurallar (özet)"):
    st.markdown("""
- **CSV ayraç:** `;`  
- **Gerekli sütunlar:** `Issue key` (veya `Issue Key`), `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`  
- **Tablo mantığı (senaryoya göre):** A: Data/Pre yok • B: Pre gerekli • C: Data gerekli • D: Data+Pre gerekli  
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14
""")

###############################################################################
#                           Sidebar Controls                                   #
###############################################################################
st.sidebar.header("⚙️ Ayarlar")
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

###############################################################################
#                            Helper Functions                                  #
###############################################################################
def _text(x):
    """Safely convert a value to string."""
    return str(x or "")

def _match(pattern: str, text: str) -> re.Match:
    """Case-insensitive regex search that tolerates missing text."""
    return re.search(pattern, text or "", re.IGNORECASE)

def extract_first(text: str, key: str) -> str:
    """
    Extract the first value of a given JSON-like key from the provided text.

    The search is case-insensitive and spans multiple lines.
    Returns the captured value or an empty string if not found.
    """
    m = re.search(rf'"{re.escape(key)}"\s*:\s*"(.*?)"', text or "", re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def has_data_tag_with_value(steps_text: str) -> bool:
    """
    Determine if a 'Data:' tag is present and populated.

    A Data tag counts as present only when there is content after the colon on the same
    line.  Leading dashes and spaces are ignored.  Empty or meaningless values
    such as '-', 'none', 'n/a', etc. are not considered valid.
    """
    pattern = re.compile(r'(?:^|\r?\n)\s*[-\s]*Data\s*:\s*(.*)', re.IGNORECASE)
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    for m in pattern.finditer(steps_text or ""):
        val = (m.group(1) or "").strip().lower()
        val_norm = re.sub(r'\s+', ' ', val)
        if val_norm not in meaningless and len(val_norm) > 0:
            return True
    return False

def has_data_json_field_with_value(steps_text: str) -> bool:
    """
    Determine if a JSON-like 'Data' field is present and non-empty.

    Matches "Data": "<value>" occurrences.  Values consisting solely of whitespace or
    meaningless tokens are ignored.
    """
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    matches = re.findall(r'"Data"\s*:\s*"(.*?)"', steps_text or "", re.IGNORECASE | re.DOTALL)
    for m in matches:
        val_norm = re.sub(r'\s+', ' ', (m or "").strip()).lower()
        if val_norm not in meaningless and len(val_norm) > 0:
            return True
    return False

def has_data_present_for_scoring(steps_text: str) -> bool:
    """
    Return True only if the 'Data:' tag or JSON 'Data' field is present with a value.
    An empty tag or empty field no longer qualifies.
    """
    return has_data_tag_with_value(steps_text) or has_data_json_field_with_value(steps_text)

def has_precond_tag_with_value(steps_text: str) -> bool:
    """
    Detect an explicit precondition label populated with content.

    Looks for 'Precondition:' at the beginning of a line followed by meaningful content.
    """
    pattern = re.compile(r'(?:^|\r?\n)\s*[-\s]*Precondition\s*:\s*(.*)', re.IGNORECASE)
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    for m in pattern.finditer(steps_text or ""):
        val = (m.group(1) or "").strip().lower()
        val_norm = re.sub(r'\s+', ' ', val)
        if val_norm not in meaningless and len(val_norm) > 0:
            return True
    return False

def has_precond_json_field_with_value(steps_text: str) -> bool:
    """
    Detect a JSON-like 'Precondition' field with non-empty value.
    """
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    matches = re.findall(r'"Precondition"\s*:\s*"(.*?)"', steps_text or "", re.IGNORECASE | re.DOTALL)
    for m in matches:
        val_norm = re.sub(r'\s+', ' ', (m or "").strip()).lower()
        if val_norm not in meaningless and len(val_norm) > 0:
            return True
    return False

def has_precond_present_for_scoring(steps_text: str) -> bool:
    """
    Return True if a precondition is explicitly provided and non-empty.
    """
    return has_precond_tag_with_value(steps_text) or has_precond_json_field_with_value(steps_text)

def scan_data_signals(text: str):
    """
    Identify heuristics that suggest the test case requires data.

    Signals include SQL keywords, JSON bodies, user identifiers and HTTP payload indicators.
    The function returns a list of unique signal names.
    """
    t = (text or "").lower()
    signals = []
    if _match(r'\b(select|insert|update|delete)\b', t): signals.append("SQL")
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t) and \
       _match(r'"\w+"\s*:\s*".+?"', t): signals.append("JSON body")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\-]?id|subscriber)\b', t): signals.append("Kimlik alanı")
    if _match(r'\b(post|put|patch)\b', t) and _match(r'\b(body|payload)\b', t): signals.append("POST payload")
    if _match(r'<\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*>', t) or \
       _match(r'\{\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*\}', t):
        signals.append("Placeholder(ID)")
    return signals

def scan_precond_signals(text: str):
    """
    Identify heuristics that suggest the test case requires a precondition.

    Signals include mentions of login/authentication, existing subscriptions/users, setup,
    environment configuration or feature flags.
    """
    t = (text or "").lower()
    signals = []
    if _match(r'\bprecondition\b|ön\s*koşul|given .*already', t): signals.append("Precondition ifadesi")
    if _match(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth)\b', t): signals.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): signals.append("Abonelik aktif")
    if _match(r'\bexisting user|mevcut kullanıcı\b', t): signals.append("Mevcut kullanıcı/hesap")
    if _match(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission)\b', t): signals.append("Ortam/Ayar/Yetki")
    return signals

def decide_data_needed(summary: str, steps_text: str) -> bool:
    """
    Determine whether the test case logically requires data.

    Data is considered necessary if:
        * The tester explicitly provides data (Data tag or JSON Data field), OR
        * Strong signals from the summary/steps indicate that data is involved
          (e.g. presence of multiple data signals like SQL operations, payloads, etc.).
    """
    combined = (summary or "") + "\n" + (steps_text or "")
    # If tester supplied data content, definitely needed.
    if has_data_present_for_scoring(steps_text):
        return True
    # Otherwise rely on heuristics: at least 2 distinct signals -> requires data.
    signals = scan_data_signals(combined)
    return len(set(signals)) >= 2

def decide_precond_needed(summary: str, steps_text: str) -> bool:
    """
    Determine whether the test case logically requires a precondition.

    A precondition is considered necessary if:
        * The tester explicitly filled a precondition field/tag, OR
        * At least one precondition signal is detected in the summary/steps.
    """
    combined = (summary or "") + "\n" + (steps_text or "")
    if has_precond_present_for_scoring(steps_text):
        return True
    signals = scan_precond_signals(combined)
    return len(set(signals)) >= 1

def choose_table(summary: str, steps_text: str):
    """
    Classify the test case into one of the tables A, B, C or D based on data and precondition needs.

    Returns:
        table: str -> one of "A","B","C","D"
        base:  int -> base point value for each criterion in the table
        active: list[int] -> list of criterion indices to evaluate for scoring
    """
    data_needed = decide_data_needed(summary, steps_text)
    pre_needed = decide_precond_needed(summary, steps_text)

    # Both needed -> Table D
    if data_needed and pre_needed:
        return "D", 14, [1,2,3,4,5,6,7]
    # Only data needed -> Table C
    if data_needed:
        return "C", 17, [1,2,3,5,6,7]
    # Only precondition needed -> Table B
    if pre_needed:
        return "B", 17, [1,2,4,5,6,7]
    # Neither needed -> Table A
    return "A", 20, [1,2,5,6,7]

def score_one(row):
    """
    Score a single test case row and return a dictionary of scoring details.

    Each criterion is evaluated only if it is active for the table to which the
    case belongs.  The total is the sum of points awarded for active criteria.
    """
    key = _text(row.get('Issue key') or row.get('Issue Key'))
    summary = _text(row.get('Summary'))
    priority = _text(row.get('Priority')).lower()
    steps_text = _text(row.get('Custom field (Manual Test Steps)'))

    # Extract Action and Expected result from JSON-like steps text
    action = extract_first(steps_text, "Action")
    expected = extract_first(steps_text, "Expected Result")

    # Determine table classification and base point value
    table, base, active = choose_table(summary, steps_text)

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

    # 3) Data – must have non-empty tag or JSON field for points
    if 3 in active:
        if has_data_present_for_scoring(steps_text):
            pts['Data'] = base; notes.append("✅ Data mevcut (etiket/alan)"); total += base
        else:
            pts['Data'] = 0; notes.append("❌ Data bulunamadı")

    # 4) Ön Koşul
    if 4 in active:
        if has_precond_present_for_scoring(steps_text):
            pts['Ön Koşul'] = base; notes.append("✅ Ön koşul belirtilmiş/ima edilmiş"); total += base
        else:
            pts['Ön Koşul'] = 0; notes.append("❌ Ön koşul eksik")

    # 5) Stepler – kırıntı mantığı
    if 5 in active:
        if not action.strip():
            pts['Stepler'] = 0; notes.append("❌ Stepler boş")
        elif any(x in action for x in [",", " ardından ", " sonra ", " ve "]):
            kırp = 5 if base >= 17 else 3
            pts['Stepler'] = max(base - kırp, 1); notes.append(f"🔸 Birleşik ama mantıklı ({pts['Stepler']})"); total += pts['Stepler']
        else:
            pts['Stepler'] = base; notes.append("✅ Stepler düzgün"); total += base

    # 6) Client
    if 6 in active:
        ck = ["android","ios","web","mac","windows","chrome","safari"]
        if any(c in summary.lower() for c in ck) or any(c in action.lower() for c in ck):
            pts['Client'] = base; notes.append("✅ Client bilgisi var"); total += base
        else:
            pts['Client'] = 0; notes.append("❌ Client bilgisi eksik")

    # 7) Expected
    if 7 in active:
        if not expected.strip():
            pts['Expected'] = 0; notes.append("❌ Expected result eksik")
        elif any(w in expected.lower() for w in ["test edilir","kontrol edilir"]):
            pts['Expected'] = max(base-3, 1); notes.append(f"🔸 Expected zayıf ifade ({pts['Expected']})"); total += pts['Expected']
        else:
            pts['Expected'] = base; notes.append("✅ Expected düzgün"); total += base

    return {
        "Key": key,
        "Summary": summary,
        "Tablo": table,
        "Toplam Puan": total,
        **pts,
        "Açıklama": " | ".join(notes),
    }

###############################################################################
#                                Main Logic                                    #
###############################################################################
if uploaded:
    # Seed random sampling consistently if requested
    if fix_seed:
        random.seed(20250831 + st.session_state.reroll)
    else:
        random.seed(time.time_ns())

    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    # Sample test cases for evaluation
    if len(df) > sample_size:
        idx = random.sample(range(len(df)), sample_size)
        sample = df.iloc[idx].copy()
    else:
        sample = df.copy()

    # Compute scoring
    results = sample.apply(score_one, axis=1, result_type='expand')

    # ---------- KPI Summaries ----------
    total_cases = len(results)
    avg_score = round(results["Toplam Puan"].mean() if total_cases else 0, 1)
    min_score = int(results["Toplam Puan"].min()) if total_cases else 0
    max_score = int(results["Toplam Puan"].max()) if total_cases else 0
    dist = results['Tablo'].value_counts().reindex(["A","B","C","D"]).fillna(0).astype(int)

    k1, k2, k3, k4 = st.columns([1,1,1,1])
    with k1:
        st.markdown('<div class="kpi"><div class="kpi-title">Toplam Örnek</div><div class="kpi-value">{}</div><div class="kpi-sub">Değerlendirilen</div></div>'.format(total_cases), unsafe_allow_html=True)
    with k2:
        st.markdown('<div class="kpi"><div class="kpi-title">Dağılım (A/B/C/D)</div><div class="kpi-value">{}/{}/{}/{}</div><div class="kpi-sub">Tablo adetleri</div></div>'.format(dist["A"],dist["B"],dist["C"],dist["D"]), unsafe_allow_html=True)
    with k3:
        st.markdown('<div class="kpi"><div class="kpi-title">Ortalama Skor</div><div class="kpi-value">{}</div><div class="kpi-sub">Min: {} • Max: {}</div></div>'.format(avg_score, min_score, max_score), unsafe_allow_html=True)
    with k4:
        st.markdown('<div class="kpi"><div class="kpi-title">Rapor Zamanı</div><div class="kpi-value">{}</div><div class="kpi-sub">Yerel saat</div></div>'.format(datetime.now().strftime("%H:%M")), unsafe_allow_html=True)

    st.markdown("### 📈 Tablo Dağılımı")
    st.bar_chart(dist)

    # ---------- Score percentage + table ----------
    MAX_BY_TABLE = {"A": 100, "B": 102, "C": 102, "D": 98}
    results["Maks Puan"] = results["Tablo"].map(MAX_BY_TABLE).fillna(100)
    results["Skor %"] = (results["Toplam Puan"] / results["Maks Puan"]).clip(0,1) * 100
    results["Skor %"] = results["Skor %"].round(1)

    show_df = results[["Key","Summary","Tablo","Toplam Puan","Skor %","Açıklama"]].copy()

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Key": st.column_config.TextColumn("Key", help="Issue key"),
            "Summary": st.column_config.TextColumn("Summary", width="medium"),
            "Tablo": st.column_config.TextColumn("Tablo"),
            "Toplam Puan": st.column_config.NumberColumn("Toplam Puan", format="%d"),
            "Skor %": st.column_config.ProgressColumn("Skor %", help="Toplam puanın tabloya göre maksimuma oranı", min_value=0, max_value=100),
            "Açıklama": st.column_config.TextColumn("Açıklama", width="large"),
        }
    )

    st.download_button(
        "📥 Sonuçları CSV olarak indir",
        data=show_df.to_csv(index=False, sep=';', encoding='utf-8'),
        file_name=f"testcase_skorlari_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    # ---------- Detail Cards ----------
    st.markdown("## 📝 Detaylar")
    for _, r in results.iterrows():
        max_pt = MAX_BY_TABLE.get(r["Tablo"], 100)
        pct = float(r["Toplam Puan"]) / max_pt if max_pt else 0
        badge_class = {"A":"badge badge-a","B":"badge badge-b","C":"badge badge-c","D":"badge badge-d"}.get(r["Tablo"], "badge")

        st.markdown('<div class="case-card">', unsafe_allow_html=True)
        st.markdown(f'''
            <div class="case-head">
              <div class="case-title">🔍 {r["Key"]} — {r["Summary"]}</div>
              <div class="case-meta"><span class="{badge_class}">Tablo {r["Tablo"]}</span></div>
            </div>
        ''', unsafe_allow_html=True)

        c1, c2 = st.columns([3,1])
        with c1:
            st.markdown(f"**Toplam Puan:** `{int(r['Toplam Puan'])}` / `{int(max_pt)}`")
            st.progress(min(max(pct,0),1.0))
        with c2:
            st.markdown(f"**Skor %:** **{round(pct*100,1)}%**")

        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        kriterler = ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']
        for k in kriterler:
            if k in r and pd.notna(r[k]):
                st.markdown(f"- **{k}**: {int(r[k])} puan")
        st.markdown(f"🗒️ **Açıklamalar:** {r['Açıklama']}")
        st.markdown('</div>', unsafe_allow_html=True)
