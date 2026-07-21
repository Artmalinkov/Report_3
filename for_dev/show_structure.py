# for_dev/show_structure.py
'''
Показать структуру проекта
'''
import os
from pathlib import Path


def print_structure(directory, prefix="", exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = [".venv", "__pycache__", ".git", ".idea", "reports", "logs", ".pytest_cache"]

    items = sorted(Path(directory).iterdir())
    items = [item for item in items if not any(ex in str(item) for ex in exclude_dirs)]

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "

        if item.is_dir():
            print(f"{prefix}{connector}{item.name}/")
            extension = "    " if is_last else "│   "
            print_structure(item, prefix + extension, exclude_dirs)
        else:
            print(f"{prefix}{connector}{item.name}")


if __name__ == "__main__":
    print("📁 Структура проекта Report_3:")
    print(".")
    print_structure("..")