# -*- coding: utf-8 -*-
"""
CHIR文本格式解析器
解析chir-dis工具生成的.chirtxt文件

CHIR文本格式示例:
func @main.main(): Unit
  %0 = Allocate ...
  %1 = Spawn(%0, ...)
  ...
"""

import os
import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class CHIRExprKind(Enum):
    """CHIR表达式类型"""
    # 终结符
    GOTO = "GoTo"
    BRANCH = "Branch"
    EXIT = "Exit"
    
    # 内存操作
    LOAD = "Load"
    STORE = "Store"
    ALLOCATE = "Allocate"
    GET_ELEMENT_REF = "GetElementRef"
    
    # Spawn表达式
    SPAWN = "Spawn"
    SPAWN_WITH_EXCEPTION = "SpawnWithException"
    
    # 函数调用
    APPLY = "Apply"
    INVOKE = "Invoke"
    INVOKE_STATIC = "InvokeStatic"
    
    # 同步原语
    INTRINSIC = "Intrinsic"
    
    # 其他
    CONSTANT = "Constant"
    FIELD = "Field"
    TUPLE = "Tuple"
    LAMBDA = "Lambda"
    IF = "If"
    LOOP = "Loop"
    
    # 未知
    UNKNOWN = "Unknown"


@dataclass
class CHIRValue:
    """CHIR值"""
    id: int  # 值编号，如 %0, %1
    name: str = ""
    type_name: str = ""
    is_global: bool = False
    is_parameter: bool = False
    source_location: Optional[Tuple[str, int, int]] = None  # (file, line, col)


@dataclass
class CHIRExpression:
    """CHIR表达式"""
    result_var: Optional[int] = None  # 结果变量编号
    kind: CHIRExprKind = CHIRExprKind.UNKNOWN
    operands: List[int] = field(default_factory=list)  # 操作数变量编号
    raw_text: str = ""
    source_location: Optional[Tuple[str, int, int]] = None


@dataclass
class CHIRBlock:
    """CHIR基本块"""
    id: int
    label: str = ""
    expressions: List[CHIRExpression] = field(default_factory=list)
    predecessors: Set[int] = field(default_factory=set)
    successors: Set[int] = field(default_factory=set)


@dataclass
class CHIRFunction:
    """CHIR函数"""
    name: str
    full_name: str = ""
    return_type: str = "Unit"
    parameters: List[CHIRValue] = field(default_factory=list)
    local_values: Dict[int, CHIRValue] = field(default_factory=dict)
    blocks: Dict[int, CHIRBlock] = field(default_factory=dict)
    entry_block: Optional[int] = None
    spawn_expressions: List[CHIRExpression] = field(default_factory=list)
    memory_accesses: List[CHIRExpression] = field(default_factory=list)
    source_location: Optional[Tuple[str, int, int]] = None


@dataclass
class CHIRClass:
    """CHIR类定义"""
    name: str
    full_name: str = ""
    fields: Dict[str, str] = field(default_factory=dict)  # name -> type
    methods: List[CHIRFunction] = field(default_factory=list)
    source_location: Optional[Tuple[str, int, int]] = None


@dataclass
class CHIRModule:
    """CHIR模块"""
    name: str
    file_path: str
    functions: List[CHIRFunction] = field(default_factory=list)
    classes: List[CHIRClass] = field(default_factory=list)
    global_values: Dict[int, CHIRValue] = field(default_factory=dict)
    
    # 并发相关信息
    spawn_points: List[Tuple[CHIRFunction, CHIRExpression]] = field(default_factory=list)
    shared_variables: Set[int] = field(default_factory=set)


class CHIRTextParser:
    """CHIR文本格式解析器"""
    
    # 正则表达式模式
    FUNC_PATTERN = re.compile(r'^func\s+@([\w.]+)\(\s*:\s*(\w+)')
    CLASS_PATTERN = re.compile(r'^class\s+@([\w.]+)')
    BLOCK_PATTERN = re.compile(r'^(\w+):')
    VALUE_DEF_PATTERN = re.compile(r'^%(\d+)\s*=\s*(.+)')
    VALUE_REF_PATTERN = re.compile(r'%(\d+)')
    LOCATION_PATTERN = re.compile(r'loc\("([^"]+)",\s*(\d+),\s*(\d+)\)')
    
    def __init__(self):
        self.current_file: str = ""
        self.lines: List[str] = []
        self.line_idx: int = 0
        
    def parse_file(self, file_path: str) -> Optional[CHIRModule]:
        """解析CHIR文本文件"""
        if not os.path.exists(file_path):
            print(f"错误: CHIR文件不存在: {file_path}")
            return None
        
        self.current_file = file_path
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.lines = f.readlines()
        except Exception as e:
            print(f"读取文件错误: {e}")
            return None
        
        module = CHIRModule(
            name=os.path.basename(file_path).replace('.chirtxt', ''),
            file_path=file_path
        )
        
        self.line_idx = 0
        while self.line_idx < len(self.lines):
            line = self.lines[self.line_idx].strip()
            
            if line.startswith('func '):
                func = self._parse_function()
                if func:
                    module.functions.append(func)
                    # 收集spawn点
                    for expr in func.spawn_expressions:
                        module.spawn_points.append((func, expr))
            elif line.startswith('class '):
                cls = self._parse_class()
                if cls:
                    module.classes.append(cls)
            else:
                self.line_idx += 1
        
        # 分析共享变量
        self._analyze_shared_variables(module)
        
        return module
    
    def _parse_function(self) -> Optional[CHIRFunction]:
        """解析函数定义"""
        line = self.lines[self.line_idx].strip()
        match = self.FUNC_PATTERN.match(line)
        if not match:
            self.line_idx += 1
            return None
        
        full_name = match.group(1)
        return_type = match.group(2)
        name = full_name.split('.')[-1]
        
        func = CHIRFunction(
            name=name,
            full_name=full_name,
            return_type=return_type
        )
        
        self.line_idx += 1
        
        # 解析函数体
        current_block: Optional[CHIRBlock] = None
        indent_level = len(self.lines[self.line_idx - 1]) - len(self.lines[self.line_idx - 1].lstrip())
        
        while self.line_idx < len(self.lines):
            line = self.lines[self.line_idx]
            stripped = line.strip()
            
            # 检查缩进，如果缩进减少到函数级别，则函数结束
            if stripped and not line.startswith(' ' * (indent_level + 1)) and not line.startswith('\t'):
                if stripped.startswith('func ') or stripped.startswith('class '):
                    break
            
            if not stripped:
                self.line_idx += 1
                continue
            
            # 解析基本块标签
            block_match = self.BLOCK_PATTERN.match(stripped)
            if block_match:
                block_label = block_match.group(1)
                block_id = len(func.blocks)
                current_block = CHIRBlock(id=block_id, label=block_label)
                func.blocks[block_id] = current_block
                if func.entry_block is None:
                    func.entry_block = block_id
                self.line_idx += 1
                continue
            
            # 解析值定义和表达式
            value_match = self.VALUE_DEF_PATTERN.match(stripped)
            if value_match:
                var_id = int(value_match.group(1))
                expr_text = value_match.group(2)
                
                expr = self._parse_expression(expr_text)
                expr.result_var = var_id
                
                # 提取源码位置
                loc_match = self.LOCATION_PATTERN.search(stripped)
                if loc_match:
                    expr.source_location = (
                        loc_match.group(1),
                        int(loc_match.group(2)),
                        int(loc_match.group(3))
                    )
                
                if current_block:
                    current_block.expressions.append(expr)
                
                # 记录特殊表达式
                if expr.kind == CHIRExprKind.SPAWN or expr.kind == CHIRExprKind.SPAWN_WITH_EXCEPTION:
                    func.spawn_expressions.append(expr)
                elif expr.kind in (CHIRExprKind.LOAD, CHIRExprKind.STORE):
                    func.memory_accesses.append(expr)
                
                # 记录局部值
                if var_id not in func.local_values:
                    func.local_values[var_id] = CHIRValue(
                        id=var_id,
                        type_name=self._extract_type_from_expr(expr_text)
                    )
            
            self.line_idx += 1
        
        return func
    
    def _parse_expression(self, expr_text: str) -> CHIRExpression:
        """解析表达式"""
        expr = CHIRExpression(raw_text=expr_text)
        
        # 提取操作数
        operands = [int(m.group(1)) for m in self.VALUE_REF_PATTERN.finditer(expr_text)]
        expr.operands = operands
        
        # 确定表达式类型
        expr_text_upper = expr_text.upper()
        
        if expr_text.startswith('Spawn(') or expr_text.startswith('Spawn '):
            expr.kind = CHIRExprKind.SPAWN
        elif 'SpawnWithException' in expr_text:
            expr.kind = CHIRExprKind.SPAWN_WITH_EXCEPTION
        elif expr_text.startswith('Load('):
            expr.kind = CHIRExprKind.LOAD
        elif expr_text.startswith('Store('):
            expr.kind = CHIRExprKind.STORE
        elif expr_text.startswith('Allocate('):
            expr.kind = CHIRExprKind.ALLOCATE
        elif expr_text.startswith('GetElementRef('):
            expr.kind = CHIRExprKind.GET_ELEMENT_REF
        elif expr_text.startswith('Apply('):
            expr.kind = CHIRExprKind.APPLY
        elif expr_text.startswith('Invoke('):
            expr.kind = CHIRExprKind.INVOKE
        elif expr_text.startswith('InvokeStatic('):
            expr.kind = CHIRExprKind.INVOKE_STATIC
        elif expr_text.startswith('Intrinsic('):
            expr.kind = CHIRExprKind.INTRINSIC
        elif expr_text.startswith('GoTo '):
            expr.kind = CHIRExprKind.GOTO
        elif expr_text.startswith('Branch '):
            expr.kind = CHIRExprKind.BRANCH
        elif expr_text.startswith('Exit'):
            expr.kind = CHIRExprKind.EXIT
        elif expr_text.startswith('Constant('):
            expr.kind = CHIRExprKind.CONSTANT
        elif expr_text.startswith('Field('):
            expr.kind = CHIRExprKind.FIELD
        elif expr_text.startswith('If('):
            expr.kind = CHIRExprKind.IF
        elif expr_text.startswith('Loop('):
            expr.kind = CHIRExprKind.LOOP
        elif expr_text.startswith('Lambda('):
            expr.kind = CHIRExprKind.LAMBDA
        
        return expr
    
    def _extract_type_from_expr(self, expr_text: str) -> str:
        """从表达式中提取类型信息"""
        # 查找 ": Type" 模式
        type_match = re.search(r':\s*([\w.<>\[\],\s]+)\s*=', expr_text)
        if type_match:
            return type_match.group(1).strip()
        return ""
    
    def _parse_class(self) -> Optional[CHIRClass]:
        """解析类定义"""
        line = self.lines[self.line_idx].strip()
        match = self.CLASS_PATTERN.match(line)
        if not match:
            self.line_idx += 1
            return None
        
        full_name = match.group(1)
        name = full_name.split('.')[-1]
        
        cls = CHIRClass(
            name=name,
            full_name=full_name
        )
        
        self.line_idx += 1
        
        # 解析类体（简化处理）
        while self.line_idx < len(self.lines):
            line = self.lines[self.line_idx].strip()
            if line.startswith('func ') or line.startswith('class '):
                break
            self.line_idx += 1
        
        return cls
    
    def _analyze_shared_variables(self, module: CHIRModule):
        """分析共享变量"""
        # 查找被多个spawn访问的变量
        spawn_accessed_vars: Dict[int, int] = {}  # var_id -> spawn_count
        
        for func, spawn_expr in module.spawn_points:
            for op_var in spawn_expr.operands:
                if op_var in spawn_accessed_vars:
                    spawn_accessed_vars[op_var] += 1
                else:
                    spawn_accessed_vars[op_var] = 1
        
        # 被多个spawn访问的变量可能是共享的
        for var_id, count in spawn_accessed_vars.items():
            if count > 1:
                module.shared_variables.add(var_id)
    
    def parse_directory(self, dir_path: str) -> List[CHIRModule]:
        """解析目录中的所有CHIR文件"""
        modules = []
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.chirtxt'):
                    file_path = os.path.join(root, file)
                    module = self.parse_file(file_path)
                    if module:
                        modules.append(module)
        
        return modules


def detect_races_from_chir(module: CHIRModule) -> List[Dict]:
    """从CHIR模块检测数据竞争"""
    races = []
    
    # 收集每个spawn点访问的变量
    spawn_accesses: List[Tuple[CHIRFunction, CHIRExpression, Set[int]]] = []
    
    for func in module.functions:
        for spawn in func.spawn_expressions:
            # 分析spawn表达式访问的变量
            accessed_vars = set(spawn.operands)
            
            # 查找spawn闭包中的内存访问
            # 简化处理：假设spawn的操作数就是闭包变量
            spawn_accesses.append((func, spawn, accessed_vars))
    
    # 检查spawn对之间的竞争
    for i, (func1, spawn1, vars1) in enumerate(spawn_accesses):
        for func2, spawn2, vars2 in spawn_accesses[i+1:]:
            # 查找共享变量
            shared = vars1 & vars2
            if shared:
                # 检查是否有写操作
                # 简化处理：假设所有访问都可能导致竞争
                for var_id in shared:
                    race = {
                        'type': 'RW',  # 或 'WW'
                        'variable': f'%{var_id}',
                        'location1': spawn1.source_location or (func1.full_name, 0, 0),
                        'location2': spawn2.source_location or (func2.full_name, 0, 0),
                        'thread1': f'spawn@{func1.full_name}',
                        'thread2': f'spawn@{func2.full_name}'
                    }
                    races.append(race)
    
    return races