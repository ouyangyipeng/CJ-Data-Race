#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓颉数据竞争静态检测工具 - 主入口
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chir_parser.parser import CHIRParser
from analyzer.concurrency import ConcurrencyAnalyzer
from analyzer.race_detector import RaceDetector
from output.formatter import OutputFormatter


class CangjieRaceDetector:
    """仓颉数据竞争静态检测工具主类"""
    
    def __init__(self, project_path: str, output_file: str = "race_detection_result.txt"):
        self.project_path = Path(project_path).resolve()
        self.output_file = output_file
        self.chir_files: List[Path] = []
        self.race_results: List[Dict] = []
        
    def find_chir_files(self) -> List[Path]:
        """查找项目中的CHIR文件"""
        chir_files = []
        # 查找.chir或.chir.json文件
        for pattern in ['**/*.chir', '**/*.chir.json', '**/chir_output/**']:
            chir_files.extend(self.project_path.glob(pattern))
        return chir_files
    
    def compile_project(self) -> bool:
        """使用cjpm编译项目生成CHIR"""
        try:
            # 检查cjpm是否可用
            result = subprocess.run(
                ['cjpm', 'build', '--emit-chir'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            return result.returncode == 0
        except FileNotFoundError:
            print("警告: cjpm未安装，尝试使用其他方式获取CHIR")
            return False
        except subprocess.TimeoutExpired:
            print("错误: 编译超时")
            return False
    
    def analyze(self) -> List[Dict]:
        """执行数据竞争分析"""
        # 1. 查找CHIR文件
        self.chir_files = self.find_chir_files()
        
        if not self.chir_files:
            print("未找到CHIR文件，尝试编译项目...")
            if not self.compile_project():
                print("错误: 无法生成CHIR文件")
                return []
            self.chir_files = self.find_chir_files()
        
        print(f"找到 {len(self.chir_files)} 个CHIR文件")
        
        # 2. 解析CHIR
        parser = CHIRParser()
        parsed_modules = []
        for chir_file in self.chir_files:
            print(f"解析: {chir_file}")
            module = parser.parse(str(chir_file))
            if module:
                parsed_modules.append(module)
        
        # 3. 并发分析
        print("执行并发分析...")
        concurrency_analyzer = ConcurrencyAnalyzer(parsed_modules)
        thread_info = concurrency_analyzer.analyze()
        
        # 4. 数据竞争检测
        print("执行数据竞争检测...")
        detector = RaceDetector(parsed_modules, thread_info)
        self.race_results = detector.detect()
        
        return self.race_results
    
    def save_results(self):
        """保存检测结果"""
        formatter = OutputFormatter(self.race_results)
        output = formatter.format()
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        
        print(f"检测结果已保存到: {self.output_file}")
        print(f"共检测到 {len(self.race_results)} 个潜在数据竞争")


def main():
    parser = argparse.ArgumentParser(
        description='仓颉数据竞争静态检测工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py /path/to/cangjie/project
  python main.py /path/to/cangjie/project -o result.txt
        """
    )
    parser.add_argument('project_path', help='仓颉工程根目录路径')
    parser.add_argument('-o', '--output', default='race_detection_result.txt',
                        help='输出文件路径 (默认: race_detection_result.txt)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细输出')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.project_path):
        print(f"错误: 目录不存在: {args.project_path}")
        sys.exit(1)
    
    detector = CangjieRaceDetector(args.project_path, args.output)
    results = detector.analyze()
    detector.save_results()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())