"""
Показать структуру проекта и содержание файлов
"""
import sys
from pathlib import Path
from datetime import datetime


def print_structure(directory, prefix="", exclude_dirs=None, exclude_files=None):
    """Вывод структуры папок и файлов"""
    if exclude_dirs is None:
        exclude_dirs = [".venv", "__pycache__", ".git", ".idea", "reports", "logs", ".pytest_cache", "structure_full"]

    if exclude_files is None:
        exclude_files = [".env", "*.pyc", "*.pyo", "MAIN_PROMT.md"]

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
            if item.suffix in ['.py', '.md', '.txt', '.html', '.yml', '.yaml', '.json', '.toml', '.gitignore',
                               '.dockerignore']:
                print(f"{prefix}    📝 Содержимое {item.name}:")
                print(f"{prefix}    {'─' * 40}")
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Добавляем отступы к каждой строке
                        for line in content.splitlines():
                            print(f"{prefix}    │ {line}")
                except UnicodeDecodeError:
                    print(f"{prefix}    │ ⚠️ Бинарный файл (не отображается)")
                except Exception as e:
                    print(f"{prefix}    │ ❌ Ошибка чтения: {e}")
                print()


if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent

    # Создаем папку для сохранения
    output_dir = root_dir / "for_dev" /"structure_full"
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