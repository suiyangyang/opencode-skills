---
name: opencode-orchestrator
description: 自动化开发任务调度器，支持任务树管理、开发测试流程自动化（不含 /opencode 命令处理）
metadata:
  {
    "copaw": { "emoji": "🔧" }
  }
---

# OpenCode Orchestrator

通过CLI调用控制OpenCode完成自动化开发与测试。

## 何时使用

- 有多个需要顺序执行的开发任务
- 需要自动完成开发→测试→验证流程
- 需要任务依赖管理和断点续传
- 需要重置错误任务时（使用 /task-reset-err 命令）
- 需要清空所有任务时（使用 /task-clear 命令）

## 使用方式

### 任务执行命令

```bash
# 常规执行
python main.py run

# 查看状态
python main.py status

# 重置错误任务（清理残留错误配置，将 processing 状态的任务重置为 pending）
python main.py reset-err

# 清空所有任务（清空 tasks.json 和 state.json）
python main.py clear
```

## 特殊命令

| 命令 | 说明 | Agent 触发方式 |
|------|----------------|----------------|
| `/task-reset-err` | 重置错误任务，清理残留配置 | 用户输入 |
| `/task-clear` | 清空所有任务 | 用户输入 |

## 返回值解析

### run 命令

| status | 含义 | Agent动作 |
|--------|------|-----------|
| `processing` | 任务进行中 | 继续调用 |
| `done` | 当前任务完成 | 可停止或继续 |
| `idle` | 无可执行任务 | 停止调用 |
| `error` | 执行出错 | 检查日志 |

### reset-err 命令

| status | 含义 |
|--------|------|
| `success` | 重置成功，返回重置的任务数量 |
| `error` | 重置失败 |

### clear 命令

| status | 含义 |
|--------|------|
| `success` | 清空成功 |
| `error` | 清空失败 |

## 状态流转

```
pending → processing → develop_done → testing → done
                              ↑____________↓
                            (测试失败，重试)
```

## 配置文件

> **注意**：配置统一使用 opencode-config 的配置文件 `../opencode-config/opencode_config.json`（相对于 skills/opencode-orchestrator 目录）

### opencode_config.json
```json
{
  "base_url": "http://192.168.1.45:8908",
  "auth": {
    "type": "basic",
    "username": "your_username",
    "password": "your_password"
  },
  "timeout": 300
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| base_url | OpenCode 服务器地址 | http://localhost:4096 |
| auth.username | 认证用户名 | opencode |
| auth.password | 认证密码 | (空) |
| timeout | 请求超时时间(秒) | 300 (5分钟) |

### tasks.json
```json
{
  "tasks": [
    {
      "id": "task_login",
      "description": "实现登录接口",
      "directory": "E:\\Project\\Test",
      "status": "pending",
      "dependencies": [],
      "session_id": null
    }
  ]
}
```

## Agent使用示例

```
当有开发任务需要自动执行时：
1. cd skills/opencode-orchestrator
2. python main.py run
3. 解析返回JSON：
   - status=processing → 再次调用
   - status=done → 任务完成
   - status=idle → 无任务，停止
   - status=error → 检查错误信息
```