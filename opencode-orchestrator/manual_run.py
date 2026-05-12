#!/usr/bin/env python3
"""
使用 orchestrator 的 run_once 逐轮执行任务
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import run_once, load_tasks, save_tasks
import json

# 任务描述
phase_a_task = """你是一个经验丰富的 .NET WPF 开发者，负责为 opencode-desktop 项目实现聊天输入区域的增强功能。

## 项目背景
opencode-desktop 是一个类似 Cursor 的 IDE 项目，使用 WPF 开发。项目位于 E:\\Work\\Code\\Tools\\AutoDev。

## 当前任务
请根据以下需求完成 Phase A 输入区增强功能的开发。

### Task A1: 富文本 Prompt 输入支持
- 调研并引入富文本编辑器组件（如 AvalonEdit 或自定义实现）
- 扩展 ChatComposerControl 支持 Markdown 语法高亮
- 实现 Enter 提交 / Shift+Enter 换行的可配置行为
- 验证：输入多行文本并使用 Shift+Enter 换行，功能正常；Markdown 内容正确渲染；提交后输入框正确清空

### Task A2: Slash Command 实现
- 定义 slash command 数据模型（CommandInfo）
- 实现命令解析器，识别 / 开头的输入
- 添加命令下拉建议列表组件
- 实现命令执行逻辑与 autocomplete
- 验证：输入 / 触发命令下拉列表；键盘上下导航选择命令；选择命令后正确插入到输入框；Tab 键自动补全命令

### Task A3: @agent 插入功能
- 实现 AgentSelector 下拉组件
- 扩展输入解析器识别 @ 语法
- 添加 @ 触发的 agent 候选列表
- 插入选中 agent 到输入框
- 验证：输入 @ 触发 agent 列表弹出；选择 agent 后正确插入 mention；发送消息时 mention 信息正确传递

### Task A4: 文件/图片附件支持
- 实现附件上传组件（拖拽 + 按钮选择）
- 支持常见图片格式预览（JPG/PNG/GIF/WebP）
- 实现附件删除与重命名
- 将附件信息集成到消息发送流程
- 验证：拖拽文件到输入区成功上传；图片附件显示缩略图；非图片文件显示文件名与图标；删除附件后不再出现在发送内容中

### Task A5: 上下文文件注入
- 实现 ContextChipsPanel 上下文管理组件
- 支持文件/文件夹添加为上下文
- 实现上下文文件的语法高亮展示
- 支持上下文的移除与编辑
- 验证：添加文件到上下文后显示为 chip；chip 显示文件名，可点击打开；删除 chip 后上下文正确更新；发送消息时上下文信息正确传递

## 要求
1. 请先查看项目现有结构，了解代码组织方式
2. 遵循项目现有代码风格
3. 确保代码可编译运行
4. 完成后明确说明"Phase A 开发完成"
"""

# 检查当前任务状态
tasks = load_tasks()
print("=== 当前任务状态 ===")
for t in tasks['tasks']:
    print(f"  {t['id']}: status={t['status']}, session_id={t.get('session_id')}")

# 手动设置 session_id
for t in tasks['tasks']:
    if t['id'] == 'phase_a':
        t['session_id'] = 'ses_25c17f883ffeU3gI4VTt1JpS37'
        t['status'] = 'processing'

save_tasks(tasks)
print("\n已更新 phase_a 任务状态和 session_id")

# 继续调用 run_once
print("\n=== 调用 run_once ===")
result = run_once()
print(json.dumps(result, ensure_ascii=False, indent=2))
