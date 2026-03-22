# -*- coding: utf-8 -*-
"""
增强版并发分析模块
支持更多同步原语：Mutex、RWLock、SpinLock、Atomic、Channel
实现更精确的数据流分析
"""

from typing import List, Dict, Set, Optional, Tuple, FrozenSet
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto


class SyncPrimitiveType(Enum):
    """同步原语类型"""
    MUTEX = auto()
    RWLOCK_READ = auto()
    RWLOCK_WRITE = auto()
    SPINLOCK = auto()
    ATOMIC = auto()
    CHANNEL_SEND = auto()
    CHANNEL_RECV = auto()
    SYNCHRONIZED = auto()


class AccessType(Enum):
    """访问类型"""
    READ = "R"
    WRITE = "W"
    READ_WRITE = "RW"  # 读写操作


@dataclass(frozen=True)
class SourceLocation:
    """源码位置"""
    file_path: str
    line: int
    column: int = 0
    
    def __str__(self):
        return f"{self.file_path}:{self.line}:{self.column}"


@dataclass
class Variable:
    """变量"""
    name: str
    type_name: str = ""
    is_shared: bool = False
    is_atomic: bool = False
    is_volatile: bool = False
    location: Optional[SourceLocation] = None
    
    def __hash__(self):
        return hash((self.name, self.type_name))
    
    def __eq__(self, other):
        if not isinstance(other, Variable):
            return False
        return self.name == other.name and self.type_name == other.type_name


@dataclass
class SyncRegion:
    """同步区域"""
    sync_type: SyncPrimitiveType
    lock_object: Optional[Variable]
    start_location: SourceLocation
    end_location: Optional[SourceLocation] = None
    protected_vars: Set[Variable] = field(default_factory=set)


@dataclass
class AccessInfo:
    """访问信息"""
    variable: Variable
    access_type: AccessType
    location: SourceLocation
    thread_id: str
    in_sync_region: bool = False
    sync_region: Optional[SyncRegion] = None
    is_atomic: bool = False


@dataclass
class ThreadContext:
    """线程上下文"""
    thread_id: str
    spawn_location: SourceLocation
    entry_function: str
    accessed_vars: Set[Variable] = field(default_factory=set)
    write_vars: Set[Variable] = field(default_factory=set)
    read_vars: Set[Variable] = field(default_factory=set)
    sync_regions: List[SyncRegion] = field(default_factory=list)
    spawned_threads: List[str] = field(default_factory=list)


@dataclass
class DataFlowFact:
    """数据流事实"""
    available_vars: Set[Variable] = field(default_factory=set)
    protected_vars: Set[Variable] = field(default_factory=set)  # 被同步保护的变量
    must_be_shared: Set[Variable] = field(default_factory=set)  # 必定被共享的变量
    may_be_shared: Set[Variable] = field(default_factory=set)   # 可能被共享的变量


class EnhancedConcurrencyAnalyzer:
    """增强版并发分析器"""
    
    # 同步原语方法名模式
    SYNC_METHODS = {
        # Mutex
        'lock': SyncPrimitiveType.MUTEX,
        'unlock': SyncPrimitiveType.MUTEX,
        'tryLock': SyncPrimitiveType.MUTEX,
        
        # RWLock
        'readLock': SyncPrimitiveType.RWLOCK_READ,
        'readUnlock': SyncPrimitiveType.RWLOCK_READ,
        'writeLock': SyncPrimitiveType.RWLOCK_WRITE,
        'writeUnlock': SyncPrimitiveType.RWLOCK_WRITE,
        
        # SpinLock
        'spinLock': SyncPrimitiveType.SPINLOCK,
        'spinUnlock': SyncPrimitiveType.SPINLOCK,
        
        # Channel
        'send': SyncPrimitiveType.CHANNEL_SEND,
        'receive': SyncPrimitiveType.CHANNEL_RECV,
        'recv': SyncPrimitiveType.CHANNEL_RECV,
    }
    
    # 原子类型
    ATOMIC_TYPES = {
        'AtomicInt32', 'AtomicInt64', 'AtomicUInt32', 'AtomicUInt64',
        'AtomicBool', 'AtomicReference', 'AtomicI32', 'AtomicI64',
        'AtomicU32', 'AtomicU64', 'AtomicBool', 'AtomicRef'
    }
    
    # 原子操作方法
    ATOMIC_METHODS = {
        'load', 'store', 'exchange', 'compareAndSwap', 'fetchAdd',
        'fetchSub', 'fetchAnd', 'fetchOr', 'fetchXor'
    }
    
    def __init__(self):
        self.threads: Dict[str, ThreadContext] = {}
        self.accesses: Dict[Variable, List[AccessInfo]] = defaultdict(list)
        self.sync_regions: List[SyncRegion] = []
        self.global_vars: Set[Variable] = set()
        self.shared_vars: Set[Variable] = set()
        self.data_flow_facts: Dict[str, DataFlowFact] = {}
        
        # 锁保护分析
        self.lock_protected: Dict[Variable, Set[SyncRegion]] = defaultdict(set)
        
        # 线程间共享分析
        self.var_access_threads: Dict[Variable, Set[str]] = defaultdict(set)
    
    def analyze_source(self, source_code: str, file_path: str) -> Dict:
        """分析源代码"""
        lines = source_code.split('\n')
        
        # 第一遍：识别全局变量和类成员
        self._collect_globals_and_members(lines, file_path)
        
        # 第二遍：识别spawn表达式
        self._find_spawns(lines, file_path)
        
        # 第三遍：分析同步区域
        self._analyze_sync_regions(lines, file_path)
        
        # 第四遍：分析变量访问
        self._analyze_accesses(lines, file_path)
        
        # 第五遍：数据流分析
        self._perform_data_flow_analysis()
        
        # 第六遍：识别共享变量
        self._identify_shared_variables()
        
        return {
            'threads': self.threads,
            'accesses': dict(self.accesses),
            'sync_regions': self.sync_regions,
            'shared_vars': self.shared_vars,
            'lock_protected': dict(self.lock_protected)
        }
    
    def _collect_globals_and_members(self, lines: List[str], file_path: str):
        """收集全局变量和类成员"""
        in_class = False
        class_name = ""
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 类定义
            if stripped.startswith('class ') or stripped.startswith('public class '):
                in_class = True
                parts = stripped.split()
                class_name = parts[1] if len(parts) > 1 else ""
                continue
            
            if in_class and stripped == '}':
                in_class = False
                class_name = ""
                continue
            
            # 成员变量
            if in_class and ('var ' in stripped or 'let ' in stripped):
                var = self._parse_variable(stripped, file_path, i + 1)
                if var:
                    var.is_shared = True  # 类成员默认可能被共享
                    self.global_vars.add(var)
            
            # 全局变量
            if not in_class and (stripped.startswith('var ') or stripped.startswith('let ')):
                var = self._parse_variable(stripped, file_path, i + 1)
                if var:
                    self.global_vars.add(var)
    
    def _parse_variable(self, line: str, file_path: str, line_num: int) -> Optional[Variable]:
        """解析变量声明"""
        # 简化解析
        import re
        
        # 匹配 var/let name: Type 或 var/let name = value
        match = re.match(r'(?:var|let)\s+(\w+)(?:\s*:\s*(\w+))?', line)
        if match:
            name = match.group(1)
            type_name = match.group(2) or ""
            
            is_atomic = type_name in self.ATOMIC_TYPES
            
            return Variable(
                name=name,
                type_name=type_name,
                is_atomic=is_atomic,
                location=SourceLocation(file_path, line_num)
            )
        return None
    
    def _find_spawns(self, lines: List[str], file_path: str):
        """查找spawn表达式"""
        import re
        
        thread_counter = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # spawn表达式: spawn { ... } 或 spawn(expression)
            if 'spawn' in stripped.lower():
                # 查找闭包或函数引用
                spawn_match = re.search(r'spawn\s*(?:\(\s*)?(\w+)?', stripped)
                if spawn_match:
                    thread_id = f"thread_{thread_counter}"
                    thread_counter += 1
                    
                    entry_func = spawn_match.group(1) or "anonymous"
                    
                    thread_ctx = ThreadContext(
                        thread_id=thread_id,
                        spawn_location=SourceLocation(file_path, i + 1),
                        entry_function=entry_func
                    )
                    self.threads[thread_id] = thread_ctx
    
    def _analyze_sync_regions(self, lines: List[str], file_path: str):
        """分析同步区域"""
        import re
        
        current_sync: Optional[SyncRegion] = None
        sync_stack: List[SyncRegion] = []
        brace_count = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # synchronized块
            if 'synchronized' in stripped:
                # 查找锁对象
                match = re.search(r'synchronized\s*\(\s*(\w+)\s*\)', stripped)
                lock_obj = None
                if match:
                    lock_obj = Variable(name=match.group(1))
                
                sync_region = SyncRegion(
                    sync_type=SyncPrimitiveType.SYNCHRONIZED,
                    lock_object=lock_obj,
                    start_location=SourceLocation(file_path, i + 1)
                )
                sync_stack.append(sync_region)
                current_sync = sync_region
            
            # Mutex.lock()
            for method, sync_type in self.SYNC_METHODS.items():
                if f'.{method}(' in stripped:
                    # 查找锁对象
                    match = re.search(r'(\w+)\s*\.\s*' + method, stripped)
                    if match:
                        lock_obj = Variable(name=match.group(1))
                        
                        if 'lock' in method.lower() or 'Lock' in method:
                            sync_region = SyncRegion(
                                sync_type=sync_type,
                                lock_object=lock_obj,
                                start_location=SourceLocation(file_path, i + 1)
                            )
                            sync_stack.append(sync_region)
                        elif 'unlock' in method.lower() or 'Unlock' in method:
                            if sync_stack:
                                sync_stack[-1].end_location = SourceLocation(file_path, i + 1)
                                self.sync_regions.append(sync_stack.pop())
            
            # 跟踪大括号
            brace_count += stripped.count('{') - stripped.count('}')
            
            if current_sync and brace_count == 0 and '{' not in stripped:
                current_sync.end_location = SourceLocation(file_path, i + 1)
                self.sync_regions.append(current_sync)
                if sync_stack:
                    sync_stack.pop()
                current_sync = sync_stack[-1] if sync_stack else None
    
    def _analyze_accesses(self, lines: List[str], file_path: str):
        """分析变量访问"""
        import re
        
        for thread_id, thread_ctx in self.threads.items():
            # 分析线程中的访问
            spawn_line = thread_ctx.spawn_location.line
            
            # 简化：分析spawn之后的代码
            for i in range(spawn_line - 1, len(lines)):
                line = lines[i]
                stripped = line.strip()
                
                # 检查是否在同步区域内
                in_sync = self._is_in_sync_region(file_path, i + 1)
                sync_region = self._get_sync_region(file_path, i + 1)
                
                # 变量读取
                read_matches = re.finditer(r'(?<![.\w])(\w+)(?!\s*=)', stripped)
                for match in read_matches:
                    var_name = match.group(1)
                    var = Variable(name=var_name)
                    
                    access = AccessInfo(
                        variable=var,
                        access_type=AccessType.READ,
                        location=SourceLocation(file_path, i + 1),
                        thread_id=thread_id,
                        in_sync_region=in_sync,
                        sync_region=sync_region
                    )
                    self.accesses[var].append(access)
                    self.var_access_threads[var].add(thread_id)
                    thread_ctx.accessed_vars.add(var)
                    thread_ctx.read_vars.add(var)
                
                # 变量写入
                write_matches = re.finditer(r'(\w+)\s*=\s*', stripped)
                for match in write_matches:
                    var_name = match.group(1)
                    var = Variable(name=var_name)
                    
                    access = AccessInfo(
                        variable=var,
                        access_type=AccessType.WRITE,
                        location=SourceLocation(file_path, i + 1),
                        thread_id=thread_id,
                        in_sync_region=in_sync,
                        sync_region=sync_region
                    )
                    self.accesses[var].append(access)
                    self.var_access_threads[var].add(thread_id)
                    thread_ctx.accessed_vars.add(var)
                    thread_ctx.write_vars.add(var)
    
    def _is_in_sync_region(self, file_path: str, line: int) -> bool:
        """检查位置是否在同步区域内"""
        for region in self.sync_regions:
            if (region.start_location.file_path == file_path and
                region.start_location.line <= line and
                (region.end_location is None or region.end_location.line >= line)):
                return True
        return False
    
    def _get_sync_region(self, file_path: str, line: int) -> Optional[SyncRegion]:
        """获取位置所在的同步区域"""
        for region in self.sync_regions:
            if (region.start_location.file_path == file_path and
                region.start_location.line <= line and
                (region.end_location is None or region.end_location.line >= line)):
                return region
        return None
    
    def _perform_data_flow_analysis(self):
        """执行数据流分析"""
        # 初始化
        for var in self.global_vars:
            fact = DataFlowFact()
            fact.available_vars.add(var)
            self.data_flow_facts[var.name] = fact
        
        # 迭代直到不动点
        changed = True
        iterations = 0
        max_iterations = 100
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for var, accesses in self.accesses.items():
                # 检查是否被多个线程访问
                threads = self.var_access_threads.get(var, set())
                if len(threads) > 1:
                    if var not in self.data_flow_facts[var.name].must_be_shared:
                        self.data_flow_facts[var.name].must_be_shared.add(var)
                        changed = True
                
                # 检查是否有写操作
                has_write = any(a.access_type in (AccessType.WRITE, AccessType.READ_WRITE) 
                               for a in accesses)
                
                # 检查是否被同步保护
                protected_by = set()
                for access in accesses:
                    if access.in_sync_region and access.sync_region:
                        protected_by.add(access.sync_region)
                
                if protected_by:
                    self.lock_protected[var].update(protected_by)
    
    def _identify_shared_variables(self):
        """识别共享变量"""
        for var, threads in self.var_access_threads.items():
            if len(threads) > 1:
                # 被多个线程访问
                self.shared_vars.add(var)
            elif var in self.global_vars:
                # 全局变量可能被共享
                self.shared_vars.add(var)
    
    def get_race_candidates(self) -> List[Tuple[Variable, List[AccessInfo]]]:
        """获取可能导致竞争的变量和访问"""
        candidates = []
        
        for var in self.shared_vars:
            # 检查是否有并发写或读写冲突
            accesses = self.accesses.get(var, [])
            
            # 过滤掉被同步保护的访问
            unprotected_accesses = [
                a for a in accesses 
                if not a.in_sync_region and not a.is_atomic
            ]
            
            # 检查是否有写操作
            has_write = any(a.access_type in (AccessType.WRITE, AccessType.READ_WRITE) 
                           for a in unprotected_accesses)
            
            # 检查是否被多个线程访问
            threads = set(a.thread_id for a in unprotected_accesses)
            
            if has_write and len(threads) > 1:
                candidates.append((var, unprotected_accesses))
        
        return candidates


def analyze_concurrency(source_code: str, file_path: str) -> Dict:
    """分析并发问题的便捷函数"""
    analyzer = EnhancedConcurrencyAnalyzer()
    return analyzer.analyze_source(source_code, file_path)