"""
WebSocket连接管理器
支持多房间多用户实时协作
"""
from typing import Dict, List, Set
from fastapi import WebSocket
import json
import asyncio

class ConnectionManager:
    """WebSocket连接管理器 - 支持多房间多用户实时协作"""
    
    def __init__(self):
        # 活跃连接: {room_id: {user_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 用户信息: {room_id: {user_id: {"name": str, "role": str}}}
        self.user_info: Dict[str, Dict[str, dict]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str = "匿名用户"):
        """接受新的WebSocket连接加入特定房间"""
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
            self.user_info[room_id] = {}
            
        self.active_connections[room_id][user_id] = websocket
        self.user_info[room_id][user_id] = {
            "name": user_name,
            "role": "participant",
            "connected_at": asyncio.get_event_loop().time()
        }
        
        # 广播用户加入消息到房间
        await self.broadcast(room_id, {
            "type": "user_joined",
            "user_id": user_id,
            "user_name": user_name,
            "online_count": len(self.active_connections[room_id])
        })
    
    def disconnect(self, room_id: str, user_id: str):
        """断开特定房间的用户连接"""
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            del self.active_connections[room_id][user_id]
            
        user_name = "未知用户"
        if room_id in self.user_info and user_id in self.user_info[room_id]:
            user_name = self.user_info[room_id][user_id].get("name", "未知用户")
            del self.user_info[room_id][user_id]
            
        # 如果房间空了，清理房间
        if room_id in self.active_connections and not self.active_connections[room_id]:
            del self.active_connections[room_id]
            if room_id in self.user_info:
                del self.user_info[room_id]
                
        return user_name
    
    async def send_personal_message(self, room_id: str, message: dict, user_id: str):
        """发送私人消息给特定用户"""
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            websocket = self.active_connections[room_id][user_id]
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(room_id, user_id)
    
    async def broadcast(self, room_id: str, message: dict, exclude: Set[str] = None):
        """广播消息给特定房间的所有用户"""
        if room_id not in self.active_connections:
            return
            
        exclude = exclude or set()
        disconnected = []
        
        for user_id, websocket in self.active_connections[room_id].items():
            if user_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(user_id)
        
        # 清理断开的连接
        for user_id in disconnected:
            self.disconnect(room_id, user_id)
            
    def get_online_users(self, room_id: str) -> List[Dict]:
        """获取特定房间的在线用户列表"""
        if room_id not in self.user_info:
            return []
            
        return [
            {
                "user_id": uid,
                "name": info["name"],
                "role": info["role"]
            }
            for uid, info in self.user_info[room_id].items()
        ]
    
    def get_online_count(self, room_id: str) -> int:
        """获取特定房间的在线用户数量"""
        if room_id not in self.active_connections:
            return 0
        return len(self.active_connections[room_id])
    
    async def handle_message(self, room_id: str, user_id: str, data: dict):
        """处理来自用户的消息"""
        message_type = data.get("type", "chat")
        
        if message_type == "chat":
            # 广播聊天消息
            user_name = "匿名"
            if room_id in self.user_info and user_id in self.user_info[room_id]:
                user_name = self.user_info[room_id][user_id].get("name", "匿名")
                
            await self.broadcast(room_id, {
                "type": "human_message",
                "user_id": user_id,
                "user_name": user_name,
                "content": data.get("content", ""),
                "timestamp": asyncio.get_event_loop().time()
            })
        
        elif message_type == "typing":
            # 广播正在输入状态
            user_name = "匿名"
            if room_id in self.user_info and user_id in self.user_info[room_id]:
                user_name = self.user_info[room_id][user_id].get("name", "匿名")
                
            await self.broadcast(room_id, {
                "type": "user_typing",
                "user_id": user_id,
                "user_name": user_name
            }, exclude={user_id})
        
        elif message_type == "request_users":
            # 返回在线用户列表
            await self.send_personal_message(room_id, {
                "type": "online_users",
                "users": self.get_online_users(room_id)
            }, user_id)
        
        return data


# 全局连接管理器实例
ws_manager = ConnectionManager()
