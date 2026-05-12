#!/usr/bin/env python3
"""
Git pre-commit review hook
在提交前自动使用 review model 审查变更内容
"""
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import (
    DEFAULT_REVIEW_MODEL,
    parse_review_result,
)
import requests

REVIEW_PROMPT = """你是一个资深代码审查专家。请审查以下 git 提交中的代码变更。

## 代码变更 (git diff)
```
{diff}
```

## 审查要求
1. **代码逻辑**：检查代码逻辑是否正确
2. **安全性**：检查是否存在安全漏洞（硬编码密钥、敏感信息泄露等）
3. **代码风格**：检查命名规范和可读性
4. **潜在问题**：检查边界条件和错误处理

## 输出格式
如果代码没有问题，只回复：
```
REVIEW_PASS
```

如果代码有问题，按以下格式列出每个问题：
```
[严重程度: 高/中/低] 文件: xxx, 问题: xxx, 建议: xxx
```"""


def run():
    # 获取暂存区的 diff
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=30
        )
        diff = result.stdout
    except FileNotFoundError:
        print("[review] git not found, skipping review")
        return True
    except subprocess.TimeoutExpired:
        print("[review] git diff timed out, skipping review")
        return True

    if not diff.strip():
        return True

    # 使用 review model API 审查
    model_id = DEFAULT_REVIEW_MODEL["modelID"]
    api_key = DEFAULT_REVIEW_MODEL["apiKey"]

    if not api_key:
        print("[review] No API key configured, skipping review")
        return True

    prompt = REVIEW_PROMPT.format(diff=diff)

    # 直接调用 DeepSeek API
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
    }

    try:
        print("[review] Reviewing changes...")
        r = requests.post(url, headers=headers, json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        print("[review] Cannot connect to API, skipping review")
        return True
    except Exception as e:
        print(f"[review] Review API error: {e}")
        return True

    passed, issues = parse_review_result(text)

    if passed:
        print("[review] Review passed")
        return True

    print("[review] Review found issues:")
    for issue in issues:
        severity = issue.get("severity", "未知")
        file = issue.get("file", "未知文件")
        problem = issue.get("problem", "")
        suggestion = issue.get("suggestion", "")
        print(f"    [{severity}] {file}: {problem}")
        print(f"      建议: {suggestion}")

    has_high = any(i.get("severity") == "高" for i in issues)

    if has_high:
        print("[review] Blocking commit: found HIGH severity issues")
        print("[review] 请修复上述高严重性问题后重新提交")
        return False

    ans = input("[review] 发现非高严重性问题，是否强制提交？(y/N): ").strip().lower()
    return ans != "y"


if __name__ == "__main__":
    if not run():
        sys.exit(1)
