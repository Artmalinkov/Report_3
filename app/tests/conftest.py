# app/tests/conftest.py
"""
Настройка сбора тестов pytest
"""

# Эти файлы — ручные диагностические скрипты (запускаются напрямую,
# python app/tests/test_fns_api.py), а не автотесты: они делают живые
# запросы к платным/лимитированным внешним API (ФНС, IO_NET) и не должны
# выполняться при каждом запуске pytest.
collect_ignore = [
    "test_fns_api.py",
    "test_ionet_api.py",
    "test_integration.py",
    "test_report_generator.py",
]
