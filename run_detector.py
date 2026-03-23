#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓颉数据竞争静态检测工具 - 完整流程入口
支持直接分析仓颉源码
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Set

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chir_parser.cangjie_parser import CangjieParser, ThreadContext, ParsedFunction
from chir_parser.ast_nodes import (
    Module, RaceCondition, SourceLocation, MemoryAccess, AccessType, Variable
)


class DirectRaceDetector:
    """直接从源码检测数据竞争"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.races: List[RaceCondition] = []
        self.detected_races: Set[Tuple] = set()
    
    def analyze(self) -> List[RaceCondition]:
        """执行数据竞争分析"""
        # 1. 解析仓颉源码
        parser = CangjieParser()
        modules = parser.parse_directory(str(self.project_path))
        
        if not modules:
            print("警告: 未找到仓颉源文件")
            return []
        
        print(f"找到 {len(modules)} 个模块")
        
        # 2. 获取线程上下文
        threads = parser.get_threads()
        print(f"找到 {len(threads)} 个spawn线程")
        
        # 3. 获取public函数
        public_funcs = parser.get_public_functions()
        print(f"找到 {len(public_funcs)} 个public函数")
        
        # 4. 检测线程间数据竞争
        self._detect_thread_races(threads)
        
        # 5. 检测public接口数据竞争
        self._detect_public_interface_races(public_funcs)
        
        return self.races
    
    def _detect_thread_races(self, threads: List[ThreadContext]):
        """检测线程间的数据竞争"""
        if len(threads) < 2:
            return
        
        # 收集每个线程的变量访问
        for i, thread1 in enumerate(threads):
            for j, thread2 in enumerate(threads[i+1:], i+1):
                # 检查两个线程之间的竞争
                self._check_thread_pair(thread1, thread2)
    
    def _check_thread_pair(self, thread1: ThreadContext, thread2: ThreadContext):
        """检查两个线程之间的数据竞争"""
        # 按变量分组访问
        var_accesses1: Dict[str, List[MemoryAccess]] = {}
        var_accesses2: Dict[str, List[MemoryAccess]] = {}
        
        for access in thread1.accesses:
            var_name = access.variable.name
            if var_name not in var_accesses1:
                var_accesses1[var_name] = []
            var_accesses1[var_name].append(access)
        
        for access in thread2.accesses:
            var_name = access.variable.name
            if var_name not in var_accesses2:
                var_accesses2[var_name] = []
            var_accesses2[var_name].append(access)
        
        # 检查共享变量
        shared_vars = set(var_accesses1.keys()) & set(var_accesses2.keys())
        
        for var_name in shared_vars:
            accesses1 = var_accesses1[var_name]
            accesses2 = var_accesses2[var_name]
            
            # 检查是否有写操作
            for a1 in accesses1:
                for a2 in accesses2:
                    # 至少有一个是写
                    if a1.access_type == AccessType.READ and a2.access_type == AccessType.READ:
                        continue
                    
                    # 检查是否受同步保护
                    if self._is_protected(a1, thread1) and self._is_protected(a2, thread2):
                        # 检查是否是同一个锁
                        lock1 = a1.metadata.get('protected_by')
                        lock2 = a2.metadata.get('protected_by')
                        if lock1 and lock2 and lock1 == lock2:
                            continue
                    
                    # 发现数据竞争
                    race_type = "WW" if (a1.access_type == AccessType.WRITE and 
                                        a2.access_type == AccessType.WRITE) else "RW"
                    
                    race = RaceCondition(
                        race_type=race_type,
                        thread1_spawn_loc=SourceLocation(
                            file_path=thread1.file_path,
                            file_name=thread1.file_name,
                            line=thread1.spawn_line
                        ),
                        thread1_race_loc=a1.location,
                        thread2_spawn_loc=SourceLocation(
                            file_path=thread2.file_path,
                            file_name=thread2.file_name,
                            line=thread2.spawn_line
                        ),
                        thread2_race_loc=a2.location,
                        variable=Variable(name=var_name)
                    )
                    self._add_race(race)
    
    def _is_protected(self, access: MemoryAccess, thread: ThreadContext) -> bool:
        """检查访问是否受同步保护"""
        return access.metadata.get('protected_by') is not None
    
    def _detect_public_interface_races(self, functions: List[ParsedFunction]):
        """检测public接口的数据竞争"""
        if len(functions) < 2:
            return
        
        # 收集每个函数访问的全局变量
        func_accesses: Dict[str, Dict[str, List[MemoryAccess]]] = {}
        
        for func in functions:
            func_accesses[func.name] = {}
            for access in func.accesses:
                var_name = access.variable.name
                if var_name not in func_accesses[func.name]:
                    func_accesses[func.name][var_name] = []
                func_accesses[func.name][var_name].append(access)
        
        # 检查函数对之间的竞争
        for i, func1 in enumerate(functions):
            for func2 in functions[i+1:]:
                self._check_function_pair(func1, func2, func_accesses)
    
    def _check_function_pair(self, func1: ParsedFunction, func2: ParsedFunction,
                            func_accesses: Dict[str, Dict[str, List[MemoryAccess]]]):
        """检查两个public函数之间的数据竞争"""
        accesses1 = func_accesses.get(func1.name, {})
        accesses2 = func_accesses.get(func2.name, {})
        
        # 检查共享变量
        shared_vars = set(accesses1.keys()) & set(accesses2.keys())
        
        for var_name in shared_vars:
            for a1 in accesses1[var_name]:
                for a2 in accesses2[var_name]:
                    # 至少有一个是写
                    if a1.access_type == AccessType.READ and a2.access_type == AccessType.READ:
                        continue
                    
                    race_type = "WW" if (a1.access_type == AccessType.WRITE and 
                                        a2.access_type == AccessType.WRITE) else "RW"
                    
                    race = RaceCondition(
                        race_type=race_type,
                        thread1_spawn_loc=SourceLocation(
                            file_path=func1.file_path,
                            file_name=func1.file_name,
                            line=func1.declare_line
                        ),
                        thread1_race_loc=a1.location,
                        thread2_spawn_loc=SourceLocation(
                            file_path=func2.file_path,
                            file_name=func2.file_name,
                            line=func2.declare_line
                        ),
                        thread2_race_loc=a2.location,
                        variable=Variable(name=var_name),
                        is_public_interface=True,
                        declare_line1=func1.declare_line,
                        declare_line2=func2.declare_line
                    )
                    self._add_race(race)
    
    def _add_race(self, race: RaceCondition):
        """添加检测到的竞争（去重）"""
        race_key = (
            race.race_type,
            race.thread1_spawn_loc.file_path if race.thread1_spawn_loc else "",
            race.thread1_spawn_loc.line if race.thread1_spawn_loc else 0,
            race.thread1_race_loc.line if race.thread1_race_loc else 0,
            race.thread2_spawn_loc.file_path if race.thread2_spawn_loc else "",
            race.thread2_spawn_loc.line if race.thread2_spawn_loc else 0,
            race.thread2_race_loc.line if race.thread2_race_loc else 0,
            race.variable.name if race.variable else ""
        )
        
        if race_key not in self.detected_races:
            self.detected_races.add(race_key)
            self.races.append(race)


def format_output(races: List[RaceCondition]) -> str:
    """格式化输出结果
    
    根据赛题要求，输出格式为：
    (RaceType，((filePath1,fileName1,spawnLine1),(filePath1',fileName1',raceLine1')),((filePath2,fileName2,spawnLine2),(filePath2',fileName2',raceLine2')))
    注意：RaceType后面使用中文逗号"，"
    """
    if not races:
        return ""
    
    lines = []
    for race in races:
        if race.is_public_interface:
            # 公共接口竞争格式
            line = (
                f"({race.race_type}，"
                f"(({race.thread1_spawn_loc.file_path},{race.thread1_spawn_loc.file_name},{race.declare_line1}),"
                f"({race.thread1_race_loc.file_path},{race.thread1_race_loc.file_name},{race.thread1_race_loc.line})),"
                f"(({race.thread2_spawn_loc.file_path},{race.thread2_spawn_loc.file_name},{race.declare_line2}),"
                f"({race.thread2_race_loc.file_path},{race.thread2_race_loc.file_name},{race.thread2_race_loc.line})))"
            )
        else:
            # 线程间竞争格式
            line = (
                f"({race.race_type}，"
                f"(({race.thread1_spawn_loc.file_path},{race.thread1_spawn_loc.file_name},{race.thread1_spawn_loc.line}),"
                f"({race.thread1_race_loc.file_path},{race.thread1_race_loc.file_name},{race.thread1_race_loc.line})),"
                f"(({race.thread2_spawn_loc.file_path},{race.thread2_spawn_loc.file_name},{race.thread2_spawn_loc.line}),"
                f"({race.thread2_race_loc.file_path},{race.thread2_race_loc.file_name},{race.thread2_race_loc.line})))"
            )
        lines.append(line)
    
    return "\n".join(lines)


def get_summary(races: List[RaceCondition]) -> str:
    """获取检测摘要"""
    total = len(races)
    rw_count = sum(1 for r in races if r.race_type == "RW")
    ww_count = sum(1 for r in races if r.race_type == "WW")
    public_count = sum(1 for r in races if r.is_public_interface)
    
    return (
        f"数据竞争检测摘要:\n"
        f"  总计: {total} 个潜在数据竞争\n"
        f"  读写竞争(RW): {rw_count} 个\n"
        f"  写写竞争(WW): {ww_count} 个\n"
        f"  公共接口竞争: {public_count} 个"
    )


def main():
    parser = argparse.ArgumentParser(
        description='仓颉数据竞争静态检测工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('project_path', help='仓颉工程根目录路径')
    parser.add_argument('-o', '--output', default='race_detection_result.txt',
                        help='输出文件路径')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.project_path):
        print(f"错误: 目录不存在: {args.project_path}")
        sys.exit(1)
    
    print(f"分析项目: {args.project_path}")
    
    detector = DirectRaceDetector(args.project_path)
    races = detector.analyze()
    
    # 保存结果
    output = format_output(races)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"检测结果已保存到: {args.output}")
    print(get_summary(races))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())