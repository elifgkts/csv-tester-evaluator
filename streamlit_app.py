import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="CSV Test Case Evaluator", layout="wide")

# Tablo türünü belirleme

def determine_table(precondition, test_data):
    if precondition and test_data:
        return "D"
    elif precondition:
        return "B"
    elif test_data:
        return "C"
    else:
        return "A"

# Kriterler ve puan değerleri
points = {
    "A": [
        ("Test başlığı anlaşılır mı?", 20),
        ("Öncelik bilgisi girilmiş mi?", 20),
        ("Test stepleri var ve doğru ayrıştırılmış mı?", 20),
        ("Senaryonun hangi clientta koşulacağı belli mi?", 20),
        ("Expected result bulunuyor mu?", 20)
    ],
    "B": [
        ("Test başlığı anlaşılır mı?", 17),
        ("Öncelik bilgisi girilmiş mi?", 17),
        ("Test ön koşul eklenmiş mi?", 17),
        ("Test stepleri var ve doğru ayrıştırılmış mı?", 17),
        ("Senaryonun hangi clientta koşulacağı belli mi?", 17),
        ("Expected result bulunuyor mu?", 17)
    ],
    "C": [
        ("Test başlığı anlaşılır mı?", 17),
        ("Öncelik bilgisi girilmiş mi?", 17),
        ("Test datası eklenmiş mi?", 17),
        ("Test stepleri var ve doğru ayrıştırılmış mı?", 17),
        ("Senaryonun hangi clientta koşulacağı belli mi?", 17),
        ("Expected result bulunuyor mu?", 17)
    ],
    "D": [
        ("Test başlığı anlaşılır mı?", 14),
        ("Öncelik bilgisi girilmiş mi?", 14),
        ("Test datası eklenmiş mi?", 14),
        ("Test ön koşul eklenmiş mi?", 14),
        ("Test stepleri var ve doğru ayrıştırılmış mı?", 14),
        ("Senaryonun hangi clientta koşulacağı belli mi?", 14)
    ]
}

st.title("📋 Test Case Değerlendirme Uygulaması (CSV)")
st.markdown("CSV dosyanızı yükleyin, rastgele 5 test case detaylı ve açıklamalı şekilde puanlansın.")

uploaded_file = st.file_uploader("CSV Dosyasını Yükle", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=";", engine="python")
    if df.shape[0] < 5:
        st.error("En az 5 test case içeren bir CSV yükleyin.")
    else:
        sampled = df.sample(5, random_state=42).reset_index(drop=True)
        st.subheader("📊 Örnek 5 Test Case Değerlendirmesi")

        for idx, row in sampled.iterrows():
            summary = str(row.get("Summary", "")).strip()
            priority = str(row.get("Priority", "")).strip()
            attachments = str(row.get("Attachments", "")).lower()

            has_precondition = "ön koşul" in attachments
            has_data = "test data" in attachments

            table_type = determine_table(has_precondition, has_data)
            kriterler = points[table_type]
            total_score = 0
            explanations = []
            kriter_durum = []

            # Değerlendirme
            for kriter, max_puan in kriterler:
                puan = max_puan
                durum = "✅"
                aciklama = ""

                if "başlığı" in kriter:
                    if not summary:
                        puan, durum, aciklama = 0, "❌", "Başlık boş."
                    else:
                        aciklama = "Başlık yeterince açık."

                elif "öncelik" in kriter:
                    if not priority:
                        puan, durum, aciklama = 0, "❌", "Priority girilmemiş."
                    else:
                        aciklama = "Priority girilmiş."

                elif "ön koşul" in kriter:
                    if not has_precondition:
                        puan, durum, aciklama = 0, "❌", "Ön koşul belirtilmemiş."
                    else:
                        aciklama = "Ön koşul sağlanmış."

                elif "test datası" in kriter:
                    if not has_data:
                        puan, durum, aciklama = 0, "❌", "Test datası eksik."
                    else:
                        aciklama = "Test datası sağlanmış."

                elif "stepleri" in kriter:
                    if not any(x in attachments for x in ["1.", "2.", "step", "adım"]):
                        puan, durum, aciklama = 0, "❌", "Step'ler ayrıştırılmamış."
                    else:
                        aciklama = "Adımlar ayrılmış."

                elif "expected" in kriter:
                    if "beklenen" not in attachments:
                        puan, durum, aciklama = 0, "❌", "Expected result eksik."
                    else:
                        aciklama = "Expected result mevcut."

                elif "client" in kriter:
                    if not any(x in attachments for x in ["ios", "android", "web"]):
                        puan, durum, aciklama = 0, "❌", "Client bilgisi eksik."
                    else:
                        aciklama = "Client platform belirtilmiş."

                kriter_durum.append((kriter, durum, puan, max_puan, aciklama))
                total_score += puan

            # Görselleştirme
            st.markdown(f"### ✅ {idx+1}. {row.get('Issue Key', f'Test {idx+1}')}")
            st.markdown(f"**Tablo:** {table_type} ({'Her iki alan gerekli' if table_type=='D' else 'Test datası var ama ön koşul yok' if table_type=='C' else 'Ön koşul var ama test datası yok' if table_type=='B' else 'Test datası ve ön koşul gerekmiyor'})")
            st.markdown(f"**Puan:** {total_score} / {sum(p[1] for p in kriterler)}")

            with st.expander("Kriterler ve Açıklamalar"):
                for kriter, durum, puan, max_puan, aciklama in kriter_durum:
                    st.markdown(f"- **{kriter}** {durum} (**{puan}/{max_puan}**)  \\\n                        _{aciklama}_")

            st.markdown("---")
