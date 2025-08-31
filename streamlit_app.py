import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="Test Case SLA", page_icon="📋", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama, test caselerinizi **A, B, C veya D** tablosuna göre değerlendirir.  
Her test case'in ait olduğu tablo, **senaryo içeriğine göre otomatik belirlenir** ve 7 kritere göre puanlama yapılır.
""")

# 🔢 Kurallar ve Tablo Yapısı
with st.expander("📌 Değerlendirme Kuralları ve Tablo Bilgisi"):
    st.markdown("""
**CSV formatı:** CSV dosyası `;` (noktalı virgül) ile ayrılmalı.

**Gerekli sütunlar:** `Issue Key`, `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`

### 🧮 Kullanılan Kurallar ve Tablo Seçimi:
- **A Tablosu**: Veri veya ön koşul gerekmeyen testler. (5 kriter)
- **B Tablosu**: Sadece ön koşul gereken testler. (6 kriter)
- **C Tablosu**: Sadece test verisi gereken testler. (6 kriter)
- **D Tablosu**: Hem ön koşul hem test verisi gereken testler. (7 kriter)

### 📝 Kriterler:
1. Test başlığı anlaşılır mı?
2. Öncelik bilgisi girilmiş mi?
3. Test datası eklenmiş mi? (yalnızca C ve D tablolarında)
4. Test ön koşul eklenmiş mi? (yalnızca B ve D tablolarında)
5. Test stepleri var mı ve doğru ayrıştırılmış mı?
6. Hangi clientta koşulacağı belli mi?
7. Expected result var mı ve anlamlı mı?

### 🎯 Puanlama:
- A: 5 kriter × 20 puan = 100 puan
- B/C: 6 kriter × 17 puan = 102 puan
- D: 7 kriter × 14 puan = 98 puan

🔴 Eksik kriter varsa puanı **tamamen kırılır (0)**.
🟠 Step alanı tek bir bloksa ama benzer işlemler birlikteyse: **10 puan kırılır.**
🟡 Step yerine summary tekrar edildiyse: **1 puan verilir.**
✅ Step’ler düzgün ayrılmışsa: **tam puan** verilir.
    """)



# 🎯 Kaç test case değerlendirilecek?
sample_size = st.slider("📌 Kaç test case örneği değerlendirilsin?", min_value=1, max_value=50, value=5)

# 📤 CSV Yükleme
uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    st.success("✅ Dosya başarıyla yüklendi. Örnekler değerlendiriliyor...")

    sampled_df = df.sample(n=sample_size, random_state=42)

    def score_case(row):
        key = row['Issue key']
        summary = str(row['Summary']).strip()
        priority = str(row['Priority']).strip().lower()
        labels = str(row['Labels']).lower()
        steps_field = str(row['Custom field (Manual Test Steps)'])

        action = re.search(r'"Action"\s*:\s*"(.*?)"', steps_field)
        data = re.search(r'"Data"\s*:\s*"(.*?)"', steps_field)
        expected = re.search(r'"Expected Result"\s*:\s*"(.*?)"', steps_field)

        action = action.group(1) if action else ""
        data = data.group(1) if data else ""
        expected = expected.group(1) if expected else ""

        testdata_needed = bool(re.search(r'data:|msisdn|token|auth|account|payload|config', steps_field, re.IGNORECASE))
        precondition_needed = 'precond' in labels

        if testdata_needed and precondition_needed:
            table, base, aktif = "D", 14, [1,2,3,4,5,6,7]
        elif testdata_needed:
            table, base, aktif = "C", 17, [1,2,3,5,6,7]
        elif precondition_needed:
            table, base, aktif = "B", 17, [1,2,4,5,6,7]
        else:
            table, base, aktif = "A", 20, [1,2,5,6,7]

        puanlar, açıklamalar, toplam = {}, [], 0

        if 1 in aktif:
            if len(summary) < 10:
                puanlar['Başlık'], açıklamalar = 0, açıklamalar + ["❌ Başlık çok kısa"]
            elif any(x in summary.lower() for x in ["test edilir", "kontrol edilir"]):
                puanlar['Başlık'] = base - 3
                açıklamalar.append(f"🔸 Başlık zayıf ifade (puan: {base - 3})")
                toplam += base - 3
            else:
                puanlar['Başlık'] = base
                açıklamalar.append("✅ Başlık anlaşılır")
                toplam += base

        if 2 in aktif:
            if priority in ["", "null", "none"]:
                puanlar['Öncelik'], açıklamalar = 0, açıklamalar + ["❌ Öncelik bilgisi eksik"]
            else:
                puanlar['Öncelik'] = base
                açıklamalar.append("✅ Öncelik bilgisi var")
                toplam += base

        if 3 in aktif:
            if data.strip():
                puanlar['Data'] = base
                açıklamalar.append("✅ Test datası var")
                toplam += base
            else:
                puanlar['Data'] = 0
                açıklamalar.append("❌ Test datası eksik")

        if 4 in aktif:
            if precondition_needed:
                puanlar['Ön Koşul'] = base
                açıklamalar.append("✅ Ön koşul gerekli ve belirtilmiş")
                toplam += base
            else:
                puanlar['Ön Koşul'] = 0
                açıklamalar.append("❌ Ön koşul eksik")

        if 5 in aktif:
            if not action.strip():
                puanlar['Stepler'] = 0
                açıklamalar.append("❌ Stepler boş")
            elif any(x in action for x in [",", " ardından ", " sonra ", " ve "]):
                puanlar['Stepler'] = 3
                açıklamalar.append("🔸 Step birleşik (puan: 3)")
                toplam += 3
            else:
                puanlar['Stepler'] = base
                açıklamalar.append("✅ Stepler ayrılmış")
                toplam += base

        if 6 in aktif:
            clients = ["android", "ios", "web", "mac", "windows"]
            if any(c in summary.lower() for c in clients) or any(c in action.lower() for c in clients):
                puanlar['Client'] = base
                açıklamalar.append("✅ Client bilgisi var")
                toplam += base
            else:
                puanlar['Client'] = 0
                açıklamalar.append("❌ Client bilgisi eksik")

        if 7 in aktif:
            if not expected.strip():
                puanlar['Expected'] = 0
                açıklamalar.append("❌ Expected result eksik")
            elif any(w in expected.lower() for w in ["test edilir", "kontrol edilir"]):
                puanlar['Expected'] = base - 3
                açıklamalar.append(f"🔸 Expected zayıf ifade (puan: {base - 3})")
                toplam += base - 3
            else:
                puanlar['Expected'] = base
                açıklamalar.append("✅ Expected result düzgün")
                toplam += base

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Toplam Puan": toplam,
            **puanlar,
            "Açıklama": "\n".join(açıklamalar),
            "Action": action,
            "Data": data,
            "Expected Result": expected
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(sonuçlar.set_index("Key").T)

    st.download_button("📥 Sonuçları CSV olarak indir", data=sonuçlar.to_csv(index=False, sep=';', encoding='utf-8'), file_name="testcase_skorlari.csv", mime="text/csv")

    st.markdown("## 📝 Detaylı İnceleme")
    for _, row in sonuçlar.iterrows():
        st.markdown(f"### 🔍 {row['Key']} | {row['Summary']}")
        st.markdown(f"📌 **Tablo:** `{row['Tablo']}` | 🧮 **Toplam Puan:** `{row['Toplam Puan']}`")

        for kriter in ['Başlık', 'Öncelik', 'Data', 'Ön Koşul', 'Stepler', 'Client', 'Expected']:
            if kriter in row:
                st.markdown(f"➡️ **{kriter}**: `{row[kriter]}` puan")

        st.markdown(f"🗒️ Açıklamalar:\n{row['Açıklama']}")
        st.divider()

