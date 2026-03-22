# -*- coding: utf-8 -*-
"""
数据竞争检测模块
检测仓颉程序中的数据竞争
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from chir_parser.ast_nodes import (
    Module, Function, Class, Variable, BasicBlock, CHIRNode,
    SpawnExpression, SyncExpression, LockExpression, MemoryAccess,
    SourceLocation, ThreadInfo, RaceCondition, AccessType, SyncType
)
from .concurrency import ConcurrencyAnalyzer, AccessInfo, ThreadGroup


class RaceDetector:
    """数据竞争检测器"""
    
    def __init__(self, modules: List[Module], thread_info: Dict[str, ThreadInfo]):
        self.modules = modules
        self.thread_info = thread_info
        self.races: List[RaceCondition] = []
        self.detected_races: Set[Tuple] = set()  # 用于去重
        
        # 构建模块查找表
        self.module_map: Dict[str, Module] = {}
        for module in modules:
            self.module_map[module.file_path] = module
    
    def detect(self) -> List[RaceCondition]:
        """执行数据竞争检测"""
        # 1. 创建并发分析器
        self.analyzer = ConcurrencyAnalyzer(self.modules)
        self.analyzer.analyze()
        
        # 2. 检测线程间的数据竞争
        self._detect_thread_races()
        
        # 3. 检测public接口的数据竞争
        self._detect_public_interface_races()
        
        return self.races
    
    def _detect_thread_races(self):
        """检测线程间的数据竞争"""
        # 获取所有共享变量
        shared_vars = self.analyzer.get_shared_variables()
        
        for var in shared_vars:
            accesses = self.analyzer.get_concurrent_accesses(var.name)
            
            if len(accesses) < 2:
                continue
            
            # 检查每对访问
            for i, access1 in enumerate(accesses):
                for access2 in accesses[i+1:]:
                    # 检查是否存在竞争
                    race = self._check_race(access1, access2)
                    if race:
                        self._add_race(race)
    
    def _check_race(self, access1: AccessInfo, access2: AccessInfo) -> Optional[RaceCondition]:
        """检查两个访问之间是否存在数据竞争"""
        # 1. 必须是不同线程
        if access1.thread_id == access2.thread_id:
            return None
        
        # 2. 至少有一个是写操作
        if (access1.access_type == AccessType.READ and 
            access2.access_type == AccessType.READ):
            return None  # 读-读不构成竞争
        
        # 3. 检查是否被同步保护
        if self.analyzer.are_synchronized(access1, access2):
            return None
        
        # 4. 检查原子操作
        if access1.variable and access1.variable.metadata.get('is_atomic', False):
            return None
        if access2.variable and access2.variable.metadata.get('is_atomic', False):
            return None
        
        # 确定竞争类型
        if (access1.access_type == AccessType.WRITE and 
            access2.access_type == AccessType.WRITE):
            race_type = "WW"
        else:
            race_type = "RW"
        
        # 获取线程的spawn位置
        spawn_loc1 = self.analyzer.get_spawn_location(access1.thread_id)
        spawn_loc2 = self.analyzer.get_spawn_location(access2.thread_id)
        
        if not spawn_loc1 or not spawn_loc2:
            return None
        
        return RaceCondition(
            race_type=race_type,
            thread1_spawn_loc=spawn_loc1,
            thread1_race_loc=access1.location,
            thread2_spawn_loc=spawn_loc2,
            thread2_race_loc=access2.location,
            variable=access1.variable
        )
    
    def _detect_public_interface_races(self):
        """检测public接口的数据竞争"""
        # 分析public函数中访问的变量
        public_accesses: Dict[str, List[AccessInfo]] = defaultdict(list)
        
        for func_name, func in self.analyzer.public_interfaces.items():
            accesses = self._get_function_accesses(func)
            for access in accesses:
                if access.variable:
                    public_accesses[access.variable.name].append(access)
        
        # 检查public接口间的竞争
        for var_name, accesses in public_accesses.items():
            if len(accesses) < 2:
                continue
            
            for i, access1 in enumerate(accesses):
                for access2 in accesses[i+1:]:
                    # 检查是否来自不同的public函数
                    func1 = self._find_containing_function(access1)
                    func2 = self._find_containing_function(access2)
                    
                    if func1 and func2 and func1.full_name != func2.full_name:
                        # 检查竞争
                        race = self._check_public_race(access1, access2, func1, func2)
                        if race:
                            self._add_race(race)
    
    def _get_function_accesses(self, func: Function) -> List[AccessInfo]:
        """获取函数中的所有变量访问"""
        accesses = []
        
        for bb in func.basic_blocks:
            for stmt in bb.statements:
                if isinstance(stmt, MemoryAccess):
                    accesses.append(AccessInfo(
                        variable=stmt.variable,
                        access_type=stmt.access_type,
                        location=stmt.location,
                        thread_id="main",  # public接口默认在主线程
                        in_sync_block=False
                    ))
        
        return accesses
    
    def _find_containing_function(self, access: AccessInfo) -> Optional[Function]:
        """查找包含访问的函数"""
        if not access.location:
            return None
        
        for module in self.modules:
            for func in module.functions:
                if self._access_in_function(access, func):
                    return func
            
            for cls in module.classes:
                for method in cls.methods:
                    if self._access_in_function(access, method):
                        return method
        
        return None
    
    def _access_in_function(self, access: AccessInfo, func: Function) -> bool:
        """检查访问是否在函数中"""
        if not access.location or not func.location:
            return False
        
        # 简化检查：比较文件路径和行号范围
        return (access.location.file_path == func.location.file_path and
                func.location.line <= access.location.line)
    
    def _check_public_race(
        self,
        access1: AccessInfo,
        access2: AccessInfo,
        func1: Function,
        func2: Function
    ) -> Optional[RaceCondition]:
        """检查public接口间的竞争"""
        # 至少有一个是写操作
        if (access1.access_type == AccessType.READ and 
            access2.access_type == AccessType.READ):
            return None
        
        # 确定竞争类型
        if (access1.access_type == AccessType.WRITE and 
            access2.access_type == AccessType.WRITE):
            race_type = "WW"
        else:
            race_type = "RW"
        
        # 创建竞争条件
        return RaceCondition(
            race_type=race_type,
            thread1_spawn_loc=SourceLocation(
                file_path=func1.location.file_path if func1.location else "",
                file_name=func1.location.file_name if func1.location else "",
                line=func1.location.line if func1.location else 0
            ),
            thread1_race_loc=access1.location,
            thread2_spawn_loc=SourceLocation(
                file_path=func2.location.file_path if func2.location else "",
                file_name=func2.location.file_name if func2.location else "",
                line=func2.location.line if func2.location else 0
            ),
            thread2_race_loc=access2.location,
            variable=access1.variable,
            is_public_interface=True,
            declare_line1=func1.location.line if func1.location else 0,
            declare_line2=func2.location.line if func2.location else 0
        )
    
    def _add_race(self, race: RaceCondition):
        """添加检测到的竞争（去重）"""
        # 创建唯一标识
        race_key = (
            race.race_type,
            race.thread1_spawn_loc.file_path,
            race.thread1_spawn_loc.line,
            race.thread1_race_loc.line,
            race.thread2_spawn_loc.file_path,
            race.thread2_spawn_loc.line,
            race.thread2_race_loc.line,
            race.variable.name if race.variable else ""
        )
        
        if race_key not in self.detected_races:
            self.detected_races.add(race_key)
            self.races.append(race)
    
    def get_statistics(self) -> Dict:
        """获取检测统计信息"""
        return {
            "total_races": len(self.races),
            "rw_races": sum(1 for r in self.races if r.race_type == "RW"),
            "ww_races": sum(1 for r in self.races if r.race_type == "WW"),
            "public_interface_races": sum(1 for r in self.races if r.is_public_interface),
            "thread_races": sum(1 for r in self.races if not r.is_public_interface)
        }