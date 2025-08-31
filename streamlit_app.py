# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v1.2 – Data kriteri katı doğrulama ("Data:" şart)
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Test Case SLA", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama test caseleri **A/B/C/D** tablosuna göre otomatik sınıflandırır ve 7 kriter üzerinden puanlar.  
**Data** kriteri, yalnızca **`Custom field (Manual Test Steps)` içinde `Data:` etiketi** varsa puanlanır.
""")

with st.expander("📌 Kurallar (özet)"):
    st.markdown("""
- **CSV ayraç:** `;`
- **Sütunlar:** `Issue key`, `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`
- **Tablo seçimi (senaryoya göre):**
  - A: Data da precondition da gerekmiyor
  - B: Precondition gerekli
  - C: Data gerekli
  - D: Hem data hem precondition gerekli
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14  
- **Data kuralı:** Sadece *Manual Test Steps* alanında **`Data:`** etiketi geçerse **var** kabul edilir.
""")

sample_size = st.slider("📌 Kaç test case değerlendirilsin?", 1, 50, 5)
uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def extract_first(text, key):
    # JSON benzeri içerikte "Key": "..." desenini yakalar (esnek, çok satırlı)
    m = re.search(rf'"{key}"\s*:\s*"(.*?)"', text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def has_data_tag(steps_text):
    # Sadece Manual Test Steps alanında "Data:" etiketi var mı?
    return bool(re.search(r'(?:^|\n|\r)\s*[-\s]*Data\s*:', steps_text, re.IGNORECASE))

def has_precondition(steps_text, labels_text):
    return ('precond' in labels_text.lower()
            or bool(re.search(r'\bprecondition\b|\bön\s*koşul\b', steps_text, re.IGNORECASE)))

def choose_table(steps_text, labels_text):
    data_needed = has_data_tag(steps_text) or bool(
        re.search(r'\b(msisdn|token|auth|payload|account|config)\b', steps_text, re.IGNORECASE)
    )
    precond_needed = has_precondition(steps_text, labels_text)
    if data_needed and precond_needed:
        return "D", 14, [1,2,3,4,5,6,7]
    if data_needed:
        return "C", 17, [1,2,3,5,6,7]
    if precond_needed:
        return "B", 17, [1,2,4,5,6,7]
    return "A", 20, [1,2,5,6,7]

def score_one(row):
    key = str(row.get('Issue key') or row.get('Issue Key') or "").strip()
    summary = str(row.get('Summary') or "").strip()
    priority = str(row.get('Priority') or "").strip().lower()
    labels = str(row.get('Labels') or "")
    steps_text = str(row.get('Custom field (Manual Test Steps)') or "")

    # Ham alanlardan örnek birer Action/Data/Expected çek (gösterim için değil, kontroller için)
    action = extract_first(steps_text, "Action")
    data_val = extract_first(steps_text, "Data")
    expected = extract_first(steps_text, "Expected Result")

    table, base, active = choose_table(steps_text, labels)
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

    # 3) Data  ➜ SADECE "Data:" etiketi varsa puan
    if 3 in active:
        data_present = has_data_tag(steps_text)
        if data_present:
            pts['Data'] = base; notes.append("✅ `Data:` etiketi var"); total += base
        else:
            pts['Data'] = 0; notes.append("❌ `Data:` etiketi yok (0)")

    # 4) Ön Koşul
    if 4 in active:
        if has_precondition(steps_text, labels):
            pts['Ön Koşul'] = base; notes.append("✅ Ön koşul belirtilmiş"); total += base
        else:
            pts['Ön Koşul'] = 0; notes.append("❌ Ön koşul eksik")

    # 5) Stepler (ayrıştırma kalitesi – kırıntı kuralı)
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
        ck = ["android","ios","web","mac","windows"]
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
        "Açıklama": " | ".join(notes)
    }

if uploaded:
    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)  # son çare

    sample = df.sample(n=sample_size, random_state=42) if len(df) >= sample_size else df.copy()
    results = sample.apply(score_one, axis=1, result_type='expand')

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(results.set_index("Key"))

    st.download_button(
        "📥 Sonuçları CSV olarak indir",
        data=results.to_csv(index=False, sep=';', encoding='utf-8'),
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
