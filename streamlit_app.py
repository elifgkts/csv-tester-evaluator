# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v1.1 – "ham Data yerine skor" güncellemesi
import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="Test Case SLA", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama, test caselerinizi **A, B, C veya D** tablosuna göre değerlendirir.  
Her test case'in ait olduğu tablo, **senaryo içeriğine göre otomatik belirlenir** ve 7 kritere göre puanlama yapılır.
""")

with st.expander("📌 Değerlendirme Kuralları ve Tablo Açıklamaları"):
    st.markdown("""
**CSV formatı:** CSV dosyası `;` (noktalı virgül) ile ayrılmış olmalıdır.  
**Gerekli sütunlar:** `Issue key`, `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`

### 🧩 Tablo Türleri:
| Tablo | Açıklama |
|---|---|
| A | Veri veya ön koşul gerekmeyen testler |
| B | Ön koşul gerekli |
| C | Test datası gerekli |
| D | Ön koşul + Test datası gerekli |

### ✅ Kriterler:
1. Test başlığı anlaşılır mı?
2. Öncelik bilgisi girilmiş mi?
3. Test datası eklenmiş mi?
4. Test ön koşul eklenmiş mi?
5. Test stepleri var ve doğru ayrıştırılmış mı?
6. Senaryonun hangi clientta koşulacağı belli mi?
7. Expected result bulunuyor mu?

### 📊 Puanlama:
| Tablo | Kriter Sayısı | Kriter Puanı | Maks |
|---|---:|---:|---:|
| A | 5 | 20 | 100 |
| B | 6 | 17 | 102 |
| C | 6 | 17 | 102 |
| D | 7 | 14 | 98 |

### 🔸 Step Puanlama Detayı:
- Step hiç ayrıştırılmamış ve sadece summary tekrarıysa: **1 puan**
- Benzer sorgular birleşik ama mantıklı gruplanmışsa: **10–15 puan**
- Düzgün ayrılmışsa: **tam puan**
""")

sample_size = st.slider("📌 Kaç test case örneği değerlendirilsin?", 1, 50, 5)

uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    st.success("✅ Dosya yüklendi. Seçilen örnekler değerlendiriliyor...")
    sampled_df = df.sample(n=sample_size, random_state=42) if len(df) >= sample_size else df.copy()

    def score_case(row):
        key = str(row.get('Issue key') or row.get('Issue Key') or "").strip()
        summary = str(row.get('Summary') or "").strip()
        priority = str(row.get('Priority') or "").strip().lower()
        labels = str(row.get('Labels') or "").lower()
        steps_field = str(row.get('Custom field (Manual Test Steps)') or "")

        # Action / Data / Expected (ham) yakalama
        action_match = re.search(r'"Action"\s*:\s*"(.*?)"', steps_field, re.IGNORECASE|re.DOTALL)
        data_match = re.search(r'"Data"\s*:\s*"(.*?)"', steps_field, re.IGNORECASE|re.DOTALL)
        expected_match = re.search(r'"Expected Result"\s*:\s*"(.*?)"', steps_field, re.IGNORECASE|re.DOTALL)

        action = (action_match.group(1).strip() if action_match else "")
        data = (data_match.group(1).strip() if data_match else "")
        expected = (expected_match.group(1).strip() if expected_match else "")

        # Tablo Seçimi (içeriğe göre)
        testdata_needed = bool(re.search(r'\b(data:|msisdn|token|auth|account|payload|config)\b', steps_field, re.IGNORECASE))
        precondition_needed = ('precond' in labels) or bool(re.search(r'\bprecondition\b|\bön ?koşul\b', steps_field, re.IGNORECASE))

        if testdata_needed and precondition_needed:
            table, base, aktif = "D", 14, [1,2,3,4,5,6,7]
        elif testdata_needed:
            table, base, aktif = "C", 17, [1,2,3,5,6,7]
        elif precondition_needed:
            table, base, aktif = "B", 17, [1,2,4,5,6,7]
        else:
            table, base, aktif = "A", 20, [1,2,5,6,7]

        puanlar, aciklamalar, toplam = {}, [], 0

        # 1) Başlık
        if 1 in aktif:
            if len(summary) < 10:
                puanlar['Başlık'] = 0
                aciklamalar.append("❌ Başlık çok kısa (0)")
            elif any(w in summary.lower() for w in ["test edilir", "kontrol edilir"]):
                puanlar['Başlık'] = base - 3
                aciklamalar.append(f"🔸 Zayıf ifade ('test edilir') → {base-3}")
                toplam += base - 3
            else:
                puanlar['Başlık'] = base
                aciklamalar.append("✅ Başlık anlaşılır")
                toplam += base

        # 2) Öncelik
        if 2 in aktif:
            if priority in ["", "null", "none"]:
                puanlar['Öncelik'] = 0
                aciklamalar.append("❌ Öncelik bilgisi eksik")
            else:
                puanlar['Öncelik'] = base
                aciklamalar.append("✅ Öncelik bilgisi girilmiş")
                toplam += base

        # 3) Test datası
        if 3 in aktif:
            if data:
                puanlar['Data'] = base
                aciklamalar.append("✅ Test datası var")
                toplam += base
            else:
                puanlar['Data'] = 0
                aciklamalar.append("❌ Test datası eksik")

        # 4) Ön koşul
        if 4 in aktif:
            if precondition_needed:
                puanlar['Ön Koşul'] = base
                aciklamalar.append("✅ Ön koşul gerekli ve belirtilmiş")
                toplam += base
            else:
                puanlar['Ön Koşul'] = 0
                aciklamalar.append("❌ Ön koşul eksik")

        # 5) Stepler
        if 5 in aktif:
            if not action:
                puanlar['Stepler'] = 0
                aciklamalar.append("❌ Stepler tamamen boş")
            elif any(x in action for x in [",", " ardından ", " sonra ", " ve "]):
                # birleşik ama kabul edilebilir → kırıntı
                kırp = 5 if base >= 17 else 3  # C/B'de 5, D'de 3 kırp
                puanlar['Stepler'] = max(base - kırp, 1)
                aciklamalar.append(f"🔸 Adımlar birleşik ama mantıklı gruplanmış ({puanlar['Stepler']})")
                toplam += puanlar['Stepler']
            else:
                puanlar['Stepler'] = base
                aciklamalar.append("✅ Stepler ayrı ve düzgün")
                toplam += base

        # 6) Client
        if 6 in aktif:
            client_keywords = ["android", "ios", "web", "mac", "windows"]
            if any(c in summary.lower() for c in client_keywords) or any(c in action.lower() for c in client_keywords):
                puanlar['Client'] = base
                aciklamalar.append("✅ Client bilgisi var")
                toplam += base
            else:
                puanlar['Client'] = 0
                aciklamalar.append("❌ Client bilgisi eksik")

        # 7) Expected Result
        if 7 in aktif:
            if not expected:
                puanlar['Expected'] = 0
                aciklamalar.append("❌ Expected result eksik")
            elif any(w in expected.lower() for w in ["test edilir", "kontrol edilir"]):
                puanlar['Expected'] = base - 3
                aciklamalar.append(f"🔸 Zayıf ifade ('test edilir') → {base-3}")
                toplam += base - 3
            else:
                puanlar['Expected'] = base
                aciklamalar.append("✅ Expected result düzgün")
                toplam += base

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Toplam Puan": toplam,
            **puanlar,
            # Ham içerikleri saklıyoruz ama UI/CSV'de göstermeyeceğiz (toggle hariç)
            "_Action_raw": action,
            "_Data_raw": data,
            "_Expected_raw": expected,
            "Açıklama": " | ".join(aciklamalar)
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    # 📊 Görüntülenecek ve indirilecek veri setinden ham alanları çıkar
    gizli_kolonlar = ["_Action_raw", "_Data_raw", "_Expected_raw"]
    gösterim_df = sonuçlar.drop(columns=gizli_kolonlar, errors="ignore").copy()

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(gösterim_df.set_index("Key"))

    st.download_button(
        "📥 Sonuçları CSV olarak indir",
        data=gösterim_df.to_csv(index=False, sep=';', encoding='utf-8'),
        file_name="testcase_skorlari.csv",
        mime="text/csv"
    )

    # Ham içeriği gerekli olursa aç-kapa
    show_raw = st.toggle("🔎 Ham içeriği göster (Action/Data/Expected)", value=False)

    st.markdown("## 📝 Detaylı İnceleme")
    for _, row in sonuçlar.iterrows():
        st.markdown(f"### 🔍 {row['Key']} | {row['Summary']}")
        st.markdown(f"📌 **Tablo:** `{row['Tablo']}` | 🧮 **Toplam Puan:** `{row['Toplam Puan']}`")

        # ——— Artık burada ham içerikleri varsayılan olarak GÖSTERMİYORUZ ———
        if show_raw:
            st.markdown(f"📍 **Action (ham):** `{row['_Action_raw']}`")
            st.markdown(f"📍 **Data (ham):** `{row['_Data_raw']}`")
            st.markdown(f"📍 **Expected (ham):** `{row['_Expected_raw']}`")

        # Sadece skorları göster
        for kriter in ['Başlık', 'Öncelik', 'Data', 'Ön Koşul', 'Stepler', 'Client', 'Expected']:
            if kriter in row and pd.notna(row[kriter]):
                st.markdown(f"➡️ **{kriter}**: {int(row[kriter])} puan")

        st.markdown(f"🗒️ Açıklamalar: {row['Açıklama']}")
