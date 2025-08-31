import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="Test Case Değerlendirici", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")
st.markdown("""
Bu uygulama, test caselerinizi **A, B, C veya D tablosuna** göre değerlendirir.
Her test case'in ait olduğu tablo, **senaryo içeriğine göre otomatik belirlenir** ve 7 kritere göre puanlama yapılır.
""")

with st.expander("📌 Değerlendirme Kuralları ve Kriter Açıklamaları"):
    st.markdown("""
**CSV formatı:** CSV dosyası `;` (noktalı virgül) ile ayrılmış olmalıdır.

**Gerekli sütunlar:**
- Issue Key
- Summary
- Priority
- Labels
- Custom field (Manual Test Steps)

**Tablo Seçimi (Senaryoya göre):**
- **A:** Test datası ya da ön koşul olması zorunlu olmayan testler (5 kriter)
- **B:** Mutlaka ön koşul gerektiren testler (6 kriter)
- **C:** Mutlaka test datası gerektiren testler (6 kriter)
- **D:** Hem test datası hem ön koşul gerektiren testler (7 kriter)

**Kriterler:**
1. Test başlığı anlaşılır mı?
2. Öncelik bilgisi girilmiş mi?
3. Test datası eklenmiş mi? *(C, D için)*
4. Test ön koşul eklenmiş mi? *(B, D için)*
5. Test stepleri var ve doğru ayrıştırılmış mı?
6. Senaryonun hangi clientta koşulacağı belli mi?
7. Expected result bulunuyor mu?
""")

uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    st.success("✅ Dosya başarıyla yüklendi. Şimdi örnekleri puanlayalım.")

    sample_size = st.slider("📌 Kaç test case örneği değerlendirilsin?", min_value=1, max_value=len(df), value=5)
    sampled_df = df.sample(n=sample_size, random_state=42)

    def score_case(row):
        key = row['Issue key']
        summary = str(row['Summary']).strip()
        priority = str(row['Priority']).strip().lower()
        labels = str(row['Labels']).lower()
        steps_field = str(row['Custom field (Manual Test Steps)'])

        action_match = re.search(r'"Action"\s*:\s*"(.*?)"', steps_field)
        data_match = re.search(r'"Data"\s*:\s*"(.*?)"', steps_field)
        expected_match = re.search(r'"Expected Result"\s*:\s*"(.*?)"', steps_field)

        action = action_match.group(1) if action_match else ""
        data = data_match.group(1) if data_match else ""
        expected = expected_match.group(1) if expected_match else ""

        testdata_needed = bool(data.strip()) or bool(re.search(r'data:|msisdn|token|auth|account|payload|config', steps_field, re.IGNORECASE))
        precondition_needed = (
            'precond' in labels
            or bool(re.search(r'precond|\bön koşul\b|setup|required|gereklidir', steps_field, re.IGNORECASE))
        )

        if testdata_needed and precondition_needed:
            table = "D"
            base = 14
            aktif_kriterler = [1, 2, 3, 4, 5, 6, 7]
        elif testdata_needed:
            table = "C"
            base = 17
            aktif_kriterler = [1, 2, 3, 5, 6, 7]
        elif precondition_needed:
            table = "B"
            base = 17
            aktif_kriterler = [1, 2, 4, 5, 6, 7]
        else:
            table = "A"
            base = 20
            aktif_kriterler = [1, 2, 5, 6, 7]

        explanations = []
        total = 0
        kriter_puanlari = dict.fromkeys([
            "Başlık Puanı", "Öncelik Puanı", "Data Puanı", "Precondition Puanı", "Step Puanı", "Client Puanı", "Expected Puanı"
        ], None)

        if 1 in aktif_kriterler:
            if len(summary) < 10:
                explanations.append("❌ Test başlığı çok kısa, yeterli değil (0 puan)")
                kriter_puanlari["Başlık Puanı"] = 0
            elif any(word in summary.lower() for word in ["alanına gidilir", "tıklanır"]):
                explanations.append(f"🔸 Test başlığı zayıf ifade edilmiş: {summary} (puan: {base-3})")
                kriter_puanlari["Başlık Puanı"] = base - 3
                total += base - 3
            else:
                explanations.append("✅ Test başlığı anlaşılır (tam puan)")
                kriter_puanlari["Başlık Puanı"] = base
                total += base

        if 2 in aktif_kriterler:
            if priority in ["", "null", "none"]:
                explanations.append("❌ Öncelik bilgisi eksik")
                kriter_puanlari["Öncelik Puanı"] = 0
            else:
                explanations.append("✅ Öncelik bilgisi girilmiş")
                kriter_puanlari["Öncelik Puanı"] = base
                total += base

        if 3 in aktif_kriterler:
            if data.strip():
                explanations.append("✅ Test datası girilmiş")
                kriter_puanlari["Data Puanı"] = base
                total += base
            else:
                explanations.append("❌ Test datası eksik")
                kriter_puanlari["Data Puanı"] = 0

        if 4 in aktif_kriterler:
            if precondition_needed:
                explanations.append("✅ Ön koşul gerekli ve belirtilmiş")
                kriter_puanlari["Precondition Puanı"] = base
                total += base
            else:
                explanations.append("❌ Ön koşul gerekli ancak eksik")
                kriter_puanlari["Precondition Puanı"] = 0

        if 5 in aktif_kriterler:
            if not action.strip():
                explanations.append("❌ Step alanı tamamen boş")
                kriter_puanlari["Step Puanı"] = 0
            elif any(token in action for token in [",", " ve ", " ardından ", " sonra"]):
                explanations.append(f"🔸 Adımlar tek stepe yazılmış: {action} (puan: 3)")
                kriter_puanlari["Step Puanı"] = 3
                total += 3
            else:
                explanations.append("✅ Stepler doğru şekilde ayrılmış")
                kriter_puanlari["Step Puanı"] = base
                total += base

        if 6 in aktif_kriterler:
            client_keywords = ["android", "ios", "web", "mac", "windows"]
            if any(kw in summary.lower() for kw in client_keywords) or any(kw in action.lower() for kw in client_keywords):
                explanations.append("✅ Client bilgisi var")
                kriter_puanlari["Client Puanı"] = base
                total += base
            else:
                explanations.append("❌ Hangi clientta koşulacağı belirtilmemiş")
                kriter_puanlari["Client Puanı"] = 0

        if 7 in aktif_kriterler:
            if not expected.strip():
                explanations.append("❌ Expected result tamamen boş")
                kriter_puanlari["Expected Puanı"] = 0
            elif any(word in expected.lower() for word in ["test edilir", "kontrol edilir"]):
                explanations.append(f"🔸 Expected result zayıf ifade edilmiş: {expected} (puan: {base-3})")
                kriter_puanlari["Expected Puanı"] = base - 3
                total += base - 3
            else:
                explanations.append("✅ Expected result düzgün yazılmış")
                kriter_puanlari["Expected Puanı"] = base
                total += base

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Action": action,
            "Data": data,
            "Expected": expected,
            **kriter_puanlari,
            "Toplam Puan": total,
            "Açıklama": "\n".join(explanations)
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    st.markdown("## 📊 Değerlendirme Sonuçları")
    st.dataframe(sonuçlar)

    csv = sonuçlar.to_csv(index=False, sep=';', encoding='utf-8')
    st.download_button("📥 Sonuçları indir (CSV)", data=csv, file_name="testcase_skorlari.csv", mime="text/csv")

    st.markdown("## 📝 Detaylı Açıklamalar")
    for _, row in sonuçlar.iterrows():
        st.markdown(f"### 🔍 {row['Key']} — {row['Summary']}")
        st.markdown(f"**Tablo:** `{row['Tablo']}`  |  **Puan:** `{row['Toplam Puan']}`")
        st.info(row['Açıklama'])
