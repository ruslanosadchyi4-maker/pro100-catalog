import streamlit as st
from google import genai
from PIL import Image

# Налаштування сторінки
st.set_page_config(
	page_title="PRO100 Catalog",
	page_icon="🛍️",
	layout="wide"
)

# Безпечне отримання API-ключа з секретів Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
	st.error("⚠️ Не знайдено `GEMINI_API_KEY` у Streamlit Secrets. Будь ласка, додайте його в налаштуваннях хмари.")
	st.stop()

# Ініціалізація клієнта Gemini
client = genai.Client(api_key=api_key)

# --- Бокова панель (Sidebar) ---
with st.sidebar:
	st.title("🛍️ PRO100 Catalog")
	st.markdown("### Керування проєктом")

	analysis_mode = st.selectbox(
		"Режим обробки",
		["Стандартний аналіз", "Поглиблений опис"]
	)

	st.markdown("---")
	st.markdown("### ℹ️ Про застосунок")
	st.info(
		"Цей інструмент створений для автоматичного аналізу та класифікації "
		"товарів за допомогою штучного інтелекту Google Gemini."
	)

	st.markdown("---")
	st.caption("🚀 Версія: 1.1.0 (Production)")
	st.caption("☁️ Розгорнуто на Streamlit Cloud")

# --- Головний екран ---
st.title("📦 Автоматизований каталог товарів")
st.markdown("Завантажте зображення товару, щоб ШІ проаналізував його та сформував картку.")

# Завантаження файлу
uploaded_file = st.file_uploader("Виберіть зображення товару", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
	col1, col2 = st.columns(2)

	with col1:
		image = Image.open(uploaded_file)
		st.image(image, caption="Завантажене зображення", use_container_width=True)

	with col2:
		st.markdown("### 📊 Статус обробки")
		if st.button("🚀 Запустити аналіз ШІ", type="primary"):
			with st.spinner("ШІ аналізує зображення... Зачекайте секунду."):
				try:
					# Запит до моделі Gemini
					response = client.models.generate_content(
						model='gemini-2.5-flash',
						contents=[
							image,
							"Проаналізуй це зображення товару для каталогу. Надай назву, категорію та детальний опис."
						]
					)

					st.success("Аналіз успішно завершено!")

					# Структурований вивід у контейнері
					with st.container(border=True):
						st.markdown("#### 🏷️ Результати класифікації")
						st.write(response.text)

				except Exception as e:
					st.error(f"Сталася помилка під час аналізу: {e}")
