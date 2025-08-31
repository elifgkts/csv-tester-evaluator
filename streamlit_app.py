# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v4.1 – Hata Düzeltmeleri ve İyileştirmeler
import streamlit as st
import pandas as pd
import re
import time
import html
from datetime import datetime

# ---------- Sayfa & Stil ----------
st.set_page_config(page_title="Test Case Kalite Değerlendirmesi", layout="wide")
CUSTOM_CSS = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.app-hero{background:linear-gradient(135deg,#1f6feb 0%,#0ea5e9 100%);color:#fff;padding:18px 22px;border-radius:14px;margin-bottom:18px;box-shadow:0 8px 24px rgba(2,6,23,.18)}
.app-hero h1{font-size:24px;margin:0 0 6px 0;line-height:1.2}
.app-hero p{margin:0;opacity:.95}
.kpi{border-radius:14px;padding:14px;background:#fff;border:1px solid rgba(2,6,23,.06);box-shadow:0 4px 16px rgba(2,6,23,.06)}
.kpi .kpi-title{font-size:12px;color:#475569;margin-bottom:6px}
.kpi .kpi-value{font-size:20px;font-weight:700;color:#0f172a}
.kpi .kpi-sub{font-size:12px;color:#64748b}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid rgba(2,6,23,.08);background:#f8fafc;color:#0f172a}
.badge-a{background:#eef2ff;color:#3730a3;border-color:#c7d2fe}
.badge-b{background:#ecfeff;color:#155e75;border-color:#a5f3fc}
.badge-c{background:#fef9c3;color:#854d0e;border-color:#fde68a}
.badge-d{background:#fee2e2;color:#991b1b;border-color:#fecaca}
.case-card{border-radius:14px;padding:14px 16px;background:#fff;border:1px solid rgba(2,6,23,.06);box-shadow:0 6px 24px rgba(2,6,23,.06);margin-bottom:14px}
.case-head{display:flex;align-items:center;justify-content:space-between;gap:8px;border-bottom:1px dashed rgba(2,6,23,.08);padding-bottom:8px;margin-bottom:8px}
.case-title{font-weight:700;color:#0f172a}
.case-meta{font-size:12px;color:#475569}
.hr-soft{border:none;border-top:1px dashed rgba(2,6,23,.08);margin:8px 0}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown(f"""
<div class="app-hero">
  <h1>📋 Test Case Kalite Değerlendirmesi</h1>
  <p>Tablo (A/B/C/D) yalnızca <b>Summary + Steps</b> sinyallerinden; <b>Data</b> sütunu sadece puanda dikkate alınır.
  <span style="opacity:0.8">Rapor zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span></p>
</div>
""", unsafe_allow_html=True)

with st.expander("📌 Kurallar (özet)"):
    st.markdown("""
- **CSV ayraç:** `;`
- **Gerekli sütunlar:** `Issue key` (veya `Issue Key`), `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`
- **Tablo mantığı:** A: Data/Pre yok • B: Pre gerekli • C: Data gerekli • D: Data+Pre gerekli
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14
""")

# ---------- Sidebar ----------
st.sidebar.header("⚙️ Ayarlar")
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 100, 8)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=True)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x):
    return "" if pd.isna(x) else str(x)

def norm(text: str) -> str:
    t = _text(text)
    t = html.unescape(t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = t.replace("&nbsp;", " ")
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def _match(pattern, text):
    return re.search(pattern, _text(text), re.IGNORECASE)

def has_data_tag(steps_text:str) -> bool:
    return bool(re.search(r'(?:^|\n|\r|\|)\s*[-\s]*Data\s*[:|]\s*\S', _text(steps_text), re.IGNORECASE))

def has_precond_tag(steps_text:str) -> bool:
    return bool(re.search(r'(?:^|\n|\r|\|)\s*[-\s]*(Precondition|Ön\s*Koşul|Ön\s*Şart)\s*[:|]\s*\S', _text(steps_text), re.IGNORECASE))

def extract_first(text, key):
    try:
        pattern = rf'"{key}"\s*:\s*"(.*?)"'
        matches = re.findall(pattern, _text(text), re.IGNORECASE | re.DOTALL)
        if matches:
            return matches[0].strip().replace('\\n', '\n')
    except Exception:
        return ""
    return ""

def has_data_present_for_scoring(steps_text:str) -> bool:
    if has_data_tag(steps_text):
        return True
    matches = re.findall(r'"Data"\s*:\s*"(.*?)"', _text(steps_text), re.IGNORECASE | re.DOTALL)
    return any(len((m or "").strip()) > 0 for m in matches)

# ---------- Sinyaller & Niyet Analizi ----------
ACTION_VERBS = r'(doğrula|kontrol et|sorgula|getir|oluştur|sil|güncelle|değiştir|ekle|ara|görüntüle)'
ENTITY_NOUNS = r'(kullanıcı|sipariş|ürün|hesap|fatura|abonelik|cihaz|bilet|kayıt|rapor|servis|yanıt|kod)'
ID_WORDS   = r'(msisdn|token|iban|imei|email|e-?posta|username|password|pass|user[_\-]?id|order[_\-]?id|uuid|guid|isbn|tckn|tax|vergi)'

def data_signal_score(summary:str, steps:str):
    summary_norm = norm(summary).lower()
    steps_norm = norm(steps).lower()
    combined_text = summary_norm + "\n" + steps_norm

    score = 0.0
    reasons = []

    if _match(ACTION_VERBS, summary_norm) and _match(ENTITY_NOUNS, summary_norm):
        score += 3.0; reasons.append("Özet niyet analizi (Aksiyon+Varlık)")
    if has_data_present_for_scoring(steps):
        score += 3.0; reasons.append("Data etiketi (dolu)")
    if _match(r'\b(select|insert|update|delete|from|where|join)\b', combined_text):
        score += 2.0; reasons.append("SQL")
    if _match(r'"\w+"\s*:\s*".+?"', combined_text) and (_match(r'\b(json|payload|body|request|response)\b', combined_text) or combined_text.count(':') > 2):
        score += 2.0; reasons.append("JSON body")
    if _match(r'https?://', combined_text) and (_match(r'\b(api|endpoint|request|postman|graphql)\b', combined_text) or _match(r'[\?\&]\w+=', combined_text)):
        score += 1.0; reasons.append("API/URL")
    if _match(rf'\b{ID_WORDS}\b', combined_text):
        score += 1.0; reasons.append("Kimlik alanı")

    needed = score >= 2.5
    return needed, list(set(reasons))

def precond_signals(text:str):
    t = norm(text).lower()
    reasons = []
    if has_precond_tag(text): reasons.append("Precondition etiketi (dolu)")
    if _match(r'\bprecondition\b|ön\s*koşul|ön\s*şart|given .*already', t): reasons.append("Precondition if.")
    if _match(r'\b(logged in|login|sign in|session|giriş yap(mış|ın)|authenticated|auth|bearer|authorization)\b', t): reasons.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): reasons.append("Abonelik")
    if _match(r'\bexisting user|mevcut kullanıcı|kayıtlı kullanıcı|account exists\b', t): reasons.append("Mevcut kullanıcı")
    if _match(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission|yetki)\b', t): reasons.append("Ortam/Ayar/Yetki")
    return list(set(reasons))

def choose_table(summary, steps_text):
    data_needed, data_reasons = data_signal_score(summary, steps_text)
    pre_needed,  pre_reasons  = precond_signals(summary + "\n" + steps_text)

    if data_needed and pre_needed:
        return "D", 14, [1,2,3,4,5,6,7], data_reasons, pre_reasons
    if data_needed:
        return "C", 17, [1,2,3,5,6,7], data_reasons, pre_reasons
    if pre_needed:
        return "B", 17, [1,2,4,5,6,7], data_reasons, pre_reasons
    return "A", 20, [1,2,5,6,7], data_reasons, pre_reasons

# ---------- Skorlama ----------
def score_one(row):
    key = _text(row.get('Issue key') or row.get('Issue Key'))
    summary = _text(row.get('Summary'))
    priority = _text(row.get('Priority')).lower()
    steps_text = _text(row.get('Custom field (Manual Test Steps)'))

    table, base, active, data_reasons, pre_reasons = choose_table(summary, steps_text)
    action = extract_first(steps_text, "Action")
    expected = extract_first(steps_text, "Expected Result")

    pts, notes, total = {}, [], 0

    if table == "A": notes.append("🧭 Sınıflandırma: Tablo A — Data & Precondition sinyali/niyeti saptanmadı.")
    elif table == "B": notes.append(f"🧭 Sınıflandırma: Tablo B — Önkoşul sinyalleri: {', '.join(pre_reasons)}.")
    elif table == "C": notes.append(f"🧭 Sınıflandırma: Tablo C — Data sinyalleri/niyeti: {', '.join(data_reasons)}.")
    else: notes.append(f"🧭 Sınıflandırma: Tablo D — Data: {', '.join(data_reasons)}; Pre: {', '.join(pre_reasons)}.")

    # --- Puanlama Kriterleri (HATALAR DÜZELTİLDİ) ---
    if 1 in active: # Başlık
        if not summary or len(norm(summary)) < 10:
            pts['Başlık'] = 0; notes.append("❌ Başlık çok kısa")
        elif any(w in summary.lower() for w in ["test edilir", "kontrol edilir"]):
            pts['Başlık'] = max(base - 3, 1); notes.append(f"🔸 Başlık zayıf ifade ({pts['Başlık']})")
            total += pts['Başlık'] # <<< HATA BURADAYDI, EKLENDİ
        else:
            pts['Başlık'] = base; notes.append("✅ Başlık anlaşılır")
            total += base
    if 2 in active: # Öncelik
        if priority in ["", "null", "none", "nan"]:
            pts['Öncelik'] = 0; notes.append("❌ Öncelik eksik")
        else:
            pts['Öncelik'] = base; notes.append("✅ Öncelik var")
            total += base
    if 3 in active: # Data
        if has_data_present_for_scoring(steps_text):
            pts['Data'] = base; notes.append("✅ Data mevcut (etiket/JSON alanı)")
            total += base
        else:
            pts['Data'] = 0; notes.append("❌ Data belirtilmemiş")
    if 4 in active: # Ön Koşul
        if has_precond_tag(steps_text): # Sadece etiket varlığına bakmak daha doğru
            pts['Ön Koşul'] = base; notes.append("✅ Ön koşul belirtilmiş")
            total += base
        else:
            pts['Ön Koşul'] = 0; notes.append("❌ Ön koşul belirtilmemiş")
    if 5 in active: # Stepler
        if not action.strip():
            pts['Stepler'] = 0; notes.append("❌ Stepler boş")
        elif len(action.split('\n')) > 1 or any(x in action for x in [",", " ardından ", " sonra ", " ve "]):
            pts['Stepler'] = max(base - (5 if base >= 17 else 3), 1); notes.append(f"🔸 Birleşik adımlar ({pts['Stepler']})")
            total += pts['Stepler'] # <<< HATA BURADAYDI, EKLENDİ
        else:
            pts['Stepler'] = base; notes.append("✅ Stepler atomik")
            total += base
    if 6 in active: # Client
        ck = ["android","ios","web","mac","windows","chrome","safari", "be", "backend", "fe", "frontend"]
        labels_text = _text(row.get('Labels', ''))
        combined_client_text = norm(summary).lower() + " " + norm(action).lower() + " " + labels_text.lower()
        if any(c in combined_client_text for c in ck):
            pts['Client'] = base; notes.append("✅ Client bilgisi var")
            total += base
        else:
            pts['Client'] = 0; notes.append("❌ Client bilgisi eksik")
    if 7 in active: # Expected
        if not expected.strip():
            pts['Expected'] = 0; notes.append("❌ Expected result eksik")
        elif any(w in expected.lower() for w in ["test edilir","kontrol edilir"]):
            pts['Expected'] = max(base-3, 1); notes.append(f"🔸 Expected zayıf ifade ({pts['Expected']})")
            total += pts['Expected'] # <<< HATA BURADAYDI, EKLENDİ
        else:
            pts['Expected'] = base; notes.append("✅ Expected düzgün")
            total += base

    return pd.Series({"Key": key, "Summary": norm(summary), "Tablo": table, "Toplam Puan": total, **pts, "Açıklama": " | ".join(notes)})

# ---------- Çalıştır ----------
if uploaded:
    try:
        df = pd.read_csv(uploaded, sep=';', on_bad_lines='skip')
    except Exception as e:
        st.error(f"CSV okuma hatası. Ayraç olarak noktalı virgül (;) kullanıldığına emin misin? Hata: {e}")
        st.stop()
    
    # Gerekli sütunların varlığını kontrol et
    required_cols = ['Summary', 'Priority', 'Custom field (Manual Test Steps)']
    if not ('Issue key' in df.columns or 'Issue Key' in df.columns):
        st.error("CSV dosyasında 'Issue key' veya 'Issue Key' sütunu bulunamadı.")
        st.stop()
    for col in required_cols:
        if col not in df.columns:
            st.error(f"CSV dosyasında gerekli olan '{col}' sütunu bulunamadı.")
            st.stop()

    df.columns = df.columns.str.strip()
    if 'Issue key' not in df.columns and 'Issue Key' in df.columns:
        df = df.rename(columns={'Issue Key': 'Issue key'})
    label_cols = [col for col in df.columns if 'Labels' in col]
    if label_cols:
        df['Labels'] = df[label_cols].apply(lambda x: ' '.join(x.dropna().astype(str)), axis=1)
    else:
        df['Labels'] = '' # Labels sütunu yoksa boş oluştur

    if df.empty:
        st.warning("Yüklenen CSV dosyası boş veya okunabilir satır içermiyor.")
    else:
        random_state = 42 + st.session_state.reroll if fix_seed else int(time.time())
        sample = df.sample(n=min(sample_size, len(df)), random_state=random_state)

        results = sample.apply(score_one, axis=1)

        # --- UI Çıktıları ---
        if results.empty:
            st.info("Değerlendirilecek örneklem oluşturulamadı.")
        else:
            total_cases = len(results)
            avg_score = round(results["Toplam Puan"].mean(), 1)
            min_score = int(results["Toplam Puan"].min())
            max_score = int(results["Toplam Puan"].max())
            dist = results['Tablo'].value_counts().reindex(["A","B","C","D"]).fillna(0).astype(int)

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f'<div class="kpi"><div class="kpi-title">Toplam Örnek</div><div class="kpi-value">{total_cases}</div><div class="kpi-sub">Değerlendirilen</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="kpi"><div class="kpi-title">Dağılım (A/B/C/D)</div><div class="kpi-value">{dist["A"]}/{dist["B"]}/{dist["C"]}/{dist["D"]}</div><div class="kpi-sub">Tablo adetleri</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="kpi"><div class="kpi-title">Ortalama Skor</div><div class="kpi-value">{avg_score}</div><div class="kpi-sub">Min: {min_score} • Max: {max_score}</div></div>', unsafe_allow_html=True)
            with c4: st.markdown(f'<div class="kpi"><div class="kpi-title">Rapor Zamanı</div><div class="kpi-value">{datetime.now().strftime("%H:%M")}</div><div class="kpi-sub">Yerel saat</div></div>', unsafe_allow_html=True)

            st.markdown("### 📈 Tablo Dağılımı")
            st.bar_chart(dist)

            MAX_BY_TABLE = {"A": 100, "B": 102, "C": 102, "D": 98}
            results["Maks Puan"] = results["Tablo"].map(MAX_BY_TABLE).fillna(100)
            results["Skor %"] = (results["Toplam Puan"] / results["Maks Puan"]).clip(0,1) * 100
            results["Skor %"] = results["Skor %"].round(1)

            show_df = results[["Key","Summary","Tablo","Toplam Puan","Skor %","Açıklama"]].copy()

            st.markdown("## 📊 Değerlendirme Tablosu")
            st.dataframe(show_df, use_container_width=True, hide_index=True, column_config={"Key": st.column_config.TextColumn("Key"), "Summary": st.column_config.TextColumn("Summary", width="medium"), "Tablo": st.column_config.TextColumn("Tablo"), "Toplam Puan": st.column_config.NumberColumn("Toplam Puan", format="%d"), "Skor %": st.column_config.ProgressColumn("Skor %", min_value=0, max_value=100), "Açıklama": st.column_config.TextColumn("Açıklama", width="large")})

            st.download_button("📥 Sonuçları CSV olarak indir", data=show_df.to_csv(index=False, sep=';', encoding='utf-8'), file_name=f"testcase_skorlari_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

            st.markdown("## 📝 Detaylar")
            for _, r in results.iterrows():
                max_pt = MAX_BY_TABLE.get(r["Tablo"], 100)
                pct = float(r["Toplam Puan"]) / max_pt if max_pt > 0 else 0
                badge_class = {"A":"badge-a","B":"badge-b","C":"badge-c","D":"badge-d"}.get(r["Tablo"], "")
                
                st.markdown(f'''<div class="case-card">
                    <div class="case-head">
                      <div class="case-title">🔍 {html.escape(r["Key"])} — {html.escape(r["Summary"])}</div>
                      <div class="case-meta"><span class="badge {badge_class}">Tablo {r["Tablo"]}</span></div>
                    </div>''', unsafe_allow_html=True)
                
                d1, d2 = st.columns([3,1])
                with d1:
                    st.markdown(f"**Toplam Puan:** `{int(r['Toplam Puan'])}` / `{int(max_pt)}`")
                    st.progress(min(max(pct,0),1.0))
                with d2: st.markdown(f"**Skor %:** **{round(pct*100,1)}%**")
                
                st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)
                for k in ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']:
                    if k in r and pd.notna(r[k]): st.markdown(f"- **{k}**: {int(r[k])} puan")
                st.markdown(f"🗒️ **Açıklamalar:** {html.escape(r['Açıklama'])}")
                st.markdown('</div>', unsafe_allow_html=True)
