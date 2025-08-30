
import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="CSV Test Case Evaluator", layout="wide")

def determine_table(precondition, test_data):
    if precondition and test_data:
        return "D"
    elif precondition:
        return "B"
    elif test_data:
        return "C"
    else:
        return "A"

points = {
    "A": [("Test başlığı anlaşılır mı?", 20),
          ("Öncelik bilgisi girilmiş mi?", 20),
          ("Test stepleri var ve doğru ayrıştırılmış mı?", 20),
          ("Senaryonun hangi clientta koşulcağı belli mi?", 20),
          ("Expected result bulunuyor mu?", 20)],
    "B": [("Test başlığı anlaşılır mı?", 17),
          ("Öncelik bilgisi girilmiş mi?", 17),
          ("Test ön koşul eklenmiş mi?", 17),
          ("Test stepleri var ve doğru ayrıştırılmış mı?", 17),
          ("Senaryonun hangi clientta koşulcağı belli mi?", 17),
          ("Expected result bulunuyor mu?", 17)],
    "C": [("Test başlığı anlaşılır mı?", 17),
          ("Öncelik bilgisi girilmiş mi?", 17),
          ("Test datası eklenmiş mi?", 17),
          ("Test stepleri var ve doğru ayrıştırılmış mı?", 17),
          ("Senaryonun hangi clientta koşulcağı belli mi?", 17),
          ("Expected result bulunuyor mu?", 17)],
    "D": [("Test başlığı anlaşılır mı?", 14),
          ("Öncelik bilgisi girilmiş mi?", 14),
          ("Test datası eklenmiş mi?", 14),
          ("Test ön koşul eklenmiş mi?", 14),
          ("Test stepleri var ve doğru ayrıştırılmış mı?", 14),
          ("Senaryonun hangi clientta koşulcağı belli mi?", 14)]
}

st.title("📋 Test Case Değerlendirme Uygulaması (CSV)")
st.markdown("CSV dosyanızı yükleyin, rastgele 5 test case otomatik olarak puanlansın.")

uploaded_file = st.file_uploader("CSV Dosyasını Yükle", type="csv")

if uploaded_file:
df = pd.read_csv(uploaded_file, sep=";", engine="python")
    if df.shape[0] < 5:
        st.error("En az 5 test case içeren bir CSV yükleyin.")
    else:
        sampled = df.sample(5, random_state=42).reset_index(drop=True)
        st.subheader("📊 Örnek 5 Test Case Değerlendirmesi")

        for idx, row in sampled.iterrows():
            st.markdown(f"### 🎯 Test Case {idx + 1}")
            summary = str(row.get("Summary", ""))
            priority = str(row.get("Priority", ""))
            attachments = str(row.get("Attachments", ""))

            has_precondition = "ön koşul" in attachments.lower()
            has_data = "test data" in attachments.lower()

            table_type = determine_table(has_precondition, has_data)
            kriterler = points[table_type]
            total_score = 0

            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(f"**Tablo Türü:** {table_type}")
                st.markdown(f"**Summary:** {summary}")
                st.markdown(f"**Priority:** {priority}")
            with cols[1]:
                st.markdown("#### Puanlar")

            for kriter, max_puan in kriterler:
                puan = max_puan
                if "başlığı" in kriter and not summary.strip():
                    puan = 0
                elif "öncelik" in kriter and not priority.strip():
                    puan = 0
                elif "ön koşul" in kriter and not has_precondition:
                    puan = 0
                elif "test datası" in kriter and not has_data:
                    puan = 0
                elif "stepleri" in kriter and not any(word in attachments.lower() for word in ["1.", "2.", "step", "adım"]):
                    puan = 0
                elif "expected" in kriter and "beklenen" not in attachments.lower():
                    puan = 0
                elif "client" in kriter and not any(x in attachments.lower() for x in ["ios", "android", "web"]):
                    puan = 0

                total_score += puan
                with cols[1]:
                    st.write(f"{kriter}: {puan}/{max_puan}")

            with cols[1]:
                st.markdown(f"### 🔥 Toplam Puan: **{total_score} / {sum(p[1] for p in kriterler)}**")
            st.markdown("---")
