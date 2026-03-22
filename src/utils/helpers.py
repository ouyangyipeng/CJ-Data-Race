# -*- coding: utf-8 -*-
"""
工具函数
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional


def find_cangjie_files(project_path: str) -> List[str]:
    """查找仓颉源文件"""
    cj_files = []
    project_dir = Path(project_path)
    
    for pattern in ['**/*.cj', '**/*.cangjie']:
        cj_files.extend(str(f) for f in project_dir.glob(pattern))
    
    return cj_files


def find_chir_files(project_path: str) -> List[str]:
    """查找CHIR中间文件"""
    chir_files = []
    project_dir = Path(project_path)
    
    for pattern in ['**/*.chir', '**/*.chir.json', '**/chir_output/**/*']:
        chir_files.extend(str(f) for f in project_dir.glob(pattern))
    
    return chir_files


def parse_line_info(line_str: str) -> Tuple[str, int]:
    """
    解析行信息字符串
    格式: "file.cj:123" 或 "file.cj:123:45"
    返回: (文件名, 行号)
    """
    match = re.match(r'(.+):(\d+)(?::\d+)?$', line_str)
    if match:
        return match.group(1), int(match.group(2))
    return line_str, 0


def normalize_path(path: str) -> str:
    """规范化路径"""
    return str(Path(path).resolve())


def get_relative_path(full_path: str, base_path: str) -> str:
    """获取相对路径"""
    try:
        return str(Path(full_path).relative_to(base_path))
    except ValueError:
        return full_path


def extract_file_name(path: str) -> str:
    """从路径中提取文件名"""
    return Path(path).name


def extract_dir_name(path: str) -> str:
    """从路径中提取目录名"""
    return str(Path(path).parent)


def is_valid_cangjie_project(project_path: str) -> bool:
    """检查是否是有效的仓颉项目"""
    project_dir = Path(project_path)
    
    # 检查cjpm.toml或cjpm.json
    if (project_dir / 'cjpm.toml').exists():
        return True
    if (project_dir / 'cjpm.json').exists():
        return True
    
    # 检查是否有.cj文件
    cj_files = list(project_dir.glob('**/*.cj'))
    if cj_files:
        return True
    
    return False


def read_file_content(file_path: str) -> Optional[str]:
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件失败: {file_path}, 错误: {e}")
        return None


def write_file_content(file_path: str, content: str) -> bool:
    """写入文件内容"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"写入文件失败: {file_path}, 错误: {e}")
        return False


def ensure_dir(dir_path: str) -> bool:
    """确保目录存在"""
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败: {dir_path}, 错误: {e}")
        return False


def count_lines(file_path: str) -> int:
    """统计文件行数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_source_line(file_path: str, line_number: int) -> Optional[str]:
    """获取源文件指定行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if 1 <= line_number <= len(lines):
                return lines[line_number - 1].rstrip()
    except Exception:
        pass
    return None