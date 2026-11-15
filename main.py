import os
import json
import csv
import shutil
import time
from google import genai
from PIL import Image

def load_config(config_path: str = "config.json"):
	if not os.path.exists(config_path):
		print(f"⚠️ Файл конфігурації {config_path} не знайдено. Перевірте наявність.")
		return None
	with open(config_path, "r", encoding="utf-8") as f:
		return json.load(f)

def process_folder(input_folder: str = "images", json_output: str = "catalog.json", csv_output: str = "catalog.csv"):
	# Завантажуємо налаштування клієнта з конфігу
	config = load_config()
	if not config:
		return

	print(f"🚀 Запуск системи для клієнта/проєкту: {config.get('client_name', 'Невідомо')}")
	print(f"🎯 Ніша: {config.get('target_niche', 'Загальна')}\n")

	if not os.path.exists(input_folder):
		print(f"Папку {input_folder} не знайдено.")
		return

	processed_folder = os.path.join(input_folder, "processed")
	error_folder = os.path.join(input_folder, "errors")
	os.makedirs(processed_folder, exist_ok=True)
	os.makedirs(error_folder, exist_ok=True)

	client = genai.Client()
	supported_extensions = (".jpg", ".jpeg", ".png", ".webp")

	files = [f for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f)) and f.lower().endswith(supported_extensions)]

	if not files:
		print(f"У папці {input_folder} немає нових зображень для обробки.")
		return

	print(f"Знайдено зображень для обробки: {len(files)}", flush=True)
	catalog = []

	# Беремо промпт безпосередньо з конфігурації
	prompt = config.get("prompt")
	csv_columns = config.get("csv_columns", ["source_file", "name"])

	for index, filename in enumerate(files, start=1):
		image_path = os.path.join(input_folder, filename)
		print(f"\n[{index}/{len(files)}] Обробка файлу: {filename}...", flush=True)

		max_retries = 3
		success = False

		for attempt in range(1, max_retries + 1):
			try:
				image = Image.open(image_path)
				response = client.models.generate_content(
				model="gemini-3.5-flash",
				contents=[image, prompt],
				config={
					"response_mime_type": "application/json"
				}
			)

				item_data = json.loads(response.text)
				item_data["source_file"] = filename
				catalog.append(item_data)
				print(f" ✅ Успішно: {item_data.get('name', 'Без назви')}", flush=True)

				shutil.move(image_path, os.path.join(processed_folder, filename))
				success = True
				break

			except Exception as e:
				print(f" ⚠️ Спроба {attempt}/{max_retries} не вдалася: {e}", flush=True)
				if attempt < max_retries:
					print(f" ⏳ Чекаємо 3 секунди перед повтором...", flush=True)
					time.sleep(3)
				else:
					print(f" ❌ ПОМИЛКА: Не вдалося обробити {filename} після {max_retries} спроб.", flush=True)
					try:
						shutil.move(image_path, os.path.join(error_folder, filename))
					except Exception:
						pass

	time.sleep(2)

	# 1. Зберігаємо у JSON
	with open(json_output, "w", encoding="utf-8") as f:
		json.dump(catalog, f, ensure_ascii=False, indent=4)

	# 2. Зберігаємо у CSV згідно з колонками в конфігу
	if catalog:
		with open(csv_output, "w", encoding="utf-8-sig", newline="") as f:
			writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction="ignore")
			writer.writeheader()
			for item in catalog:
				writer.writerow(item)

	print(f"\n🎉 Готово! Успішно опрацьовано {len(catalog)} з {len(files)} файлів.", flush=True)
	print(f"📂 Результати збережено у {json_output} та {csv_output}.")
	print(f"📁 Опрацьовані фото перенесено в {processed_folder}/")

if __name__ == "__main__":
	process_folder()

