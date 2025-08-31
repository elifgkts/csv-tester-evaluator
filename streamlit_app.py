import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="Test Case Değerlendirici", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi — QA Manager Gözünden")
st.markdown("""
Bu uygulama, manuel test caselerinizi **A, B, C veya D tablosuna** göre değerlendirir.
Her test case'in ait olduğu tablo, **senaryo içeriğine göre otomatik belirlenir** ve 7 kritere göre puanlama yapılır.
""")

with st.expander("📌 Değerlendirme Kuralları ve Kriter Açıklamaları"):
    st.markdown("""
**CSV formatı:** CSV dosyası `;` (noktalı virgül) ile ayrılmış olmalıdır.

**Gerekli sütunlar:**
- Key
- Summary
- Priority
- Labels
- Custom field (Manual Test Steps)

**Tablo Seçimi (Senaryoya göre):**
- **A:** Ne test datası ne ön koşul gerektirmeyen testler (5 kriter)
- **B:** Sadece ön koşul gerektiren testler (6 kriter)
- **C:** Sadece test datası gerektiren testler (6 kriter)
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

        explanations = []
        total = 0

        # Kriter 1: Test başlığı
        if 1 in aktif_kriterler:
            if len(summary) < 10:
                explanations.append("❌ Test başlığı çok kısa, yeterli değil (0 puan)")
            elif any(word in summary.lower() for word in ["alanına gidilir", "tıklanır"]):
                explanations.append(f"🔸 Test başlığı zayıf ifade edilmiş: {summary} (puan: {base-3})")
                total += base - 3
            else:
                explanations.append("✅ Test başlığı anlaşılır (tam puan)")
                total += base

        # Kriter 2: Priority
        if 2 in aktif_kriterler:
            if priority in ["", "null", "none"]:
                explanations.append("❌ Öncelik bilgisi eksik")
            else:
                explanations.append("✅ Öncelik bilgisi girilmiş")
                total += base

        # Kriter 3: Test datası
        if 3 in aktif_kriterler:
            if data.strip():
                explanations.append("✅ Test datası girilmiş")
                total += base
            else:
                explanations.append("❌ Test datası eksik")

        # Kriter 4: Precondition
        if 4 in aktif_kriterler:
            if precondition_needed:
                explanations.append("✅ Ön koşul gerekli ve label'da belirtilmiş")
                total += base
            else:
                explanations.append("❌ Ön koşul gerekli ancak eksik")

        # Kriter 5: Stepler
        if 5 in aktif_kriterler:
            if not action.strip():
                explanations.append("❌ Step alanı tamamen boş")
            elif any(token in action for token in [",", " ve ", " ardından ", " sonra"]):
                explanations.append(f"🔸 Adımlar tek stepe yazılmış: {action} (puan: 3)")
                total += 3
            else:
                explanations.append("✅ Stepler doğru şekilde ayrılmış")
                total += base

        # Kriter 6: Client bilgisi
        if 6 in aktif_kriterler:
            client_keywords = ["android", "ios", "web", "mac", "windows"]
            if any(kw in summary.lower() for kw in client_keywords) or any(kw in action.lower() for kw in client_keywords):
                explanations.append("✅ Client bilgisi var")
                total += base
            else:
                explanations.append("❌ Hangi clientta koşulacağı belirtilmemiş")

        # Kriter 7: Expected result
        if 7 in aktif_kriterler:
            if not expected.strip():
                explanations.append("❌ Expected result tamamen boş")
            elif any(word in expected.lower() for word in ["test edilir", "kontrol edilir"]):
                explanations.append(f"🔸 Expected result zayıf ifade edilmiş: {expected} (puan: {base-3})")
                total += base - 3
            else:
                explanations.append("✅ Expected result düzgün yazılmış")
                total += base

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Toplam Puan": total,
            "Açıklama": "\n".join(explanations)
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    st.markdown("## 📊 Değerlendirme Sonuçları")
    st.dataframe(sonuçlar, use_container_width=True)
