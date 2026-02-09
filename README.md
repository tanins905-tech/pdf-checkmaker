# Генератор PDF из данных

## Установка

Перейдите в директорию проекта и установите зависимости:

```bash
cd C:\Users\Tanin\Desktop\PDF
pip install -r requirements.txt
```

**Windows:** WeasyPrint требует GTK3. Установите через [MSYS2](https://www.msys2.org/) или:
```bash
pip install weasyprint
# При ошибках: установите GTK3 для Windows
```

**macOS:** Обычно работает после `pip install weasyprint`.

## Запуск

```bash
python generate_pdf.py
```

## Структура проекта

- `data/` — CSV и JSON файлы с данными (должны содержать поле `invoice_id` или `id`)
- `templates/` — HTML-шаблоны (Jinja2)
- `output/` — сгенерированные PDF
