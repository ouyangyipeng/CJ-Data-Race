# -*- coding: utf-8 -*-
"""
CHIR AST节点定义
定义仓颉CHIR中间语言的抽象语法树节点
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum


class AccessType(Enum):
    """访问类型"""
    READ = "R"
    WRITE = "W"
    READ_WRITE = "RW"


class SyncType(Enum):
    """同步类型"""
    MUTEX = "mutex"
    RWLOCK = "rwlock"
    SPINLOCK = "spinlock"
    ATOMIC = "atomic"
    CHANNEL = "channel"
    CONDITION = "condition"


@dataclass
class SourceLocation:
    """源代码位置"""
    file_path: str
    file_name: str
    line: int
    column: int = 0
    
    def __str__(self):
        return f"{self.file_path}/{self.file_name}:{self.line}"


@dataclass
class CHIRNode:
    """CHIR节点基类"""
    location: Optional[SourceLocation] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Variable(CHIRNode):
    """变量定义"""
    name: str = ""
    var_type: str = "unknown"
    is_shared: bool = False
    is_mutable: bool = True
    is_escaped: bool = False  # 是否逃逸到其他线程


@dataclass
class MemoryAccess(CHIRNode):
    """内存访问"""
    variable: Optional[Variable] = None
    access_type: AccessType = AccessType.READ
    is_atomic: bool = False


@dataclass
class SpawnExpression(CHIRNode):
    """Spawn表达式 - 创建新线程"""
    spawn_id: str = ""
    closure: Optional['Function'] = None  # 线程执行的闭包/函数
    spawn_line: int = 0  # spawn语句所在行
    captured_vars: List[Variable] = field(default_factory=list)


@dataclass
class SyncExpression(CHIRNode):
    """同步表达式"""
    sync_type: SyncType = SyncType.MUTEX
    target: Optional[Variable] = None  # 同步对象
    body: List[CHIRNode] = field(default_factory=list)


@dataclass
class LockExpression(CHIRNode):
    """锁表达式"""
    lock_type: SyncType = SyncType.MUTEX
    lock_var: Optional[Variable] = None
    body: List[CHIRNode] = field(default_factory=list)


@dataclass
class BasicBlock(CHIRNode):
    """基本块"""
    label: str = ""
    statements: List[CHIRNode] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)


@dataclass
class Function(CHIRNode):
    """函数定义"""
    name: str = ""
    full_name: str = ""  # 完整限定名
    parameters: List[Variable] = field(default_factory=list)
    return_type: str = "void"
    local_vars: List[Variable] = field(default_factory=list)
    basic_blocks: List[BasicBlock] = field(default_factory=list)
    is_public: bool = False
    is_spawn_entry: bool = False  # 是否是spawn入口函数
    spawn_line: int = 0  # 如果是spawn入口，记录spawn行号


@dataclass
class Class(CHIRNode):
    """类定义"""
    name: str = ""
    full_name: str = ""
    fields: List[Variable] = field(default_factory=list)
    methods: List[Function] = field(default_factory=list)
    is_public: bool = False


@dataclass
class Module(CHIRNode):
    """模块/包"""
    name: str = ""
    file_path: str = ""
    functions: List[Function] = field(default_factory=list)
    classes: List[Class] = field(default_factory=list)
    global_vars: List[Variable] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


@dataclass
class ThreadInfo:
    """线程信息"""
    thread_id: str = ""
    spawn_location: Optional[SourceLocation] = None
    entry_function: Optional[Function] = None
    accessed_vars: Set[Variable] = field(default_factory=set)
    write_vars: Set[Variable] = field(default_factory=set)
    read_vars: Set[Variable] = field(default_factory=set)
    sync_objects: Set[Variable] = field(default_factory=set)


@dataclass
class RaceCondition:
    """数据竞争"""
    race_type: str = ""  # "RW" or "WW"
    thread1_spawn_loc: Optional[SourceLocation] = None  # 线程1的spawn位置
    thread1_race_loc: Optional[SourceLocation] = None   # 线程1的竞争位置
    thread2_spawn_loc: Optional[SourceLocation] = None  # 线程2的spawn位置
    thread2_race_loc: Optional[SourceLocation] = None   # 线程2的竞争位置
    variable: Optional[Variable] = None                 # 竞争变量
    is_public_interface: bool = False  # 是否是public接口导致的竞争
    declare_line1: int = 0  # public接口声明行
    declare_line2: int = 0  # public接口声明行
    
    def to_output_format(self) -> str:
        """转换为输出格式"""
        if self.is_public_interface:
            return (
                f"({self.race_type},"
                f"(({self.thread1_spawn_loc.file_path},{self.thread1_spawn_loc.file_name},{self.declare_line1}),"
                f"({self.thread1_race_loc.file_path},{self.thread1_race_loc.file_name},{self.thread1_race_loc.line})),"
                f"(({self.thread2_spawn_loc.file_path},{self.thread2_spawn_loc.file_name},{self.declare_line2}),"
                f"({self.thread2_race_loc.file_path},{self.thread2_race_loc.file_name},{self.thread2_race_loc.line})))"
            )
        else:
            return (
                f"({self.race_type},"
                f"(({self.thread1_spawn_loc.file_path},{self.thread1_spawn_loc.file_name},{self.thread1_spawn_loc.line}),"
                f"({self.thread1_race_loc.file_path},{self.thread1_race_loc.file_name},{self.thread1_race_loc.line})),"
                f"(({self.thread2_spawn_loc.file_path},{self.thread2_spawn_loc.file_name},{self.thread2_spawn_loc.line}),"
                f"({self.thread2_race_loc.file_path},{self.thread2_race_loc.file_name},{self.thread2_race_loc.line})))"
            )