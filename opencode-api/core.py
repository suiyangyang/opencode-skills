#!/usr/bin/env python3
"""
OpenCode API - 核心功能模块
"""
import os
import json
import requests
import context
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# 配置路径 - 使用共享配置文件
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
OPENCODER_DIR = os.path.dirname(SKILL_DIR)  # .../opencoder
SHARED_CONFIG_PATH = os.path.join(OPENCODER_DIR, "opencode-config", "opencode_config.json")
LOCAL_CONFIG_PATH = os.path.join(SKILL_DIR, "opencode-config", "opencode_config.json")

# ===== 日志配置 =====
LOGS_DIR = os.path.join(SKILL_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# 配置 API 专用日志器
api_logger = logging.getLogger("opencode_api")
api_logger.setLevel(logging.DEBUG)

# 北京时间格式化器（精确到毫秒）
class BeijingFormatter(logging.Formatter):
    """北京时间日志格式化器"""
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone(timedelta(hours=8)))
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%H:%M:%S.%f")[:-3]

# 避免重复添加 handler
if not api_logger.handlers:
    log_file = os.path.join(LOGS_DIR, f"api_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 使用北京时间格式化器，精确到毫秒
    formatter = BeijingFormatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S.%f")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    api_logger.addHandler(file_handler)
    api_logger.addHandler(console_handler)


def _sanitize_headers(headers: Dict[str, str], auth: Dict[str, Any]) -> Dict[str, str]:
    """清理头部中的敏感信息"""
    sanitized = headers.copy()
    # 隐藏密码
    if "password" in str(auth):
        sanitized["X-Password-Sanitized"] = "***"
    return sanitized


def _log_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    auth: Optional[Dict[str, Any]] = None
) -> None:
    """记录 API 请求日志"""
    api_logger.info("=" * 60)
    api_logger.info("📤 API 请求")
    api_logger.info(f"   方法: {method}")
    api_logger.info(f"   URL: {url}")
    api_logger.info(f"   Headers: {json.dumps(_sanitize_headers(headers, auth or {}), ensure_ascii=False, indent=4)}")
    
    if params:
        api_logger.info(f"   查询参数: {json.dumps(params, ensure_ascii=False, indent=4)}")
    
    if data:
        # 对于消息内容，限制长度避免日志过大
        data_str = json.dumps(data, ensure_ascii=False, indent=4)
        if len(data_str) > 1000:
            data_str = data_str[:1000] + "\n   ... (truncated, total length: " + str(len(data_str)) + ")"
        api_logger.info(f"   请求体: {data_str}")
    
    api_logger.info("-" * 60)


def _log_response(response_data: Dict[str, Any], status_code: Optional[int] = None, elapsed: Optional[float] = None) -> None:
    """记录 API 响应日志"""
    api_logger.info("=" * 60)
    api_logger.info("📥 API 响应")
    
    if status_code is not None:
        api_logger.info(f"   状态码: {status_code}")
    
    if elapsed is not None:
        api_logger.info(f"   耗时: {elapsed:.3f}s")
    
    # 响应的 data 字段可能很大，单独处理
    if "data" in response_data:
        data_part = response_data["data"]
        data_str = json.dumps(data_part, ensure_ascii=False, indent=4)
        if len(data_str) > 1500:
            data_str = data_str[:1500] + "\n   ... (truncated, total length: " + str(len(data_str)) + ")"
        api_logger.info(f"   响应数据:\n   {data_str}")
    else:
        # 整个响应较小，直接记录
        resp_str = json.dumps(response_data, ensure_ascii=False, indent=4)
        if len(resp_str) > 1500:
            resp_str = resp_str[:1500] + "\n   ... (truncated, total length: " + str(len(resp_str)) + ")"
        api_logger.info(f"   响应: {resp_str}")
    
    api_logger.info("=" * 60)


def get_current_paw_session_id() -> str:
    """
    获取当前 QwenPaw 会话 ID
    
    该值通过命令行参数 --session-id 传入，Agent 调用 skill 时应指定：
    python main.py get-sessionlist --session-id 1776356413363
    
    Returns:
        当前 QwenPaw 会话 ID，默认 "default"
    """
    return context.current_session_id or os.environ.get("COPAW_SESSION_ID", "default")


def load_config() -> Dict[str, Any]:
    """加载 OpenCode 配置文件，优先使用共享配置"""
    # 优先使用共享配置
    config_path = SHARED_CONFIG_PATH if os.path.exists(SHARED_CONFIG_PATH) else LOCAL_CONFIG_PATH
    
    if not os.path.exists(config_path):
        return {
            "base_url": "http://localhost:4096",
            "auth": {"type": "basic", "username": "opencode", "password": ""},
            "sessions": []
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict[str, Any]) -> None:
    """保存配置到共享配置文件"""
    os.makedirs(os.path.dirname(SHARED_CONFIG_PATH), exist_ok=True)
    with open(SHARED_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_timeout() -> int:
    """获取超时时间（秒），默认 300 秒（5分钟）"""
    config = load_config()
    return config.get("timeout", 300)


def make_request(
    method: str,
    endpoint: str,
    config: Dict[str, Any],
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """发送 HTTP 请求到 OpenCode 服务器"""
    import time
    
    base_url = config.get("base_url", "http://localhost:4096").rstrip("/")
    url = f"{base_url}{endpoint}"
    
    auth = config.get("auth", {})
    auth_type = auth.get("type", "basic")
    
    # 设置认证
    if auth_type == "basic":
        auth_tuple = (auth.get("username", ""), auth.get("password", ""))
    else:
        auth_tuple = None
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # 获取当前会话的 dir，添加到 header（如果已设置）
    current_session_config = _get_current_session_config(config)
    if current_session_config:
        dir_value = current_session_config.get("dir", "")
        if dir_value:
            headers["x-opencode-directory"] = dir_value
    
    # 使用指定超时或默认超时
    request_timeout = timeout if timeout is not None else get_timeout()
    
    # 记录请求日志
    _log_request(method, url, headers, data=data, params=params, auth=auth)
    
    start_time = time.time()
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, auth=auth_tuple, headers=headers, params=params, timeout=request_timeout)
        elif method.upper() == "POST":
            response = requests.post(url, auth=auth_tuple, headers=headers, json=data, timeout=request_timeout)
        elif method.upper() == "PATCH":
            response = requests.patch(url, auth=auth_tuple, headers=headers, json=data, timeout=request_timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, auth=auth_tuple, headers=headers, timeout=request_timeout)
        else:
            result = {"status": "error", "message": f"不支持的 HTTP 方法: {method}"}
            _log_response(result, elapsed=time.time() - start_time)
            return result
        
        # 尝试解析 JSON 响应
        try:
            result_data = response.json()
        except json.JSONDecodeError:
            result_data = {"raw": response.text}
        
        elapsed = time.time() - start_time
        
        if response.status_code >= 200 and response.status_code < 300:
            result = {"status": "success", "data": result_data}
            _log_response(result, status_code=response.status_code, elapsed=elapsed)
            return result
        else:
            result = {
                "status": "error",
                "message": f"HTTP {response.status_code}",
                "detail": result_data
            }
            _log_response(result, status_code=response.status_code, elapsed=elapsed)
            return result
    
    except requests.exceptions.ConnectionError as e:
        result = {
            "status": "error",
            "message": f"无法连接到 OpenCode 服务器: {base_url}",
            "hint": "请确保 OpenCode 服务器正在运行"
        }
        _log_response(result, elapsed=time.time() - start_time)
        return result
    except requests.exceptions.Timeout:
        result = {"status": "error", "message": f"请求超时（{request_timeout}秒）"}
        _log_response(result, elapsed=time.time() - start_time)
        return result
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        _log_response(result, elapsed=time.time() - start_time)
        return result


def _get_current_session_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """获取当前 CoPaw 会话对应的配置条目"""
    paw_session_id = get_current_paw_session_id()
    sessions = config.get("sessions", [])
    
    for session in sessions:
        if session.get("pawSessionId") == paw_session_id:
            return session
    
    return None


def get_current_session_id(config: Dict[str, Any]) -> Optional[str]:
    """获取当前 CoPaw 会话对应的 OpenCode Session ID"""
    current_session = _get_current_session_config(config)
    if current_session:
        return current_session.get("opencodeSessionId")
    return None


def get_sessionlist() -> Dict[str, Any]:
    """获取所有会话列表"""
    config = load_config()
    return make_request("GET", "/session", config)


def create_session(title: Optional[str] = None) -> Dict[str, Any]:
    """创建新会话"""
    config = load_config()
    data = {}
    if title:
        data["title"] = title
    
    return make_request("POST", "/session", config, data=data)


def set_dir(dir_path: str) -> Dict[str, Any]:
    """设置当前会话的工作目录"""
    config = load_config()
    paw_session_id = get_current_paw_session_id()
    
    sessions = config.get("sessions", [])
    
    # 查找并更新或添加
    found = False
    for session in sessions:
        if session.get("pawSessionId") == paw_session_id:
            session["dir"] = dir_path
            found = True
            break
    
    if not found:
        sessions.append({
            "pawSessionId": paw_session_id,
            "dir": dir_path,
            "opencodeSessionId": None
        })
    
    config["sessions"] = sessions
    save_config(config)
    
    return {
        "status": "success",
        "message": f"已设置当前会话的工作目录: {dir_path}",
        "pawSessionId": paw_session_id,
        "dir": dir_path
    }


def set_session(sessionid: str) -> Dict[str, Any]:
    """设置当前会话的 OpenCode Session ID"""
    config = load_config()
    paw_session_id = get_current_paw_session_id()
    
    sessions = config.get("sessions", [])
    
    # 查找并更新或添加
    found = False
    for session in sessions:
        if session.get("pawSessionId") == paw_session_id:
            session["opencodeSessionId"] = sessionid
            found = True
            break
    
    if not found:
        sessions.append({
            "pawSessionId": paw_session_id,
            "opencodeSessionId": sessionid
        })
    
    config["sessions"] = sessions
    save_config(config)
    
    return {
        "status": "success",
        "message": f"已设置当前会话的 OpenCode Session ID: {sessionid}",
        "pawSessionId": paw_session_id,
        "opencodeSessionId": sessionid
    }


def get_messagelist(limit: Optional[int] = None) -> Dict[str, Any]:
    """获取当前会话的消息列表"""
    config = load_config()
    session_id = get_current_session_id(config)
    
    if not session_id:
        return {
            "status": "error",
            "message": "未设置当前会话的 OpenCode Session ID",
            "hint": "请先使用 /opencode set-session <sessionid> 设置"
        }
    
    params = {"limit": limit} if limit else None
    return make_request("GET", f"/session/{session_id}/message", config, params=params)


def get_message(messageid: str) -> Dict[str, Any]:
    """获取指定消息的详情"""
    config = load_config()
    session_id = get_current_session_id(config)
    
    if not session_id:
        return {
            "status": "error",
            "message": "未设置当前会话的 OpenCode Session ID",
            "hint": "请先使用 /opencode set-session <sessionid> 设置"
        }
    
    return make_request("GET", f"/session/{session_id}/message/{messageid}", config)


def send_message(original_message: str, model: Optional[str] = None, agent: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """
    发送消息并等待响应

    Args:
        original_message: 用户输入的聊天内容（必须原样发送，不做任何处理）
            注意：此参数在日志中记录为 "原始消息"，API 请求体中的 text 字段必须与此完全一致
        model: 可选，指定模型 ID。如果为空，自动从配置文件读取
        agent: 可选，指定 agent 类型（默认为 "build"，可用 "plan"）
        provider: 可选，指定 provider ID。如果为空，自动从配置文件读取

    Returns:
        包含 info 和 parts 的响应
    """
    import hashlib

    config = load_config()
    session_id = get_current_session_id(config)

    if not session_id:
        return {
            "status": "error",
            "message": "未设置当前会话的 OpenCode Session ID",
            "hint": "请先使用 /opencode set-session <sessionid> 或 /opencode new-session 创建新会话"
        }

    # 计算原始消息的哈希值，用于验证
    message_hash = hashlib.sha256(original_message.encode('utf-8')).hexdigest()[:16]

    # 自动从配置文件读取模型和 provider（如果未指定）
    model_config = config.get("model", {})
    effective_model = model or model_config.get("modelID")
    effective_provider = provider or model_config.get("providerID")

    # 构建请求体 - 关键：必须使用 original_message原值，不得修改
    body = {
        "role": "user",
        "parts": [{"type": "text", "text": original_message}],  # ⚠️ 强制使用原始消息
        "agent": agent or "build"  # 默认使用 "build"，可指定 "plan" 等
    }

    # 处理 model 和 provider
    if effective_model or effective_provider:
        model_info = {}
        if effective_model:
            model_info["modelID"] = effective_model
        if effective_provider:
            model_info["providerID"] = effective_provider
        body["model"] = model_info

    # 记录原始消息到日志（用于审计对比）
    api_logger.info("=" * 60)
    api_logger.info(f"📝 原始消息 [hash:{message_hash}]")
    api_logger.info(f"   text: {original_message}")
    api_logger.info(f"   agent: {body['agent']}")
    if "model" in body:
        api_logger.info(f"   model: {body['model']}")
    api_logger.info("=" * 60)

    response = make_request("POST", f"/session/{session_id}/message", config, data=body)

    # 如果请求成功，验证响应中的消息是否与原始消息一致
    if response.get("status") == "success":
        resp_data = response.get("data", {})
        resp_parts = resp_data.get("info", {}).get("parts", [])
        # 这里可以进一步验证，但主要是记录审计日志

    return response