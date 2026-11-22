from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import json
import re
import time
from typing import Any
from google import genai
from google.genai import types
import pandas as pd
from PIL import Image
import streamlit as st

# Налаштування сторінки
st.set_page_config(
	page_title="PRO100 Catalog", page_icon="🛍️", layout="wide"
)

# Безпечне отримання API-ключа з секретів Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
	st.error(
		"⚠️ Не знайдено `GEMINI_API_KEY` у Streamlit Secrets. Будь ласка,"
		" додайте його в налаштуваннях хмари."
)
st.stop()

# Ініціалізація клієнта Gemini
client = genai.Client(api_key=api_key)

# Назви колонок у фінальному CSV (окремий стовпець під кожне поле)
CSV_COLUMNS = [
	"ID",
	"Source File",
	"Title",
	"Category",
	"SKU",
	"Estimated Price (EUR)",
	"Tags",
	"Description",
	"Settings",
]

# Ініціалізація сховища у st.session_state
if "catalog_items" not in st.session_state:
	st.session_state.catalog_items = []


def clean_cell(value: Any) -> str:
	"""Прибирає зайві переноси рядків та пробіли, щоб таблиця не ламалась."""
	if value is None:
		return ""
	if isinstance(value, list):
		text = ", ".join(str(x).strip() for x in value if str(x).strip())
	else:
		text = str(value)
	text = re.sub(r"[\r\n]+", " ", text)
	text = re.sub(r"\s{2,}", " ", text).strip()
	return text


def optimize_image_bytes(
	uploaded_file, max_side: int = 1400, quality: int = 85
) -> tuple[str, bytes]:
	"""Зменшує розмір зображення та конвертує у компактний JPEG для швидкої передачі."""
	uploaded_file.seek(0)
	img = Image.open(uploaded_file).convert("RGB")
	width, height = img.size
	longest_side = max(width, height)

	if longest_side > max_side:
		scale = max_side / longest_side
		new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
		img = img.resize(new_size, Image.Resampling.LANCZOS)

	buf = BytesIO()
	img.save(buf, format="JPEG", quality=quality, optimize=True)
	return uploaded_file.name, buf.getvalue()


def make_batches(items: list[Any], batch_size: int) -> list[list[Any]]:
	return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def parse_json_response(raw_text: str) -> list[dict[str, Any]]:
	"""Безпечно парсить JSON-відповідь навіть якщо модель додала зайві символи."""
	cleaned = raw_text.strip()
	if cleaned.startswith("```"):
		cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
		cleaned = re.sub(r"\s*```$", "", cleaned)

	parsed = json.loads(cleaned)
	if isinstance(parsed, dict):
		if "items" in parsed and isinstance(parsed["items"], list):
			return parsed["items"]
		return [parsed]
	if isinstance(parsed, list):
		return parsed
	return []


def analyze_photo_batch(
	batch_files: list[tuple[str, bytes]],
	target_language: str,
	tone_style: str,
	max_retries: int = 3,
) -> list[dict[str, Any]]:
	"""Аналізує батч фотографій за один API-запит і повертає список словників."""
	file_names = [name for name, _ in batch_files]
	contents: list[Any] = []

	for fname, img_bytes in batch_files:
		contents.append(f"Зображення з файлу: {fname}")
		contents.append(
		types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
	)

	prompt = f"""
Ти — експерт з каталогізації товарів для e-commerce та Shopify.
Проаналізуй УСІ надані зображення ({', '.join(file_names)}) і поверни JSON-масив об'єктів — по одному об'єкту на кожне зображення у вказаному порядку.

ВАЖЛИВО:
- Усі текстові значення (title, category, tags, description) мають бути написані мовою: {target_language}.
- Стиль опису має відповідати вимозі: {tone_style}.
- Поверни ВИКЛЮЧНО валідний JSON-масив без markdown-блоків і зайвого тексту.

Для кожного зображення заповни поля:
- "source_file": точна назва файлу зі списку вище
- "title": коротка, чітка та приваблива назва товару
- "category": основна категорія товару
- "sku": логічний артикул (наприклад, PRD-10482)
- "estimated_price_eur": орієнтовна ринкова ціна числом або діапазоном у євро, наприклад "29.00" або "25.00 - 35.00"
- "tags": 3–5 ключових тегів через кому
- "description": чистий структурований опис товару в один абзац без переносів рядка
"""
	contents.append(prompt)

	last_error: Exception | None = None
	for attempt in range(1, max_retries + 1):
		try:
			response = client.models.generate_content(
				model="gemini-3.5-flash",
				contents=contents,
				config=types.GenerateContentConfig(
					response_mime_type="application/json",
					temperature=0.2,
				),
			)
			rows = parse_json_response(response.text or "[]")

			normalized_batch: list[dict[str, Any]] = []
			for idx, fname in enumerate(file_names):
				row = rows[idx] if idx < len(rows) and isinstance(rows[idx], dict) else {}
				normalized_batch.append({
					"Source File": clean_cell(row.get("source_file") or fname),
					"Title": clean_cell(row.get("title") or fname),
					"Category": clean_cell(row.get("category") or "General"),
					"SKU": clean_cell(row.get("sku") or f"PRD-{idx + 1:05d}"),
					"Estimated Price (EUR)": clean_cell(
						row.get("estimated_price_eur") or ""
					),
					"Tags": clean_cell(row.get("tags") or ""),
					"Description": clean_cell(row.get("description") or ""),
					"Settings": f"{target_language} | {tone_style}",
				})
			return normalized_batch

		except Exception as exc:
			last_error = exc
			if attempt < max_retries:
				time.sleep(1.5 * attempt)

	# Якщо батч не пройшов після всіх спроб — фіксуємо помилку без падіння всієї програми
	return [
		{
			"Source File": clean_cell(fname),
			"Title": "Помилка обробки",
			"Category": "",
			"SKU": "",
			"Estimated Price (EUR)": "",
			"Tags": "",
			"Description": clean_cell(f"Не вдалося обробити фото: {last_error}"),
			"Settings": f"{target_language} | {tone_style}",
		}
		for fname in file_names
	]


def build_catalog_dataframe(items: list[dict[str, Any]]) -> pd.DataFrame:
	"""Формує акуратний DataFrame з чітким порядком колонок."""
	if not items:
		return pd.DataFrame(columns=CSV_COLUMNS)

	prepared_rows = []
	for idx, item in enumerate(items, start=1):
		row = {"ID": idx}
		for col in CSV_COLUMNS:
			if col == "ID":
				continue
			row[col] = clean_cell(item.get(col, ""))
		prepared_rows.append(row)

	df = pd.DataFrame(prepared_rows, columns=CSV_COLUMNS)
	return df


# --- Бокова панель (Sidebar) ---
with st.sidebar:
	st.title("🛍️ PRO100 Catalog")
	st.markdown("### ⚙️ Налаштування генерації")

	target_language = st.selectbox(
		"Мова опису", ["Українська", "English", "Español"]
	)

	tone_style = st.selectbox(
		"Стиль комунікації",
		[
			"Комерційний (стандарт)",
			"Емоційний (для Instagram / TikTok)",
			"Технічний / B2B (для складу)",
		],
	)

	st.markdown("### ⚡ Швидкість і батчі")
	batch_size = st.slider(
		"Фото в одному запиті (батч)",
		min_value=1,
		max_value=8,
		value=5,
		help="Більший батч зменшує кількість запитів до API та прискорює обробку масиву.",
	)
	max_workers = st.slider(
		"Паралельних потоків",
		min_value=1,
		max_value=4,
		value=2,
		help="Кількість батчів, які обробляються одночасно.",
	)

	st.markdown("---")
	if st.button("🗑️ Очистити історію каталогу", use_container_width=True):
		st.session_state.catalog_items = []
		st.rerun()

	st.markdown("---")
	st.markdown("### ℹ️ Про застосунок")
	st.info(
		"Пакетний аналіз товарів через Gemini Vision з експортом у чисто"
		" структурований CSV для каталогу та Shopify."
	)

	st.markdown("---")
	st.caption("🚀 Версія: 2.0.0 (Batch & Clean CSV)")
	st.caption("☁️ Розгорнуто на Streamlit Cloud")

# --- Головний екран ---
st.title("📦 Автоматизований каталог товарів")
st.markdown(
	"Завантажте **одне або одразу декілька зображень товарів** — ШІ обробить"
	" їх батчами та сформує акуратну таблицю з окремими стовпцями під кожне"
	" поле."
)

uploaded_files = st.file_uploader(
	"Виберіть одне або кілька зображень товарів",
	type=["jpg", "jpeg", "png", "webp"],
	accept_multiple_files=True,
)

if uploaded_files:
	st.markdown(f"#### 🖼️ Обрано файлів: **{len(uploaded_files)}**")

	# Компактне прев'ю завантажених фото
	preview_cols = st.columns(min(len(uploaded_files), 5))
	for idx, f in enumerate(uploaded_files[:10]):
		with preview_cols[idx % len(preview_cols)]:
			st.image(f, caption=f.name, use_container_width=True)
	if len(uploaded_files) > 10:
		st.caption(
			f"...та ще {len(uploaded_files) - 10} фото (усі будуть включені в"
			" обробку)."
		)

	if st.button(
		f"🚀 Запустити пакетний аналіз ({len(uploaded_files)} фото)",
		type="primary",
	):
		start_time = time.time()
		progress_bar = st.progress(0)
		status_text = st.empty()

		try:
			status_text.info("Оптимізую зображення та формую батчі...")
			optimized_files = [optimize_image_bytes(f) for f in uploaded_files]
			batches = make_batches(optimized_files, batch_size=batch_size)

			# Зберігаємо порядок батчів, щоб результати йшли послідовно
			batch_results: dict[int, list[dict[str, Any]]] = {}
			completed_batches = 0
			total_batches = len(batches)

			with ThreadPoolExecutor(
				max_workers=min(max_workers, total_batches)
			) as executor:
				future_to_idx = {
				executor.submit(
					analyze_photo_batch, batch, target_language, tone_style
				): b_idx
				for b_idx, batch in enumerate(batches)
			}

			for future in as_completed(future_to_idx):
				b_idx = future_to_idx[future]
				batch_results[b_idx] = future.result()
				completed_batches += 1
				progress_bar.progress(completed_batches / total_batches)
				status_text.info(
					f"Оброблено батчів: {completed_batches} з {total_batches}..."
				)

			added_items: list[dict[str, Any]] = []
			for b_idx in range(total_batches):
				added_items.extend(batch_results.get(b_idx, []))

			st.session_state.catalog_items.extend(added_items)
			elapsed = time.time() - start_time

			status_text.empty()
			progress_bar.empty()
			st.success(
				f"✅ Готово! Оброблено {len(added_items)} товарів за {elapsed:.1f} сек."
			)

		except Exception as e:
			status_text.empty()
			progress_bar.empty()
			st.error(f"Сталася помилка під час пакетного аналізу: {e}")

	# --- Вивід таблиці каталогу та експорт у CSV ---
	if st.session_state.catalog_items:
		st.markdown("---")
		df_catalog = build_catalog_dataframe(st.session_state.catalog_items)
		csv_bytes = df_catalog.to_csv(index=False, encoding="utf-8-sig").encode(
			"utf-8-sig"
		)

		col_title, col_btn = st.columns([3, 1])
		with col_title:
			st.markdown(
				f"### 📚 Таблиця каталогу ({len(df_catalog)} позицій)"
			)
		with col_btn:
			st.download_button(
				label="📥 Завантажити чистий CSV",
				data=csv_bytes,
				file_name="pro100_catalog_clean.csv",
				mime="text/csv",
				type="secondary",
				use_container_width=True,
			)

	# Професійний табличний перегляд перед завантаженням
	st.dataframe(df_catalog, use_container_width=True, hide_index=True)

	# Детальний перегляд кожної картки за потреби
	with st.expander("🔍 Детальний перегляд карток по позиціях"):
		for _, row in df_catalog.iterrows():
			st.markdown(f"**#{row['ID']} — {row['Title']}** (`{row['SKU']}`)")
			st.caption(
				f"Файл: {row['Source File']} | Категорія: {row['Category']} | Ціна:"
				f" €{row['Estimated Price (EUR)']} | {row['Settings']}"
			)
			if row["Tags"]:
				st.write(f"**Теги:** {row['Tags']}")
			if row["Description"]:
				st.write(row["Description"])
			st.divider()
