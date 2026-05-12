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
| `develop_done` | 开发完成，触发两阶段 review | 继续调用（orchestrator 自动执行阶段1或阶段2） |
| `reviewing` | review 进行中（阶段1用开发模型，阶段2用review模型） | 继续轮询 |
| `review_fix` | 发现代码问题，修复中 | 继续轮询 |
| `review_fix_by_reviewer` | 阶段2已达3轮，review模型直接修复 | 继续轮询 |
| `done` | 当前任务完成（review 通过） | 可停止或继续 |
| `idle` | 无可执行任务 | 停止调用 |
| `error` | 执行出错 | 检查日志 |

> **注意**：`develop_done` 不再直接进入 reviewModel 审查。orchestrator 会根据 `review_stage` 状态自动选择阶段1（开发模型审查）或阶段2（review模型审查）。

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
┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐
│   pending    │────▶│  processing  │────▶│       develop_done           │
│  (待执行)     │     │ (开发模型执行) │     │ (开发完成，触发两阶段 review) │
└──────────────┘     └──────────────┘     └──────────────┬───────────────┘
                                                         │
                                          ┌──────────────┴──────────────┐
                                          │   阶段1：开发模型 review      │
                                          │   (独立会话，最多3轮)         │
                                          └──────────────┬──────────────┘
                                                         │
                                              ┌──────────┴──────────┐
                                              │                     │
                                           (pass)              (issues)
                                              │                     │
                                              ▼                     ▼
                                            done          ┌────────────────┐
                                                          │ < 3轮?         │
                                                          └───────┬────────┘
                                                                  │
                                                      ┌───────────┴───────────┐
                                                      │                       │
                                                     YES                      NO
                                                      │                       │
                                                      ▼                       ▼
                                           ┌─────────────────┐    ┌──────────────────────────┐
                                           │ 开发会话修复     │    │   阶段2：review模型 review │
                                           │ → develop_done  │    │   (独立会话，最多3轮)       │
                                           └─────────────────┘    └──────────────┬─────────────┘
                                                                                 │
                                                                      ┌──────────┴──────────┐
                                                                      │                     │
                                                                   (pass)              (issues)
                                                                      │                     │
                                                                      ▼                     ▼
                                                                    done          ┌────────────────┐
                                                                                  │ < 3轮?         │
                                                                                  └───────┬────────┘
                                                                                          │
                                                                              ┌───────────┴───────────┐
                                                                              │                       │
                                                                             YES                      NO
                                                                              │                       │
                                                                              ▼                       ▼
                                                                   ┌─────────────────┐    ┌──────────────────────────┐
                                                                   │ 开发会话修复     │    │ review模型直接修复        │
                                                                   │ → develop_done  │    │ (在 review session 中)   │
                                                                   └─────────────────┘    └────────────┬─────────────┘
                                                                                                       │
                                                                                                       ▼
                                                                                                     done
```

### 两阶段 Review 架构

| 阶段 | 审查模型 | 修复模型 | 最大轮次 | 超限后 |
|------|---------|---------|---------|--------|
| **阶段1** | 开发模型 (独立会话) | 开发模型 (开发会话) | 3 轮 | 进入阶段2 |
| **阶段2** | reviewModel (独立会话) | 开发模型 (开发会话) | 3 轮 | reviewModel 直接修复 |

**设计理由**：
- **阶段1**：先用成本较低的开发模型自审，多数简单问题在此阶段解决
- **阶段2**：阶段1未通过才使用强 review 模型，节省强模型调用成本
- 每个 review 轮次都创建**新独立会话**，上下文干净，只读磁盘代码

### 状态说明

| 状态 | 含义 |
|------|------|
| `pending` | 等待执行 |
| `processing` | 正在用开发模型执行任务 |
| `develop_done` | 开发模型完成任务，等待 review（可能触发阶段1或阶段2） |
| `reviewing` | 正在审查代码（阶段1用开发模型，阶段2用review模型） |
| `review_fix` | 发现代码问题，正在用开发模型修复 |
| `review_fix_by_reviewer` | 阶段2 已达3轮，由 reviewModel 直接修复 |
| `done` | 任务完成（含 review 通过） |
| `error` | 执行出错 |

### 结果扩展字段

| 字段 | 说明 | 可能值 |
|------|------|--------|
| `review_stage` | 当前审查阶段 | `"dev"` (阶段1), `"pro"` (阶段2), `null` |
| `review_round` | 当前阶段内的轮次 | `1`, `2`, `3`, `null` |
| `review_issues_count` | 当前发现的问题数 | `0`, `1`, `2`, ... |

## 配置文件

> **注意**：配置统一使用 opencode-config 的配置文件 `skills/opencode-config/opencode_config.json`

### opencode_config.json
```json
{
  "base_url": "http://192.168.1.45:8908",
  "auth": {
    "type": "basic",
    "username": "your_username",
    "password": "your_password"
  },
  "timeout": 300,
  "model": {
    "modelID": "qwen-27b",
    "providerID": "realer",
    "max_ctx": 80000,
    "compact_threshold": 0.8
  },
  "reviewModel": {
    "modelID": "deepseek-v4-pro",
    "providerID": "deepseek",
    "max_ctx": 200000,
    "compact_threshold": 0.8
  }
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| base_url | OpenCode 服务器地址 | http://localhost:4096 |
| auth.username | 认证用户名 | opencode |
| auth.password | 认证密码 | (空) |
| timeout | 总超时时间(秒)，包括轮询总时间 | 300 (5分钟) |
| poll_interval | 轮询间隔(秒) | 5 |
| poll_timeout | 单次轮询请求超时(秒) | 30 |
| model.modelID | 开发模型 ID | qwen-27b |
| model.providerID | 开发模型 provider | realer |
| model.max_ctx | 开发模型最大上下文 | 32768 |
| model.compact_threshold | 开发模型压缩触发阈值(80%=0.8) | 0.8 |
| reviewModel.modelID | review 模型 ID | deepseek-v4-pro |
| reviewModel.providerID | review 模型 provider | deepseek |
| reviewModel.max_ctx | review 模型最大上下文 | 200000 |
| reviewModel.compact_threshold | review 模型压缩触发阈值 | 0.8 |

> **注意**：`apiKey` 由服务端配置，客户端无需设置。

### 消息发送机制（方案 A）

从 v2.0 开始，使用异步 API + 客户端轮询机制：

1. **发送消息**：使用 `POST /session/:id/prompt_async`（立即返回 204）
2. **轮询结果**：使用 `GET /session/:id/message/:messageID` 轮询获取处理结果
3. **超时控制**：应用层控制总超时和轮询间隔，更灵活

优势：
- 避免 requests timeout 导致的连接断开
- 支持断点续传
- 更灵活的超时和重试逻辑

## 上下文自动压缩

当 input tokens 达到模型最大上下文的阈值（默认 80%）时，在下一次发送消息前自动执行压缩。开发模型和 review 模型分别使用各自配置的 `max_ctx` 和 `compact_threshold`。

### 压缩机制

1. **触发时机**：下一次发送消息前
2. **触发条件**：`input_tokens / max_ctx >= compact_threshold`
3. **超时时间**：3 分钟
4. **重试次数**：1 次
5. **压缩失败**：继续执行任务（不阻塞）

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