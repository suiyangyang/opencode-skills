# OpenCode Skills

## 简介 | Introduction

QwenPaw Agent 的 OpenCode 开发技能集，包含 API 调用、任务调度和等待重试三大核心功能，内置两阶段代码审查工作流。

OpenCode skill suite for QwenPaw Agent, providing API invocation, automated task scheduling with two-stage code review, and wait/retry capabilities.

---

## 项目结构 | Project Structure

```
opencode-skills/
├── opencode-api/           # OpenCode API 调用工具
├── opencode-orchestrator/  # 自动化任务调度器（含两阶段 review）
├── opencode-config/        # 共享配置文件
├── wait/                   # 等待重试工具，用于长时间任务和超时处理
└── README-ZH.md           # 本文档
```

---

## 中文说明

### 组件概述

| 组件 | 说明 |
|------|------|
| opencode-api | CLI 工具，与 OpenCode Server API 交互，管理会话、消息和 review |
| opencode-orchestrator | 任务调度器，自动执行开发→两阶段 review→完成流程 |
| opencode-config | 共享配置文件，供以上两个组件共用 |
| wait | 等待工具，处理长时间任务和超时重试场景 |

### 安装配置

#### 1. 配置文件

在 `opencode-config/` 目录下创建 `opencode_config.json`：

```json
{
  "base_url": "http://localhost:4096",
  "auth": {
    "type": "basic",
    "username": "opencode",
    "password": "your_password"
  },
  "sessions": [],
  "timeout": 300,
  "model": {
    "modelID": "deepseek-v4-flash",
    "providerID": "deepseek",
    "max_ctx": 80000,
    "compact_threshold": 0.8
  },
  "reviewModel": {
    "modelID": "deepseek-v4-pro",
    "providerID": "deepseek",
    "max_ctx": 1000000,
    "compact_threshold": 0.8
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| base_url | OpenCode 服务器地址 | http://localhost:4096 |
| auth.username | 认证用户名 | opencode |
| auth.password | 认证密码 | (空) |
| timeout | 请求超时时间(秒) | 300 |
| model | 开发模型配置（含最大上下文和压缩阈值） | deepseek-v4-flash |
| reviewModel | review 专用模型配置（阶段2使用强模型） | deepseek-v4-pro |

#### 2. sessions 字段说明

```json
{
  "sessions": [
    {
      "pawSessionId": "paw_session_xxx",
      "opencodeSessionId": "ses_xxx",
      "dir": "path/to/workspace"
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
| `send-review <内容>` | 发送 review 消息（自动使用 reviewModel） |
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
| `develop_done` | 开发完成，触发两阶段 review | 继续调用（orchestrator 自动执行 review） |
| `reviewing` | review 进行中 | 继续轮询 |
| `review_fix` | 发现代码问题，修复中 | 继续轮询 |
| `done` | 完成（含 review 通过） | 继续调用获取下一个任务 |
| `idle` | 无可执行任务 | 停止调用 |
| `error` | 执行出错 | 检查日志 |

#### 两阶段 Review 工作流

任务开发完成后自动触发两阶段代码审查：

```
开发完成 → 阶段1：开发模型自审（独立会话，最多3轮）
         → pass → done
         → fail → 开发模型修复 → 回到阶段1
         → 3轮未通过 → 阶段2：review模型审查（独立会话，最多3轮）
                     → pass → done
                     → fail → 开发模型修复 → 回到阶段2
                     → 3轮未通过 → review模型直接修复 → done
```

| 阶段 | 审查模型 | 修复模型 | 最大轮次 | 超限后 |
|------|---------|---------|---------|--------|
| 阶段1 | 开发模型 | 开发模型 | 3轮 | 进入阶段2 |
| 阶段2 | reviewModel | 开发模型 | 3轮 | reviewModel直接修复 |

> 长时间任务超时处理：使用 wait skill 等待并重试2次，再决定后续动作。

#### 任务配置 (tasks.json)

```json
{
  "tasks": [
    {
      "id": "task_login",
      "description": "实现登录接口",
      "directory": "path/to/workspace",
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
| opencode-api | CLI tool for interacting with OpenCode Server API, managing sessions, messages, and code review |
| opencode-orchestrator | Task scheduler with two-stage code review: dev model self-review, then reviewModel review |
| opencode-config | Shared configuration file for the above components |
| wait | Wait utility for long-running tasks and timeout retry handling |

### Installation & Configuration

#### 1. Configuration File

Create `opencode_config.json` in `opencode-config/` directory:

```json
{
  "base_url": "http://localhost:4096",
  "auth": {
    "type": "basic",
    "username": "opencode",
    "password": "your_password"
  },
  "sessions": [],
  "timeout": 300,
  "model": {
    "modelID": "deepseek-v4-flash",
    "providerID": "deepseek",
    "max_ctx": 80000,
    "compact_threshold": 0.8
  },
  "reviewModel": {
    "modelID": "deepseek-v4-pro",
    "providerID": "deepseek",
    "max_ctx": 1000000,
    "compact_threshold": 0.8
  }
}
```

| Config | Description | Default |
|--------|-------------|---------|
| base_url | OpenCode server address | http://localhost:4096 |
| auth.username | Auth username | opencode |
| auth.password | Auth password | (empty) |
| timeout | Request timeout (seconds) | 300 |
| model | Development model config (max context, compact threshold) | deepseek-v4-flash |
| reviewModel | Review model config for stage 2 (stronger model) | deepseek-v4-pro |

#### 2. sessions Field

```json
{
  "sessions": [
    {
      "pawSessionId": "paw_session_xxx",
      "opencodeSessionId": "ses_xxx",
      "dir": "path/to/workspace"
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
| `send-review <content>` | Send review message (auto uses reviewModel) |
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

Automated development task scheduler with two-stage code review.

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
| `develop_done` | Dev done, triggers two-stage review | Continue (orchestrator auto-runs review) |
| `reviewing` | Code review in progress | Keep polling |
| `review_fix` | Issues found, fixing in progress | Keep polling |
| `done` | Completed (review passed) | Continue for next task |
| `idle` | No executable tasks | Stop calling |
| `error` | Execution error | Check logs |

#### Two-Stage Review Workflow

After development completes, a two-stage code review is automatically triggered:

```
dev done → Stage 1: dev model self-review (independent session, up to 3 rounds)
         → pass → done
         → fail → dev model fixes → back to Stage 1
         → 3 rounds fail → Stage 2: reviewModel review (independent session, up to 3 rounds)
                     → pass → done
                     → fail → dev model fixes → back to Stage 2
                     → 3 rounds fail → reviewModel fixes directly → done
```

| Stage | Review Model | Fix Model | Max Rounds | On Exceed |
|-------|-------------|-----------|------------|-----------|
| Stage 1 | Dev model | Dev model | 3 | Enter Stage 2 |
| Stage 2 | reviewModel | Dev model | 3 | reviewModel fixes directly |

> For long-running tasks with timeout: use wait skill to wait and retry up to 2 times, then decide next action.

### Wait Skill

Utility for handling long-running tasks and timeout scenarios.

#### Usage

```bash
# Wait 5 minutes (default)
./wait/wait.sh

# Wait 60 seconds
./wait/wait.sh 60
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| seconds | Wait duration in seconds | 300 (5 minutes) |

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

