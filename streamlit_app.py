# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v2.1 – Data Block Fix
import streamlit as st
import pandas as pd
import re
import time
import random
from datetime import datetime

# ---------- Sayfa & Stil ----------
st.set_page_config(page_title="Test Case SLA", layout="wide")

CUSTOM_CSS = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.app-hero {
  background: linear-gradient(135deg, #1f6feb 0%, #0ea5e9 100%);
  color: white; padding: 18px 22px; border-radius: 14px; margin-bottom: 18px;
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.18);
}
.app-hero h1 { font-size: 24px; margin: 0 0 6px 0; line-height: 1.2; }
.app-hero p { margin: 0; opacity: 0.95; }
.kpi {
  border-radius: 14px; padding: 14px; background: #fff;
  border: 1px solid rgba(2,6,23,0.06); box-shadow: 0 4px 16px rgba(2,6,23,0.06);
}
.kpi .kpi-title { font-size: 12px; color: #475569; margin-bottom: 6px; }
.kpi .kpi-value { font-size: 20px; font-weight: 700; color: #0f172a; }
.kpi .kpi-sub { font-size: 12px; color: #64748b; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px;
  border: 1px solid rgba(2,6,23,0.08); background: #f8fafc; color: #0f172a; }
.badge-a { background: #eef2ff; color: #3730a3; border-color: #c7d2fe; }
.badge-b { background: #ecfeff; color: #155e75; border-color: #a5f3fc; }
.badge-c { background: #fef9c3; color: #854d0e; border-color: #fde68a; }
.badge-d { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
.case-card {
  border-radius: 14px; padding: 14px 16px; background: #fff;
  border: 1px solid rgba(2,6,23,0.06); box-shadow: 0 6px 24px rgba(2,6,23,0.06);
  margin-bottom: 14px;
}
.case-head { display: flex; align-items: center; justify-content: space-between; gap: 8px;
  border-bottom: 1px dashed rgba(2,6,23,0.08); padding-bottom: 8px; margin-bottom: 8px; }
.case-title { font-weight: 700; color: #0f172a; }
.case-meta { font-size: 12px; color: #475569; }
.hr-soft { border: none; border-top: 1px dashed rgba(2,6,23,0.08); margin: 8px 0; }
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

# ---------- Sidebar Kontroller ----------
st.sidebar.header("⚙️ Ayarlar")
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x): 
    return str(x or "")

def _match(pattern, text):
    return re.search(pattern, text or "", re.IGNORECASE)

def _cleanup_html(s: str) -> str:
    s = s or ""
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</?(p|div|li|tr|td|th|ul|ol|span)>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return s

def _is_meaningless(val: str) -> bool:
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    return re.sub(r'\s+', ' ', (val or '')).strip().lower() in meaningless

def extract_first(text, key):
    m = re.search(rf'"{key}"\s*:\s*"(.*?)"', text or "", re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def extract_data_blocks(steps_text: str) -> list[str]:
    blocks = []
    # JSON "Data":"..."
    for m in re.finditer(r'"Data"\s*:\s*"(?:\\.|[^"])*"', steps_text or "", re.IGNORECASE | re.DOTALL):
        raw = m.group(0)
        val = re.sub(r'^.*?":\s*"(.*)"$', r'\1', raw, flags=re.DOTALL)
        val = val.replace('\\"', '"').strip()
        if val:
            blocks.append(val)
    # HTML temizleyip Data başlığı
    txt = _cleanup_html(steps_text)
    pattern = re.compile(
        r'(?:^|\n)\s*Data\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Expected\s*Result|Action|Attachments?)\b|$)',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = m.group(1).strip()
        if val:
            blocks.append(val)
    return [b for b in blocks if b.strip()]

def is_meaningful_data(value: str) -> bool:
    if _is_meaningless(value):
        return False
    v = value.strip()
    if re.search(r'https?://', v, re.I): return True
    if re.search(r'\b(select|insert|update|delete)\b', v, re.I): return True
    if re.search(r'\b[a-z_]+\.[a-z_]+\b', v, re.I): return True
    if len(re.sub(r'\s+', '', v)) >= 2: return True
    return False

def has_data_present_for_scoring(steps_text: str) -> bool:
    blocks = extract_data_blocks(steps_text)
    return any(is_meaningful_data(b) for b in blocks)

# Precondition signal taramaları aynı (kısaltıyorum burada)
def scan_precond_signals(text:str):
    t = (text or "").lower()
    signals = []
    if _match(r'\bprecondition\b|ön\s*koşul|given .*already', t): signals.append("Precondition ifadesi")
    if _match(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth)\b', t): signals.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): signals.append("Abonelik aktif")
    if _match(r'\bexisting user|mevcut kullanıcı\b', t): signals.append("Mevcut kullanıcı/hesap")
    if _match(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission)\b', t): signals.append("Ortam/Ayar/Yetki")
    return signals

def decide_data_needed(summary, steps_text):
    if has_data_present_for_scoring(steps_text):
        return True
    combined = (summary or "") + "\n" + (steps_text or "")
    signals = []
    if _match(r'\b(select|insert|update|delete)\b', combined): signals.append("SQL")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\b', combined): signals.append("ID field")
    return len(set(signals)) >= 1

def decide_precond_needed(summary, steps_text):
    combined = (summary or "") + "\n" + (steps_text or "")
    signals = scan_precond_signals(combined)
    return len(set(signals)) >= 1

def choose_table(summary, steps_text):
    data_needed = decide_data_needed(summary, steps_text)
    pre_needed = decide_precond_needed(summary, steps_text)
    if data_needed and pre_needed: return "D", 14, [1,2,3,4,5,6,7]
    if data_needed: return "C", 17, [1,2,3,5,6,7]
    if pre_needed: return "B", 17, [1,2,4,5,6,7]
    return "A", 20, [1,2,5,6,7]

def score_one(row):
    key = _text(row.get('Issue key') or row.get('Issue Key'))
    summary = _text(row.get('Summary'))
    priority = _text(row.get('Priority')).lower()
    steps_text = _text(row.get('Custom field (Manual Test Steps)'))
    action = extract_first(steps_text, "Action")
    expected = extract_first(steps_text, "Expected Result")
    table, base, active = choose_table(summary, steps_text)

    pts, notes, total = {}, [], 0
    if 1 in active:
        if not summary: pts['Başlık']=0; notes.append("❌ Başlık eksik")
        else: pts['Başlık']=base; notes.append("✅ Başlık"); total+=base
    if 2 in active:
        pts['Öncelik']=base if priority else 0
        notes.append("✅ Öncelik" if priority else "❌ Öncelik eksik")
        if priority: total+=base
    if 3 in active:
        if has_data_present_for_scoring(steps_text):
            pts['Data']=base; notes.append("✅ Data var"); total+=base
        else:
            pts['Data']=0; notes.append("❌ Data yok")
    if 4 in active:
        if decide_precond_needed(summary, steps_text):
            pts['Ön Koşul']=base; notes.append("✅ Precondition var"); total+=base
        else: pts['Ön Koşul']=0; notes.append("❌ Precondition yok")
    if 5 in active:
        pts['Stepler']=base if action else 0
        notes.append("✅ Stepler" if action else "❌ Stepler boş")
        if action: total+=base
    if 6 in active:
        ck=["android","ios","web","mac","windows","chrome","safari"]
        if any(c in summary.lower() for c in ck) or any(c in action.lower() for c in ck):
            pts['Client']=base; notes.append("✅ Client"); total+=base
        else: pts['Client']=0; notes.append("❌ Client yok")
    if 7 in active:
        if expected: pts['Expected']=base; notes.append("✅ Expected"); total+=base
        else: pts['Expected']=0; notes.append("❌ Expected yok")
    return {"Key":key,"Summary":summary,"Tablo":table,"Toplam Puan":total,**pts,"Açıklama":" | ".join(notes)}

# ---------- Çalıştır ----------
if uploaded:
    if fix_seed: random.seed(20250831 + st.session_state.reroll)
    else: random.seed(time.time_ns())
    try: df = pd.read_csv(uploaded, sep=';')
    except: df = pd.read_csv(uploaded)

    if len(df)>sample_size: sample=df.sample(n=sample_size, random_state=random.getrandbits(32))
    else: sample=df.copy()

    results=sample.apply(score_one, axis=1, result_type='expand')

    # KPI
    total_cases=len(results)
    avg_score=round(results["Toplam Puan"].mean() if total_cases else 0,1)
    min_score=int(results["Toplam Puan"].min()) if total_cases else 0
    max_score=int(results["Toplam Puan"].max()) if total_cases else 0
    dist=results['Tablo'].value_counts().reindex(["A","B","C","D"]).fillna(0).astype(int)

    st.markdown("### 📈 Tablo Dağılımı")
    st.bar_chart(dist)
    MAX_BY_TABLE={"A":100,"B":102,"C":102,"D":98}
    results["Maks Puan"]=results["Tablo"].map(MAX_BY_TABLE).fillna(100)
    results["Skor %"]=(results["Toplam Puan"]/results["Maks Puan"]).clip(0,1)*100
    results["Skor %"]=results["Skor %"].round(1)

    show_df=results[["Key","Summary","Tablo","Toplam Puan","Skor %","Açıklama"]]
    st.dataframe(show_df,use_container_width=True,hide_index=True)
