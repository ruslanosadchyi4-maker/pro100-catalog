import streamlit as st
from google import genai
from PIL import Image
import csv
import io

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
	st.markdown("### ⚙️ Налаштування генерації")

	# Вибір мови
	target_language = st.selectbox(
		"Мова опису",
		["Українська", "English", "Español"]
	)

	# Вибір стилю/тону
	tone_style = st.selectbox(
		"Стиль комунікації",
		[
			"Комерційний (стандарт)",
			"Емоційний (для Instagram / TikTok)",
			"Технічний / B2B (для складу)"
		]
	)

	st.markdown("---")
	st.markdown("### ℹ️ Про застосунок")
	st.info(
		"Цей інструмент створений для автоматичного аналізу, ціноутворення "
		"та класифікації товарів за допомогою штучного інтелекту Google Gemini."
	)

	st.markdown("---")
	st.caption("🚀 Версія: 1.5.0 (Pro)")
	st.caption("☁️ Розгорнуто на Streamlit Cloud")

# --- Головний екран ---
st.title("📦 Автоматизований каталог товарів")
st.markdown("Завантажте зображення товару, щоб ШІ згенерував картку, артикул, ціну та теги з урахуванням обраної мови й стилю.")

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
			with st.spinner("ШІ аналізує товар з урахуванням налаштувань..."):
				try:
					# Динамічний промпт з урахуванням мови та стилю
					prompt = f"""
					Проаналізуй це зображення товару для комерційного каталогу.
					ВАЖЛИВО: Увесь текст відповіді має бути написаний мовою: {target_language}.
					Стиль опису повинен відповідати вимозі: {tone_style}.

					Надай інформацію у такому форматі:
					- **Назва:** коротка та приваблива назва товару
					- **Категорія:** до якої категорії належить товар
					- **Артикул (SKU):** згенеруй унікальний логічний артикул (наприклад, PRD-XXXXX)
					- **Орієнтовна ціна:** запропонуй ринкову ціну в євро (€)
					- **Теги:** 3-5 ключових тегів через кому
					- **Опис:** комерційний опис товару відповідно до обраного стилю
					"""

					response = client.models.generate_content(
						model='gemini-3.5-flash',
						contents=[image, prompt]
					)

					st.success("Товар успішно оброблено!")

					# Зберігаємо результат в історію сесії
					new_item = {
						"mode": f"{target_language} | {tone_style}",
						"description": response.text
					}
					st.session_state.catalog_items.append(new_item)

					# Структурований вивід поточного результату
					with st.container(border=True):
						st.markdown("#### 🏷️ Згенерована картка товару")
						st.write(response.text)

				except Exception as e:
					st.error(f"Сталася помилка під час аналізу: {e}")

# --- Вивід історії каталогу та експорт ---
if st.session_state.catalog_items:
	st.markdown("---")

	col_title, col_btn = st.columns([2, 1])
	with col_title:
		st.markdown("### 📚 Історія збережених позицій у каталозі")
	with col_btn:
		csv_buffer = io.StringIO()
		writer = csv.writer(csv_buffer)
		writer.writerow(["ID", "Settings", "Content"])
		for idx, item in enumerate(st.session_state.catalog_items, 1):
			writer.writerow([idx, item["mode"], item["description"]])

		st.download_button(
			label="📥 Експортувати каталог (CSV)",
			data=csv_buffer.getvalue(),
			file_name="pro100_catalog.csv",
			mime="text/csv",
			type="secondary"
		)

for idx, item in enumerate(reversed(st.session_state.catalog_items), 1):
	item_number = len(st.session_state.catalog_items) - idx + 1
	with st.expander(f"📦 Товар #{item_number} ({item['mode']})"):
		st.write(item["description"])
