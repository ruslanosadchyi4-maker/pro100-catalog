import streamlit as st
from google import genai

# Безпечне отримання ключа
api_key = st.secrets.get("GEMINI_APY_KEY")
if api_key:
	client = genai.Client(api_key=api_key)

# --- Юокова панель ---
with st.sidebar:
	st.title("PRO100 Catalog")
# --- Створення стильної бокової панелі (Sidebar) ---
with st.sidebar:
	st.title("🛍️ PRO100 Catalog")
	st.markdown("### Керування проєктом")

	# Вибір режиму чи налаштувань (можна буде розширити)
	analysis_mode = st.selectbox(
		"Режим обробки",
		["Стандартний аналіз", "Поглиблений опис"]
	)

	st.markdown("---")

	# Інформаційний блок
	st.markdown("### ℹ️ Про застосунок")
	st.info(
		"Цей інструмент створений для автоматичного аналізу та класифікації "
		"товарів за допомогою штучного інтелекту Google Gemini."
	)

	st.markdown("---")
	st.caption("🚀 Версія: 1.1.0 (Production)")
	st.caption("☁️ Розгорнуто на Streamlit Cloud")

 

