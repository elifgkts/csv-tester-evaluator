import streamlit as st
import pandas as pd
import random
import ast

# ———— Yardımcı Fonksiyonlar ————

def tablo_tipi_belirle(row):
    precond = pd.notna(row['Custom field (Tests association with a Pre-Condition)'])
    steps_raw = row['Custom field (Manual Test Steps)']
    test_data = 'Data:' in steps_raw if isinstance(steps_raw, str) else False

    if precond and test_data:
        return 'D'
    elif precond:
        return 'B'
    elif test_data:
        return 'C'
    else:
        return 'A'

def puan_tablosu(tablo):
    if tablo == 'A':
        return {
            'Test başlığı anlaşılır mı?': 20,
            'Öncelik bilgisi girilmiş mi?': 20,
            'Test stepleri var ve doğru ayrıştırılmış mı?': 20,
            'Senaryonun hangi clientta koşulcağı belli mi?': 20,
            'Expected result bulunuyor mu?': 20
        }
    elif tablo == 'B':
        return {
            'Test başlığı anlaşılır mı?': 17,
            'Öncelik bilgisi girilmiş mi?': 17,
            'Test ön koşul eklenmiş mi?': 17,
            'Test stepleri var ve doğru ayrıştırılmış mı?': 17,
            'Senaryonun hangi clientta koşulcağı belli mi?': 17,
            'Expected result bulunuyor mu?': 17
        }
    elif tablo == 'C':
        return {
            'Test başlığı anlaşılır mı?': 17,
            'Öncelik bilgisi girilmiş mi?': 17,
            'Test datası eklenmiş mi?': 17,
            'Test stepleri var ve doğru ayrıştırılmış mı?': 17,
            'Senaryonun hangi clientta koşulcağı belli mi?': 17,
            'Expected result bulunuyor mu?': 17
        }
    else:  # D tablosu
        return {
            'Test başlığı anlaşılır mı?': 14,
            'Öncelik bilgisi girilmiş mi?': 14,
            'Test datası eklenmiş mi?': 14,
            'Test ön koşul eklenmiş mi?': 14,
            'Test stepleri var ve doğru ayrıştırılmış mı?': 14,
            'Senaryonun hangi clientta koşulcağı belli mi?': 14,
            'Expected result bulunuyor mu?': 14
        }

def kriter_puani(kriter, tablo, row):
    steps = row['Custom field (Manual Test Steps)']
    labels = row.get('Labels', '')
    summary = str(row.get('Summary', ''))
    priority = str(row.get('Priority', ''))
    precond = row['Custom field (Tests association with a Pre-Condition)']
    puan = puan_tablosu(tablo)[kriter]

    if kriter == 'Test başlığı anlaşılır mı?':
        if not summary.strip(): return 0, '❌ Başlık boş'
        elif len(summary.strip()) < 10: return puan - 5, '⚠️ Çok kısa başlık'
        elif any(word in summary.lower() for word in ['alanına gidilir', 'butonuna tıklanır']): return puan - 3, '⚠️ İfade QA açısından zayıf'
        else: return puan, '✅ Açıklayıcı'

    if kriter == 'Öncelik bilgisi girilmiş mi?':
        return (puan, '✅ Var') if priority.strip() else (0, '❌ Eksik')

    if kriter == 'Test datası eklenmiş mi?':
        return (puan, '✅ Data: var') if 'Data:' in steps else (0, '❌ Eksik')

    if kriter == 'Test ön koşul eklenmiş mi?':
        return (puan, '✅ Ön koşul girilmiş') if pd.notna(precond) and str(precond).strip() else (0, '❌ Eksik')

    if kriter == 'Test stepleri var ve doğru ayrıştırılmış mı?':
        try:
            parsed = ast.literal_eval(steps)
            if isinstance(parsed, list) and len(parsed) > 1:
                return puan, '✅ Ayrı adımlar'
            else:
                return 0, '❌ Tüm işlemler tek stepte'
        except:
            return 0, '❌ Step verisi çözülemedi'

    if kriter == 'Senaryonun hangi clientta koşulcağı belli mi?':
        if any(word in summary.lower() for word in ['web', 'ios', 'android']):
            return puan, '✅ Client belirtilmiş'
        else:
            return 0, '❌ Client bilgisi eksik'

    if kriter == 'Expected result bulunuyor mu?':
        try:
            parsed = ast.literal_eval(steps)
            expected = parsed[0].get('Expected Result', '') if isinstance(parsed, list) else ''
            if not expected.strip():
                return 0, '❌ Boş'
            elif len(expected.strip()) < 10:
                return puan - 3, '⚠️ Çok kısa ifade'
            elif any(phrase in expected.lower() for phrase in ['test edilir', 'kontrol edilir']):
                return puan - 2, '⚠️ Test tanımı yapılmış, beklenen sonuç değil'
            else:
                return puan, '✅ Beklenen sonuç yazılmış'
        except:
            return 0, '❌ Expected çözümlenemedi'

    return 0, '❓ Bilinmeyen kriter'

# ———— Streamlit Arayüz ————

st.title('📋 Test Case Değerlendirme Aracı (GPT Destekli)')
uploaded_file = st.file_uploader("Lütfen test case CSV dosyasını yukleyin (\";\" ile ayrılmış)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, delimiter=';')
    rastgele_caseler = df.sample(n=5)

    for i, (_, row) in enumerate(rastgele_caseler.iterrows(), 1):
        tablo = tablo_tipi_belirle(row)
        kriterler = puan_tablosu(tablo)

        st.subheader(f"🎯 Test Case {i}: {row['Issue key']}")
        st.markdown(f"**Summary:** {row['Summary']}")
        st.markdown(f"**Tablo Türü:** `{tablo}`")

        toplam = 0
        max_toplam = sum(kriterler.values())

        for kriter in kriterler:
            puan, aciklama = kriter_puani(kriter, tablo, row)
            toplam += puan
            durum = "✅" if puan == kriterler[kriter] else ("⚠️" if 0 < puan < kriterler[kriter] else "❌")
            st.markdown(f"- {durum} **{kriter} ({puan}/{kriterler[kriter]}):** {aciklama}")

        st.markdown(f"**🎯 Toplam Puan:** `{toplam} / {max_toplam}`")
        st.markdown("---")
