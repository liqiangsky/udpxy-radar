"""
数据清洗器模块：
每个数据源对应一个独立的清洗函数，文件名与 source_type 对应。
通用格式: {source_type}_cleaner.py，必须实现 clean(data: dict) -> list[dict]
"""
