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
    "A": ["Summary", "Priority", "Steps", "Client", "Expected Result"],
    "B": ["Summary", "Priority", "Precondition", "Steps", "Client", "Expected Result"],
    "C": ["Summary", "Priority", "Test Data", "Steps", "Client", "Expected Result"],
    "D": ["Summary", "Priority", "Test Data", "Precondition", "Steps", "Client"]
}

point_values = {"A": 20, "B": 17, "C": 17, "D": 14}

def check_criterion(criterion, row_text):
    row_text = row_text.lower()
    if criterion == "Summary":
        return bool(row_text.strip())
    if criterion == "Priority":
        return bool(row_text.strip())
    if criterion == "Steps":
        return any(key in row_text for key in ["1.", "2.", "step", "adım"])
    if criterion == "Expected Result":
        return "beklenen" in row_text
    if criterion == "Client":
        return any(k in row_text for k in ["ios", "android", "web"])
    if criterion == "Precondition":
        return "ön koşul" in row_text
    if criterion == "Test Data":
        return "test data" in row_text or "veri" in row_text
    return False

st.title("📋 Test Case Değerlendirme Uygulaması (CSV)")
st.markdown("CSV dosyanızı yükleyin, rastgele 5 test case otomatik olarak değerlendirilip açıklamalı şekilde puanlansın.")

uploaded_file = st.file_uploader("CSV Dosyasını Yükle", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=None, engine="python")
    if df.shape[0] < 5:
        st.error("En az 5 test case içeren bir CSV yükleyin.")
    else:
        sampled = df.sample(5, random_state=42).reset_index(drop=True)
        st.subheader("📊 Örnek 5 Test Case Değerlendirmesi")

        for idx, row in sampled.iterrows():
            summary = str(row.get("Summary", ""))
            priority = str(row.get("Priority", ""))
            attachments = str(row.get("Attachments", ""))

            has_precondition = "ön koşul" in attachments.lower()
            has_data = "test data" in attachments.lower()
            table_type = determine_table(has_precondition, has_data)

            kriterler = points[table_type]
            puan_basi = point_values[table_type]
            max_score = len(kriterler) * puan_basi
            total_score = 0
            detaylar = []

            st.markdown(f"### ✅ {idx + 1}. {row.get('Issue key', f'Case {idx+1}')}\n- Tablo: {table_type} ({'Test datası var' if has_data else 'yok'}, {'önkoşul var' if has_precondition else 'önkoşul yok'})")

            for kriter in kriterler:
                ilgili_text = summary + " " + priority + " " + attachments
                mevcut = check_criterion(kriter, ilgili_text)

                if mevcut:
                    total_score += puan_basi
                    detaylar.append(f"- {kriter} ✅")
                else:
                    if kriter == "Precondition" and table_type == "C":
                        detaylar.append(f"- {kriter} ❌ (gerekli değil çünkü C tablosu)")
                    else:
                        detaylar.append(f"- {kriter} ❌")

            st.markdown(f"**Puan: {total_score} / {max_score}**")
            st.markdown("**Kriterler:**\n" + "\n".join(detaylar))

            aciklama = []
            if not has_precondition and "Precondition" in kriterler and table_type != "C":
                aciklama.append("Ön koşul eksik.")
            if not has_data and "Test Data" in kriterler:
                aciklama.append("Test datası eksik veya yeterince açık değil.")
            if not check_criterion("Steps", attachments):
                aciklama.append("Adımlar düzgün ayrılmamış olabilir.")
            if not check_criterion("Expected Result", attachments):
                aciklama.append("Beklenen sonuç belirtilmemiş.")
            if not check_criterion("Client", attachments):
                aciklama.append("Hangi clientta koşulacağı belirsiz.")

            if aciklama:
                st.markdown(f"**Açıklama:** {' '.join(aciklama)}")
            else:
                st.markdown("**Açıklama:** Tüm kriterler tabloya uygun şekilde sağlanıyor.")
            st.markdown("---")
