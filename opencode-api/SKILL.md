---
name: opencode-api
description: OpenCode Server API 调用工具，用于与本地 OpenCode 服务器交互，管理会话和消息。当用户输入 /opencode 或 opencode 命令时使用本 skill。
metadata:
  {
    "copaw": { "emoji": "📡" }
  }
---

# OpenCode API

通过 CLI 调用 OpenCode Server API 进行会话管理和消息查询。

## 何时使用

- 需要查看 OpenCode 服务器上的会话列表
- 需要创建新会话
- 需要设置当前会话的 OpenCode Session ID
- 需要设置当前会话的工作目录（用于 POST 请求的 x-opencode-directory header）
- 需要查看会话中的消息列表
- 需要查看特定消息的详情
- 需要向 OpenCode 发送消息并获取响应（原样转发用户输入）

## 使用方式

> ⚠️ **重要**：`--session-id` 是全局参数，必须放在**命令名称之前**，放在命令之后会被当作命令参数解析。

```bash
# 列出所有会话（需要通过 --session-id 指定当前 QwenPaw 会话）
python main.py --session-id 1776356413363 get-sessionlist

# 创建新会话（自动更新配置中的 session id）
python main.py --session-id 1776356413363 new-session

# 创建新会话并设置标题
python main.py --session-id 1776356413363 new-session --title '会话标题'

# 设置当前会话的 OpenCode Session ID
python main.py --session-id 1776356413363 set-session <sessionid>

# 设置当前会话的工作目录（POST 请求会携带 x-opencode-directory header）
python main.py --session-id 1776356413363 set-dir <目录路径>

# 列出当前会话的消息列表
python main.py --session-id 1776356413363 get-messagelist

# 获取指定消息详情
python main.py --session-id 1776356413363 get-message <messageid>

# 发送消息并等待响应（原样转发，不允许修改）
python main.py --session-id 1776356413363 send-message '你的问题'

> ⚠️ **重要约束**：Agent 调用 `send-message` 时，**必须原样转发用户输入的消息**，不得添加任何额外信息（如工作目录说明、上下文补充等）。工作目录已通过 `x-opencode-directory` header 传递，无需在消息正文中重复。

# 发送消息并指定模型和provider
python main.py --session-id 1776356413363 send-message '你的问题' --model <modelid> --provider <providerid>

# 发送消息并指定 agent
python main.py --session-id 1776356413363 send-message '你的问题' --agent <agentname>

# 发送计划指令（agent=plan）
python main.py --session-id 1776356413363 plan '分析项目结构'

# 显示帮助信息
python main.py help
```

## 命令说明

| 命令 | 说明 | 参数 |
|------|------|------|
| `--session-id` | 全局参数，每个命令都应指定，放在命令名称之前 | 必填 |
| `get-sessionlist` | 获取所有会话列表 | |
| `new-session` | 创建新会话，创建成功后自动更新当前会话配置中的 opencodeSessionId | 可选：`--title` |
| `set-session` | 设置当前会话的 OpenCode Session ID（自动保存到配置） | |
| `set-dir` | 设置当前会话的工作目录（POST 请求会携带 x-opencode-directory header） | |
| `get-messagelist` | 获取当前会话的消息列表 | 可选：`--limit` |
| `get-message` | 获取指定消息的详情 | |
| `send-message` | 发送消息并等待响应，**原样转发用户输入**，不添加任何额外信息 | 必填：消息内容（必须原样转发）；可选：`--model`、`--provider`、`--agent` |
| `plan` | 发送计划指令（agent=plan），用于需求分析和规划 | 必填：消息内容；可选：`--model`、`--provider` |
| `help` | 显示帮助信息 | 无 |

## Session ID 管理

每个 QwenPaw 会话都有独立的配置，互不干扰。Session ID 通过命令行参数 `--session-id` 传入，**必须放在命令名称之前**：

```
python main.py --session-id <当前对话的 Session ID> <command>
```

错误示例 ❌：
```bash
python main.py set-dir 'E:\Work\Code' --session-id 1776356413363
# --session-id 放在命令之后，会被解析为 set-dir 的路径参数
```

正确示例 ✅：
```bash
python main.py --session-id 1776356413363 set-dir 'E:\Work\Code'
```

Session ID 从对话开头的分隔区域获取：
```
====================
- Session ID: 1776356413363
- User ID: default
- Channel: console
...
====================
```

## 配置文件

配置文件位于 `skills/opencode-config/opencode_config.json`，每个 QwenPaw 会话独立存储配置：

```json
{
  "base_url": "http://192.168.1.45:8908",
  "auth": {
    "type": "basic",
    "username": "opencode",
    "password": "xxx"
  },
  "sessions": [
    {
      "pawSessionId": "1776356413363",
      "opencodeSessionId": "ses_xxx",
      "dir": "E:\\Project\\MyApp"
    },
    {
      "pawSessionId": "1776356789309",
      "opencodeSessionId": "ses_yyy",
      "dir": "E:\\Project\\Other"
    }
  ]
}
```

## x-opencode-directory Header

当设置 `dir` 后，POST 请求会自动携带 `x-opencode-directory` header：

```
x-opencode-directory: E:\Project\MyApp
```

这对于在多项目环境下正确路由请求到 OpenCode 服务器非常重要。

## Agent 调用规范

> ⚠️ **强制要求**：`send-message` 命令必须**原样转发**用户输入的消息，**不得修改**。

### 正确示例 ✅
```bash
# 用户输入：实现除法功能
# Agent 原样转发：
python main.py --session-id 1776356413363 send-message '实现除法功能'
```

### 错误示例 ❌
```bash
# 禁止添加额外说明
python main.py --session-id 1776356413363 send-message '实现除法功能。请先查看当前目录...'

# 禁止添加上下文
python main.py --session-id 1776356413363 send-message '请在 E:\Work\Code\Test 中实现除法功能'
```

### 原因说明
- 工作目录已通过 `x-opencode-directory` header 传递给 OpenCode
- 消息内容必须保持用户原始输入，确保意图不被扭曲
- 任何上下文补充都可能导致 OpenCode 理解偏差

```
当用户需要设置工作目录时：
1. cd skills/opencode-api
2. python main.py --session-id 1776356413363 set-dir 'E:\\Project\\MyApp'
3. 解析返回 JSON 并显示给用户
4. 目录会保存到当前 QwenPaw 会话的配置中，后续 POST 请求会自动携带 x-opencode-directory header
```

## 返回值解析

| status | 含义 | Agent动作 |
|--------|------|-----------|
| `success` | 操作成功 | 显示返回数据 |
| `error` | 操作失败 | 显示错误信息 |

### send-message 返回值

| status | 含义 |
|--------|------|
| `success` | 成功，data 中包含 OpenCode 返回的 info 和 parts |
| `error` | 失败，message 中包含错误信息 |