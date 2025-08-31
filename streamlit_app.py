import streamlit as st
import pandas as pd
import random
import ast

# Sayfa ayarları
st.set_page_config(page_title="Test Case Skorlama", layout="wide")
st.title("🧪 Test Case Skorlama Aracı")

# CSV Yükleme
uploaded_file = st.file_uploader("CSV dosyasını yükleyin (JIRA'dan alınan)", type=["csv"])

# Açıklama
with st.expander("ℹ️ Detaylı Açıklama ve Kurallar"):
    st.markdown("""
    **✨ Değerlendirme Kriterleri ve Tablolar**

    Test case'ler için 7 ana kriter değerlendirilir:
    1. Test başlığı anlaşılır mı?
    2. Öncelik bilgisi girilmiş mi?
    3. Test datası eklenmiş mi? ("Custom field (Manual Test Steps)" içinde `Data:` olarak belirtilmeli)
    4. Test ön koşul eklenmiş mi?
    5. Test stepleri var ve **doğru ayrıştırılmış mı?** (Summary'nin tekrarlanması veya tek step olmamalı)
    6. Senaryonun hangi clientta koşulacağı belli mi? (iOS/Android/Web vb.)
    7. Expected result bulunuyor mu? (yalnızca gerçek beklenen sonuçlar kabul edilir)

    **🔹 Tablolar ve Kriter Sayısı:**
    - A: Hiçbir önkoşul ya da veri gerektirmez (5 kriter, her biri 20 puan)
    - B: Önkoşul gerekli (6 kriter, her biri 17 puan)
    - C: Veri gerekli (6 kriter, her biri 17 puan)
    - D: Önkoşul + veri gerekli (7 kriter, her biri 14 puan)

    ❌ Eksik olan her kriterin puanı tamamen kırılır. Kırıntı puan uygulaması yalnızca başlık ve stepler için geçerlidir.

    **🌟 QA Manager Yorumu önemlidir:**
    - Stepler gerçekten doğru ayrıştırılmış mı?
    - Expected Result gerçek bir beklenen sonuç mu?
    - Summary içeriği uygun mu? ("...gidilir" yerine "gidilmesi" gibi doğruluk aranır)

    **⚡ïe Not:** CSV her zaman `;` ile ayrılmış olmalıdır.
    CSV şu sütun başlıklarını içermelidir:
    - `Key`, `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`, `Custom field (Tests association with a Pre-Condition)`
    """)

# Yardımcı fonksiyonlar
def parse_manual_steps(manual_step):
    try:
        steps = ast.literal_eval(manual_step)
        if isinstance(steps, list):
            return steps
        else:
            return []
    except:
        return []

def step_score(steps, summary):
    if not steps:
        return 0, "Step alanı boş"
    elif len(steps) == 1 and summary.lower().strip() in steps[0]["Action"].lower():
        return 1, "Tek bir stepte sadece summary tekrarlanmış"
    elif len(steps) == 1:
        return 5, "Sadece tek step yazılmış"
    else:
        return 20, "Step ayrımı yapılmış"

def expected_result_score(steps):
    for s in steps:
        result = s.get("Expected Result", "").lower()
        if result and not any(word in result for word in ["test", "kontrol", "doğrulanır"]):
            return 20, "Gerçek bir beklenen sonuç var"
        elif result:
            return 10, "Expected Result alanında testin ne olduğu yazılmış"
    return 0, "Expected Result boş"

def test_data_exists(steps):
    for s in steps:
        if s.get("Data"):
            return True
    return False

# Ana işleyiş
if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=";")
    sampled = df.sample(5)

    for _, row in sampled.iterrows():
        key = row['Key']
        summary = row['Summary']
        priority = row['Priority']
        labels = str(row.get("Labels", ""))
        precondition = str(row.get("Custom field (Tests association with a Pre-Condition)", ""))
        manual_raw = row['Custom field (Manual Test Steps)']

        steps = parse_manual_steps(manual_raw)

        # Tablo belirleme
        needs_data = test_data_exists(steps)
        needs_precond = bool(precondition.strip())

        if needs_data and needs_precond:
            table = "D"
            kriterler = ["title", "priority", "data", "precond", "steps", "client", "expected"]
            max_puan = 14
        elif needs_precond:
            table = "B"
            kriterler = ["title", "priority", "precond", "steps", "client", "expected"]
            max_puan = 17
        elif needs_data:
            table = "C"
            kriterler = ["title", "priority", "data", "steps", "client", "expected"]
            max_puan = 17
        else:
            table = "A"
            kriterler = ["title", "priority", "steps", "client", "expected"]
            max_puan = 20

        toplam = 0
        detay = []

        # Kriter puanlama
        for k in kriterler:
            if k == "title":
                if not summary.strip():
                    puan = 0
                    aciklama = "Summary boş"
                elif summary.endswith("alanına gidilir"):
                    puan = max_puan - 2
                    aciklama = "Yanlış ifade: gidilir yerine gidilmesi yazılmalı"
                else:
                    puan = max_puan
                    aciklama = "Anlaşılır başlık"
            elif k == "priority":
                puan = max_puan if priority else 0
                aciklama = "Var" if priority else "Eksik"
            elif k == "data":
                puan = max_puan if test_data_exists(steps) else 0
                aciklama = "Var" if test_data_exists(steps) else "Eksik"
            elif k == "precond":
                puan = max_puan if precondition.strip() else 0
                aciklama = "Var" if precondition.strip() else "Eksik"
            elif k == "steps":
                puan, aciklama = step_score(steps, summary)
                puan = min(puan, max_puan)
            elif k == "client":
                if any(word in summary.lower() for word in ["ios", "android", "web"]):
                    puan = max_puan
                    aciklama = "Platform belirtilmiş"
                else:
                    puan = 0
                    aciklama = "Platform eksik"
            elif k == "expected":
                puan, aciklama = expected_result_score(steps)
                puan = min(puan, max_puan)

            toplam += puan
            detay.append((k, puan, aciklama))

        st.markdown(f"### 🔢 {key} | Tablo: {table} | Toplam: **{toplam} / 100**")
        for k, p, a in detay:
            durum = "✅" if p == max_puan else ("⚠" if 0 < p < max_puan else "❌")
            st.write(f"{durum} **{k}**: {p} - {a}")
        st.markdown("---")
