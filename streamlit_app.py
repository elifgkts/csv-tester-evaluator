import streamlit as st
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
