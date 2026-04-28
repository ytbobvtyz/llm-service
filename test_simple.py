#!/usr/bin/env python3
import sys
import os

# Добавляем корень проекта в путь Python
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Files in app directory:")
for f in os.listdir(os.path.join(project_root, 'app')):
    if f.endswith('.py'):
        print(f"  - {f}")

try:
    print("\n1. Testing imports...")
    import app.models
    print(f"✅ app.models imported: {app.models}")
    
    import app.mcp_tools
    print(f"✅ app.mcp_tools imported: {app.mcp_tools}")
    print(f"   git_mcp: {app.mcp_tools.git_mcp}")
    
    import app.ollama_client
    print(f"✅ app.ollama_client imported: {app.ollama_client}")
    
    # Test instantiation
    from app.ollama_client import OllamaClient
    client = OllamaClient()
    print(f"✅ OllamaClient instantiated: {client}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Test complete")