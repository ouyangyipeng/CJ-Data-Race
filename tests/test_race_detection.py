# -*- coding: utf-8 -*-
"""
测试用例 - 数据竞争检测
"""

import os
import sys
import unittest
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chir_parser.parser import CHIRParser
from chir_parser.ast_nodes import (
    Module, Function, Variable, SpawnExpression, MemoryAccess,
    SourceLocation, AccessType, RaceCondition
)
from analyzer.concurrency import ConcurrencyAnalyzer
from analyzer.race_detector import RaceDetector
from output.formatter import OutputFormatter


class TestCHIRParser(unittest.TestCase):
    """测试CHIR解析器"""
    
    def test_parse_json_module(self):
        """测试JSON格式模块解析"""
        parser = CHIRParser()
        # 创建测试数据
        test_data = {
            'name': 'test_module',
            'functions': [
                {
                    'name': 'main',
                    'full_name': 'test_module.main',
                    'is_public': True,
                    'parameters': [],
                    'local_vars': [
                        {'name': 'x', 'type': 'int', 'is_shared': True}
                    ]
                }
            ]
        }
        
        module = parser._build_module_from_json(test_data, 'test.chir.json')
        self.assertIsNotNone(module)
        self.assertEqual(module.name, 'test_module')
        self.assertEqual(len(module.functions), 1)
        self.assertEqual(module.functions[0].name, 'main')
    
    def test_parse_variable(self):
        """测试变量解析"""
        parser = CHIRParser()
        var_data = {
            'name': 'counter',
            'type': 'int64',
            'is_shared': True,
            'is_mutable': True
        }
        
        var = parser._parse_variable(var_data)
        self.assertIsNotNone(var)
        self.assertEqual(var.name, 'counter')
        self.assertEqual(var.var_type, 'int64')
        self.assertTrue(var.is_shared)
    
    def test_parse_spawn(self):
        """测试spawn表达式解析"""
        parser = CHIRParser()
        spawn_data = {
            'spawn_id': 'spawn_1',
            'spawn_line': 10,
            'location': {
                'file_path': '/test',
                'file_name': 'test.cj',
                'line': 10
            },
            'captured_vars': [
                {'name': 'x', 'type': 'int'}
            ]
        }
        
        spawn = parser._parse_spawn(spawn_data)
        self.assertIsNotNone(spawn)
        self.assertEqual(spawn.spawn_id, 'spawn_1')
        self.assertEqual(spawn.spawn_line, 10)
        self.assertEqual(len(spawn.captured_vars), 1)


class TestConcurrencyAnalyzer(unittest.TestCase):
    """测试并发分析器"""
    
    def setUp(self):
        """设置测试环境"""
        self.module = Module(
            name='test_module',
            file_path='/test/test.cj'
        )
        
        # 创建测试函数
        self.func = Function(
            name='main',
            full_name='test_module.main',
            location=SourceLocation('/test', 'test.cj', 1)
        )
        
        # 创建共享变量
        self.shared_var = Variable(
            name='counter',
            var_type='int64',
            is_shared=True
        )
        
        self.func.local_vars = [self.shared_var]
        self.module.functions = [self.func]
    
    def test_analyze_module(self):
        """测试模块分析"""
        analyzer = ConcurrencyAnalyzer([self.module])
        thread_info = analyzer.analyze()
        
        self.assertIsNotNone(thread_info)
    
    def test_shared_variable_detection(self):
        """测试共享变量检测"""
        analyzer = ConcurrencyAnalyzer([self.module])
        analyzer.analyze()
        
        shared_vars = analyzer.get_shared_variables()
        # 初始情况下没有并发访问
        self.assertEqual(len(shared_vars), 0)


class TestRaceDetector(unittest.TestCase):
    """测试数据竞争检测器"""
    
    def setUp(self):
        """设置测试环境"""
        self.module = Module(
            name='test_module',
            file_path='/test/test.cj'
        )
        
        self.func = Function(
            name='main',
            full_name='test_module.main',
            location=SourceLocation('/test', 'test.cj', 1)
        )
        
        self.module.functions = [self.func]
    
    def test_detect_no_race(self):
        """测试无竞争情况"""
        detector = RaceDetector([self.module], {})
        races = detector.detect()
        
        # 无并发访问，应该没有竞争
        self.assertEqual(len(races), 0)
    
    def test_race_condition_creation(self):
        """测试竞争条件创建"""
        race = RaceCondition(
            race_type="RW",
            thread1_spawn_loc=SourceLocation('/test', 'test.cj', 5),
            thread1_race_loc=SourceLocation('/test', 'test.cj', 10),
            thread2_spawn_loc=SourceLocation('/test', 'test.cj', 6),
            thread2_race_loc=SourceLocation('/test', 'test.cj', 12),
            variable=Variable(name='x', var_type='int')
        )
        
        self.assertEqual(race.race_type, "RW")
        self.assertIsNotNone(race.variable)


class TestOutputFormatter(unittest.TestCase):
    """测试输出格式化器"""
    
    def test_format_empty_races(self):
        """测试空竞争列表格式化"""
        formatter = OutputFormatter([])
        output = formatter.format()
        self.assertEqual(output, "")
    
    def test_format_thread_race(self):
        """测试线程竞争格式化"""
        race = RaceCondition(
            race_type="RW",
            thread1_spawn_loc=SourceLocation('/test/src', 'test.cj', 5),
            thread1_race_loc=SourceLocation('/test/src', 'test.cj', 10),
            thread2_spawn_loc=SourceLocation('/test/src', 'test.cj', 6),
            thread2_race_loc=SourceLocation('/test/src', 'test.cj', 12),
            variable=Variable(name='x', var_type='int')
        )
        
        formatter = OutputFormatter([race])
        output = formatter.format()
        
        self.assertIn("RW", output)
        self.assertIn("test.cj", output)
    
    def test_format_public_race(self):
        """测试public接口竞争格式化"""
        race = RaceCondition(
            race_type="WW",
            thread1_spawn_loc=SourceLocation('/test/src', 'test.cj', 5),
            thread1_race_loc=SourceLocation('/test/src', 'test.cj', 10),
            thread2_spawn_loc=SourceLocation('/test/src', 'test.cj', 8),
            thread2_race_loc=SourceLocation('/test/src', 'test.cj', 15),
            variable=Variable(name='counter', var_type='int64'),
            is_public_interface=True,
            declare_line1=5,
            declare_line2=8
        )
        
        formatter = OutputFormatter([race])
        output = formatter.format()
        
        self.assertIn("WW", output)
        self.assertIn("test.cj", output)
    
    def test_get_summary(self):
        """测试摘要输出"""
        races = [
            RaceCondition(
                race_type="RW",
                thread1_spawn_loc=SourceLocation('/test', 'test.cj', 5),
                thread1_race_loc=SourceLocation('/test', 'test.cj', 10),
                thread2_spawn_loc=SourceLocation('/test', 'test.cj', 6),
                thread2_race_loc=SourceLocation('/test', 'test.cj', 12),
                variable=Variable(name='x', var_type='int')
            ),
            RaceCondition(
                race_type="WW",
                thread1_spawn_loc=SourceLocation('/test', 'test.cj', 7),
                thread1_race_loc=SourceLocation('/test', 'test.cj', 11),
                thread2_spawn_loc=SourceLocation('/test', 'test.cj', 8),
                thread2_race_loc=SourceLocation('/test', 'test.cj', 13),
                variable=Variable(name='y', var_type='int')
            )
        ]
        
        formatter = OutputFormatter(races)
        summary = formatter.get_summary()
        
        self.assertIn("总计: 2", summary)
        self.assertIn("读写竞争(RW): 1", summary)
        self.assertIn("写写竞争(WW): 1", summary)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_pipeline(self):
        """测试完整流程"""
        # 创建测试模块
        module = Module(
            name='test',
            file_path='/test/test.cj'
        )
        
        func = Function(
            name='main',
            full_name='test.main',
            location=SourceLocation('/test', 'test.cj', 1)
        )
        
        module.functions = [func]
        
        # 分析
        analyzer = ConcurrencyAnalyzer([module])
        thread_info = analyzer.analyze()
        
        # 检测
        detector = RaceDetector([module], thread_info)
        races = detector.detect()
        
        # 输出
        formatter = OutputFormatter(races)
        output = formatter.format()
        
        # 验证
        self.assertIsNotNone(output)


if __name__ == '__main__':
    unittest.main()