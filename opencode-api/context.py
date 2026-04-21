#!/usr/bin/env python3
"""
上下文信息模块 - 存储当前调用的会话信息
"""
from typing import Optional

# 当前 QwenPaw Session ID（由 main.py 设置）
current_session_id: Optional[str] = None