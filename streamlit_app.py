import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="Test Case Değerlendirici", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi ")

st.markdown("""
Bu uygulama, test caselerinizi **A, B, C veya D tablosuna** göre değerlendirir.
Her test case'in ait olduğu tablo, **senaryo içeriğine göre otomatik belirlenir** ve 7 kritere göre puanlama yapılır.
""")

# 📌 Kullanım Kuralları
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

**Önemli Notlar:**
- Test datası sadece **Manual Test Steps** içindeki `Data:` kısmına bakılarak kontrol edilir.
- Expected Result alanı gerçekten beklenen sonuç belirtmiyorsa, eksik sayılır.
- Step alanında **tüm işlemler tek bir satıra yazılmışsa**, bu durum hatalı sayılır ve **tam puan yerine kırıntı puan (1-5 arası)** verilir.
- Test başlığı kötü yazılmışsa yine **tam sıfır değil**, 1-5 puanlık bir kırıntı puan verilir.
- "test edilir", "kontrol edilir" gibi ifadeler summary'de veya expected'da varsa puan düşer.
""")

# 📌 Kaç test case değerlendirilsin?
sample_size = st.slider("🎯 Kaç test case örneği değerlendirilsin?", min_value=1, max_value=50, value=5)

# 📤 CSV Yükleme
uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    st.success("✅ Dosya başarıyla yüklendi. Şimdi örnekleri puanlayalım.")
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

        testdata_needed = bool(re.search(r'data:|msisdn|token|auth|account|payload|config', steps_field, re.IGNORECASE))
        precondition_needed = 'precond' in labels

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

        puanlar = {"Başlık": 0, "Öncelik": 0, "Data": 0, "Ön Koşul": 0, "Stepler": 0, "Client": 0, "Expected": 0}
        explanations = []
        total = 0

        if 1 in aktif_kriterler:
            if len(summary) < 10:
                explanations.append("❌ Test başlığı çok kısa, yeterli değil (0 puan)")
            elif any(word in summary.lower() for word in ["alanına gidilir", "tıklanır", "test edilir"]):
                explanations.append(f"🔸 Test başlığı zayıf ifade edilmiş: {summary} (puan: {base-3})")
                puanlar["Başlık"] = base - 3
            else:
                explanations.append("✅ Test başlığı anlaşılır")
                puanlar["Başlık"] = base

        if 2 in aktif_kriterler:
            if priority in ["", "null", "none"]:
                explanations.append("❌ Öncelik bilgisi eksik")
            else:
                explanations.append("✅ Öncelik bilgisi girilmiş")
                puanlar["Öncelik"] = base

        if 3 in aktif_kriterler:
            if data.strip():
                explanations.append("✅ Test datası girilmiş")
                puanlar["Data"] = base
            else:
                explanations.append("❌ Test datası eksik")

        if 4 in aktif_kriterler:
            if precondition_needed:
                explanations.append("✅ Ön koşul gerekli ve label'da belirtilmiş")
                puanlar["Ön Koşul"] = base
            else:
                explanations.append("❌ Ön koşul gerekli ancak eksik")

        if 5 in aktif_kriterler:
            if not action.strip():
                explanations.append("❌ Step alanı tamamen boş")
            elif any(token in action for token in [",", " ve ", " ardından ", " sonra"]):
                explanations.append(f"🔸 Adımlar tek stepe yazılmış: {action} (puan: 3)")
                puanlar["Stepler"] = 3
            else:
                explanations.append("✅ Stepler doğru şekilde ayrılmış")
                puanlar["Stepler"] = base

        if 6 in aktif_kriterler:
            client_keywords = ["android", "ios", "web", "mac", "windows"]
            if any(kw in summary.lower() for kw in client_keywords) or any(kw in action.lower() for kw in client_keywords):
                explanations.append("✅ Client bilgisi var")
                puanlar["Client"] = base
            else:
                explanations.append("❌ Hangi clientta koşulacağı belirtilmemiş")

        if 7 in aktif_kriterler:
            if not expected.strip():
                explanations.append("❌ Expected result tamamen boş")
            elif any(word in expected.lower() for word in ["test edilir", "kontrol edilir"]):
                explanations.append(f"🔸 Expected result zayıf ifade edilmiş: {expected} (puan: {base-3})")
                puanlar["Expected"] = base - 3
            else:
                explanations.append("✅ Expected result düzgün yazılmış")
                puanlar["Expected"] = base

        total = sum(puanlar.values())

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Toplam Puan": total,
            **puanlar,
            "Action": action,
            "Data": data,
            "Expected Result": expected,
            "Açıklama": explanations
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    st.markdown("## 📊 Değerlendirme Sonuçları")
    st.dataframe(sonuçlar.drop(columns=["Açıklama"]))

    csv = sonuçlar.to_csv(index=False, sep=';', encoding='utf-8')
    st.download_button("📥 Sonuçları indir (CSV)", data=csv, file_name="testcase_skorlari.csv", mime="text/csv")

    st.markdown("## 📝 Detaylı Açıklamalar")
    for _, row in sonuçlar.iterrows():
        st.markdown(f"### 🔍 {row['Key']} — {row['Summary']}")
        st.markdown(f"**Tablo:** `{row['Tablo']}`  |  **Puan:** `{row['Toplam Puan']}`")
        st.markdown(f"**🎯 Kriter Bazlı Puanlar:**")
        for k in ["Başlık", "Öncelik", "Data", "Ön Koşul", "Stepler", "Client", "Expected"]:
            st.markdown(f"- {k}: `{row[k]}`")
        st.markdown("**🧾 Açıklamalar:**")
        for aciklama in row['Açıklama']:
            st.markdown(f"- {aciklama}")
