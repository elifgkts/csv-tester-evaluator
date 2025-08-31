# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v1.3 – Doğru tablo seçimi + gerçek rastgele örnekleme
import streamlit as st
import pandas as pd
import re
import time
import random

st.set_page_config(page_title="Test Case SLA", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama test caseleri **A/B/C/D** tablosuna göre **senaryo içeriğini analiz ederek** otomatik sınıflandırır ve 7 kritere göre puanlar.  

""")

with st.expander("📌 Kurallar (özet)"):
    st.markdown("""
- **CSV ayraç:** `;`
- **Gerekli sütunlar:** `Issue key` (veya `Issue Key`), `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`
- **Tablo mantığı (senaryoya göre):**
  - **A:** Data da önkoşul da gerekmiyor
  - **B:** Önkoşul gerekli
  - **C:** Data gerekli
  - **D:** Hem data hem önkoşul gerekli
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14
""")

colA, colB = st.columns([1,1])
sample_size = colA.slider("📌 Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = colB.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.button("🎲 Yeniden örnekle"):
    st.session_state.reroll = st.session_state.reroll + 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x): 
    return str(x or "")

def has_data_signal(text):
    """
    Senaryonun DATA gerektirdiğine işaret eden güçlü sinyaller:
    - SQL: select/insert/update/delete
    - API/JSON: payload/body/json/headers, {} veya : ile key:value şablonları
    - Kimlik bilgileri/kimlikler: token/msisdn/iban/imei/email/username/password
    - Değişken placeholder: <...> veya {...}
    """
    t = text.lower()
    sql = re.search(r'\b(select|insert|update|delete)\b', t)
    api = re.search(r'\b(json|payload|body|headers|authorization|bearer|content-type)\b', t)
    ids = re.search(r'\b(msisdn|token|iban|imei|email|username|password|session|otp|验证码|auth)\b', t)
    keyvals = re.search(r'\b\w+\s*:\s*[^:\n]+', t)  # key: value
    placeholders = re.search(r'<[^>]+>|\{[^}]+\}', t)
    numbers_like = re.search(r'\b\d{10,}\b', t)  # uzun sayılar (msisdn vb)
    return any([sql, api, ids, keyvals, placeholders, numbers_like])

def has_data_tag(steps_text):
    # Data PUANLAMA için sadece "Data:" etiketi geçerli
    return bool(re.search(r'(?:^|\n|\r)\s*[-\s]*Data\s*:', steps_text, re.IGNORECASE))

def has_precondition_signal(text):
    """
    Önkoşul gereksinimini belirleyen sinyaller:
    - "Precondition", "Ön Koşul", "Given ... already"
    - Giriş/abonelik/ürün varlığı vb: login/giriş yapmış, aboneliği var, kullanıcı mevcut
    - Ortam/ayar: feature flag/seed/setup/config done
    """
    t = text.lower()
    explicit = re.search(r'\bprecondition\b|ön\s*koşul|given .*already', t)
    login = re.search(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth)\b', t)
    subscription = re.search(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t)
    user_exists = re.search(r'\bexisting user|mevcut kullanıcı\b', t)
    env = re.search(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission)\b', t)
    return any([explicit, login, subscription, user_exists, env])

def extract_first(text, key):
    # JSON benzeri içerikten "Key": "..." yakala
    m = re.search(rf'"{key}"\s*:\s*"(.*?)"', text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def choose_table(summary, steps_text):
    """
    Tablo seçimi senaryonun GERÇEKTEN ne gerektirdiğine göre:
      - data_needed: içerikte data sinyali (SQL/JSON/placeholder/kimlikler...)
      - precond_needed: içerikte önkoşul sinyali (login/Precondition/...).
    Not: Data puanlaması yine sadece "Data:" etiketi ile yapılır.
    """
    combined = (summary + "\n" + steps_text)
    data_needed = has_data_signal(combined)
    precond_needed = has_precondition_signal(combined)
    if data_needed and precond_needed:
        return "D", 14, [1,2,3,4,5,6,7]
    if data_needed:
        return "C", 17, [1,2,3,5,6,7]
    if precond_needed:
        return "B", 17, [1,2,4,5,6,7]
    return "A", 20, [1,2,5,6,7]

def score_one(row):
    key = _text(row.get('Issue key') or row.get('Issue Key'))
    summary = _text(row.get('Summary'))
    priority = _text(row.get('Priority')).lower()
    steps_text = _text(row.get('Custom field (Manual Test Steps)'))
    labels = _text(row.get('Labels'))  # sadece ek sinyal olarak; karar verici değil

    action = extract_first(steps_text, "Action")
    data_val = extract_first(steps_text, "Data")
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

    # 3) Data – sadece "Data:" etiketi varsa puan
    if 3 in active:
        if has_data_tag(steps_text):
            pts['Data'] = base; notes.append("✅ `Data:` etiketi var"); total += base
        else:
            pts['Data'] = 0; notes.append("❌ `Data:` etiketi yok (0)")

    # 4) Ön Koşul
    if 4 in active:
        if has_precondition_signal(summary + "\n" + steps_text):
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
        # Ham içerikleri saklıyoruz ama göstermiyoruz
        "_Action_raw": action, "_Data_raw": data_val, "_Expected_raw": expected
    }

# ---------- Çalıştır ----------
if uploaded:
    # seed yönetimi (deterministik istenirse)
    if fix_seed:
        random.seed(20250831 + st.session_state.reroll)
    else:
        random.seed(time.time_ns())

    # CSV oku (önce ; sonra varsayılan)
    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    # Gerçek rastgele örnekleme
    if len(df) > sample_size:
        idx = random.sample(range(len(df)), sample_size)
        sample = df.iloc[idx].copy()
    else:
        sample = df.copy()

    results = sample.apply(score_one, axis=1, result_type='expand')

    # Ham alanları çıkar, sadece skorları göster
    hide_cols = ["_Action_raw","_Data_raw","_Expected_raw"]
    show_df = results.drop(columns=hide_cols, errors="ignore").copy()

    # Dağılım özeti
    dist = show_df['Tablo'].value_counts().sort_index()
    st.markdown("### 📈 Tablo Dağılımı")
    st.write({k:int(v) for k,v in dist.items()})

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(show_df.set_index("Key"))

    st.download_button(
        "📥 Sonuçları CSV olarak indir",
        data=show_df.to_csv(index=False, sep=';', encoding='utf-8'),
        file_name="testcase_skorlari.csv",
        mime="text/csv"
    )

    st.markdown("## 📝 Detaylar")
    for _, r in results.iterrows():
        st.markdown(f"### 🔍 {r['Key']} | {r['Summary']}")
        st.markdown(f"**Tablo:** `{r['Tablo']}` • **Toplam:** `{r['Toplam Puan']}`")
        for k in ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']:
            if k in r and pd.notna(r[k]):
                st.markdown(f"- **{k}**: {int(r[k])} puan")
        st.markdown(f"🗒️ **Açıklamalar:** {r['Açıklama']}")
