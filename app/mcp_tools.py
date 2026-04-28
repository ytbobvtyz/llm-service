#!/usr/bin/env python3
"""
MCP (Model Context Protocol) инструменты для работы с Git и проектом
"""

import os
import subprocess
from typing import Dict, List, Optional


class GitMCP:
    """MCP инструменты для работы с Git репозиторием"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
    
    def get_current_branch(self) -> Dict[str, str]:
        """Получить текущую git-ветку"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            return {
                "branch": branch if branch else "detached HEAD",
                "status": "success"
            }
        except subprocess.CalledProcessError as e:
            return {
                "branch": "unknown",
                "status": "error",
                "error": str(e)
            }
    
    def get_file_list(self, extension: Optional[str] = None) -> List[str]:
        """Получить список файлов в проекте"""
        files = []
        exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'data', 'static', 'ollama_data', '.kilo'}
        
        for root, dirs, filenames in os.walk(self.repo_path):
            # Исключаем ненужные директории
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for filename in filenames:
                if extension and not filename.endswith(extension):
                    continue
                if filename.endswith(('.py', '.md', '.yml', '.yaml', '.txt', '.html', '.css', '.js', '.json')):
                    rel_path = os.path.relpath(os.path.join(root, filename), self.repo_path)
                    files.append(rel_path)
        
        return sorted(files)
    
    def get_project_structure(self, max_depth: int = 3) -> str:
        """Получить древовидную структуру проекта"""
        structure = []
        exclude = {'.git', '__pycache__', 'venv', '.venv', 'data', 'static', 'ollama_data', '.kilo'}
        
        def walk_dir(path: str, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            
            items = sorted([i for i in os.listdir(path) if i not in exclude])
            
            for i, item in enumerate(items):
                item_path = os.path.join(path, item)
                is_last = i == len(items) - 1
                
                if os.path.isdir(item_path):
                    structure.append(f"{prefix}{'└── ' if is_last else '├── '}{item}/")
                    walk_dir(item_path, prefix + ("    " if is_last else "│   "), depth + 1)
                else:
                    if item.endswith(('.py', '.md', '.yml', '.yaml', '.html', '.css', '.js', '.json')):
                        structure.append(f"{prefix}{'└── ' if is_last else '├── '}{item}")
        
        walk_dir(self.repo_path)
        return "\n".join(structure) if structure else "Нет файлов"
    
    def get_readme_content(self) -> Optional[str]:
        """Прочитать README.md"""
        readme_paths = ["README.md", "docs/README.md", "README.txt"]
        
        for path in readme_paths:
            full_path = os.path.join(self.repo_path, path)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
        return None
    
    def get_diff(self) -> str:
        """Получить текущие изменения (uncommitted)"""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout if result.stdout else "Нет незакоммиченных изменений"
        except subprocess.CalledProcessError as e:
            return f"Ошибка: {e}"


# Создаём экземпляр для использования в API
git_mcp = GitMCP()