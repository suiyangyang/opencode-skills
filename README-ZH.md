# OpenCode Skills

## 简介 | Introduction

QwenPaw Agent 的 OpenCode 开发技能集，包含 API 调用和任务调度两大核心功能。

OpenCode skill suite for QwenPaw Agent, providing API invocation and task scheduling capabilities.

---

## 项目结构 | Project Structure

```
opencode-skills/
├── opencode-api/           # OpenCode API 调用工具
├── opencode-orchestrator/  # 自动化任务调度器
├── opencode-config/        # 共享配置文件
└── README.md              # 本文档
```

---

## 中文说明

### 组件概述

| 组件 | 说明 |
|------|------|
| opencode-api | CLI 工具，与 OpenCode Server API 交互，管理会话和消息 |
| opencode-orchestrator | 任务调度器，管理多个开发任务，自动执行开发→测试→验证流程 |
| opencode-config | 共享配置文件，供以上两个组件共用 |

### 安装配置

#### 1. 配置文件

在 `opencode-config/` 目录下创建 `opencode_config.json`：

```json
{
  "base_url": "http://192.168.1.45:8908",
  "auth": {
    "type": "basic",
    "username": "opencode",
    "password": "your_password"
  },
  "sessions": [],
  "timeout": 300,
  "model": {
    "modelID": "MiniMax-M2.7",
    "providerID": "minimax-cn-coding-plan"
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| base_url | OpenCode 服务器地址 | http://localhost:4096 |
| auth.username | 认证用户名 | opencode |
| auth.password | 认证密码 | (空) |
| timeout | 请求超时时间(秒) | 300 |

#### 2. sessions 字段说明

```json
{
  "sessions": [
    {
      "pawSessionId": "1776356413363",
      "opencodeSessionId": "ses_xxx",
      "dir": "E:\Project\MyApp"
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| pawSessionId | QwenPaw 会话 ID |
| opencodeSessionId | OpenCode 会话 ID |
| dir | 工作目录 |

---

### OpenCode API

CLI 工具，与 OpenCode Server API 交互。

#### 使用方法

```bash
cd opencode-api
python main.py --session-id <QwenPaw会话ID> <命令>
```

#### 命令参考

| 命令 | 说明 |
|------|------|
| `get-sessionlist` | 获取所有会话列表 |
| `new-session` | 创建新会话 |
| `new-session --title '标题'` | 创建带标题的会话 |
| `set-session <id>` | 设置当前会话 ID |
| `set-dir <路径>` | 设置工作目录 |
| `get-messagelist` | 获取消息列表 |
| `get-message <id>` | 获取消息详情 |
| `send-message <内容>` | 发送消息（原样转发用户输入） |
| `send-message <内容> --model <id>` | 指定模型发送 |
| `send-message <内容> --agent <name>` | 指定 Agent 发送 |
| `plan <内容>` | 发送计划指令 |
| `help` | 显示帮助 |

#### 返回值

| status | 含义 |
|--------|------|
| `success` | 操作成功 |
| `error` | 操作失败 |

#### 重要约束

> ⚠️ `--session-id` 必须放在命令名称**之前**
> 
> ⚠️ `send-message` 必须**原样转发**用户输入，不得添加额外说明

---

### OpenCode Orchestrator

自动化开发任务调度器。

#### 使用方法

```bash
cd opencode-orchestrator
python main.py <命令>
```

#### 命令参考

| 命令 | 说明 |
|------|------|
| `run` | 执行任务（核心命令） |
| `status` | 查看当前状态 |
| `reset-err` | 重置错误任务 |
| `clear` | 清空所有任务 |

#### 返回值解析

| status | 含义 | Agent 动作 |
|--------|------|-----------|
| `processing` | 任务进行中 | 继续调用 |
| `done` | 当前任务完成 | 继续调用获取下一个任务 |
| `idle` | 无可执行任务 | 停止调用 |
| `error` | 执行出错 | 检查日志 |

#### 状态流转

```
pending → processing → develop_done → testing → done
                              ↑____________↓
                            (测试失败，重试)
```

#### 任务配置 (tasks.json)

```json
{
  "tasks": [
    {
      "id": "task_login",
      "description": "实现登录接口",
      "directory": "E:\Project\Test",
      "status": "pending",
      "dependencies": [],
      "session_id": null
    }
  ]
}
```

#### 特殊命令

通过 QwenPaw 对话触发：

| 命令 | 说明 |
|------|------|
| `/task-reset-err` | 重置错误任务 |
| `/task-clear` | 清空所有任务 |

---

## English Introduction

### Component Overview

| Component | Description |
|-----------|-------------|
| opencode-api | CLI tool for interacting with OpenCode Server API, managing sessions and messages |
| opencode-orchestrator | Task scheduler for automated development→testing→verification workflow |
| opencode-config | Shared configuration file for the above components |

### Installation & Configuration

#### 1. Configuration File

Create `opencode_config.json` in `opencode-config/` directory:

```json
{
  "base_url": "http://192.168.1.45:8908",
  "auth": {
    "type": "basic",
    "username": "opencode",
    "password": "your_password"
  },
  "sessions": [],
  "timeout": 300,
  "model": {
    "modelID": "MiniMax-M2.7",
    "providerID": "minimax-cn-coding-plan"
  }
}
```

| Config | Description | Default |
|--------|-------------|---------|
| base_url | OpenCode server address | http://localhost:4096 |
| auth.username | Auth username | opencode |
| auth.password | Auth password | (empty) |
| timeout | Request timeout (seconds) | 300 |

#### 2. sessions Field

```json
{
  "sessions": [
    {
      "pawSessionId": "1776356413363",
      "opencodeSessionId": "ses_xxx",
      "dir": "E:\Project\MyApp"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| pawSessionId | QwenPaw session ID |
| opencodeSessionId | OpenCode session ID |
| dir | Working directory |

---

### OpenCode API

CLI tool for interacting with OpenCode Server API.

#### Usage

```bash
cd opencode-api
python main.py --session-id <QwenPawSessionID> <command>
```

#### Command Reference

| Command | Description |
|---------|-------------|
| `get-sessionlist` | List all sessions |
| `new-session` | Create new session |
| `new-session --title 'title'` | Create session with title |
| `set-session <id>` | Set current session ID |
| `set-dir <path>` | Set working directory |
| `get-messagelist` | Get message list |
| `get-message <id>` | Get message details |
| `send-message <content>` | Send message (forward verbatim) |
| `send-message <content> --model <id>` | Send with specific model |
| `send-message <content> --agent <name>` | Send with specific agent |
| `plan <content>` | Send plan command |
| `help` | Show help |

#### Return Value

| status | Meaning |
|--------|---------|
| `success` | Operation successful |
| `error` | Operation failed |

#### Important Notes

> ⚠️ `--session-id` must be placed **before** the command name
> 
> ⚠️ `send-message` must **forward user input verbatim**, no additional explanations

---

### OpenCode Orchestrator

Automated development task scheduler.

#### Usage

```bash
cd opencode-orchestrator
python main.py <command>
```

#### Command Reference

| Command | Description |
|---------|-------------|
| `run` | Execute tasks (core command) |
| `status` | Check current status |
| `reset-err` | Reset error tasks |
| `clear` | Clear all tasks |

#### Return Value Parsing

| status | Meaning | Agent Action |
|--------|---------|--------------|
| `processing` | Task in progress | Continue calling |
| `done` | Current task completed | Continue for next task |
| `idle` | No executable tasks | Stop calling |
| `error` | Execution error | Check logs |

#### State Flow

```
pending → processing → develop_done → testing → done
                              ↑____________↓
                            (test failed, retry)
```

#### Task Configuration (tasks.json)

```json
{
  "tasks": [
    {
      "id": "task_login",
      "description": "Implement login API",
      "directory": "E:\Project\Test",
      "status": "pending",
      "dependencies": [],
      "session_id": null
    }
  ]
}
```

