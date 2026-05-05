#!/usr/bin/env python3
"""
MCP (Model Context Protocol) инструменты для работы с файлами проекта
"""

import os
import re
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime
import fnmatch


class FileMCP:
    """MCP инструменты для работы с файлами проекта"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = os.path.abspath(project_root)
        self.backup_dir = os.path.join(self.project_root, ".file_mcp_backups")
        self._create_backup_dir()
    
    def _create_backup_dir(self):
        """Создаёт директорию для бэкапов"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)
    
    def _get_relative_path(self, absolute_path: str) -> str:
        """Преобразует абсолютный путь в относительный"""
        try:
            return os.path.relpath(absolute_path, self.project_root)
        except ValueError:
            return absolute_path
    
    def _is_safe_path(self, filepath: str) -> bool:
        """Проверяет, что файл находится внутри проекта"""
        try:
            abs_path = os.path.abspath(filepath)
            rel_path = os.path.relpath(abs_path, self.project_root)
            # Проверяем, что путь не выходит за пределы проекта
            return not rel_path.startswith('..') and not os.path.isabs(rel_path)
        except ValueError:
            return False
    
    def _backup_file(self, filepath: str) -> str:
        """Создаёт резервную копию файла"""
        if not os.path.exists(filepath):
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        backup_name = f"{filename}.backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        shutil.copy2(filepath, backup_path)
        return backup_path
    
    # ========== ЧТЕНИЕ ФАЙЛОВ ==========
    
    def read_file(self, filepath: str, max_lines: Optional[int] = None) -> Dict[str, Any]:
        """Прочитать содержимое файла"""
        if not self._is_safe_path(filepath):
            return {
                "success": False,
                "error": f"Путь находится вне проекта: {filepath}"
            }
        
        try:
            if not os.path.exists(filepath):
                return {
                    "success": False,
                    "error": f"Файл не существует: {filepath}"
                }
            
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            content = ''.join(lines)
            if max_lines and len(lines) > max_lines:
                content = ''.join(lines[:max_lines]) + f"\n... (показано {max_lines} из {len(lines)} строк)"
            
            return {
                "success": True,
                "content": content,
                "lines": len(lines),
                "path": self._get_relative_path(filepath)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка чтения файла: {str(e)}"
            }
    
    def list_files(self, pattern: str = "*", max_depth: int = 3) -> List[str]:
        """Список файлов проекта по шаблону"""
        files = []
        exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'data', 'static', 'ollama_data', '.kilo', '.file_mcp_backups'}
        
        for root, dirs, filenames in os.walk(self.project_root):
            # Исключаем ненужные директории
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            # Проверяем глубину
            rel_depth = root[len(self.project_root):].count(os.sep)
            if rel_depth > max_depth:
                continue
            
            for filename in filenames:
                if fnmatch.fnmatch(filename, pattern):
                    rel_path = os.path.relpath(os.path.join(root, filename), self.project_root)
                    files.append(rel_path)
        
        return sorted(files)
    
    # ========== ПОИСК ==========
    
    def search_in_files(self, query: str, file_pattern: str = "*.py", max_results: int = 20) -> List[Dict[str, Any]]:
        """Поиск текста в файлах проекта"""
        results = []
        files = self.list_files(file_pattern, max_depth=5)
        
        for file_path in files:
            if len(results) >= max_results:
                break
            
            full_path = os.path.join(self.project_root, file_path)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if query.lower() in content.lower():
                    # Находим строки с совпадением
                    lines = content.split('\n')
                    matches = []
                    for i, line in enumerate(lines, 1):
                        if query.lower() in line.lower():
                            matches.append({
                                "line": i,
                                "content": line.strip()[:100]
                            })
                    
                    results.append({
                        "file": file_path,
                        "matches": matches[:5],  # Ограничиваем количество строк
                        "match_count": len(matches)
                    })
            except Exception:
                continue
        
        return results
    
    def find_imports(self, module_name: str) -> List[Dict[str, Any]]:
        """Найти все места, где импортируется указанный модуль"""
        results = []
        files = self.list_files("*.py", max_depth=5)
        
        for file_path in files:
            full_path = os.path.join(self.project_root, file_path)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ищем импорты
                import_patterns = [
                    f"import {module_name}",
                    f"from {module_name} import",
                    f"import.*{module_name}.*as",
                    f"from.*{module_name}.*import"
                ]
                
                matches = []
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    if any(pattern in line_lower for pattern in import_patterns):
                        matches.append({
                            "line": i,
                            "content": line.strip()[:100]
                        })
                
                if matches:
                    results.append({
                        "file": file_path,
                        "imports": matches
                    })
            except Exception:
                continue
        
        return results
    
    # ========== ИЗМЕНЕНИЕ ФАЙЛОВ ==========
    
    def create_file(self, filepath: str, content: str, backup: bool = True) -> Dict[str, Any]:
        """Создать новый файл"""
        if not self._is_safe_path(filepath):
            return {
                "success": False,
                "error": f"Путь находится вне проекта: {filepath}"
            }
        
        try:
            # Проверяем, существует ли файл
            if os.path.exists(filepath):
                if backup:
                    self._backup_file(filepath)
            
            # Создаем директории, если нужно
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": self._get_relative_path(filepath),
                "size": len(content),
                "created": True if not os.path.exists(filepath) else False
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка создания файла: {str(e)}"
            }
    
    def update_file(self, filepath: str, new_content: str) -> Dict[str, Any]:
        """Обновить существующий файл с созданием бэкапа"""
        if not self._is_safe_path(filepath):
            return {
                "success": False,
                "error": f"Путь находится вне проекта: {filepath}"
            }
        
        try:
            if not os.path.exists(filepath):
                return {
                    "success": False,
                    "error": f"Файл не существует: {filepath}"
                }
            
            # Создаем бэкап
            backup_path = self._backup_file(filepath)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "path": self._get_relative_path(filepath),
                "backup": os.path.basename(backup_path) if backup_path else None,
                "size": len(new_content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка обновления файла: {str(e)}"
            }
    
    def append_to_file(self, filepath: str, content: str) -> Dict[str, Any]:
        """Добавить содержимое в конец файла"""
        if not self._is_safe_path(filepath):
            return {
                "success": False,
                "error": f"Путь находится вне проекта: {filepath}"
            }
        
        try:
            if not os.path.exists(filepath):
                # Если файл не существует, создаем его
                return self.create_file(filepath, content, backup=False)
            
            # Создаем бэкап
            backup_path = self._backup_file(filepath)
            
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": self._get_relative_path(filepath),
                "backup": os.path.basename(backup_path) if backup_path else None,
                "appended": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка добавления в файл: {str(e)}"
            }
    
    # ========== АНАЛИЗ ==========
    
    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Анализ файла: структура, импорты, функции, классы"""
        if not self._is_safe_path(filepath):
            return {
                "success": False,
                "error": f"Путь находится вне проекта: {filepath}"
            }
        
        try:
            if not os.path.exists(filepath):
                return {
                    "success": False,
                    "error": f"Файл не существует: {filepath}"
                }
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            analysis = {
                "path": self._get_relative_path(filepath),
                "lines": len(lines),
                "size_bytes": os.path.getsize(filepath),
                "imports": [],
                "functions": [],
                "classes": [],
                "file_type": os.path.splitext(filepath)[1].lower()
            }
            
            # Анализ для Python файлов
            if analysis["file_type"] == '.py':
                for i, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Импорты
                    if line_stripped.startswith(('import ', 'from ')):
                        analysis["imports"].append({
                            "line": i,
                            "content": line_stripped
                        })
                    
                    # Функции
                    elif line_stripped.startswith('def '):
                        func_name = line_stripped[4:].split('(')[0].strip()
                        analysis["functions"].append({
                            "line": i,
                            "name": func_name,
                            "signature": line_stripped
                        })
                    
                    # Классы
                    elif line_stripped.startswith('class '):
                        class_name = line_stripped[6:].split('(')[0].split(':')[0].strip()
                        analysis["classes"].append({
                            "line": i,
                            "name": class_name,
                            "signature": line_stripped
                        })
            
            # Анализ для Markdown файлов
            elif analysis["file_type"] == '.md':
                headers = []
                for i, line in enumerate(lines, 1):
                    if line.startswith('#'):
                        headers.append({
                            "line": i,
                            "level": len(line) - len(line.lstrip('#')),
                            "title": line.lstrip('#').strip()
                        })
                analysis["headers"] = headers
            
            return {
                "success": True,
                "analysis": analysis
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка анализа файла: {str(e)}"
            }


# Создаём экземпляр для использования в API
file_mcp = FileMCP()
