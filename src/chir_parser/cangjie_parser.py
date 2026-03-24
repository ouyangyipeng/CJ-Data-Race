# -*- coding: utf-8 -*-
"""
仓颉源码解析器 - 增强版
直接解析仓颉源代码(.cj文件)，提取并发结构和数据竞争
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

from .ast_nodes import (
    Module, Function, Variable, BasicBlock, CHIRNode,
    SpawnExpression, SyncExpression, LockExpression, MemoryAccess,
    SourceLocation, AccessType, SyncType
)


@dataclass
class ThreadContext:
    """线程上下文"""
    spawn_line: int
    file_path: str
    file_name: str
    accesses: List[MemoryAccess] = field(default_factory=list)
    sync_objects: Set[str] = field(default_factory=set)
    in_lock: bool = False
    current_lock: Optional[str] = None
    metadata: Dict = field(default_factory=dict)  # 额外元数据，如是否在循环内


@dataclass 
class ParsedFunction:
    """解析后的函数"""
    name: str
    is_public: bool
    declare_line: int
    file_path: str
    file_name: str
    accesses: List[MemoryAccess] = field(default_factory=list)
    spawns: List[SpawnExpression] = field(default_factory=list)


class CangjieParser:
    """仓颉源码解析器 - 增强版"""
    
    def __init__(self):
        self.current_file: str = ""
        self.current_file_name: str = ""
        self.current_content: str = ""
        self.threads: List[ThreadContext] = []
        self.functions: List[ParsedFunction] = []
        self.global_vars: Dict[str, Variable] = {}
        # 函数调用分析：记录每个函数访问的全局变量及其读写类型
        self.function_globals: Dict[str, Set[str]] = defaultdict(set)
        self.function_write_globals: Dict[str, Set[str]] = defaultdict(set)  # 写的全局变量
        self.function_read_globals: Dict[str, Set[str]] = defaultdict(set)   # 读的全局变量
    
    def parse_file(self, file_path: str) -> Optional[Module]:
        """解析仓颉源文件"""
        self.current_file = str(Path(file_path).parent)
        self.current_file_name = Path(file_path).name
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.current_content = f.read()
        except Exception as e:
            print(f"读取文件失败: {file_path}, 错误: {e}")
            return None
        
        return self._parse_source()
    
    def parse_directory(self, dir_path: str) -> List[Module]:
        """解析目录中的所有仓颉源文件"""
        modules = []
        dir_path = Path(dir_path)
        
        for cj_file in dir_path.glob('**/*.cj'):
            module = self.parse_file(str(cj_file))
            if module:
                modules.append(module)
        
        return modules
    
    def _parse_source(self) -> Module:
        """解析源代码"""
        lines = self.current_content.split('\n')
        
        module = Module(
            name=Path(self.current_file_name).stem,
            file_path=self.current_file
        )
        
        # 第一遍：收集全局变量和函数定义
        self._collect_globals_and_functions(lines)
        
        # 第二遍：分析函数体中的全局变量访问（用于过程间分析）
        self._analyze_function_globals(lines)
        
        # 第三遍：分析每个spawn线程
        self._analyze_spawns(lines)
        
        # 第四遍：分析public函数
        self._analyze_public_functions(lines)
        
        # 构建模块结构
        for func in self.functions:
            module_func = Function(
                name=func.name,
                full_name=f"{module.name}.{func.name}",
                is_public=func.is_public,
                location=SourceLocation(
                    file_path=func.file_path,
                    file_name=func.file_name,
                    line=func.declare_line
                )
            )
            module.functions.append(module_func)
        
        for var_name, var in self.global_vars.items():
            module.global_vars.append(var)
        
        return module
    
    def _collect_globals_and_functions(self, lines: List[str]):
        """收集全局变量和函数定义"""
        # 函数定义模式
        func_pattern = re.compile(r'(public\s+)?func\s+(\w+)\s*\(')
        # 变量声明模式
        var_pattern = re.compile(r'(public\s+)?(let|var)\s+(\w+)\s*:\s*(\w+)')
        
        brace_count = 0
        in_function = False
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 跳过注释
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # 统计大括号
            brace_count += stripped.count('{') - stripped.count('}')
            
            # 函数定义
            func_match = func_pattern.search(stripped)
            if func_match:
                is_public = func_match.group(1) is not None
                func_name = func_match.group(2)
                self.functions.append(ParsedFunction(
                    name=func_name,
                    is_public=is_public,
                    declare_line=line_num,
                    file_path=self.current_file,
                    file_name=self.current_file_name
                ))
                in_function = True
            
            # 全局变量（不在函数内）
            if not in_function and brace_count == 0:
                var_match = var_pattern.search(stripped)
                if var_match:
                    is_public = var_match.group(1) is not None
                    var_name = var_match.group(3)
                    var_type = var_match.group(4)
                    self.global_vars[var_name] = Variable(
                        name=var_name,
                        var_type=var_type,
                        is_shared=is_public,
                        is_mutable=(var_match.group(2) == 'var'),
                        location=SourceLocation(
                            file_path=self.current_file,
                            file_name=self.current_file_name,
                            line=line_num
                        )
                    )
            
            if brace_count == 0:
                in_function = False
    
    def _analyze_function_globals(self, lines: List[str]):
        """分析函数体中访问的全局变量（用于过程间分析）"""
        write_pattern = re.compile(r'(\w+)\s*=\s*[^=]')
        read_pattern = re.compile(r'\b(\w+)\b(?!\s*[=(:])')
        
        for func in self.functions:
            # 找到函数体范围
            func_start = func.declare_line
            func_end = len(lines)
            brace_count = 0
            started = False
            
            for line_num in range(func_start, len(lines) + 1):
                line = lines[line_num - 1]
                stripped = line.strip()
                
                if '{' in stripped:
                    if not started:
                        started = True
                    brace_count += stripped.count('{')
                
                if '}' in stripped:
                    brace_count -= stripped.count('}')
                    if started and brace_count == 0:
                        func_end = line_num
                        break
            
            # 分析函数体内的全局变量访问
            for line_num in range(func_start, func_end + 1):
                if line_num > len(lines):
                    break
                line = lines[line_num - 1]
                stripped = line.strip()
                
                # 检测写操作
                for write_match in write_pattern.finditer(stripped):
                    var_name = write_match.group(1)
                    if var_name in self.global_vars:
                        self.function_globals[func.name].add(var_name)
                        self.function_write_globals[func.name].add(var_name)
                
                # 检测读操作
                for read_match in read_pattern.finditer(stripped):
                    var_name = read_match.group(1)
                    if var_name in self.global_vars:
                        self.function_globals[func.name].add(var_name)
                        self.function_read_globals[func.name].add(var_name)
    
    def _analyze_spawns(self, lines: List[str]):
        """分析spawn创建的线程"""
        spawn_pattern = re.compile(r'spawn\s*{')
        # Mutex锁操作
        lock_pattern = re.compile(r'(\w+)\.lock\(\)')
        unlock_pattern = re.compile(r'(\w+)\.unlock\(\)')
        # RWLock读写锁操作
        read_lock_pattern = re.compile(r'(\w+)\.readLock\(\)')
        read_unlock_pattern = re.compile(r'(\w+)\.readUnlock\(\)')
        write_lock_pattern = re.compile(r'(\w+)\.writeLock\(\)')
        write_unlock_pattern = re.compile(r'(\w+)\.writeUnlock\(\)')
        # SpinLock操作
        spin_lock_pattern = re.compile(r'(\w+)\.spinLock\(\)')
        spin_unlock_pattern = re.compile(r'(\w+)\.spinUnlock\(\)')
        # synchronized块
        synchronized_pattern = re.compile(r'synchronized\s*\((\w+)\)')
        # 循环模式检测
        for_loop_pattern = re.compile(r'for\s*\(')
        while_loop_pattern = re.compile(r'while\s*\(')
        
        write_pattern = re.compile(r'(\w+)\s*=\s*[^=]')  # 赋值，不是比较
        read_pattern = re.compile(r'(?<![=<>!])\b(\w+)\b(?!\s*[=(:])')  # 变量使用
        local_var_pattern = re.compile(r'(let|var)\s+(\w+)\s*:')  # 局部变量声明
        # 数组访问模式: data[0] = ... 或 ... = data[0]
        array_write_pattern = re.compile(r'(\w+)\s*\[\s*\w*\s*\]\s*=')
        array_read_pattern = re.compile(r'(\w+)\s*\[\s*\w*\s*\]')
        # 类成员访问模式: obj.member = ... 或 ... = obj.member
        member_write_pattern = re.compile(r'(\w+)\.(\w+)\s*=')
        member_read_pattern = re.compile(r'\b(\w+)\.(\w+)\b(?!\s*=)')
        # 函数调用模式
        func_call_pattern = re.compile(r'(\w+)\s*\(')
        
        current_thread: Optional[ThreadContext] = None
        brace_stack: List[int] = []  # 记录大括号层级和对应的行号
        in_spawn = False
        spawn_brace_level = 0
        thread_local_vars: Set[str] = set()  # 当前线程的局部变量
        
        # 循环追踪
        in_loop = False
        loop_brace_level = 0
        loop_spawn_count = 0  # 循环内spawn计数
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 跳过注释
            if stripped.startswith('//'):
                continue
            
            # 检测循环开始
            if for_loop_pattern.search(stripped) or while_loop_pattern.search(stripped):
                in_loop = True
                loop_brace_level = len(brace_stack)
                loop_spawn_count = 0
            
            # 检测spawn
            if spawn_pattern.search(stripped):
                # 如果在循环内，创建多个线程实例来模拟循环效果
                if in_loop and len(brace_stack) > loop_brace_level:
                    # 循环内的spawn，创建2个线程实例来模拟竞争
                    # (因为循环会执行多次，至少会有2个并发实例)
                    # 使用列表保存循环内创建的线程
                    self.loop_threads = []
                    for _ in range(2):
                        thread = ThreadContext(
                            spawn_line=line_num,
                            file_path=self.current_file,
                            file_name=self.current_file_name
                        )
                        thread.metadata['in_loop'] = True
                        self.threads.append(thread)
                        self.loop_threads.append(thread)
                    current_thread = self.loop_threads[0]  # 设置当前线程用于分析
                    loop_spawn_count += 1
                else:
                    # 非循环内的spawn，正常处理
                    current_thread = ThreadContext(
                        spawn_line=line_num,
                        file_path=self.current_file,
                        file_name=self.current_file_name
                    )
                    self.threads.append(current_thread)
                    self.loop_threads = None
                
                in_spawn = True
                spawn_brace_level = len(brace_stack)
                thread_local_vars = set()  # 重置局部变量集合
            
            # 跟踪大括号
            for char in stripped:
                if char == '{':
                    brace_stack.append(line_num)
                elif char == '}':
                    if brace_stack:
                        brace_stack.pop()
                        if in_spawn and len(brace_stack) == spawn_brace_level:
                            in_spawn = False
                            current_thread = None
                            thread_local_vars = set()
                        # 检测循环结束
                        if in_loop and len(brace_stack) == loop_brace_level:
                            in_loop = False
                            loop_spawn_count = 0
            
            # 在spawn块内分析
            if current_thread and in_spawn:
                # 首先检测局部变量声明
                for local_match in local_var_pattern.finditer(stripped):
                    var_name = local_match.group(2)
                    thread_local_vars.add(var_name)
                
                # 检测Mutex锁操作
                lock_match = lock_pattern.search(stripped)
                if lock_match:
                    lock_var = lock_match.group(1)
                    current_thread.sync_objects.add(lock_var)
                    current_thread.in_lock = True
                    current_thread.current_lock = lock_var
                    # 如果是循环线程，同步到所有循环线程
                    if hasattr(self, 'loop_threads') and self.loop_threads:
                        for t in self.loop_threads:
                            t.sync_objects.add(lock_var)
                            t.in_lock = True
                            t.current_lock = lock_var
                
                unlock_match = unlock_pattern.search(stripped)
                if unlock_match:
                    current_thread.in_lock = False
                    current_thread.current_lock = None
                
                # 检测RWLock读写锁操作
                read_lock_match = read_lock_pattern.search(stripped)
                if read_lock_match:
                    lock_var = read_lock_match.group(1)
                    current_thread.sync_objects.add(lock_var)
                    current_thread.in_lock = True
                    current_thread.current_lock = lock_var
                
                read_unlock_match = read_unlock_pattern.search(stripped)
                if read_unlock_match:
                    current_thread.in_lock = False
                    current_thread.current_lock = None
                
                write_lock_match = write_lock_pattern.search(stripped)
                if write_lock_match:
                    lock_var = write_lock_match.group(1)
                    current_thread.sync_objects.add(lock_var)
                    current_thread.in_lock = True
                    current_thread.current_lock = lock_var
                
                write_unlock_match = write_unlock_pattern.search(stripped)
                if write_unlock_match:
                    current_thread.in_lock = False
                    current_thread.current_lock = None
                
                # 检测SpinLock操作
                spin_lock_match = spin_lock_pattern.search(stripped)
                if spin_lock_match:
                    lock_var = spin_lock_match.group(1)
                    current_thread.sync_objects.add(lock_var)
                    current_thread.in_lock = True
                    current_thread.current_lock = lock_var
                
                spin_unlock_match = spin_unlock_pattern.search(stripped)
                if spin_unlock_match:
                    current_thread.in_lock = False
                    current_thread.current_lock = None
                
                # 检测synchronized块
                synchronized_match = synchronized_pattern.search(stripped)
                if synchronized_match:
                    lock_var = synchronized_match.group(1)
                    current_thread.sync_objects.add(lock_var)
                    current_thread.in_lock = True
                    current_thread.current_lock = lock_var
                
                # 检测写操作
                for write_match in write_pattern.finditer(stripped):
                    var_name = write_match.group(1)
                    # 排除关键字、局部变量声明和局部变量
                    if var_name not in ('let', 'var', 'if', 'else', 'for', 'while', 'return', 'func'):
                        # 检查是否是局部变量声明行
                        if local_var_pattern.search(stripped):
                            continue  # 跳过声明行
                        # 检查是否是局部变量
                        if var_name in thread_local_vars:
                            continue  # 跳过局部变量
                        
                        access = MemoryAccess(
                            variable=Variable(name=var_name),
                            access_type=AccessType.WRITE,
                            location=SourceLocation(
                                file_path=self.current_file,
                                file_name=self.current_file_name,
                                line=line_num
                            )
                        )
                        if current_thread.in_lock:
                            access.metadata['protected_by'] = current_thread.current_lock
                        # 添加到当前线程
                        current_thread.accesses.append(access)
                        # 如果是循环线程，同步到所有循环线程
                        if hasattr(self, 'loop_threads') and self.loop_threads:
                            for t in self.loop_threads:
                                if t != current_thread:
                                    t.accesses.append(MemoryAccess(
                                        variable=Variable(name=var_name),
                                        access_type=AccessType.WRITE,
                                        location=SourceLocation(
                                            file_path=self.current_file,
                                            file_name=self.current_file_name,
                                            line=line_num
                                        ),
                                        metadata={'protected_by': current_thread.current_lock} if current_thread.in_lock else {}
                                    ))
                
                # 检测读操作（简化版，只检测变量使用）
                for read_match in read_pattern.finditer(stripped):
                    var_name = read_match.group(1)
                    # 排除关键字、类型名、局部变量和已检测的写操作
                    if var_name not in ('let', 'var', 'if', 'else', 'for', 'while', 'return', 'func',
                                       'Int64', 'Int32', 'String', 'Bool', 'Float64', 'Unit',
                                       'spawn', 'Mutex', 'RWLock', 'println', 'print'):
                        # 跳过局部变量
                        if var_name in thread_local_vars:
                            continue
                        # 检查是否已经在写操作中记录
                        already_write = any(a.variable.name == var_name and a.access_type == AccessType.WRITE
                                           for a in current_thread.accesses if a.location.line == line_num)
                        if not already_write:
                            access = MemoryAccess(
                                variable=Variable(name=var_name),
                                access_type=AccessType.READ,
                                location=SourceLocation(
                                    file_path=self.current_file,
                                    file_name=self.current_file_name,
                                    line=line_num
                                )
                            )
                            if current_thread.in_lock:
                                access.metadata['protected_by'] = current_thread.current_lock
                            current_thread.accesses.append(access)
                            # 如果是循环线程，同步到所有循环线程
                            if hasattr(self, 'loop_threads') and self.loop_threads:
                                for t in self.loop_threads:
                                    if t != current_thread:
                                        t.accesses.append(MemoryAccess(
                                            variable=Variable(name=var_name),
                                            access_type=AccessType.READ,
                                            location=SourceLocation(
                                                file_path=self.current_file,
                                                file_name=self.current_file_name,
                                                line=line_num
                                            ),
                                            metadata={'protected_by': current_thread.current_lock} if current_thread.in_lock else {}
                                        ))
                
                # 检测数组写操作: data[index] = value
                for array_match in array_write_pattern.finditer(stripped):
                    array_name = array_match.group(1)
                    if array_name not in ('let', 'var', 'if', 'else', 'for', 'while', 'return', 'func'):
                        if array_name not in thread_local_vars:
                            access = MemoryAccess(
                                variable=Variable(name=f"{array_name}[]"),
                                access_type=AccessType.WRITE,
                                location=SourceLocation(
                                    file_path=self.current_file,
                                    file_name=self.current_file_name,
                                    line=line_num
                                )
                            )
                            if current_thread.in_lock:
                                access.metadata['protected_by'] = current_thread.current_lock
                            current_thread.accesses.append(access)
                
                # 检测数组读操作: value = data[index]
                for array_match in array_read_pattern.finditer(stripped):
                    array_name = array_match.group(1)
                    if array_name not in ('let', 'var', 'if', 'else', 'for', 'while', 'return', 'func'):
                        if array_name not in thread_local_vars:
                            # 检查是否已经在写操作中记录
                            already_write = any(a.variable.name == f"{array_name}[]" and a.access_type == AccessType.WRITE
                                               for a in current_thread.accesses if a.location.line == line_num)
                            if not already_write:
                                access = MemoryAccess(
                                    variable=Variable(name=f"{array_name}[]"),
                                    access_type=AccessType.READ,
                                    location=SourceLocation(
                                        file_path=self.current_file,
                                        file_name=self.current_file_name,
                                        line=line_num
                                    )
                                )
                                if current_thread.in_lock:
                                    access.metadata['protected_by'] = current_thread.current_lock
                                current_thread.accesses.append(access)
                
                # 检测类成员写操作: obj.member = value
                for member_match in member_write_pattern.finditer(stripped):
                    obj_name = member_match.group(1)
                    member_name = member_match.group(2)
                    if obj_name not in ('let', 'var', 'if', 'else', 'for', 'while', 'return', 'func'):
                        if obj_name not in thread_local_vars:
                            access = MemoryAccess(
                                variable=Variable(name=f"{obj_name}.{member_name}"),
                                access_type=AccessType.WRITE,
                                location=SourceLocation(
                                    file_path=self.current_file,
                                    file_name=self.current_file_name,
                                    line=line_num
                                )
                            )
                            if current_thread.in_lock:
                                access.metadata['protected_by'] = current_thread.current_lock
                            current_thread.accesses.append(access)
                
                # 检测类成员读操作: value = obj.member
                for member_match in member_read_pattern.finditer(stripped):
                    obj_name = member_match.group(1)
                    member_name = member_match.group(2)
                    if obj_name not in ('let', 'var', 'if', 'else', 'for', 'while', 'return', 'func', 'println'):
                        if obj_name not in thread_local_vars:
                            # 检查是否已经在写操作中记录
                            already_write = any(a.variable.name == f"{obj_name}.{member_name}" and a.access_type == AccessType.WRITE
                                               for a in current_thread.accesses if a.location.line == line_num)
                            if not already_write:
                                access = MemoryAccess(
                                    variable=Variable(name=f"{obj_name}.{member_name}"),
                                    access_type=AccessType.READ,
                                    location=SourceLocation(
                                        file_path=self.current_file,
                                        file_name=self.current_file_name,
                                        line=line_num
                                    )
                                )
                                if current_thread.in_lock:
                                    access.metadata['protected_by'] = current_thread.current_lock
                                current_thread.accesses.append(access)
                
                # 检测函数调用并处理过程间分析
                for func_call_match in func_call_pattern.finditer(stripped):
                    func_name = func_call_match.group(1)
                    # 排除内置函数
                    if func_name not in ('println', 'print', 'spawn', 'lock', 'unlock', 'readLock',
                                         'readUnlock', 'writeLock', 'writeUnlock', 'synchronized'):
                        # 查找函数访问的全局变量
                        if func_name in self.function_globals:
                            for var_name in self.function_globals[func_name]:
                                # 根据函数是否写入该变量决定访问类型
                                if var_name in self.function_write_globals.get(func_name, set()):
                                    access_type = AccessType.WRITE
                                elif var_name in self.function_read_globals.get(func_name, set()):
                                    access_type = AccessType.READ
                                else:
                                    access_type = AccessType.READ  # 默认读
                                
                                # 添加函数调用中的变量访问
                                access = MemoryAccess(
                                    variable=Variable(name=var_name),
                                    access_type=access_type,
                                    location=SourceLocation(
                                        file_path=self.current_file,
                                        file_name=self.current_file_name,
                                        line=line_num
                                    )
                                )
                                if current_thread.in_lock:
                                    access.metadata['protected_by'] = current_thread.current_lock
                                current_thread.accesses.append(access)
    
    def _analyze_public_functions(self, lines: List[str]):
        """分析public函数的访问"""
        write_pattern = re.compile(r'(\w+)\s*=\s*[^=]')
        read_pattern = re.compile(r'\b(\w+)\b(?!\s*[=(:])')
        
        for func in self.functions:
            if not func.is_public:
                continue
            
            # 找到函数体
            func_start = func.declare_line
            func_end = len(lines)
            brace_count = 0
            started = False
            
            for line_num in range(func_start, len(lines) + 1):
                line = lines[line_num - 1]
                stripped = line.strip()
                
                if '{' in stripped:
                    if not started:
                        started = True
                    brace_count += stripped.count('{')
                
                if '}' in stripped:
                    brace_count -= stripped.count('}')
                    if started and brace_count == 0:
                        func_end = line_num
                        break
            
            # 分析函数体内的访问
            for line_num in range(func_start, func_end + 1):
                if line_num > len(lines):
                    break
                line = lines[line_num - 1]
                stripped = line.strip()
                
                # 检测写操作
                for write_match in write_pattern.finditer(stripped):
                    var_name = write_match.group(1)
                    if var_name in self.global_vars:
                        func.accesses.append(MemoryAccess(
                            variable=self.global_vars[var_name],
                            access_type=AccessType.WRITE,
                            location=SourceLocation(
                                file_path=self.current_file,
                                file_name=self.current_file_name,
                                line=line_num
                            )
                        ))
                
                # 检测读操作
                for read_match in read_pattern.finditer(stripped):
                    var_name = read_match.group(1)
                    if var_name in self.global_vars:
                        # 检查是否已记录为写
                        already_write = any(a.variable.name == var_name and a.access_type == AccessType.WRITE
                                          for a in func.accesses if a.location.line == line_num)
                        if not already_write:
                            func.accesses.append(MemoryAccess(
                                variable=self.global_vars[var_name],
                                access_type=AccessType.READ,
                                location=SourceLocation(
                                    file_path=self.current_file,
                                    file_name=self.current_file_name,
                                    line=line_num
                                )
                            ))
    
    def get_threads(self) -> List[ThreadContext]:
        """获取所有线程上下文"""
        return self.threads
    
    def get_public_functions(self) -> List[ParsedFunction]:
        """获取所有public函数"""
        return [f for f in self.functions if f.is_public]
    
    def get_global_vars(self) -> Dict[str, Variable]:
        """获取所有全局变量"""
        return self.global_vars