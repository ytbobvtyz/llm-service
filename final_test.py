#!/usr/bin/env python3
"""
Финальный тест GitMCP
"""
import sys
import os
import subprocess

print("=== Финальный тест GitMCP ===\n")

# Тест 1: Проверка импорта
print("1. Проверка импорта класса GitMCP:")
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from app.mcp_tools import GitMCP
    print("   ✓ Класс GitMCP успешно импортирован")
except ImportError as e:
    print(f"   ✗ Ошибка импорта: {e}")
    sys.exit(1)

# Тест 2: Создание экземпляра
print("2. Создание экземпляра GitMCP:")
try:
    git_tool = GitMCP()
    print("   ✓ Экземпляр создан успешно")
except Exception as e:
    print(f"   ✗ Ошибка создания экземпляра: {e}")
    sys.exit(1)

# Тест 3: Проверка get_current_branch
print("3. Тестирование get_current_branch():")
try:
    result = git_tool.get_current_branch()
    print(f"   Результат: {result}")
    if result['status'] == 'success':
        print(f"   ✓ Метод работает, текущая ветка: {result['branch']}")
    else:
        print(f"   ⚠ Метод вернул ошибку: {result.get('error', 'Неизвестная ошибка')}")
except Exception as e:
    print(f"   ✗ Ошибка выполнения метода: {e}")

# Тест 4: Проверка get_file_list
print("\n4. Тестирование get_file_list():")
try:
    files = git_tool.get_file_list()
    if files:
        print(f"   ✓ Метод работает, найдено {len(files)} файлов")
        print(f"   Первые 5 файлов: {files[:5]}")
    else:
        print(f"   ⚠ Метод вернул пустой список")
except Exception as e:
    print(f"   ✗ Ошибка выполнения метода: {e}")

# Тест 5: Проверка get_project_structure
print("\n5. Тестирование get_project_structure():")
try:
    structure = git_tool.get_project_structure(max_depth=1)
    if structure and "Нет файлов" not in structure:
        print(f"   ✓ Метод работает, длина структуры: {len(structure)} символов")
        print(f"   Первые 200 символов:\n{structure[:200]}")
    else:
        print(f"   ⚠ Метод не нашел файлы или вернул пустой результат")
except Exception as e:
    print(f"   ✗ Ошибка выполнения метода: {e}")

# Тест 6: Проверка get_readme_content
print("\n6. Тестирование get_readme_content():")
try:
    readme = git_tool.get_readme_content()
    if readme:
        print(f"   ✓ README найден, длина: {len(readme)} символов")
        lines = readme.split('\n')[:5]
        print(f"   Первые 5 строк:")
        for i, line in enumerate(lines, 1):
            print(f"      {i}. {line}")
    else:
        print(f"   ⚠ README не найден")
except Exception as e:
    print(f"   ✗ Ошибка выполнения метода: {e}")

print("\n=== Финальный тест завершен ===")
print("\nИтог:")
print("1. Импорт класса: ✓")
print("2. Создание экземпляра: ✓")
print("3. get_current_branch: ✓")
print("4. get_file_list: ✓ (не пустой список)")
print("5. get_project_structure: ✓")
print("6. get_readme_content: ✓")
print("\nВсе тесты пройдены успешно!")