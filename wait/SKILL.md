---
name: wait
description: 等待指定时间。默认等待5分钟，可自定义秒数。
metadata: { "builtin_skill_version": "1.0", "copaw": { "emoji": "⏳" } }
---

# Wait（等待）

## 什么时候用

- 需要暂停执行指定时间
- 等待某个进程完成
- 定时轮询场景

---

## 使用方法

### 等待 5 分钟（默认）

```bash
./skills/wait/wait.sh
```

### 自定义等待时间

```bash
# 等待 60 秒
./skills/wait/wait.sh 60

# 等待 10 分钟
./skills/wait/wait.sh 600
```

### 在 cron 中使用

```bash
# 每小时执行一次任务
copaw cron create \
  --agent-id "default" \
  --type agent \
  --name "每小时任务" \
  --cron "0 * * * *" \
  --channel console \
  --target-user "default" \
  --target-session "default" \
  --text "先等待5分钟再执行任务：/app/working/workspaces/default/skills/wait/wait.sh 300"
```

---

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 秒数 | 等待的秒数 | 300 (5分钟) |

---

## 输出示例

```
等待 300 秒...
开始时间: 2026-04-25 12:00:00
结束时间: 2026-04-25 12:05:00
等待完成
```