# -*- coding: utf-8 -*-
"""
并发分析模块
分析仓颉程序中的并发结构，识别线程创建、同步操作等
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from chir_parser.ast_nodes import (
    Module, Function, Class, Variable, BasicBlock, CHIRNode,
    SpawnExpression, SyncExpression, LockExpression, MemoryAccess,
    SourceLocation, ThreadInfo, AccessType, SyncType
)


@dataclass
class AccessInfo:
    """变量访问信息"""
    variable: Variable
    access_type: AccessType
    location: SourceLocation
    thread_id: str
    in_sync_block: bool = False
    sync_object: Optional[Variable] = None


@dataclass
class ThreadGroup:
    """线程组 - 同一spawn语句创建的所有线程实例"""
    spawn_location: SourceLocation
    entry_function: Function
    thread_ids: List[str] = field(default_factory=list)


class ConcurrencyAnalyzer:
    """并发分析器"""
    
    def __init__(self, modules: List[Module]):
        self.modules = modules
        self.threads: Dict[str, ThreadInfo] = {}
        self.thread_groups: List[ThreadGroup] = []
        self.accesses: Dict[str, List[AccessInfo]] = defaultdict(list)  # 变量名 -> 访问列表
        self.sync_regions: List[Tuple[SourceLocation, SourceLocation, Variable]] = []
        self.public_interfaces: Dict[str, Function] = {}  # 公共接口
        
        # 构建函数查找表
        self.function_map: Dict[str, Function] = {}
        self._build_function_map()
    
    def _build_function_map(self):
        """构建函数名到函数对象的映射"""
        for module in self.modules:
            for func in module.functions:
                self.function_map[func.full_name] = func
                if func.is_public:
                    self.public_interfaces[func.full_name] = func
            
            for cls in module.classes:
                for method in cls.methods:
                    full_name = f"{cls.full_name}.{method.name}"
                    self.function_map[full_name] = method
                    if method.is_public:
                        self.public_interfaces[full_name] = method
    
    def analyze(self) -> Dict[str, ThreadInfo]:
        """执行并发分析"""
        # 1. 识别所有spawn创建的线程
        self._find_spawns()
        
        # 2. 分析每个线程的访问模式
        self._analyze_thread_accesses()
        
        # 3. 分析同步区域
        self._analyze_sync_regions()
        
        # 4. 分析逃逸变量
        self._analyze_escaped_variables()
        
        return self.threads
    
    def _find_spawns(self):
        """查找所有spawn表达式"""
        thread_counter = 0
        
        for module in self.modules:
            for func in module.functions:
                spawns = self._find_spawns_in_function(func, module)
                for spawn in spawns:
                    thread_id = f"thread_{thread_counter}"
                    thread_counter += 1
                    
                    # 创建线程信息
                    thread_info = ThreadInfo(
                        thread_id=thread_id,
                        spawn_location=spawn.location,
                        entry_function=spawn.closure if spawn.closure else func
                    )
                    self.threads[thread_id] = thread_info
                    
                    # 查找或创建线程组
                    group_found = False
                    for group in self.thread_groups:
                        if (group.spawn_location.file_path == spawn.location.file_path and
                            group.spawn_location.line == spawn.location.line):
                            group.thread_ids.append(thread_id)
                            group_found = True
                            break
                    
                    if not group_found:
                        self.thread_groups.append(ThreadGroup(
                            spawn_location=spawn.location,
                            entry_function=spawn.closure if spawn.closure else func,
                            thread_ids=[thread_id]
                        ))
    
    def _find_spawns_in_function(self, func: Function, module: Module) -> List[SpawnExpression]:
        """在函数中查找spawn表达式"""
        spawns = []
        
        for bb in func.basic_blocks:
            for stmt in bb.statements:
                if isinstance(stmt, SpawnExpression):
                    spawns.append(stmt)
                elif isinstance(stmt, (SyncExpression, LockExpression)):
                    # 在同步块中查找spawn
                    body = stmt.body if isinstance(stmt, SyncExpression) else stmt.body
                    for inner_stmt in body:
                        if isinstance(inner_stmt, SpawnExpression):
                            spawns.append(inner_stmt)
        
        return spawns
    
    def _analyze_thread_accesses(self):
        """分析每个线程的变量访问"""
        for thread_id, thread_info in self.threads.items():
            self._analyze_function_accesses(
                thread_info.entry_function,
                thread_id,
                thread_info,
                in_sync=False,
                sync_object=None
            )
    
    def _analyze_function_accesses(
        self,
        func: Function,
        thread_id: str,
        thread_info: ThreadInfo,
        in_sync: bool = False,
        sync_object: Optional[Variable] = None
    ):
        """分析函数中的变量访问"""
        for bb in func.basic_blocks:
            for stmt in bb.statements:
                if isinstance(stmt, MemoryAccess):
                    # 记录访问
                    access_info = AccessInfo(
                        variable=stmt.variable,
                        access_type=stmt.access_type,
                        location=stmt.location,
                        thread_id=thread_id,
                        in_sync_block=in_sync,
                        sync_object=sync_object
                    )
                    
                    if stmt.variable:
                        var_name = stmt.variable.name
                        self.accesses[var_name].append(access_info)
                        
                        # 更新线程信息
                        thread_info.accessed_vars.add(stmt.variable)
                        if stmt.access_type == AccessType.WRITE:
                            thread_info.write_vars.add(stmt.variable)
                        else:
                            thread_info.read_vars.add(stmt.variable)
                
                elif isinstance(stmt, (SyncExpression, LockExpression)):
                    # 进入同步区域
                    sync_obj = stmt.target if isinstance(stmt, SyncExpression) else stmt.lock_var
                    body = stmt.body
                    
                    for inner_stmt in body:
                        if isinstance(inner_stmt, MemoryAccess):
                            access_info = AccessInfo(
                                variable=inner_stmt.variable,
                                access_type=inner_stmt.access_type,
                                location=inner_stmt.location,
                                thread_id=thread_id,
                                in_sync_block=True,
                                sync_object=sync_obj
                            )
                            
                            if inner_stmt.variable:
                                var_name = inner_stmt.variable.name
                                self.accesses[var_name].append(access_info)
                                
                                thread_info.accessed_vars.add(inner_stmt.variable)
                                if inner_stmt.access_type == AccessType.WRITE:
                                    thread_info.write_vars.add(inner_stmt.variable)
                                else:
                                    thread_info.read_vars.add(inner_stmt.variable)
                        
                        if sync_obj:
                            thread_info.sync_objects.add(sync_obj)
    
    def _analyze_sync_regions(self):
        """分析同步区域"""
        for module in self.modules:
            for func in module.functions:
                for bb in func.basic_blocks:
                    for stmt in bb.statements:
                        if isinstance(stmt, (SyncExpression, LockExpression)):
                            sync_obj = stmt.target if isinstance(stmt, SyncExpression) else stmt.lock_var
                            body = stmt.body
                            
                            if body and stmt.location:
                                # 记录同步区域的开始和结束
                                end_loc = body[-1].location if body else stmt.location
                                if sync_obj:
                                    self.sync_regions.append((
                                        stmt.location,
                                        end_loc,
                                        sync_obj
                                    ))
    
    def _analyze_escaped_variables(self):
        """分析逃逸变量 - 被多个线程访问的变量"""
        for var_name, accesses in self.accesses.items():
            # 检查是否被多个线程访问
            thread_ids = set(a.thread_id for a in accesses)
            if len(thread_ids) > 1:
                # 标记变量为共享
                for access in accesses:
                    if access.variable:
                        access.variable.is_shared = True
    
    def get_shared_variables(self) -> Set[Variable]:
        """获取所有共享变量"""
        shared = set()
        for var_name, accesses in self.accesses.items():
            thread_ids = set(a.thread_id for a in accesses)
            if len(thread_ids) > 1:
                for access in accesses:
                    if access.variable:
                        shared.add(access.variable)
        return shared
    
    def get_concurrent_accesses(self, var_name: str) -> List[AccessInfo]:
        """获取变量的并发访问"""
        accesses = self.accesses.get(var_name, [])
        if len(accesses) <= 1:
            return []
        
        # 检查是否有来自不同线程的访问
        thread_ids = set(a.thread_id for a in accesses)
        if len(thread_ids) <= 1:
            return []
        
        return accesses
    
    def is_protected_access(self, access: AccessInfo) -> bool:
        """检查访问是否受同步保护"""
        return access.in_sync_block
    
    def are_synchronized(self, access1: AccessInfo, access2: AccessInfo) -> bool:
        """检查两个访问是否被同一同步对象保护"""
        if not access1.in_sync_block or not access2.in_sync_block:
            return False
        
        if access1.sync_object and access2.sync_object:
            return access1.sync_object.name == access2.sync_object.name
        
        return False
    
    def get_thread_group(self, thread_id: str) -> Optional[ThreadGroup]:
        """获取线程所属的线程组"""
        for group in self.thread_groups:
            if thread_id in group.thread_ids:
                return group
        return None
    
    def get_spawn_location(self, thread_id: str) -> Optional[SourceLocation]:
        """获取线程的spawn位置"""
        thread_info = self.threads.get(thread_id)
        if thread_info:
            return thread_info.spawn_location
        return None