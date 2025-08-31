import streamlit as st
import pandas as pd
import random
import ast

st.set_page_config(page_title="Test Case Değerlendirme", layout="wide")
st.title("📊 Akıllı Test Case Değerlendirici")

st.markdown("""
Bu uygulama, test case değerlendirme kurallarına uygun olarak rastgele 5 test case seçer, A/B/C/D tablolarına göre sınıflandırır ve her kriteri tek tek puanlar.

**Beklenen CSV Formatı:** `;` ile ayrılmış ve aşağıdaki sütunları içermelidir:
- `Key`
- `Summary`
- `Priority`
- `Labels`
- `Custom field (Manual Test Steps)`
- `Custom field (Client)`
- `Custom field (Tests association with a Pre-Condition)`

Lütfen yukarıdaki sütun isimlerinin dosyada birebir aynı şekilde yazıldığından emin olun.
""")

uploaded_file = st.file_uploader("CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, delimiter=';', encoding='utf-8')

    st.success(f"Toplam test case: {len(df)}. Rastgele 5 tanesi aşağıda değerlendirilmiştir.")

    def determine_table(row):
        manual_steps = row['Custom field (Manual Test Steps)']
        labels = str(row['Labels']).lower()
        summary = str(row['Summary']).lower()

        try:
            steps = ast.literal_eval(manual_steps)
        except:
            steps = []

        data_exists = any('data' in step.get('fields', {}).get('Data', '').lower() for step in steps) or 'data:' in manual_steps.lower()
        expected_exists = any('expected' in step.get('fields', {}).get('Expected Result', '').lower() for step in steps)
        precondition_exists = pd.notna(row['Custom field (Tests association with a Pre-Condition)']) and row['Custom field (Tests association with a Pre-Condition)'] != ''

        if precondition_exists and data_exists:
            return "D"
        elif precondition_exists:
            return "B"
        elif data_exists:
            return "C"
        else:
            return "A"

    def score_case(row):
        table = determine_table(row)
        score = 0
        breakdown = []

        def partial_points(criterion, point, reason):
            return {"criterion": criterion, "points": point, "note": reason}

        def full_points(criterion, point):
            return {"criterion": criterion, "points": point, "note": "✅ Tam puan"}

        def zero_points(criterion, reason):
            return {"criterion": criterion, "points": 0, "note": f"❌ {reason}"}

        point = {"A": 20, "B": 17, "C": 17, "D": 14}[table]

        # 1. Summary
        summary = str(row['Summary'])
        if not summary.strip():
            breakdown.append(zero_points("Test başlığı anlaşılır mı?", "Başlık eksik"))
        elif len(summary) < 10:
            breakdown.append(partial_points("Test başlığı anlaşılır mı?", point - 5, "Başlık çok kısa"))
        elif any(w in summary for w in ["gidilir", "yapılır"]):
            breakdown.append(partial_points("Test başlığı anlaşılır mı?", point - 2, "Dil bilgisi sorunlu (gidilir/yapılır vb.)"))
        else:
            breakdown.append(full_points("Test başlığı anlaşılır mı?", point))

        # 2. Öncelik
        if pd.isna(row['Priority']) or row['Priority'] == '':
            breakdown.append(zero_points("Öncelik bilgisi girilmiş mi?", "Öncelik bilgisi boş"))
        else:
            breakdown.append(full_points("Öncelik bilgisi girilmiş mi?", point))

        # 3. Test Datası
        if table in ["C", "D"]:
            steps = ast.literal_eval(str(row['Custom field (Manual Test Steps)'])) if row['Custom field (Manual Test Steps)'] else []
            data_exists = any(step.get('fields', {}).get('Data', '').strip() for step in steps)
            if data_exists:
                breakdown.append(full_points("Test datası eklenmiş mi?", point))
            else:
                breakdown.append(zero_points("Test datası eklenmiş mi?", "Data alanı boş"))

        # 4. Önkoşul
        if table in ["B", "D"]:
            if pd.isna(row['Custom field (Tests association with a Pre-Condition)']) or row['Custom field (Tests association with a Pre-Condition)'] == '':
                breakdown.append(zero_points("Test ön koşul eklenmiş mi?", "Ön koşul alanı boş"))
            else:
                breakdown.append(full_points("Test ön koşul eklenmiş mi?", point))

        # 5. Stepler
        try:
            steps = ast.literal_eval(str(row['Custom field (Manual Test Steps)']))
        except:
            steps = []
        if not steps:
            breakdown.append(zero_points("Test stepleri var ve doğru ayrıştırılmış mı?", "Step yok"))
        elif len(steps) == 1 and summary.strip().lower() in steps[0].get('fields', {}).get('Action', '').lower():
            breakdown.append(partial_points("Test stepleri var ve doğru ayrıştırılmış mı?", 1, "Tek stepte summary yazılmış"))
        else:
            breakdown.append(full_points("Test stepleri var ve doğru ayrıştırılmış mı?", point))

        # 6. Client
        client = str(row.get("Custom field (Client)", ""))
        if client.strip():
            breakdown.append(full_points("Senaryonun hangi clientta koşulacağı belli mi?", point))
        else:
            breakdown.append(zero_points("Senaryonun hangi clientta koşulacağı belli mi?", "Client alanı boş"))

        # 7. Expected Result
        if table in ["A", "B", "C", "D"]:
            expected_texts = [step.get('fields', {}).get('Expected Result', '') for step in steps]
            expected_texts = [text for text in expected_texts if text.strip()]
            if not expected_texts:
                breakdown.append(zero_points("Expected result bulunuyor mu?", "Hiçbiri dolu değil"))
            elif any(w in expected_texts[0].lower() for w in ["test edilir", "yapılır", "alanı"]):
                breakdown.append(partial_points("Expected result bulunuyor mu?", point - 2, "Beklenen sonuç değil, işlem açıklaması var"))
            else:
                breakdown.append(full_points("Expected result bulunuyor mu?", point))

        total = sum(item['points'] for item in breakdown)
        return {
            "Key": row['Key'],
            "Summary": row['Summary'],
            "Tablo": table,
            "Toplam Puan": total,
            "Detaylar": breakdown
        }

    sampled_df = df.sample(5, random_state=42)  # Rastgele ama sabit olsun diye
    sonuçlar = sampled_df.apply(score_case, axis=1)

    for result in sonuçlar:
        st.markdown(f"### 🔹 {result['Key']} – {result['Summary']}")
        st.markdown(f"**🧮 Tablo Türü:** {result['Tablo']} &nbsp;&nbsp;|&nbsp;&nbsp; **Toplam Puan:** `{result['Toplam Puan']}`")
        for item in result['Detaylar']:
            st.markdown(f"- **{item['criterion']}** → `{item['points']}` puan – {item['note']}")
        st.markdown("---")
