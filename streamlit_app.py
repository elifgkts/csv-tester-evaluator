# 📌 Test Case Evaluator v1.0
# QA Manager: Elif Göktaş için özel olarak tasarlanmıştır.

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Test Case Değerlendirici", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama, test caselerinizi **A, B, C veya D tablosuna** göre değerlendirir.  
Her test case'in ait olduğu tablo, **senaryo içeriğine göre otomatik belirlenir** ve 7 kritere göre puanlama yapılır.
""")

# 📌 Kullanım Kuralları ve Tablo Açıklamaları
with st.expander("📌 Değerlendirme Kuralları ve Kriter Açıklamaları"):
    st.markdown("""
### ⬇️ Tablo Seçimi (Senaryoya göre):
- **A:** Test datası veya ön koşul gerektirmeyen testler (5 kriter)
- **B:** Yalnızca ön koşul gerektiren testler (6 kriter)
- **C:** Yalnızca test datası gerektiren testler (6 kriter)
- **D:** Hem test datası hem ön koşul gerektiren testler (7 kriter)

### ✅ Kriterler:
1. Test başlığı anlaşılır mı?
2. Öncelik bilgisi girilmiş mi?
3. Test datası eklenmiş mi? *(C, D için)*
4. Test ön koşul eklenmiş mi? *(B, D için)*
5. Test stepleri var ve doğru ayrıştırılmış mı?
6. Senaryonun hangi clientta koşulacağı belli mi?
7. Expected result bulunuyor mu?

### 🛠️ Notlar:
- Test datası yalnızca `Data:` alanı üzerinden kontrol edilir.
- Expected Result sadece “gerçek bir beklenen sonuç” içeriyorsa geçerli sayılır.
- Adımlar tek bir stepte birleşik ama mantıksal olarak gruplanmışsa, **az puan kırılır (örneğin 10/20)**.
- Test başlığı veya expected result **“test edilir / kontrol edilir”** gibi zayıf ifadeler içeriyorsa, puan kırılır.
""")

sample_size = st.slider("📌 Kaç test case örneği değerlendirilsin?", min_value=1, max_value=50, value=5)

# 📤 CSV Yükleme
uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    st.success("✅ Dosya başarıyla yüklendi. Şimdi örnekler değerlendiriliyor...")

    sampled_df = df.sample(n=sample_size, random_state=42)

    def score_case(row):
        key = row['Issue key']
        summary = str(row['Summary']).strip()
        priority = str(row['Priority']).strip().lower()
        labels = str(row['Labels']).lower()
        steps_field = str(row['Custom field (Manual Test Steps)'])

        # JSON benzeri alanlardan Action, Data, Expected'ı çıkar
        action_match = re.search(r'"Action"\s*:\s*"(.*?)"', steps_field)
        data_match = re.search(r'"Data"\s*:\s*"(.*?)"', steps_field)
        expected_match = re.search(r'"Expected Result"\s*:\s*"(.*?)"', steps_field)

        action = action_match.group(1) if action_match else ""
        data = data_match.group(1) if data_match else ""
        expected = expected_match.group(1) if expected_match else ""

        # Tablo Seçimi
        testdata_needed = bool(re.search(r'data:|msisdn|token|auth|account|payload|config', steps_field, re.IGNORECASE))
        precondition_needed = 'precond' in labels

        if testdata_needed and precondition_needed:
            table = "D"
            base = 14
            aktif = [1,2,3,4,5,6,7]
        elif testdata_needed:
            table = "C"
            base = 17
            aktif = [1,2,3,5,6,7]
        elif precondition_needed:
            table = "B"
            base = 17
            aktif = [1,2,4,5,6,7]
        else:
            table = "A"
            base = 20
            aktif = [1,2,5,6,7]

        puanlar = {}
        açıklamalar = []
        toplam = 0

        # 1. Başlık
        if 1 in aktif:
            if len(summary) < 10:
                puanlar['Başlık'] = 0
                açıklamalar.append("❌ Başlık çok kısa (0)")
            elif any(w in summary.lower() for w in ["test edilir", "kontrol edilir"]):
                puanlar['Başlık'] = base - 3
                açıklamalar.append(f"🔸 Zayıf ifade: 'test edilir' içeriyor (puan: {base - 3})")
                toplam += base - 3
            else:
                puanlar['Başlık'] = base
                açıklamalar.append("✅ Başlık anlaşılır")
                toplam += base

        # 2. Öncelik
        if 2 in aktif:
            if priority in ["", "null", "none"]:
                puanlar['Öncelik'] = 0
                açıklamalar.append("❌ Öncelik bilgisi eksik")
            else:
                puanlar['Öncelik'] = base
                açıklamalar.append("✅ Öncelik bilgisi girilmiş")
                toplam += base

        # 3. Test datası
        if 3 in aktif:
            if data.strip():
                puanlar['Data'] = base
                açıklamalar.append("✅ Test datası var")
                toplam += base
            else:
                puanlar['Data'] = 0
                açıklamalar.append("❌ Test datası eksik")

        # 4. Ön koşul
        if 4 in aktif:
            if precondition_needed:
                puanlar['Ön Koşul'] = base
                açıklamalar.append("✅ Ön koşul gerekli ve belirtilmiş")
                toplam += base
            else:
                puanlar['Ön Koşul'] = 0
                açıklamalar.append("❌ Ön koşul eksik")

        # 5. Stepler
        if 5 in aktif:
            if not action.strip():
                puanlar['Stepler'] = 0
                açıklamalar.append("❌ Stepler tamamen boş")
            elif any(x in action for x in [",", " ardından ", " sonra ", " ve "]):
                puanlar['Stepler'] = base - 5  # 3 yerine artık daha esnek
                açıklamalar.append(f"🔸 Adımlar birleşik ama mantıklı gruplanmış (puan: {base - 5})")
                toplam += base - 5
            else:
                puanlar['Stepler'] = base
                açıklamalar.append("✅ Stepler ayrı ve düzgün")
                toplam += base

        # 6. Client bilgisi
        if 6 in aktif:
            client_keywords = ["android", "ios", "web", "mac", "windows"]
            if any(c in summary.lower() for c in client_keywords) or any(c in action.lower() for c in client_keywords):
                puanlar['Client'] = base
                açıklamalar.append("✅ Client bilgisi var")
                toplam += base
            else:
                puanlar['Client'] = 0
                açıklamalar.append("❌ Client bilgisi eksik")

        # 7. Expected Result
        if 7 in aktif:
            if not expected.strip():
                puanlar['Expected'] = 0
                açıklamalar.append("❌ Expected result eksik")
            elif any(w in expected.lower() for w in ["test edilir", "kontrol edilir"]):
                puanlar['Expected'] = base - 3
                açıklamalar.append(f"🔸 Zayıf ifade: 'test edilir' içeriyor (puan: {base - 3})")
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
            "Açıklama": " | ".join(açıklamalar),
            "Action": action,
            "Data": data,
            "Expected Result": expected
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    # 📊 Skor Tablosu (Dikey ve okunabilir)
    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(sonuçlar.set_index("Key").T)

    # 📥 İndir
    st.download_button("📥 Sonuçları CSV olarak indir", data=sonuçlar.to_csv(index=False, sep=';', encoding='utf-8'),
                       file_name="testcase_skorlari.csv", mime="text/csv")

    # 📝 Detaylı İnceleme
    st.markdown("## 📝 Detaylı İnceleme")
    for _, row in sonuçlar.iterrows():
        st.markdown(f"### 🔍 {row['Key']} | {row['Summary']}")
        st.markdown(f"📌 **Tablo:** `{row['Tablo']}` | 🧮 **Toplam Puan:** `{row['Toplam Puan']}`")
        st.markdown(f"📍 **Action:** `{row['Action']}`")
        st.markdown(f"📍 **Data:** `{row['Data']}`")
        st.markdown(f"📍 **Expected Result:** `{row['Expected Result']}`")
        for kriter in ['Başlık', 'Öncelik', 'Data', 'Ön Koşul', 'Stepler', 'Client', 'Expected']:
            if kriter in row:
                st.markdown(f"➡️ **{kriter}**: {row[kriter]} puan")
        st.markdown(f"🗒️ Açıklamalar: {row['Açıklama']}")
