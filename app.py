import os
import json
import csv
import time
from google import genai
from PIL import Image
import streamlit as st

st.set_page_config(page_title="Ritzfair AI Catalog", page_icon="🛍️", layout="centered")

# Завантаження конфігурації
@st.cache_data
def load_config():
	if os.path.exists("config.json"):
		with open("config.json", "r", encoding="utf-8") as f:
			return json.load(f)
	return {"client_name": "Ritzfair", "target_niche": "товари", "prompt": "Аналізуй товар", "csv_columns": ["source_file", "name"]}

config = load_config()

st.title(f"🛍️ {config.get('client_name', 'Ritzfair')} — AI Cataloging System")
st.markdown(f"**Ніша:** {config.get('target_niche', 'Загальна')}")
st.write("Завантажте зображення товарів нижче, щоб автоматично згенерувати каталог, SEO-описи та таблицю.")

uploaded_files = st.file_uploader("Виберіть або перетягніть фото товарів", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)

if uploaded_files:
	st.info(f"Знайдено зображень для обробки: {len(uploaded_files)}")

	if st.button("🚀 Запустити обробку каталогу"):
		client = genai.Client()
		catalog = []

		progress_bar = st.progress(0)
		status_text = st.empty()

		temp_dir = "temp_images"
		os.makedirs(temp_dir, exist_ok=True)

		for i, uploaded_file in enumerate(uploaded_files):
			status_text.text(f"Обробка файлу {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
			image_path = os.path.join(temp_dir, uploaded_file.name)

			with open(image_path, "wb") as f:
				f.write(uploaded_file.getbuffer())

			prompt = config.get("prompt")

			# Логіка повторних спроб (retries)
			success = False
			for attempt in range(1, 4):
				try:
					image = Image.open(image_path)
					response = client.models.generate_content(
						model="gemini-3.5-flash",
						contents=[image, prompt],
						config={"response_mime_type": "application/json"}
					)
					item_data = json.loads(response.text)
					item_data["source_file"] = uploaded_file.name
					catalog.append(item_data)
					success = True
					break
				except Exception as e:
					time.sleep(2)

			progress_bar.progress((i + 1) / len(uploaded_files))
			time.sleep(1)

		status_text.text("✅ Обробку завершено успішно!")

		# Зберігаємо результати
		json_output = "catalog.json"
		csv_output = "catalog.csv"

		with open(json_output, "w", encoding="utf-8") as f:
			json.dump(catalog, f, ensure_ascii=False, indent=4)

		csv_columns = config.get("csv_columns", ["source_file", "name"])
		with open(csv_output, "w", encoding="utf-8-sig", newline="") as f:
			writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction="ignore")
			writer.writeheader()
			for item in catalog:
				writer.writerow(item)

		st.success(f"Оброблено товарів: {len(catalog)}")

		# Кнопки для завантаження результатів у браузері
		col1, col2 = st.columns(2)
		with col1:
			with open(json_output, "rb") as f:
				st.download_button("📥 Завантажити JSON", f, file_name="catalog.json", mime="application/json")
		with col2:
			with open(csv_output, "rb") as f:
				st.download_button("📊 Завантажити CSV (Таблицю)", f, file_name="catalog.csv", mime="text/csv")

		# Відображення результату у вигляді таблиці на екрані
		st.subheader("Попередній перегляд даних:")
		st.json(catalog)
