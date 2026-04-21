#!/usr/bin/env python3
"""
OpenCode API - CLI 入口
用法: python main.py <command> [options]
"""
import sys
import json
import context


def print_result(result: dict):
    """打印结果"""
    print(json.dumps(result, ensure_ascii=False, indent=2))


def show_help():
    """显示帮助信息"""
    from core import load_config
    current_session = _get_current_session_info()
    return {
        "status": "success",
        "message": "OpenCode API 可用指令",
        "note": "⚠️ --session-id 是全局参数，必须放在命令名称之前",
        "commands": [
            {
                "command": "get-sessionlist",
                "description": "获取所有会话列表",
                "example": "python main.py --session-id <id> get-sessionlist"
            },
            {
                "command": "new-session",
                "description": "创建新会话（创建后自动更新配置中的 opencodeSessionId）",
                "example": "python main.py --session-id <id> new-session --title '会话标题'"
            },
            {
                "command": "set-session",
                "description": "设置当前会话的 OpenCode Session ID",
                "example": "python main.py --session-id <id> set-session <sessionid>"
            },
            {
                "command": "set-dir",
                "description": "设置当前会话的工作目录（POST 请求会携带 x-opencode-directory header）",
                "example": "python main.py --session-id <id> set-dir 'E:\\Project\\MyApp'"
            },
            {
                "command": "get-messagelist",
                "description": "获取当前会话的消息列表",
                "example": "python main.py --session-id <id> get-messagelist --limit 10"
            },
            {
                "command": "get-message",
                "description": "获取指定消息的详情",
                "example": "python main.py --session-id <id> get-message <messageid>"
            },
            {
                "command": "send-message",
                "description": "发送消息并等待响应",
                "example": "python main.py --session-id <id> send-message '你好' --model <modelid> --agent <agentname>"
            },
            {
                "command": "plan",
                "description": "发送计划指令（agent=plan）并等待响应",
                "example": "python main.py --session-id <id> plan '分析项目结构'"
            },
            {
                "command": "help",
                "description": "显示帮助信息",
                "example": "python main.py help"
            }
        ],
        "paw_session_id": context.current_session_id or "default",
        "current_session": current_session
    }


def _get_current_session_info():
    """获取当前会话信息"""
    from core import load_config
    config = load_config()
    paw_session_id = context.current_session_id or "default"
    sessions = config.get("sessions", [])
    
    for session in sessions:
        if session.get("pawSessionId") == paw_session_id:
            result = {
                "pawSessionId": paw_session_id,
                "opencodeSessionId": session.get("opencodeSessionId")
            }
            dir_value = session.get("dir")
            if dir_value:
                result["dir"] = dir_value
            return result
    return {"pawSessionId": paw_session_id, "opencodeSessionId": None}


def _update_session_id(new_session_id: str) -> None:
    """更新配置中的 opencodeSessionId"""
    from core import load_config, save_config
    config = load_config()
    paw_session_id = context.current_session_id or "default"
    
    sessions = config.get("sessions", [])
    found = False
    for session in sessions:
        if session.get("pawSessionId") == paw_session_id:
            session["opencodeSessionId"] = new_session_id
            found = True
            break
    
    if not found:
        sessions.append({
            "pawSessionId": paw_session_id,
            "opencodeSessionId": new_session_id
        })
    
    config["sessions"] = sessions
    save_config(config)


def main():
    if len(sys.argv) < 2:
        print_result(show_help())
        return
    
    # 解析全局参数 (--session-id)
    i = 1
    while i < len(sys.argv) and sys.argv[i].startswith("--"):
        if sys.argv[i] == "--session-id" and i + 1 < len(sys.argv):
            context.current_session_id = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    if i >= len(sys.argv):
        print_result(show_help())
        return
    
    cmd = sys.argv[i]
    
    # 延迟导入，避免循环依赖
    from core import (
        get_sessionlist,
        create_session,
        set_session,
        set_dir,
        get_messagelist,
        get_message,
        send_message
    )
    
    # 帮助命令 (支持 help 和 -help)
    if cmd in ["help", "-help", "--help"]:
        print_result(show_help())
        return
    
    # 获取会话列表
    if cmd == "get-sessionlist":
        result = get_sessionlist()
        print_result(result)
    
    # 创建新会话
    elif cmd == "new-session":
        title = None
        # 解析参数
        j = i + 1
        while j < len(sys.argv):
            if sys.argv[j] == "--title" and j + 1 < len(sys.argv):
                title = sys.argv[j + 1]
                j += 2
            else:
                j += 1
        
        result = create_session(title)
        print_result(result)
        
        # 如果创建成功，自动更新配置中的 session id
        if result.get("status") == "success" and result.get("data"):
            new_session_id = result["data"].get("id")
            if new_session_id:
                _update_session_id(new_session_id)
    
    # 设置当前会话的 OpenCode Session ID
    elif cmd == "set-session":
        if i + 1 >= len(sys.argv):
            print_result({"status": "error", "message": "缺少参数：sessionid"})
            return
        
        sessionid = sys.argv[i + 1]
        result = set_session(sessionid)
        print_result(result)
    
    # 设置工作目录
    elif cmd == "set-dir":
        if i + 1 >= len(sys.argv):
            print_result({"status": "error", "message": "缺少参数：dir（工作目录路径）"})
            return
        
        dir_path = sys.argv[i + 1]
        result = set_dir(dir_path)
        print_result(result)
    
    # 获取消息列表
    elif cmd == "get-messagelist":
        limit = None
        # 解析参数
        j = i + 1
        while j < len(sys.argv):
            if sys.argv[j] == "--limit" and j + 1 < len(sys.argv):
                try:
                    limit = int(sys.argv[j + 1])
                except ValueError:
                    print_result({"status": "error", "message": "limit 必须是整数"})
                    return
                j += 2
            else:
                j += 1
        
        result = get_messagelist(limit)
        print_result(result)
    
    # 获取指定消息详情
    elif cmd == "get-message":
        if i + 1 >= len(sys.argv):
            print_result({"status": "error", "message": "缺少参数：messageid"})
            return
        
        messageid = sys.argv[i + 1]
        result = get_message(messageid)
        print_result(result)
    
    # 发送消息并等待响应
    elif cmd == "send-message":
        message = None
        model = None
        
        # 解析参数
        j = i + 1
        while j < len(sys.argv):
            if sys.argv[j] == "--model" and j + 1 < len(sys.argv):
                model = sys.argv[j + 1]
                j += 2
            elif not message:
                # 第一个未识别的参数作为 message
                message = sys.argv[j]
                j += 1
            else:
                j += 1
        
        if not message:
            print_result({"status": "error", "message": "缺少参数：message（聊天内容）"})
            return
        
        result = send_message(message, model=model)
        print_result(result)
    
    # 发送计划指令（agent=plan）
    elif cmd == "plan":
        message = None
        model = None
        
        # 解析参数
        j = i + 1
        while j < len(sys.argv):
            if sys.argv[j] == "--model" and j + 1 < len(sys.argv):
                model = sys.argv[j + 1]
                j += 2
            elif not message:
                # 第一个未识别的参数作为 message
                message = sys.argv[j]
                j += 1
            else:
                j += 1
        
        if not message:
            print_result({"status": "error", "message": "缺少参数：message（聊天内容）"})
            return
        
        result = send_message(message, model=model, agent="plan")
        print_result(result)
    
    else:
        print_result({
            "status": "error",
            "message": f"未知命令: {cmd}",
            "hint": "使用 python main.py help 查看可用命令"
        })


if __name__ == "__main__":
    main()