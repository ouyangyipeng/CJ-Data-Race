# CJ-Data-Race: 仓颉数据竞争静态检测工具

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

2026年全国大学生计算机系统能力大赛编译系统设计挑战赛（华为毕昇杯）参赛作品。

## 项目简介

CJ-Data-Race 是一个静态程序分析工具，用于检测仓颉（Cangjie）编程语言代码中的数据竞争问题。

### 主要特性

- ✅ **源码解析**: 直接解析仓颉源代码(.cj文件)
- ✅ **CHIR支持**: 支持解析CHIR中间语言文本格式
- ✅ **多同步原语**: 支持Mutex、RWLock、SpinLock、Atomic、Channel等
- ✅ **数据流分析**: 实现基本的数据流分析框架
- ✅ **低误报率**: 通过同步保护分析减少误报

## 快速开始

### 环境要求

- Python 3.8 或更高版本
- 无需额外依赖

### 安装

```bash
git clone https://github.com/ouyangyipeng/CJ-Data-Race.git
cd CJ-Data-Race
```

### 使用方法

```bash
# 检测单个项目
python3 run_detector.py <项目目录>

# 示例
python3 run_detector.py test_cases/case1_basic_race
```

### 输出格式

检测结果按照赛题要求格式输出：

```
(RaceType,((filePath1,fileName1,spawnLine1),(filePath1',fileName1',raceLine1')),((filePath2,fileName2,spawnLine2),(filePath2',fileName2',raceLine2')))
```

- `RaceType`: 竞争类型，`RW`(读写)或`WW`(写写)
- 第一个元组: 第一个线程的spawn位置和竞争位置
- 第二个元组: 第二个线程的spawn位置和竞争位置

## 项目结构

```
CJ-Data-Race/
├── src/
│   ├── chir_parser/           # CHIR解析模块
│   │   ├── parser.py          # 基础CHIR解析器
│   │   ├── chir_text_parser.py # CHIR文本格式解析器
│   │   ├── cangjie_parser.py  # 仓颉源码解析器
│   │   └── ast_nodes.py       # AST节点定义
│   ├── analyzer/              # 分析模块
│   │   ├── concurrency.py     # 并发分析器
│   │   ├── enhanced_concurrency.py # 增强版并发分析器
│   │   └── race_detector.py   # 数据竞争检测器
│   ├── output/                # 输出模块
│   │   └── formatter.py       # 输出格式化器
│   └── main.py                # 主入口
├── tests/                     # 测试
│   └── test_race_detection.py
├── test_cases/                # 测试用例
│   ├── case1_basic_race/      # 基本写写竞争
│   ├── case2_rw_race/         # 读写竞争
│   ├── case3_no_race_sync/    # 同步保护无竞争
│   ├── case4_public_interface/ # 公共接口竞争
│   └── case5_no_race/         # 无竞争
├── docs/                      # 文档
│   └── 设计文档.md
├── run_detector.py            # 运行脚本
└── README.md
```

## 测试用例

| 测试用例 | 描述 | 预期结果 | 状态 |
|---------|------|---------|------|
| case1_basic_race | 两个线程写同一变量 | 1个WW竞争 | ✅ |
| case2_rw_race | 一个线程读，一个线程写 | 1个RW竞争 | ✅ |
| case3_no_race_sync | 使用Mutex保护 | 0个竞争 | ✅ |
| case4_public_interface | 公共函数访问共享变量 | 1个竞争 | ✅ |
| case5_no_race | 访问不同变量 | 0个竞争 | ✅ |
| case6_rwlock | RWLock读写锁保护 | 0个竞争 | ✅ |
| case7_atomic | Atomic原子操作 | 0个竞争 | ✅ |
| case8_nested_spawn | 嵌套spawn竞争 | 3个WW竞争 | ✅ |
| case9_channel | Channel通道通信 | 0个竞争 | ✅ |
| case10_synchronized | synchronized块保护 | 0个竞争 | ✅ |
| case11_escaped_var | 逃逸变量竞争 | 1个WW竞争 | ✅ |
| case12_function_call | 函数调用竞争 | 1个RW竞争 | ✅ |
| case13_array_access | 数组访问竞争 | 1个RW竞争 | ✅ |
| case14_class_member | 类成员访问竞争 | 2个RW竞争 | ✅ |
| case15_conditional | 条件分支竞争 | 1个RW竞争 | ✅ |
| case16_multi_file | 多文件项目 | 1个WW竞争 | ✅ |
| case17_loop_race | 循环中的数据竞争 | 1个WW竞争 | ✅ |
| case18_struct_member | 结构体成员竞争 | 2个RW竞争 | ✅ |
| case19_reentrant_lock | 可重入锁保护 | 0个竞争 | ✅ |
| case20_multiple_vars | 多变量竞争 | 5个竞争 | ✅ |
| case21_deep_nested | 深层嵌套spawn | 6个WW竞争 | ✅ |
| case22_mutex_trylock | tryLock保护 | 0个竞争 | ✅ |
| case23_pointer_dereference | 指针解引用竞争 | 1个RW竞争 | ✅ |
| case24_future_race | Future相关竞争 | 3个竞争 | ✅ |
| case25_static_var | 静态变量竞争 | 6个竞争 | ✅ |
| case26_closure_capture | 闭包捕获变量竞争 | 2个WW竞争 | ✅ |
| case27_lamda_spawn | lambda表达式spawn | 1个WW竞争 | ✅ |
| case28_thread_local | 线程局部变量 | 0个竞争 | ✅ |
| case29_volatile_access | 多重锁保护(不同锁) | 1个WW竞争 | ✅ |
| case30_rwlock_readwrite | RWLock读写分离 | 0个竞争 | ✅ |
| case31_wait_notify | 条件变量等待通知 | 0个竞争 | ✅ |
| case32_producer_consumer | 生产者消费者模式 | 0个竞争 | ✅ |
| case33_recursive_function | 递归函数竞争 | 1个WW竞争 | ✅ |
| case34_interface_impl | 接口实现竞争 | 0个竞争 | ✅ |
| case35_dataclass_race | 数据类成员竞争 | 6个竞争 | ✅ |

**鲲鹏920环境测试结果** (2026-03-24 更新):
- 35个测试用例全部通过
- 平均执行时间: ~0.7毫秒/用例
- 总耗时: 0.025秒 (35个用例)
- 内存占用: ~12MB
- 远低于赛题要求的5分钟限制
- 测试环境: 192核鲲鹏920、8卡昇腾910B4、1.5T内存

运行测试：

```bash
python3 -m pytest tests/
```

## 技术架构

### 检测算法

1. **源码解析**: 解析仓颉源码，提取AST结构
2. **线程识别**: 识别所有spawn表达式创建的线程
3. **访问分析**: 分析每个线程的变量读写操作
4. **同步分析**: 识别同步区域和保护关系
5. **竞争检测**: 检测线程间和公共接口的数据竞争

### 支持的同步原语

- `synchronized` 块
- `Mutex` (lock/unlock)
- `RWLock` (readLock/writeLock)
- `SpinLock`
- `Atomic` 类型
- `Channel` 通信

## 作为库使用

```python
from src.chir_parser import CangjieParser
from src.analyzer import RaceDetector, EnhancedConcurrencyAnalyzer

# 解析源码
parser = CangjieParser()
modules = parser.parse_directory("path/to/project")

# 检测竞争
detector = RaceDetector(modules)
races = detector.detect()

# 输出结果
for race in races:
    print(race.to_output_format())
```

## 文档

- [新手指引](docs/新手指引.md) - 面向新成员的项目介绍
- [设计文档](docs/设计文档.md) - 详细的技术设计文档
- [进度记录](PROGRESS.md) - 项目开发进度
- [优化计划](plans/optimization_plan.md) - 后续优化方向

## 许可证

本项目采用 Apache 2.0 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request。

## 作者

ouyangyipeng

## 致谢

感谢华为毕昇杯组委会提供的技术支持和仓颉语言开源社区。