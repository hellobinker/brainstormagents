"""
WebSocket连接管理器
支持多用户实时协作
"""
from typing import Dict, List, Set
from fastapi import WebSocket
import json
import asyncio

class ConnectionManager:
    """WebSocket连接管理器 - 管理多用户实时连接"""
    
    def __init__(self):
        # 活跃连接: {user_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 用户信息: {user_id: {"name": str, "role": str}}
        self.user_info: Dict[str, Dict] = {}
        # 消息队列
        self.message_queue: asyncio.Queue = asyncio.Queue()
    
    async def connect(self, websocket: WebSocket, user_id: str, user_name: str = "匿名用户"):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_info[user_id] = {
            "name": user_name,
            "role": "participant",
            "connected_at": asyncio.get_event_loop().time()
        }
        
        # 广播用户加入消息
        await self.broadcast({
            "type": "user_joined",
            "user_id": user_id,
            "user_name": user_name,
            "online_count": len(self.active_connections)
        })
    
    def disconnect(self, user_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        user_name = self.user_info.get(user_id, {}).get("name", "未知用户")
        if user_id in self.user_info:
            del self.user_info[user_id]
        return user_name
    
    async def send_personal_message(self, message: dict, user_id: str):
        """发送私人消息给特定用户"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(user_id)
    
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """广播消息给所有连接的用户"""
        exclude = exclude or set()
        disconnected = []
        
        for user_id, websocket in self.active_connections.items():
            if user_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(user_id)
        
        # 清理断开的连接
        for user_id in disconnected:
            self.disconnect(user_id)
    
    async def broadcast_to_role(self, message: dict, role: str):
        """广播消息给特定角色的用户"""
        for user_id, info in self.user_info.items():
            if info.get("role") == role:
                await self.send_personal_message(message, user_id)
    
    def get_online_users(self) -> List[Dict]:
        """获取在线用户列表"""
        return [
            {
                "user_id": user_id,
                "name": info["name"],
                "role": info["role"]
            }
            for user_id, info in self.user_info.items()
        ]
    
    def get_online_count(self) -> int:
        """获取在线用户数量"""
        return len(self.active_connections)
    
    def set_user_role(self, user_id: str, role: str):
        """设置用户角色"""
        if user_id in self.user_info:
            self.user_info[user_id]["role"] = role
    
    async def handle_message(self, user_id: str, data: dict):
        """处理来自用户的消息"""
        message_type = data.get("type", "chat")
        
        if message_type == "chat":
            # 广播聊天消息
            user_name = self.user_info.get(user_id, {}).get("name", "匿名")
            await self.broadcast({
                "type": "human_message",
                "user_id": user_id,
                "user_name": user_name,
                "content": data.get("content", ""),
                "timestamp": asyncio.get_event_loop().time()
            })
        
        elif message_type == "typing":
            # 广播正在输入状态
            user_name = self.user_info.get(user_id, {}).get("name", "匿名")
            await self.broadcast({
                "type": "user_typing",
                "user_id": user_id,
                "user_name": user_name
            }, exclude={user_id})
        
        elif message_type == "request_users":
            # 返回在线用户列表
            await self.send_personal_message({
                "type": "online_users",
                "users": self.get_online_users()
            }, user_id)
        
        return data


# 全局连接管理器实例
manager = ConnectionManager()
