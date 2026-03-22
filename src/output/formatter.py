# -*- coding: utf-8 -*-
"""
输出格式化模块
按照赛题要求的格式输出数据竞争检测结果
"""

from typing import List, Dict
from chir_parser.ast_nodes import RaceCondition


class OutputFormatter:
    """输出格式化器"""
    
    def __init__(self, races: List[RaceCondition]):
        self.races = races
    
    def format(self) -> str:
        """格式化输出结果"""
        if not self.races:
            return ""
        
        lines = []
        for race in self.races:
            line = self._format_race(race)
            if line:
                lines.append(line)
        
        return "\n".join(lines)
    
    def _format_race(self, race: RaceCondition) -> str:
        """格式化单条数据竞争记录"""
        if race.is_public_interface:
            return self._format_public_race(race)
        else:
            return self._format_thread_race(race)
    
    def _format_thread_race(self, race: RaceCondition) -> str:
        """
        格式化线程间数据竞争
        格式: (RaceType，((filePath1,fileName1,spawnLine1),(filePath1',fileName1',raceLine1')),((filePath2,fileName2,spawnLine2),(filePath2',fileName2',raceLine2')))
        """
        return (
            f"({race.race_type},"
            f"(({race.thread1_spawn_loc.file_path},{race.thread1_spawn_loc.file_name},{race.thread1_spawn_loc.line}),"
            f"({race.thread1_race_loc.file_path},{race.thread1_race_loc.file_name},{race.thread1_race_loc.line})),"
            f"(({race.thread2_spawn_loc.file_path},{race.thread2_spawn_loc.file_name},{race.thread2_spawn_loc.line}),"
            f"({race.thread2_race_loc.file_path},{race.thread2_race_loc.file_name},{race.thread2_race_loc.line})))"
        )
    
    def _format_public_race(self, race: RaceCondition) -> str:
        """
        格式化public接口数据竞争
        格式: (RaceType，((filePath1,fileName1,declareLine1),(filePath1',fileName1',raceLine1')),((filePath2,fileName2,declareLine2),(filePath2',fileName2',raceLine2')))
        """
        return (
            f"({race.race_type},"
            f"(({race.thread1_spawn_loc.file_path},{race.thread1_spawn_loc.file_name},{race.declare_line1}),"
            f"({race.thread1_race_loc.file_path},{race.thread1_race_loc.file_name},{race.thread1_race_loc.line})),"
            f"(({race.thread2_spawn_loc.file_path},{race.thread2_spawn_loc.file_name},{race.declare_line2}),"
            f"({race.thread2_race_loc.file_path},{race.thread2_race_loc.file_name},{race.thread2_race_loc.line})))"
        )
    
    def to_json(self) -> List[Dict]:
        """转换为JSON格式"""
        result = []
        for race in self.races:
            item = {
                "race_type": race.race_type,
                "thread1": {
                    "spawn_location": {
                        "file_path": race.thread1_spawn_loc.file_path,
                        "file_name": race.thread1_spawn_loc.file_name,
                        "line": race.thread1_spawn_loc.line
                    },
                    "race_location": {
                        "file_path": race.thread1_race_loc.file_path,
                        "file_name": race.thread1_race_loc.file_name,
                        "line": race.thread1_race_loc.line
                    }
                },
                "thread2": {
                    "spawn_location": {
                        "file_path": race.thread2_spawn_loc.file_path,
                        "file_name": race.thread2_spawn_loc.file_name,
                        "line": race.thread2_spawn_loc.line
                    },
                    "race_location": {
                        "file_path": race.thread2_race_loc.file_path,
                        "file_name": race.thread2_race_loc.file_name,
                        "line": race.thread2_race_loc.line
                    }
                },
                "variable": race.variable.name if race.variable else "unknown",
                "is_public_interface": race.is_public_interface
            }
            
            if race.is_public_interface:
                item["declare_lines"] = {
                    "function1": race.declare_line1,
                    "function2": race.declare_line2
                }
            
            result.append(item)
        
        return result
    
    def get_summary(self) -> str:
        """获取检测摘要"""
        total = len(self.races)
        rw_count = sum(1 for r in self.races if r.race_type == "RW")
        ww_count = sum(1 for r in self.races if r.race_type == "WW")
        public_count = sum(1 for r in self.races if r.is_public_interface)
        
        return (
            f"数据竞争检测摘要:\n"
            f"  总计: {total} 个潜在数据竞争\n"
            f"  读写竞争(RW): {rw_count} 个\n"
            f"  写写竞争(WW): {ww_count} 个\n"
            f"  公共接口竞争: {public_count} 个"
        )