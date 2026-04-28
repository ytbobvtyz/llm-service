#!/usr/bin/env python3
import sys
import os
import traceback

# Добавляем корень проекта в путь Python
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print(f"=== Testing imports for project at {project_root} ===")

# Сначала проверяем структуру проекта
app_dir = os.path.join(project_root, 'app')
print(f"\napp directory exists: {os.path.exists(app_dir)}")
if os.path.exists(app_dir):
    print("Files in app directory:")
    for f in sorted(os.listdir(app_dir)):
        if f.endswith('.py'):
            print(f"  - {f}")

# Тестируем импорты
modules_to_test = [
    'app.models',
    'app.mcp_tools',
    'app.ollama_client',
]

print("\n=== Testing module imports ===")
for module_name in modules_to_test:
    try:
        print(f"\nTrying to import {module_name}...")
        module = __import__(module_name, fromlist=[''])
        print(f"✅ {module_name} imported successfully")
        
        # Проверяем наличие атрибутов в mcp_tools
        if module_name == 'app.mcp_tools':
            if hasattr(module, 'git_mcp'):
                print(f"  git_mcp found: {module.git_mcp}")
                print(f"  Type: {type(module.git_mcp)}")
            else:
                print(f"  ❌ git_mcp not found! Available attributes:")
                for attr in dir(module):
                    if not attr.startswith('_'):
                        print(f"    - {attr}")
        
        # Проверяем наличие атрибутов в ollama_client
        elif module_name == 'app.ollama_client':
            print(f"  Available methods in OllamaClient class:")
            from app.ollama_client import OllamaClient
            attrs = [a for a in dir(OllamaClient) if not a.startswith('_')]
            for attr in attrs:
                print(f"    - {attr}")
                
            # Проверяем наличие метода chat_with_commands
            if 'chat_with_commands' in attrs:
                print(f"  ✅ chat_with_commands method found")
            else:
                print(f"  ❌ chat_with_commands method NOT found!")
                
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        print(f"Error details:")
        exc_type, exc_value, exc_tb = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        for line in tb_lines[-3:]:
            print(f"  {line.strip()}")

print("\n=== Testing instantiation ===")
try:
    from app.ollama_client import OllamaClient
    client = OllamaClient()
    print(f"✅ OllamaClient instantiated: {client}")
except Exception as e:
    print(f"❌ Failed to instantiate OllamaClient: {e}")

print("\n=== All tests completed ===")