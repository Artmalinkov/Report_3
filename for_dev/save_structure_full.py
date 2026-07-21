"""
Показать структуру проекта и содержание файлов
"""
import sys
from pathlib import Path
from datetime import datetime


def read_file_content(file_path):
    """Пытается прочитать файл в разных кодировках"""
    encodings = [
        'utf-8-sig',  # UTF-8 с BOM
        'utf-8',  # Стандартный UTF-8
        'cp1251',  # Windows Cyrillic
        'cp866',  # DOS Cyrillic
        'latin-1',  # Западноевропейская
        'utf-16-le',  # UTF-16 Little Endian
        'utf-16-be',  # UTF-16 Big Endian
        'koi8-r',  # KOI8-R
        'iso-8859-5',  # ISO Cyrillic
        'mac-cyrillic',  # Mac Cyrillic
    ]

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                # Удаляем BOM и нулевые символы
                content = content.replace('\ufeff', '').replace('\x00', '')
                # Удаляем лишние пробелы между символами (для UTF-16 файлов)
                if encoding in ['utf-16-le', 'utf-16-be']:
                    # Проверяем, не разбиты ли символы пробелами
                    import re
                    # Если строка содержит пробелы между каждым символом
                    if re.search(r'[a-zA-Z]\s[a-zA-Z]', content[:100]):
                        # Убираем пробелы между символами
                        content = re.sub(r'(?<=[a-zA-Z0-9])\s(?=[a-zA-Z0-9=._-])', '', content)
                return content, encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception:
            continue

    return None, None


def print_structure(directory, prefix="", exclude_dirs=None, exclude_files=None):
    """Вывод структуры папок и файлов"""
    if exclude_dirs is None:
        exclude_dirs = [".venv", "__pycache__", ".git", ".idea", "reports", "logs", ".pytest_cache", "structure_full"]

    if exclude_files is None:
        exclude_files = [".env", "*.pyc", "*.pyo", "MAIN_PROMT.md", "requirements.txt"]

    items = sorted(Path(directory).iterdir())

    # Фильтруем папки и файлы
    filtered_items = []
    for item in items:
        # Проверяем исключения для папок
        if item.is_dir() and any(ex in str(item) for ex in exclude_dirs):
            continue

        # Проверяем исключения для файлов
        if item.is_file():
            # Проверяем по имени файла
            if item.name in exclude_files:
                continue
            # Проверяем по расширению
            if any(item.name.endswith(ext) for ext in exclude_files if ext.startswith('*')):
                continue

        filtered_items.append(item)

    items = filtered_items

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "

        if item.is_dir():
            print(f"{prefix}{connector}📁 {item.name}/")
            extension = "    " if is_last else "│   "
            print_structure(item, prefix + extension, exclude_dirs, exclude_files)
        else:
            print(f"{prefix}{connector}📄 {item.name}")

            # Показываем содержимое файла
            # Добавляем .txt и любые текстовые файлы
            text_extensions = [
                '.py', '.md', '.txt', '.html', '.htm',
                '.yml', '.yaml', '.json', '.toml', '.xml',
                '.gitignore', '.dockerignore', '.env.example',
                '.csv', '.log', '.ini', '.cfg', '.conf',
                '.cfg', '.conf', '.cnf'
            ]

            if item.suffix in text_extensions or item.name.startswith('.'):
                print(f"{prefix}    📝 Содержимое {item.name}:")
                print(f"{prefix}    {'─' * 40}")
                try:
                    # Пробуем разные кодировки
                    for encoding in ['utf-8', 'cp1251', 'latin-1']:
                        try:
                            with open(item, 'r', encoding=encoding) as f:
                                content = f.read()
                                # Обрезаем слишком большие файлы
                                lines = content.splitlines()
                                max_lines = 500  # Максимум строк для отображения
                                if len(lines) > max_lines:
                                    for line in lines[:max_lines]:
                                        print(f"{prefix}    │ {line}")
                                    print(f"{prefix}    │ ... (ещё {len(lines) - max_lines} строк)")
                                else:
                                    for line in lines:
                                        print(f"{prefix}    │ {line}")
                            break  # Если успешно прочитали, выходим из цикла
                        except UnicodeDecodeError:
                            continue
                    else:
                        print(f"{prefix}    │ ⚠️ Не удалось прочитать файл (возможно бинарный)")
                except Exception as e:
                    print(f"{prefix}    │ ❌ Ошибка чтения: {e}")
                print()


if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent

    # Создаем папку для сохранения
    output_dir = root_dir / "for_dev" / "structure_full"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        sys.stdout = f
        print("📁 ПОЛНАЯ СТРУКТУРА ПРОЕКТА Report_3")
        print("=" * 70)
        print(f"Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("=" * 70)
        print()
        print_structure(root_dir)
        sys.stdout = sys.__stdout__

    print(f"✅ Структура сохранена в файл: {output_file}")