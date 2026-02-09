#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт генерации PDF-документов из CSV/JSON данных и HTML-шаблонов.
"""

import csv
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("Ошибка: требуется jinja2. Установите: pip install jinja2")
    sys.exit(1)

try:
    from weasyprint import HTML, CSS
except ImportError:
    print("Ошибка: требуется weasyprint. Установите: pip install weasyprint")
    sys.exit(1)

# Директории проекта
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"


def ensure_directories():
    """Создаёт необходимые директории, если их нет."""
    DATA_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def get_data_files():
    """Возвращает списки CSV и JSON файлов из директории data."""
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    json_files = sorted(DATA_DIR.glob("*.json"))
    return list(csv_files), list(json_files)


def get_templates():
    """Возвращает список HTML-шаблонов из директории templates."""
    return sorted(TEMPLATES_DIR.glob("*.html"))


def parse_csv(filepath):
    """Парсит CSV с помощью pandas (если доступен) или csv."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        if HAS_PANDAS:
            df = pd.read_csv(f)
            return df.to_dict(orient="records")
        reader = csv.DictReader(f)
        return list(reader)


def parse_json(filepath):
    """Парсит JSON стандартной библиотекой."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Поддержка разных структур: список или {"invoices": [...]}
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("invoices", "data", "records", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return [data]
    return []


def load_data(filepath):
    """Загружает данные из CSV или JSON файла."""
    suffix = filepath.suffix.lower()
    if suffix == ".csv":
        return parse_csv(filepath)
    if suffix == ".json":
        return parse_json(filepath)
    raise ValueError(f"Неподдерживаемый формат: {suffix}")


def extract_invoice_id(item):
    """Извлекает invoice id из записи (поддержка разных имён полей)."""
    for key in ("invoice_id", "invoiceid", "id", "invoiceId", "invoice"):
        if isinstance(item, dict) and key in item:
            return str(item[key])
    return None


def get_invoices_map(data):
    """Возвращает словарь {invoice_id: item} и список id для выбора."""
    invoices = {}
    for i, item in enumerate(data):
        inv_id = extract_invoice_id(item)
        if inv_id and inv_id not in invoices:
            invoices[inv_id] = item
        elif not inv_id:
            # Нет invoice_id — используем индекс и описание (product, name и т.д.)
            idx = str(i + 1)
            if isinstance(item, dict):
                desc = item.get("product") or item.get("name") or item.get("title") or ""
                label = f"{idx} — {desc}" if desc else idx
            else:
                label = idx
            invoices[label] = item
    return invoices


def open_pdf(filepath):
    """Открывает PDF в системной программе (Windows/macOS/Linux)."""
    path = str(filepath.resolve())
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
    except Exception as e:
        print(f"Не удалось открыть PDF автоматически: {e}")
        print(f"Файл сохранён: {path}")


def render_pdf(template_path, data, output_path):
    """Генерирует PDF из HTML-шаблона с подстановкой данных."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template(template_path.name)
    html_content = template.render(**data)

    # CSS для поддержки кириллицы (DejaVu Sans)
    css_custom = CSS(string="""
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: "DejaVu Sans", "Liberation Sans", sans-serif;
            font-size: 12px;
        }
    """)

    html_obj = HTML(string=html_content, base_url=str(TEMPLATES_DIR))
    html_obj.write_pdf(output_path, stylesheets=[css_custom])


def select_from_list(items, prompt, item_label="элемент"):
    """Интерактивный выбор элемента из списка. Возвращает индекс или None."""
    if not items:
        return None
    print(f"\n{prompt}")
    print("-" * 40)
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    print("-" * 40)
    while True:
        try:
            choice = input(f"Введите номер (1-{len(items)}) или 0 для выхода: ").strip()
            num = int(choice)
            if num == 0:
                return None
            if 1 <= num <= len(items):
                return num - 1
        except ValueError:
            pass
        print("Неверный ввод. Попробуйте снова.")


def main():
    ensure_directories()

    csv_files, json_files = get_data_files()
    data_files = csv_files + json_files
    templates = get_templates()

    if not data_files:
        print("Ошибка: в директории /data нет CSV или JSON файлов.")
        return 1

    if not templates:
        print("Ошибка: в директории /templates нет HTML-шаблонов.")
        return 1

    # Вывод списка файлов и шаблонов
    print("\n" + "=" * 50)
    print("  Генератор PDF из данных и шаблонов")
    print("=" * 50)
    print("\n  Доступные файлы с данными:")
    print("-" * 40)
    for i, f in enumerate(data_files, 1):
        print(f"  {i}. {f.name}")
    print("\n  Доступные HTML-шаблоны:")
    print("-" * 40)
    for i, t in enumerate(templates, 1):
        print(f"  {i}. {t.name}")
    print("=" * 50)

    # Выбор файла данных
    data_idx = select_from_list(
        [f.name for f in data_files],
        "Выберите файл с данными:",
        "файл"
    )
    if data_idx is None:
        print("Выход.")
        return 0

    # Выбор шаблона
    template_idx = select_from_list(
        [t.name for t in templates],
        "Выберите HTML-шаблон:",
        "шаблон"
    )
    if template_idx is None:
        print("Выход.")
        return 0

    data_file = data_files[data_idx]
    template_file = templates[template_idx]

    # Загрузка данных
    try:
        data = load_data(data_file)
    except Exception as e:
        print(f"Ошибка чтения файла {data_file.name}: {e}")
        return 1

    if not data:
        print("Файл данных пуст или не содержит записей.")
        return 1

    # Построение карты чеков по invoice id
    invoices_map = get_invoices_map(data)
    if not invoices_map:
        print("Не найдено записей с полем invoice_id (или id, invoiceId).")
        return 1

    invoice_ids = sorted(invoices_map.keys())
    inv_idx = select_from_list(
        invoice_ids,
        "Выберите invoice id (чек) для генерации PDF:",
        "чек"
    )
    if inv_idx is None:
        print("Выход.")
        return 0

    invoice_id = invoice_ids[inv_idx]
    invoice_data = invoices_map[invoice_id]

    # Преобразуем данные для шаблона: flat dict
    if isinstance(invoice_data, dict):
        template_data = {k: v for k, v in invoice_data.items()}
    else:
        template_data = {"data": invoice_data}

    # Добавляем invoice_id на случай, если его не было
    template_data.setdefault("invoice_id", invoice_id)

    # Для универсального шаблона: список пар (ключ, значение)
    if isinstance(invoice_data, dict):
        template_data["_invoice_items"] = [(k, v) for k, v in invoice_data.items()]

    # Генерация PDF
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in invoice_id)
    output_filename = f"invoice_{safe_id}.pdf"
    output_path = OUTPUT_DIR / output_filename

    try:
        render_pdf(template_file, template_data, output_path)
        print(f"\n  PDF успешно создан: {output_path}")
        open_pdf(output_path)
        return 0
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
