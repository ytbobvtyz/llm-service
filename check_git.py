#!/usr/bin/env python3
import subprocess
import sys

try:
    print("Проверка git...")
    result = subprocess.run(["git", "branch", "--show-current"], 
                          capture_output=True, text=True, check=True)
    print(f"Git команда выполнена успешно")
    print(f"Текущая ветка: {result.stdout.strip()}")
    return_code = 0
except subprocess.CalledProcessError as e:
    print(f"Git команда провалилась: {e}")
    return_code = e.returncode
except FileNotFoundError:
    print("Git не найден")
    return_code = 1

sys.exit(return_code)