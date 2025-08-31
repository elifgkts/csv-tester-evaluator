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
**Gerekli Sütunlar:**
- Issue Key
- Summary
- Priority
- Labels
- Custom field (Manual Test Steps)

**Tablo Seçimi:**
- **A:** Ne test datası ne ön koşul gerekmeyen testler
- **B:** Ön koşul gerekli
- **C:** Test datası gerekli
- **D:** Hem test datası hem ön koşul gerekli

**Kriterler:**
1. Başlık anlaşılır mı?
2. Öncelik bilgisi var mı?
3. Test datası var mı?
4. Ön koşul var mı?
5. Step ayrımı doğru mu?
6. Client bilgisi belirtilmiş mi?
7. Expected Result belirtilmiş mi?
    """)

uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    st.success("✅ Dosya başarıyla yüklendi!")

    sample_size = st.slider("🎯 Kaç test case değerlendirilsin?", 1, len(df), 5)
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
            table, base, aktif = "D", 14, [1,2,3,4,5,6,7]
        elif testdata_needed:
            table, base, aktif = "C", 17, [1,2,3,5,6,7]
        elif precondition_needed:
            table, base, aktif = "B", 17, [1,2,4,5,6,7]
        else:
            table, base, aktif = "A", 20, [1,2,5,6,7]

        expl = []
        scores = dict.fromkeys(range(1,8), 0)

        # Kriter 1 - Başlık
        if 1 in aktif:
            if len(summary) < 10:
                expl.append("❌ Başlık çok kısa (0 puan)")
            elif any(w in summary.lower() for w in ["test edilir", "kontrol edilir"]):
                expl.append("🔸 Başlık test ifadesi içeriyor (puan: {}).".format(base-3))
                scores[1] = base - 3
            else:
                expl.append("✅ Başlık anlaşılır")
                scores[1] = base

        # Kriter 2 - Öncelik
        if 2 in aktif:
            if priority in ["", "null", "none"]:
                expl.append("❌ Öncelik bilgisi eksik")
            else:
                expl.append("✅ Öncelik bilgisi var")
                scores[2] = base

        # Kriter 3 - Data
        if 3 in aktif:
            if data.strip():
                expl.append("✅ Test datası var")
                scores[3] = base
            else:
                expl.append("❌ Test datası eksik")

        # Kriter 4 - Precondition
        if 4 in aktif:
            if precondition_needed:
                expl.append("✅ Ön koşul gerekli ve belirtilmiş")
                scores[4] = base
            else:
                expl.append("❌ Ön koşul gerekli ancak belirtilmemiş")

        # Kriter 5 - Step ayrımı
        if 5 in aktif:
            if not action.strip():
                expl.append("❌ Step boş")
            elif any(tok in action for tok in [",", " ve ", " ardından "]):
                expl.append("🔸 Stepler ayrılmamış (puan: 3)")
                scores[5] = 3
            else:
                expl.append("✅ Stepler ayrılmış")
                scores[5] = base

        # Kriter 6 - Client
        if 6 in aktif:
            client_kw = ["ios", "android", "web", "mac", "windows"]
            if any(kw in summary.lower() for kw in client_kw) or any(kw in action.lower() for kw in client_kw):
                expl.append("✅ Client bilgisi var")
                scores[6] = base
            else:
                expl.append("❌ Client bilgisi eksik")

        # Kriter 7 - Expected
        if 7 in aktif:
            if not expected.strip():
                expl.append("❌ Expected result eksik")
            elif any(x in expected.lower() for x in ["test edilir", "kontrol edilir"]):
                expl.append("🔸 Expected zayıf ifade (puan: {}).".format(base-3))
                scores[7] = base - 3
            else:
                expl.append("✅ Expected result düzgün")
                scores[7] = base

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Başlık Puanı": scores[1],
            "Öncelik Puanı": scores[2],
            "Test Data Puanı": scores[3],
            "Ön Koşul Puanı": scores[4],
            "Step Puanı": scores[5],
            "Client Puanı": scores[6],
            "Expected Puanı": scores[7],
            "Toplam Puan": sum(scores.values()),
            "Action": action,
            "Data": data,
            "Expected": expected,
            "Açıklama": "\n".join(expl)
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    görünüm = st.radio("Sonuçları nasıl görmek istersiniz?", ["📊 Tablo", "📋 Kartlar"])

    if görünüm == "📊 Tablo":
        st.dataframe(sonuçlar)
    else:
        for _, row in sonuçlar.iterrows():
            with st.container():
                st.markdown(f"### 🔍 {row['Key']} | {row['Summary']}")
                st.markdown(f"**🧭 Tablo:** `{row['Tablo']}` | **🔢 Toplam Puan:** `{row['Toplam Puan']}`")
                puanlar = [
                    f"✅ Başlık: {row['Başlık Puanı']}",
                    f"✅ Öncelik: {row['Öncelik Puanı']}",
                    f"✅ Data: {row['Test Data Puanı']}",
                    f"✅ Ön Koşul: {row['Ön Koşul Puanı']}",
                    f"✅ Stepler: {row['Step Puanı']}",
                    f"✅ Client: {row['Client Puanı']}",
                    f"✅ Expected: {row['Expected Puanı']}"
                ]
                st.markdown("**📌 Kriter Bazlı Puanlar:**\n" + " | ".join(puanlar))
                st.markdown("**📝 Açıklamalar:**")
                st.info(row['Açıklama'])

    csv = sonuçlar.to_csv(index=False, sep=';', encoding='utf-8')
    st.download_button("📥 Sonuçları indir (CSV)", csv, file_name="testcase_skorlari.csv", mime="text/csv")
