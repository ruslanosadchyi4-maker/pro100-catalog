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

# Ініціалізація сховища історії у st.session_state
if "catalog_items" not in st.session_state:
	st.session_state.catalog_items = []

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
		"Цей інструмент створений для автоматичного аналізу, ціноутворення "
		"та класифікації товарів за допомогою штучного інтелекту Google Gemini."
	)

	st.markdown("---")
	st.caption("🚀 Версія: 1.3.0 (Production)")
	st.caption("☁️ Розгорнуто на Streamlit Cloud")

# --- Головний екран ---
st.title("📦 Автоматизований каталог товарів")
st.markdown("Завантажте зображення товару, щоб ШІ згенерував картку, артикул, ціну та теги.")

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
			with st.spinner("ШІ аналізує товар, формує ціну та артикул..."):
				try:
					# Покращений промпт для генерації цін, артикулів та тегів
					prompt = """
					Проаналізуй це зображення товару для комерційного каталогу. Надай інформацію у такому форматі:
					- **Назва:** коротка та приваблива назва товару
					- **Категорія:** до якої категорії належить товар
					- **Артикул (SKU):** згенеруй унікальний логічний артикул (наприклад, PRD-XXXXX)
					- **Орієнтовна ціна:** запропонуй ринкову ціну в євро (€)
					- **Теги:** 3-5 ключових тегів через кому (наприклад: стильно, новинка, аксесуар)
					- **Опис:** детальний комерційний опис товару
					"""

					if analysis_mode == "Поглиблений опис":
						prompt += " Зроби опис максимально розгорнутим, додавши можливі матеріали та сфери застосування."

					response = client.models.generate_content(
						model='gemini-3.5-flash',
						contents=[image, prompt]
					)

					st.success("Товар успішно оброблено!")

					# Зберігаємо результат в історію сесії
					new_item = {
						"mode": analysis_mode,
						"description": response.text
					}
					st.session_state.catalog_items.append(new_item)

					# Структурований вивід поточного результату
					with st.container(border=True):
						st.markdown("#### 🏷️ Згенерована картка товару")
						st.write(response.text)

				except Exception as e:
					st.error(f"Сталася помилка під час аналізу: {e}")

# --- Вивід історії каталогу ---
if st.session_state.catalog_items:
	st.markdown("---")
	st.markdown("### 📚 Історія збережених позицій у каталозі")

	for idx, item in enumerate(reversed(st.session_state.catalog_items), 1):
		item_number = len(st.session_state.catalog_items) - idx + 1
		with st.expander(f"📦 Товар #{item_number} ({item['mode']})"):
			st.write(item["description"])
