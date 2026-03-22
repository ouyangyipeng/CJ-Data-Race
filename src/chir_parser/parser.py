# -*- coding: utf-8 -*-
"""
CHIR解析器
解析仓颉编译器生成的CHIR中间语言
"""

import os
import json
import re
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

from .ast_nodes import (
    Module, Function, Class, Variable, BasicBlock, CHIRNode,
    SpawnExpression, SyncExpression, LockExpression, MemoryAccess,
    SourceLocation, AccessType, SyncType
)


class CHIRParser:
    """CHIR中间语言解析器"""
    
    def __init__(self):
        self.current_file: str = ""
        self.current_line: int = 0
        self.modules: List[Module] = []
        
    def parse(self, chir_path: str) -> Optional[Module]:
        """解析CHIR文件"""
        self.current_file = chir_path
        
        if not os.path.exists(chir_path):
            print(f"错误: CHIR文件不存在: {chir_path}")
            return None
        
        # 尝试JSON格式解析
        if chir_path.endswith('.json'):
            return self._parse_json(chir_path)
        
        # 尝试文本格式解析
        return self._parse_text(chir_path)
    
    def _parse_json(self, chir_path: str) -> Optional[Module]:
        """解析JSON格式的CHIR"""
        try:
            with open(chir_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._build_module_from_json(data, chir_path)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
    
    def _build_module_from_json(self, data: Dict, file_path: str) -> Module:
        """从JSON数据构建模块"""
        module = Module(
            name=data.get('name', os.path.basename(file_path)),
            file_path=file_path
        )
        
        # 解析函数
        for func_data in data.get('functions', []):
            func = self._parse_function(func_data)
            if func:
                module.functions.append(func)
        
        # 解析类
        for class_data in data.get('classes', []):
            cls = self._parse_class(class_data)
            if cls:
                module.classes.append(cls)
        
        # 解析全局变量
        for var_data in data.get('globals', []):
            var = self._parse_variable(var_data)
            if var:
                module.global_vars.append(var)
        
        return module
    
    def _parse_function(self, data: Dict) -> Optional[Function]:
        """解析函数定义"""
        func = Function(
            name=data.get('name', ''),
            full_name=data.get('full_name', data.get('name', '')),
            return_type=data.get('return_type', 'void'),
            is_public=data.get('is_public', False),
            location=self._parse_location(data.get('location', {}))
        )
        
        # 解析参数
        for param_data in data.get('parameters', []):
            param = self._parse_variable(param_data)
            if param:
                func.parameters.append(param)
        
        # 解析局部变量
        for var_data in data.get('local_vars', []):
            var = self._parse_variable(var_data)
            if var:
                func.local_vars.append(var)
        
        # 解析基本块
        for bb_data in data.get('basic_blocks', []):
            bb = self._parse_basic_block(bb_data)
            if bb:
                func.basic_blocks.append(bb)
        
        return func
    
    def _parse_class(self, data: Dict) -> Optional[Class]:
        """解析类定义"""
        cls = Class(
            name=data.get('name', ''),
            full_name=data.get('full_name', data.get('name', '')),
            is_public=data.get('is_public', False),
            location=self._parse_location(data.get('location', {}))
        )
        
        # 解析字段
        for field_data in data.get('fields', []):
            field = self._parse_variable(field_data)
            if field:
                cls.fields.append(field)
        
        # 解析方法
        for method_data in data.get('methods', []):
            method = self._parse_function(method_data)
            if method:
                cls.methods.append(method)
        
        return cls
    
    def _parse_variable(self, data: Dict) -> Optional[Variable]:
        """解析变量定义"""
        return Variable(
            name=data.get('name', ''),
            var_type=data.get('type', 'unknown'),
            is_shared=data.get('is_shared', False),
            is_mutable=data.get('is_mutable', True),
            location=self._parse_location(data.get('location', {}))
        )
    
    def _parse_basic_block(self, data: Dict) -> Optional[BasicBlock]:
        """解析基本块"""
        bb = BasicBlock(
            label=data.get('label', ''),
            predecessors=data.get('predecessors', []),
            successors=data.get('successors', []),
            location=self._parse_location(data.get('location', {}))
        )
        
        # 解析语句
        for stmt_data in data.get('statements', []):
            stmt = self._parse_statement(stmt_data)
            if stmt:
                bb.statements.append(stmt)
        
        return bb
    
    def _parse_statement(self, data: Dict) -> Optional[CHIRNode]:
        """解析语句"""
        stmt_type = data.get('type', '')
        
        if stmt_type == 'spawn':
            return self._parse_spawn(data)
        elif stmt_type == 'sync':
            return self._parse_sync(data)
        elif stmt_type == 'lock':
            return self._parse_lock(data)
        elif stmt_type in ('load', 'store', 'read', 'write'):
            return self._parse_memory_access(data)
        else:
            # 通用语句
            return CHIRNode(
                location=self._parse_location(data.get('location', {})),
                metadata=data
            )
    
    def _parse_spawn(self, data: Dict) -> Optional[SpawnExpression]:
        """解析spawn表达式"""
        spawn = SpawnExpression(
            spawn_id=data.get('spawn_id', ''),
            spawn_line=data.get('spawn_line', data.get('location', {}).get('line', 0)),
            location=self._parse_location(data.get('location', {}))
        )
        
        # 解析闭包函数
        closure_data = data.get('closure', {})
        if closure_data:
            spawn.closure = self._parse_function(closure_data)
        
        # 解析捕获的变量
        for var_data in data.get('captured_vars', []):
            var = self._parse_variable(var_data)
            if var:
                var.is_escaped = True  # 被spawn捕获的变量逃逸
                spawn.captured_vars.append(var)
        
        return spawn
    
    def _parse_sync(self, data: Dict) -> Optional[SyncExpression]:
        """解析同步表达式"""
        sync_type_str = data.get('sync_type', 'mutex')
        try:
            sync_type = SyncType(sync_type_str)
        except ValueError:
            sync_type = SyncType.MUTEX
        
        sync = SyncExpression(
            sync_type=sync_type,
            location=self._parse_location(data.get('location', {}))
        )
        
        # 解析同步对象
        target_data = data.get('target', {})
        if target_data:
            sync.target = self._parse_variable(target_data)
        
        # 解析同步体
        for stmt_data in data.get('body', []):
            stmt = self._parse_statement(stmt_data)
            if stmt:
                sync.body.append(stmt)
        
        return sync
    
    def _parse_lock(self, data: Dict) -> Optional[LockExpression]:
        """解析锁表达式"""
        lock_type_str = data.get('lock_type', 'mutex')
        try:
            lock_type = SyncType(lock_type_str)
        except ValueError:
            lock_type = SyncType.MUTEX
        
        lock = LockExpression(
            lock_type=lock_type,
            location=self._parse_location(data.get('location', {}))
        )
        
        # 解析锁变量
        lock_var_data = data.get('lock_var', {})
        if lock_var_data:
            lock.lock_var = self._parse_variable(lock_var_data)
        
        # 解析锁体
        for stmt_data in data.get('body', []):
            stmt = self._parse_statement(stmt_data)
            if stmt:
                lock.body.append(stmt)
        
        return lock
    
    def _parse_memory_access(self, data: Dict) -> Optional[MemoryAccess]:
        """解析内存访问"""
        access_type_str = data.get('type', 'read')
        if access_type_str in ('store', 'write'):
            access_type = AccessType.WRITE
        elif access_type_str in ('load', 'read'):
            access_type = AccessType.READ
        else:
            access_type = AccessType.READ_WRITE
        
        var_data = data.get('variable', data.get('target', {}))
        var = self._parse_variable(var_data) if var_data else None
        
        return MemoryAccess(
            variable=var,
            access_type=access_type,
            is_atomic=data.get('is_atomic', False),
            location=self._parse_location(data.get('location', {}))
        )
    
    def _parse_location(self, data: Dict) -> Optional[SourceLocation]:
        """解析源代码位置"""
        if not data:
            return None
        
        return SourceLocation(
            file_path=data.get('file_path', ''),
            file_name=data.get('file_name', ''),
            line=data.get('line', 0),
            column=data.get('column', 0)
        )
    
    def _parse_text(self, chir_path: str) -> Optional[Module]:
        """解析文本格式的CHIR"""
        # 简化的文本解析，实际CHIR格式需要根据仓颉编译器文档确定
        module = Module(
            name=os.path.basename(chir_path),
            file_path=chir_path
        )
        
        try:
            with open(chir_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用正则表达式提取关键信息
            self._parse_text_content(content, module)
            
        except Exception as e:
            print(f"解析CHIR文本错误: {e}")
            return None
        
        return module
    
    def _parse_text_content(self, content: str, module: Module):
        """解析CHIR文本内容"""
        lines = content.split('\n')
        
        current_func: Optional[Function] = None
        current_class: Optional[Class] = None
        
        for i, line in enumerate(lines, 1):
            self.current_line = i
            line = line.strip()
            
            if not line or line.startswith('//') or line.startswith('#'):
                continue
            
            # 检测函数定义
            func_match = re.match(r'(public\s+)?func\s+(\w+)\s*\(([^)]*)\)', line)
            if func_match:
                if current_func:
                    module.functions.append(current_func)
                current_func = Function(
                    name=func_match.group(2),
                    full_name=func_match.group(2),
                    is_public=func_match.group(1) is not None,
                    location=SourceLocation(module.file_path, os.path.basename(module.file_path), i)
                )
                continue
            
            # 检测spawn
            spawn_match = re.search(r'spawn\s*{', line)
            if spawn_match and current_func:
                spawn = SpawnExpression(
                    spawn_id=f"spawn_{i}",
                    spawn_line=i,
                    location=SourceLocation(module.file_path, os.path.basename(module.file_path), i)
                )
                # 添加到当前基本块
                if current_func.basic_blocks:
                    current_func.basic_blocks[-1].statements.append(spawn)
                continue
            
            # 检测锁
            lock_match = re.search(r'(mutex|rwlock|spinlock)\s*\(\s*(\w+)\s*\)', line)
            if lock_match and current_func:
                try:
                    lock_type = SyncType(lock_match.group(1))
                except ValueError:
                    lock_type = SyncType.MUTEX
                
                lock = LockExpression(
                    lock_type=lock_type,
                    lock_var=Variable(name=lock_match.group(2), var_type='lock'),
                    location=SourceLocation(module.file_path, os.path.basename(module.file_path), i)
                )
                if current_func.basic_blocks:
                    current_func.basic_blocks[-1].statements.append(lock)
                continue
        
        # 添加最后一个函数
        if current_func:
            module.functions.append(current_func)