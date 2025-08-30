import streamlit as st
import pandas as pd
import re
# Başlık
st.setpageconfig(page_title="Test Case Değerlendirme", layout="wide")
st.title("📊 Test Case Kalite Değerlendirme")
# Dosya yükleme
uploadedfile = st.fileuploader("CSV dosyasını yükleyin", type=["csv"])
# Test case tablo kuralları
tablo_kriterleri = {
"A": {"kriterler": ["Summary", "Steps", "Expected Result", "Precondition", "Test Data"], "puan": 20},
"B": {"kriterler": ["Summary", "Steps", "Expected Result", "Precondition", "Test Data"], "puan": 17},
"C": {"kriterler": ["Summary", "Steps", "Expected Result", "Precondition", "Test Data"], "puan": 17},
"D": {"kriterler": ["Summary", "Steps", "Expected Result", "Precondition", "Test Data"], "puan": 14},
}
# Tablonun belirlenmesi
@st.cache_data
def belirle_tablo(precondition, testdata):
if pd.notna(precondition) and pd.notna(testdata):
return "D"
elif pd.notna(precondition):
return "B"
elif pd.notna(testdata):
return "C"
else:
return "A"
# Adım ayrıştırması
@st.cache_data
def adimlari_ayir(text):
if pd.isna(text):
return []
raw_steps = re.split(r"\n|\r", text.strip())
steps = [s.strip() for s in raw_steps if s.strip()]
return steps
if uploaded_file:
try:
df = pd.readcsv(uploadedfile, sep=";", engine="python")
st.success("Dosya başarıyla yüklendi. İlk 5 test case değerlendiriliyor...")
for idx, row in df.head(5).iterrows():
key = row.get("Key", f"Case-{idx+1}")
summary = row.get("Summary", "Özet bulunamadı")
steps_raw = row.get("Test Steps", "")
expected = row.get("Expected Result", "")
precondition = row.get("Precondition", "")
testdata = row.get("Test Data", "")
tablo = belirle_tablo(precondition, testdata)
kriterler = tablo_kriterleri[tablo]["kriterler"]
kriterpuani = tablokriterleri[tablo]["puan"]
kriter_skor = {}
# Summary
kriter_skor["Summary"] = pd.notna(summary) and len(summary.strip()) > 3
# Steps
steplist = adimlariayir(steps_raw)
kriterskor["Steps"] = len(steplist) >= 2
# Expected Result
kriter_skor["Expected Result"] = pd.notna(expected) and len(expected.strip()) > 3
# Precondition
if tablo in ["B", "D"]:
kriter_skor["Precondition"] = pd.notna(precondition) and len(precondition.strip()) > 3
else:
kriter_skor["Precondition"] = False
# Test Data
if tablo in ["C", "D"]:
kriter_skor["Test Data"] = pd.notna(testdata) and len(testdata.strip()) > 3
else:
kriter_skor["Test Data"] = False
toplamskor = sum([kriterpuani if v else 0 for k, v in kriter_skor.items()])
# Görsel çıktı
st.markdown(f"""
✅ {idx+1}. {key}
• Tablo: {tablo} ("{tablo}" tablosuna göre değerlendirme yapıldı)
• Puan: {toplam_skor} / 100
• Kriterler:
""")
for kriter, deger in kriter_skor.items():
ikon = "✅" if deger else "❌"
not_ek = " (gerekli değil çünkü {tablo} tablosu)" if kriter in ["Precondition", "Test Data"] and tablo in ["A", "B", "C"] and not deger else ""
st.markdown(f"  - {kriter} {ikon}{not_ek}")
# Açıklama
aciklama = ""
if not kriter_skor["Steps"]:
aciklama += "Adımlar eksik veya tek bir adımda yazılmış olabilir. "
if not kriter_skor["Precondition"] and tablo in ["B", "D"]:
aciklama += "Gerekli önkoşul eksik. "
if not kriter_skor["Test Data"] and tablo in ["C", "D"]:
aciklama += "Gerekli test datası eksik. "
if not aciklama:
aciklama = f"Tüm kriterler {tablo} tablosuna göre karşılanıyor."
st.markdown(f"*Açıklama:*{idx+1}. {key}
• Tablo: {tablo} ("{tablo}" tablosuna göre değerlendirme yapıldı)
• Puan: {toplam_skor} / 100
• Kriterler:
""")
for kriter, deger in kriter_skor.items():
ikon = "✅" if deger else "❌"
not_ek = " (gerekli değil çünkü {tablo} tablosu)" if kriter in ["Precondition", "Test Data"] and tablo in ["A", "B", "C"] and not deger else ""
st.markdown(f"  - {kriter} {ikon}{not_ek}")
# Açıklama
aciklama = ""
if not kriter_skor["Steps"]:
aciklama += "Adımlar eksik veya tek bir adımda yazılmış olabilir. "
if not kriter_skor["Precondition"] and tablo in ["B", "D"]:
aciklama += "Gerekli önkoşul eksik. "
if not kriter_skor["Test Data"] and tablo in ["C", "D"]:
aciklama += "Gerekli test datası eksik. "
if not aciklama:
aciklama = f"Tüm kriterler {tablo} tablosuna göre karşılanıyor."
st.markdown(f"Açıklama:*{idx+1}. {key}*
• Tablo: {tablo} ("{tablo}" tablosuna göre değerlendirme yapıldı)
• *Puan:* {toplam_skor} / 100
• *Kriterler:*Tablo: {tablo} ("{tablo}" tablosuna göre değerlendirme yapıldı)
• Puan: {toplam_skor} / 100
• Kriterler:*Tablo:* {tablo} ("{tablo}" tablosuna göre değerlendirme yapıldı)
• Puan: {toplam_skor} / 100
• Kriterler:
""")
for kriter, deger in kriter_skor.items():
ikon = "✅" if deger else "❌"
not_ek = " (gerekli değil çünkü {tablo} tablosu)" if kriter in ["Precondition", "Test Data"] and tablo in ["A", "B", "C"] and not deger else ""
st.markdown(f"  - {kriter} {ikon}{not_ek}")
# Açıklama
aciklama = ""
if not kriter_skor["Steps"]:
aciklama += "Adımlar eksik veya tek bir adımda yazılmış olabilir. "
if not kriter_skor["Precondition"] and tablo in ["B", "D"]:
aciklama += "Gerekli önkoşul eksik. "
if not kriter_skor["Test Data"] and tablo in ["C", "D"]:
aciklama += "Gerekli test datası eksik. "
if not aciklama:
aciklama = f"Tüm kriterler {tablo} tablosuna göre karşılanıyor."
st.markdown(f"Açıklama: {aciklama}")
st.markdown("---")
except Exception as e:
st.error(f"❌ Hata oluştu: {e}")
