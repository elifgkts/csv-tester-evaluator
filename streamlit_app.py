import streamlit as st
import pandas as pd
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
- Issue key
- Summary
- Priority
- Labels
- Custom field (Manual Test Steps)

**Tablo Seçimi:**
- **A:** Test datası ya da ön koşul gerekmeyen testler (varsayılan)
- **B:** Ön koşul gerekli
- **C:** Test datası gerekli
- **D:** Hem test datası hem ön koşul gerekli

**Kriterler:**
1. Test başlığı anlaşılır mı?
2. Öncelik bilgisi girilmiş mi?
3. Test datası eklenmiş mi?
4. Test ön koşul eklenmiş mi?
5. Test stepleri var ve doğru ayrıştırılmış mı?
6. Senaryonun hangi clientta koşulacağı belli mi?
7. Expected result bulunuyor mu?

**Notlar:**
- Test datası sadece Manual Test Steps içindeki `Data:` kısmından kontrol edilir.
- Expected Result alanı gerçekten beklenen sonuç belirtmiyorsa eksik sayılır.
- Stepler tek satıra yazılmışsa kırıntı puan (3), hiç yoksa 0 puan.
- Summary içinde "test edilir" gibi ifadeler varsa 2-3 puan kırılır.
    """)

uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    sample_size = st.slider("📌 Kaç test case değerlendirilsin?", 1, len(df), 5)
    sampled_df = df.sample(n=sample_size, random_state=42)

    def score_case(row):
        key = row['Issue key']
        summary = str(row['Summary'])
        priority = str(row['Priority']).lower()
        labels = str(row['Labels']).lower()
        steps = str(row['Custom field (Manual Test Steps)'])

        action_match = re.search(r'"Action"\s*:\s*"(.*?)"', steps)
        data_match = re.search(r'"Data"\s*:\s*"(.*?)"', steps)
        expected_match = re.search(r'"Expected Result"\s*:\s*"(.*?)"', steps)

        action = action_match.group(1) if action_match else ""
        data = data_match.group(1) if data_match else ""
        expected = expected_match.group(1) if expected_match else ""

        needs_data = bool(re.search(r'data:|msisdn|token|auth|account|payload|config', steps, re.IGNORECASE))
        needs_precond = 'precond' in labels

        if needs_data and needs_precond:
            table, base, kriterler = "D", 14, [1,2,3,4,5,6,7]
        elif needs_data:
            table, base, kriterler = "C", 17, [1,2,3,5,6,7]
        elif needs_precond:
            table, base, kriterler = "B", 17, [1,2,4,5,6,7]
        else:
            table, base, kriterler = "A", 20, [1,2,5,6,7]

        total = 0
        detaylar = []
        kriter_puan = {}

        if 1 in kriterler:
            if len(summary) < 10:
                detaylar.append("❌ Başlık çok kısa (0 puan)")
                kriter_puan['Başlık Puanı'] = 0
            elif re.search(r'(test edilir|kontrol edilir)', summary.lower()):
                detaylar.append(f"🔸 Zayıf başlık ifadesi: {summary} (puan: {base - 3})")
                kriter_puan['Başlık Puanı'] = base - 3
                total += base - 3
            else:
                detaylar.append("✅ Başlık anlaşılır")
                kriter_puan['Başlık Puanı'] = base
                total += base

        if 2 in kriterler:
            if priority in ["", "null", "none"]:
                detaylar.append("❌ Öncelik bilgisi eksik")
                kriter_puan['Öncelik Puanı'] = 0
            else:
                detaylar.append("✅ Öncelik bilgisi var")
                kriter_puan['Öncelik Puanı'] = base
                total += base

        if 3 in kriterler:
            if data.strip():
                detaylar.append("✅ Test datası var")
                kriter_puan['Data Puanı'] = base
                total += base
            else:
                detaylar.append("❌ Test datası eksik")
                kriter_puan['Data Puanı'] = 0

        if 4 in kriterler:
            if needs_precond:
                detaylar.append("✅ Ön koşul belirtilmiş")
                kriter_puan['Ön Koşul Puanı'] = base
                total += base
            else:
                detaylar.append("❌ Ön koşul eksik")
                kriter_puan['Ön Koşul Puanı'] = 0

        if 5 in kriterler:
            if not action.strip():
                detaylar.append("❌ Step alanı boş")
                kriter_puan['Step Puanı'] = 0
            elif any(k in action for k in [",", " ardından ", " sonra ", " ve "]):
                detaylar.append(f"🔸 Stepler tek satıra yazılmış: {action} (puan: 3)")
                kriter_puan['Step Puanı'] = 3
                total += 3
            else:
                detaylar.append("✅ Stepler ayrıştırılmış")
                kriter_puan['Step Puanı'] = base
                total += base

        if 6 in kriterler:
            if any(c in (summary + action).lower() for c in ["android", "ios", "web"]):
                detaylar.append("✅ Client bilgisi var")
                kriter_puan['Client Puanı'] = base
                total += base
            else:
                detaylar.append("❌ Client bilgisi eksik")
                kriter_puan['Client Puanı'] = 0

        if 7 in kriterler:
            if not expected.strip():
                detaylar.append("❌ Expected result eksik")
                kriter_puan['Expected Puanı'] = 0
            elif re.search(r'(test edilir|kontrol edilir)', expected.lower()):
                detaylar.append(f"🔸 Zayıf expected: {expected} (puan: {base - 3})")
                kriter_puan['Expected Puanı'] = base - 3
                total += base - 3
            else:
                detaylar.append("✅ Expected result düzgün")
                kriter_puan['Expected Puanı'] = base
                total += base

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Toplam Puan": total,
            **kriter_puan,
            "Action": action,
            "Data": data,
            "Expected": expected,
            "Açıklama": "\n".join(detaylar)
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(sonuçlar.drop(columns=['Açıklama', 'Action', 'Data', 'Expected']))

    st.markdown("## 📝 Detaylı İnceleme")
    for _, row in sonuçlar.iterrows():
        with st.expander(f"🔍 {row['Key']} | {row['Summary']} (Puan: {row['Toplam Puan']})"):
            st.markdown(f"**Tablo Türü:** `{row['Tablo']}`")
            st.markdown("""
**✅ Action:**
```
%s
```
**📦 Data:**
```
%s
```
**🎯 Expected:**
```
%s
```""" % (row['Action'], row['Data'], row['Expected']))
            st.info(row['Açıklama'])
