# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v1.8 – UI (KPI/Progress/Sidebar) + Data puanı (etiket veya JSON alanı)
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
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 100, 8)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar (mantık) ----------
def _text(x): 
    return str(x or "")

def _match(pattern, text):
    return re.search(pattern, text or "", re.IGNORECASE)

def has_data_tag(steps_text:str) -> bool:
    # Eski kural: satır başında "Data:" etiketi
    return bool(re.search(r'(?:^|\n|\r)\s*[-\s]*Data\s*:', steps_text or "", re.IGNORECASE))

def extract_first(text, key):
    # JSON benzeri içerikten "Key": "..." yakala
    m = re.search(rf'"{key}"\s*:\s*"(.*?)"', text or "", re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def has_data_present_for_scoring(steps_text:str) -> bool:
    """
    Data kriteri için 'var' kabulü:
    - "Data:" etiketi VARSA veya
    - JSON benzeri içerikte "Data": "<boş olmayan>" alanı VARSA
    - 'none', 'n/a', '-', 'yok' gibi değersiz girdiler hariç tutulur
    """
    if has_data_tag(steps_text):
        return True
    matches = re.findall(r'"Data"\s*:\s*"(.*?)"', steps_text or "", re.IGNORECASE | re.DOTALL)
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    for m in matches:
        val = re.sub(r'\s+', ' ', (m or "")).strip().lower()
        if val not in meaningless and len(val) > 0:
            return True
    return False

def scan_data_signals(text:str):
    t = (text or "").lower()
    signals = []
    if _match(r'\b(select|insert|update|delete)\b', t): signals.append("SQL")
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t) and _match(r'"\w+"\s*:\s*".+?"', t): signals.append("JSON body")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\-]?id|subscriber)\b', t): signals.append("Kimlik alanı")
    if _match(r'\b(post|put|patch)\b', t) and _match(r'\b(body|payload)\b', t): signals.append("POST payload")
    if _match(r'<\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*>', t) or \
       _match(r'\{\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*\}', t): signals.append("Placeholder(ID)")
    return signals

def scan_precond_signals(text:str):
    t = (text or "").lower()
    signals = []
    if _match(r'\bprecondition\b|ön\s*koşul|given .*already', t): signals.append("Precondition ifadesi")
    if _match(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth)\b', t): signals.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): signals.append("Abonelik aktif")
    if _match(r'\bexisting user|mevcut kullanıcı\b', t): signals.append("Mevcut kullanıcı/hesap")
    if _match(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission)\b', t): signals.append("Ortam/Ayar/Yetki")
    return signals

def decide_data_needed(summary:str, steps_text:str):
    """
    Data gerçekten gerekli mi?
    - 'Data:' etiketi **veya** JSON 'Data' alanı doluysa → doğrudan GEREKLİ.
    - Aksi halde, güçlü sinyal sayısı ≥ 2 ise GEREKLİ.
    """
    combined = (summary or "") + "\n" + (steps_text or "")
    data_field = extract_first(steps_text, "Data")
    if has_data_present_for_scoring(steps_text) or (data_field.strip() != ""):
        return True
    signals = scan_data_signals(combined)
    return len(set(signals)) >= 2

def decide_precond_needed(summary:str, steps_text:str):
    combined = (summary or "") + "\n" + (steps_text or "")
    signals = scan_precond_signals(combined)
    return len(set(signals)) >= 1

def choose_table(summary, steps_text):
    data_needed = decide_data_needed(summary, steps_text)
    pre_needed = decide_precond_needed(summary, steps_text)
    if data_needed and pre_needed:
        return "D", 14, [1,2,3,4,5,6,7]
    if data_needed:
        return "C", 17, [1,2,3,5,6,7]
    if pre_needed:
        return "B", 17, [1,2,4,5,6,7]
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

    # 3) Data – etiket **veya** JSON 'Data' alanı doluysa puan
    if 3 in active:
        if has_data_present_for_scoring(steps_text):
            pts['Data'] = base; notes.append("✅ Data mevcut (etiket/alan)"); total += base
        else:
            pts['Data'] = 0; notes.append("❌ Data bulunamadı")

    # 4) Ön Koşul
    if 4 in active:
        if decide_precond_needed(summary, steps_text):
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

# ---------- Çalıştır ----------
if uploaded:
    if fix_seed:
        random.seed(20250831 + st.session_state.reroll)
    else:
        random.seed(time.time_ns())

    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    if len(df) > sample_size:
        idx = random.sample(range(len(df)), sample_size)
        sample = df.iloc[idx].copy()
    else:
        sample = df.copy()

    results = sample.apply(score_one, axis=1, result_type='expand')

    # ---------- KPI Özetleri ----------
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

    # ---------- Skor yüzdesi + tablo ----------
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

    # ---------- Detay Kartları ----------
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
