import streamlit as st
import pandas as pd

# Streamlit sayfa ayarları
st.set_page_config(page_title="CSV Test Senaryosu Değerlendirme Aracı", layout="wide")

def determine_table(precondition, test_data):
    """
    Test senaryosunun türünü ön koşul ve test verisine göre belirler.
    
    Args:
        precondition (bool): Ön koşul var mı?
        test_data (bool): Test verisi var mı?
    
    Returns:
        str: Tablo türü ("A", "B", "C", "D").
    """
    if precondition and test_data:
        return "D"
    elif precondition:
        return "B"
    elif test_data:
        return "C"
    else:
        return "A"

# Her tablo türü için puanlama kriterleri
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
          ("Senaryonun hangi clientta koşulcağı belli mi?", 14),
          ("Expected result bulunuyor mu?", 14)]
}

# Uygulamanın kullanıcı arayüzü
st.title("📋 Test Senaryosu Değerlendirme Aracı (CSV)")
st.markdown("CSV dosyanızı yükleyin ve rastgele 5 test senaryosunun otomatik olarak değerlendirilmesini sağlayın.")

uploaded_file = st.file_uploader("CSV Dosyasını Yükleyin", type="csv")

if uploaded_file:
    # Dosya okuma işlemi
    df = None
    try:
        # Virgül (,) veya noktalı virgül (;) ayırıcısını deneyerek dosyayı okuyun
        df = pd.read_csv(uploaded_file, sep="[,;]", engine="python", on_bad_lines='skip')
    except Exception as e:
        st.error(f"Dosyayı okurken bir hata oluştu: {e}")
        st.info("Lütfen dosyanın doğru bir CSV formatında olduğundan ve virgül (,) veya noktalı virgül (;) ile ayrıldığından emin olun.")

    if df is not None:
        if df.shape[0] < 5:
            st.error("Lütfen en az 5 test senaryosu içeren bir CSV dosyası yükleyin.")
        else:
            # Rastgele 5 test senaryosu seçin
            sampled = df.sample(5, random_state=42).reset_index(drop=True)
            st.subheader("📊 Örnek 5 Test Senaryosu Değerlendirmesi")

            # Seçilen her bir test senaryosunu döngüde değerlendirir
            for idx, row in sampled.iterrows():
                st.markdown(f"### 🎯 Test Senaryosu {idx + 1}")
                summary = str(row.get("Summary", ""))
                priority = str(row.get("Priority", ""))
                attachments = str(row.get("Attachments", ""))

                # Ön koşul ve test verisi varlığını kontrol et
                has_precondition = "ön koşul" in attachments.lower()
                has_data = "test data" in attachments.lower()

                # Tablo türünü belirle ve puanlama kriterlerini al
                table_type = determine_table(has_precondition, has_data)
                kriterler = points[table_type]
                total_score = 0

                # UI için sütunları ayır
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"**Tablo Türü:** {table_type}")
                    st.markdown(f"**Özet:** {summary}")
                    st.markdown(f"**Öncelik:** {priority}")
                with cols[1]:
                    st.markdown("#### Puanlar")

                # Kriterlere göre puanlama yap
                for kriter, max_puan in kriterler:
                    puan = max_puan
                    # Kontroller
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
