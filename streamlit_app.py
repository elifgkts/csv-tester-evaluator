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

# ℹ️ Kurallar ve Tablo Yapısı
with st.expander("📌 Değerlendirme Kuralları ve Tablo Açıklamaları"):
    st.markdown("""
**CSV formatı:** CSV dosyası `;` (noktalı virgül) ile ayrılmış olmalıdır.  
**Gerekli sütunlar:** `Issue Key`, `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`

### 🧩 Tablo Türleri:
| Tablo | Açıklama                                      |
|-------|-----------------------------------------------|
| A     | Veri veya ön koşul gerekmeyen testler         |
| B     | Ön koşul gerekli                              |
| C     | Test datası gerekli                           |
| D     | Ön koşul + Test datası gerekli                |

### ✅ Kriterler:
Her tablo için 7 kriter aşağıdaki gibidir. Ancak tabloya göre bazı kriterler değerlendirme dışı bırakılır.

1. **Test başlığı anlaşılır mı?**
2. **Öncelik bilgisi girilmiş mi?**
3. **Test datası eklenmiş mi?**
4. **Test ön koşul eklenmiş mi?**
5. **Test stepleri var ve doğru ayrıştırılmış mı?**
6. **Senaryonun hangi clientta koşulacağı belli mi?**
7. **Expected result bulunuyor mu?**

### 📊 Puanlama:
| Tablo | Kriter Sayısı | Kriter Puanı | Maksimum Puan |
|-------|----------------|---------------|----------------|
| A     | 5              | 20            | 100            |
| B     | 6              | 17            | 102            |
| C     | 6              | 17            | 102            |
| D     | 7              | 14            | 98             |

### 🔸 Step Puanlama Detayı:
- Step hiç ayrıştırılmamışsa ve sadece summary tekrarıysa: **1 puan**
- Step'ler birleştirilmiş ama benzer sorgular anlamlı şekilde gruplanmışsa: **10-15 puan** (hafif kırıntı)
- Step'ler düzgün ayrılmışsa: **tam puan**

""")

# Devamı uygulamanın alt kısmında yer alır (yükleme, analiz, görselleştirme vb.)
# ... (Uygulamanın tam kodu daha uzun olduğu için burada sadece giriş bölümü gösterilmiştir. Eğer devamı da istenirse tüm script baştan sona yeniden paylaşılır.)
