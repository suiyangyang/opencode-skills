#!/usr/bin/env python3
"""
OpenCode Orchestrator - 核心逻辑
"""
import json
import os
import re
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote


def beijing_now():
    """获取北京时间（精确到毫秒）"""
    return datetime.now().astimezone(timezone(timedelta(hours=8)))

# ===== 路径 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 配置文件位于 skills/opencode-config/opencode_config.json
SKILL_DIR = os.path.dirname(SCRIPT_DIR)  # skills 目录
OPENCODER_DIR = os.path.dirname(SKILL_DIR)  # opencoder 目录
CONFIG_PATH = os.path.join(SKILL_DIR, "opencode-config", "opencode_config.json")
TASKS_PATH = os.path.join(SCRIPT_DIR, "tasks.json")
STATE_PATH = os.path.join(SCRIPT_DIR, "state.json")
LOGS_DIR = os.path.join(SKILL_DIR, "logs")

# 确保 logs 目录存在
os.makedirs(LOGS_DIR, exist_ok=True)

# 默认配置
DEFAULT_MODEL = {
    "modelID": "MiniMax-M2.7",
    "providerID": "minimax-cn-coding-plan"
}


# ===== 日志工具 =====
class TaskLogger:
    """任务日志记录器"""
    
    def __init__(self, task_description):
        # 清理任务描述，生成合法的文件名
        safe_desc = re.sub(r'[^\w\u4e00-\u9fa5]', '_', task_description)[:30]
        timestamp = beijing_now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{safe_desc}_{timestamp}.log"
        self.log_path = os.path.join(LOGS_DIR, log_filename)
        self.start_time = beijing_now()
        
        # 写入开始日志
        self._write("=" * 60)
        self._write(f"任务开始 - {self.start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        self._write(f"任务描述: {task_description}")
        self._write("=" * 60)
    
    def _write(self, message):
        """写入日志"""
        timestamp = beijing_now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
        print(log_line)
    
    def log_api(self, api_name, request_data=None, response_data=None, error=None):
        """记录 API 调用"""
        self._write("")
        self._write(f"--- API 调用: {api_name} ---")
        
        if request_data:
            self._write(f"请求输入: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        
        if error:
            self._write(f"❌ 错误: {error}")
        
        if response_data:
            # 限制响应长度，避免日志过大
            resp_str = json.dumps(response_data, ensure_ascii=False, indent=2)
            if len(resp_str) > 2000:
                resp_str = resp_str[:2000] + "\n... (truncated)"
            self._write(f"响应输出: {resp_str}")
        
        self._write(f"--- API 结束: {api_name} ---")
    
    def log_step(self, step_name, message):
        """记录步骤"""
        self._write("")
        self._write(f">>> 步骤: {step_name}")
        self._write(f"    {message}")
    
    def log_result(self, status, message):
        """记录结果"""
        self._write("")
        self._write("=" * 60)
        self._write(f"任务结束 - 状态: {status}")
        self._write(f"结果: {message}")
        elapsed = (beijing_now() - self.start_time).total_seconds()
        self._write(f"耗时: {elapsed:.2f} 秒")
        self._write("=" * 60)


# ===== 配置加载 =====
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_config():
    cfg = load_config()
    if cfg is None:
        raise Exception("opencode_config.json not found or invalid")
    # 设置默认 model
    if "model" not in cfg:
        cfg["model"] = DEFAULT_MODEL
    return cfg


# ===== 工具函数 =====
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_tasks():
    data = load_json(TASKS_PATH)
    return data.get("tasks", [])


def save_tasks(tasks):
    save_json(TASKS_PATH, {"tasks": tasks})


def load_state():
    return load_json(STATE_PATH)


def save_state(state):
    save_json(STATE_PATH, state)


def get_task(tasks, task_id):
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


def get_task_status(tasks, task_id):
    task = get_task(tasks, task_id)
    return task["status"] if task else None


def make_headers(directory):
    """生成请求头"""
    headers = {
        "x-opencode-directory": quote(directory)
    }
    return headers


# ===== OpenCode API =====
def create_session(directory, base_url, auth, logger=None):
    """创建 Session"""
    api_name = "create_session"
    request_data = {
        "url": f"{base_url}/session",
        "method": "POST",
        "params": {"directory": directory},
        "headers": {"x-opencode-directory": quote(directory)}
    }
    
    try:
        if logger:
            logger.log_api(api_name, request_data=request_data)
        
        headers = make_headers(directory)
        r = requests.post(
            f"{base_url}/session",
            params={"directory": directory},
            auth=auth,
            headers=headers,
            timeout=30
        )
        r.raise_for_status()
        result = r.json()
        
        if logger:
            logger.log_api(api_name, response_data=result)
        
        return result["id"]
    except Exception as e:
        error_msg = f"创建session失败: {e}"
        if logger:
            logger.log_api(api_name, request_data=request_data, error=error_msg)
        raise Exception(error_msg)


def send_message(session_id, message, base_url, auth, model=None, directory=None, logger=None):
    """发送消息"""
    api_name = "send_message"
    
    # 构建请求体
    body = {
        "role": "user",
        "parts": [{"type": "text", "text": message}],
        "agent": "build"
    }
    
    if model:
        body["model"] = model
    
    # 构建 headers
    headers = {}
    if directory:
        headers["x-opencode-directory"] = quote(directory)
    
    # 日志记录（包含实际的请求体）
    if logger:
        logger.log_api(api_name, request_data={
            "url": f"{base_url}/session/{session_id}/message",
            "method": "POST",
            "body": body,  # 记录实际的请求体
        })
    
    try:
        r = requests.post(
            f"{base_url}/session/{session_id}/message",
            auth=auth,
            json=body,
            headers=headers,
            timeout=load_config().get("timeout", 300) if load_config() else 300
        )
        r.raise_for_status()
        result = r.json()
        
        if logger:
            logger.log_api(api_name, response_data=result)
        
        return result
    except Exception as e:
        error_msg = f"发送消息失败: {e}"
        if logger:
            logger.log_api(api_name, error=error_msg)
        raise Exception(error_msg)


def extract_text(parts):
    texts = []
    for p in parts:
        if p.get("type") in ["text", "reasoning"]:
            texts.append(p.get("text", ""))
    return "\n".join(texts)


def parse_test_result(text):
    """尝试解析JSON测试结果"""
    # 尝试找到JSON块
    match = re.search(r'\{[^{}]*"pass"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    # 简单匹配
    return {"pass": "通过" in text or "pass" in text.lower()}


# ===== 任务调度 =====
def get_runnable_task(tasks):
    """获取可执行的任务（pending且依赖都已done）"""
    for t in tasks:
        if t["status"] == "pending":
            deps = t.get("dependencies", [])
            if all(get_task_status(tasks, dep) == "done" for dep in deps):
                return t
    return None


def setup_files():
    """初始化必要的配置文件（使用 opencode-api 的配置）"""
    # opencode_config.json (来自 opencode-api skill)
    if not os.path.exists(CONFIG_PATH):
        save_json(CONFIG_PATH, {
            "base_url": "http://localhost:4096",
            "auth": {
                "type": "basic",
                "username": "opencode",
                "password": ""
            },
            "timeout": 300
        })

    # tasks.json
    if not os.path.exists(TASKS_PATH):
        save_json(TASKS_PATH, {
            "tasks": [
                {
                    "id": "example_task",
                    "description": "示例任务",
                    "directory": ".",
                    "status": "pending",
                    "dependencies": [],
                    "session_id": None
                }
            ]
        })

    # state.json
    if not os.path.exists(STATE_PATH):
        save_json(STATE_PATH, {"current_task": None})


# ===== 主流程 =====
def run_once():
    """执行一轮任务处理"""
    logger = None
    
    try:
        # 加载配置
        cfg = get_config()
        BASE_URL = cfg["base_url"]
        AUTH = (cfg["auth"]["username"], cfg["auth"]["password"])
        MODEL = cfg.get("model", DEFAULT_MODEL)

        # 加载数据
        tasks = load_tasks()
        state = load_state()

        # 获取当前任务
        task_id = state.get("current_task")
        task = None

        if task_id:
            task = get_task(tasks, task_id)
            if task is None:
                # 任务不存在，重置状态
                state["current_task"] = None
                save_state(state)
                result = {"status": "idle", "msg": "任务不存在，已重置"}
                return result
        else:
            # 获取新任务
            task = get_runnable_task(tasks)
            if not task:
                result = {"status": "idle", "msg": "没有可执行任务"}
                return result

            # 创建日志记录器
            logger = TaskLogger(task.get("description", task["id"]))
            
            task["status"] = "processing"
            state["current_task"] = task["id"]

        # 如果还没有日志记录器（之前创建的任务），创建它
        if logger is None and task:
            logger = TaskLogger(task.get("description", task["id"]))

        # 确保session存在
        if not task.get("session_id"):
            logger.log_step("创建Session", f"目录: {task['directory']}")
            task["session_id"] = create_session(task["directory"], BASE_URL, AUTH, logger)
            logger.log_step("Session创建成功", f"Session ID: {task['session_id']}")
        else:
            logger.log_step("复用Session", f"Session ID: {task['session_id']}")

        # 获取任务的工作目录
        task_directory = task.get("directory")

        # ===== 开发阶段 =====
        if task["status"] == "processing":
            msg = f"""任务：{task['description']}

请完成开发任务，并确保代码可运行。
完成后请明确说明"开发完成"。"""

            logger.log_step("开发阶段", "发送开发任务请求...")
            logger.log_step("模型配置", f"modelID: {MODEL.get('modelID')}, providerID: {MODEL.get('providerID')}")
            resp = send_message(task["session_id"], msg, BASE_URL, AUTH, MODEL, task_directory, logger)
            text = extract_text(resp.get("parts", []))
            
            logger.log_step("开发响应", f"响应长度: {len(text)} 字符")
            
            if "开发完成" in text:
                task["status"] = "develop_done"
                logger.log_step("开发完成", "AI 确认开发完成")
            else:
                logger.log_step("继续开发", "等待进一步开发...")

        # ===== 测试阶段 =====
        elif task["status"] == "develop_done":
            task["status"] = "testing"
            logger.log_step("测试阶段", "开始测试...")

            test_prompt = """请执行测试并返回结果。

返回JSON格式：
{
  "build": true/false,
  "test": true/false,
  "coverage": true/false,
  "pass": true/false
}"""

            resp = send_message(task["session_id"], test_prompt, BASE_URL, AUTH, MODEL, task_directory, logger)
            text = extract_text(resp.get("parts", []))
            result = parse_test_result(text)

            if result.get("pass"):
                task["status"] = "done"
                state["current_task"] = None
                logger.log_step("测试通过", "所有测试通过")
            else:
                # 测试失败，重试
                task["status"] = "processing"
                task["retry"] = task.get("retry", 0) + 1
                logger.log_step("测试失败", f"重试次数: {task['retry']}")

        # 保存状态
        save_tasks(tasks)
        save_state(state)

        result = {
            "status": task["status"],
            "task": task["id"],
            "description": task.get("description", "")
        }
        
        if logger:
            logger.log_result(task["status"], json.dumps(result, ensure_ascii=False))
        
        return result

    except Exception as e:
        error_msg = str(e)
        result = {"status": "error", "msg": error_msg}
        
        if logger:
            logger.log_api("EXCEPTION", error=error_msg)
            logger.log_result("error", error_msg)
        
        return result


def reset_task():
    """重置当前任务，清理残留错误配置"""
    try:
        # 1. 清理 state.json
        state = load_state()
        state.clear()
        save_state(state)
        
        # 2. 将 tasks.json 中状态为 processing 的任务重置为 pending
        tasks = load_tasks()
        reset_count = 0
        for task in tasks:
            if task.get("status") == "processing":
                task["status"] = "pending"
                task["session_id"] = None
                reset_count += 1
        
        save_tasks(tasks)
        
        return {
            "status": "success",
            "message": f"重置完成，已清理 {reset_count} 个任务的状态",
            "reset_count": reset_count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"重置失败: {str(e)}"
        }


def clear_tasks():
    """清空所有任务，清理 tasks.json 和 state.json"""
    try:
        # 清空 state.json
        state = load_state()
        state.clear()
        save_state(state)
        
        # 清空 tasks.json
        tasks = []
        save_tasks(tasks)
        
        return {
            "status": "success",
            "message": "已清空所有任务"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"清空失败: {str(e)}"
        }


if __name__ == "__main__":
    setup_files()
    result = run_once()
    print(json.dumps(result, ensure_ascii=False))