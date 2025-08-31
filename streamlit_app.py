import streamlit as st
import pandas as pd
import random
import ast

st.set_page_config(page_title="Test Case Değerlendirici", layout="wide")
st.title("📋 Test Case Kalite Değerlendirme Aracı")
st.markdown("""
Bu araç, .csv formatındaki JIRA test case verilerini rastgele seçeceğiniz 5 test case üzerinden değerlendirir.

**Değerlendirme Kriterleri:**
- Test başlığı anlaşılır mı?
- Öncelik bilgisi girilmiş mi?
- Test datası eklenmiş mi? *(Sadece C ve D tablosunda)*
- Test ön koşul eklenmiş mi? *(Sadece B ve D tablosunda)*
- Test stepleri var ve doğru ayrıştırılmış mı?
- Senaryonun hangi clientta koşulacağı belli mi?
- Expected result bulunuyor mu?

**Not:** CSV dosyası mutlaka `;` ile ayrılmış olmalıdır.
""")

uploaded_file = st.file_uploader("CSV dosyasını yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')

    st.success(f"{len(df)} test case yüklendi.")

    sample_df = df.sample(n=5, random_state=random.randint(0, 99999)).reset_index(drop=True)

    def detect_table_type(manual_steps, summary):
        # Adımlarda test datası var mı?
        steps = []
        try:
            steps = ast.literal_eval(manual_steps)
        except:
            pass
        has_data = any((step.get("Data") or "") != "" for step in steps)

        # Örnek test datası anahtar kelimeleri
        data_keywords = ["token", "msisdn", "account", "payload", "auth", "config"]
        if any(kw in summary.lower() for kw in data_keywords):
            has_data = True

        has_precondition = 'Pre-Condition' in manual_steps or 'ön koşul' in summary.lower()

        if has_precondition and has_data:
            return "D"
        elif has_precondition:
            return "B"
        elif has_data:
            return "C"
        else:
            return "A"

    def evaluate_case(row):
        result = []
        summary = row.get("Summary", "")
        priority = row.get("Priority", "")
        platform = row.get("Platform", "")
        manual_steps_raw = row.get("Custom field (Manual Test Steps)", "[]")
        try:
            steps = ast.literal_eval(manual_steps_raw)
        except:
            steps = []

        table = detect_table_type(manual_steps_raw, summary)
        total = 0

        # Puan değerleri
        weights = {
            "A": 20,
            "B": 17,
            "C": 17,
            "D": 14
        }
        w = weights[table]

        # Başlık
        if summary.strip() == "":
            result.append(("Test başlığı anlaşılır mı?", "❌", 0, "Başlık yok."))
        elif len(summary.strip()) < 10:
            result.append(("Test başlığı anlaşılır mı?", "❌", w - 5, "Başlık kısa veya eksik ifade edilmiş."))
            total += w - 5
        elif any(word in summary.lower() for word in ["gidilir", "tıklanır", "seçilir"]):
            result.append(("Test başlığı anlaşılır mı?", "⚠️", w - 3, "Başlık anlatım olarak step gibi yazılmış."))
            total += w - 3
        else:
            result.append(("Test başlığı anlaşılır mı?", "✅", w, "Başlık açık ve anlamlı."))
            total += w

        # Öncelik
        if priority.strip() == "":
            result.append(("Öncelik bilgisi girilmiş mi?", "❌", 0, "Öncelik bilgisi yok."))
        else:
            result.append(("Öncelik bilgisi girilmiş mi?", "✅", w, "Öncelik tanımlı."))
            total += w

        # Test datası
        if table in ["C", "D"]:
            has_data = any((step.get("Data") or "") != "" for step in steps)
            if has_data:
                result.append(("Test datası eklenmiş mi?", "✅", w, "Test datası belirtilmiş."))
                total += w
            else:
                result.append(("Test datası eklenmiş mi?", "❌", 0, "Test datası eksik."))

        # Ön koşul
        if table in ["B", "D"]:
            has_pre = 'Pre-Condition' in manual_steps_raw
            if has_pre:
                result.append(("Test ön koşul eklenmiş mi?", "✅", w, "Ön koşul tanımlı."))
                total += w
            else:
                result.append(("Test ön koşul eklenmiş mi?", "❌", 0, "Ön koşul eksik."))

        # Step değerlendirme
        if not steps:
            result.append(("Test stepleri var ve doğru ayrıştırılmış mı?", "❌", 0, "Step alanı boş."))
        elif len(steps) == 1 and steps[0].get("Action", "").strip() == summary.strip():
            result.append(("Test stepleri var ve doğru ayrıştırılmış mı?", "❌", 1, "Step olarak summary yazılmış, ayrım yapılmamış."))
            total += 1
        else:
            result.append(("Test stepleri var ve doğru ayrıştırılmış mı?", "✅", w, "Step'ler var ve ayrıştırılmış."))
            total += w

        # Platform bilgisi
        if platform.strip() == "":
            result.append(("Senaryonun hangi clientta koşulacağı belli mi?", "❌", 0, "Platform bilgisi eksik."))
        else:
            result.append(("Senaryonun hangi clientta koşulacağı belli mi?", "✅", w, "Platform tanımlı."))
            total += w

        # Expected Result
        expected_results = [step.get("Expected Result", "") for step in steps if "Expected Result" in step]
        if not expected_results or all(er.strip() == "" for er in expected_results):
            result.append(("Expected result bulunuyor mu?", "❌", 0, "Expected Result eksik."))
        elif any("ne yapılacağı" in er.lower() or "test edilir" in er.lower() for er in expected_results):
            result.append(("Expected result bulunuyor mu?", "⚠️", w - 3, "Expected Result var ama testin kendisini anlatıyor."))
            total += w - 3
        else:
            result.append(("Expected result bulunuyor mu?", "✅", w, "Expected Result düzgün yazılmış."))
            total += w

        return table, total, result

    for idx, row in sample_df.iterrows():
        key = row.get("Key", "")
        summary = row.get("Summary", "")
        table, total, details = evaluate_case(row)

        with st.expander(f"🧪 {key} – {summary} (Tablo {table}) – Skor: {total}/100"):
            for crit, status, pts, explanation in details:
                st.markdown(f"**{crit}**: {status} {pts} puan – _{explanation}_")
