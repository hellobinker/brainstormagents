import networkx as nx
import json
from typing import List
from core.protocol import Message

class RealTimeVisualizer:
    def __init__(self):
        self.graph = nx.Graph()
        self.agent_nodes = set()
        self.idea_count = 0
        self.keywords = {}  # Track keyword nodes
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract key concepts from text (simple version)"""
        # Common keywords that might appear in innovation discussions
        innovation_keywords = [
            "AI", "智能", "物联网", "IoT", "大模型", "语音", "传感器", 
            "节能", "用户体验", "自动化", "云端", "边缘计算", "算法",
            "创新", "交互", "场景", "数据", "安全", "效率", "成本",
            "技术", "方案", "产品", "功能", "需求", "优化", "设计"
        ]
        
        found = []
        for kw in innovation_keywords:
            if kw in text:
                found.append(kw)
        return found[:5]  # Limit to 5 keywords per message

    def update_graph(self, messages: List[Message]):
        """Updates the graph based on messages."""
        # Process only new messages
        for i, msg in enumerate(messages):
            msg_node_id = f"msg_{i}"
            
            # Skip if already processed
            if msg_node_id in self.graph:
                continue
            
            sender = msg.sender
            
            is_human = msg.metadata.get('type') == 'human'
            
            # Add agent/human node if new
            if sender not in self.agent_nodes:
                node_type = "human" if is_human else "agent"
                self.graph.add_node(sender, type=node_type, label=sender)
                self.agent_nodes.add(sender)
            
            # Add message node
            content_preview = msg.content[:30] + "..." if len(msg.content) > 30 else msg.content
            self.graph.add_node(msg_node_id, type="message", label=content_preview)
            self.graph.add_edge(sender, msg_node_id)
            
            # Extract and add keyword nodes
            keywords = self.extract_keywords(msg.content)
            for kw in keywords:
                kw_node = f"kw_{kw}"
                if kw_node not in self.graph:
                    self.graph.add_node(kw_node, type="keyword", label=kw)
                self.graph.add_edge(msg_node_id, kw_node)
                
                # Connect agents/humans who mention same keywords
                if kw not in self.keywords:
                    self.keywords[kw] = []
                if sender not in self.keywords[kw]:
                    self.keywords[kw].append(sender)
                    # Connect this participant to others who mentioned same keyword
                    for other_participant in self.keywords[kw]:
                        if other_participant != sender:
                            self.graph.add_edge(sender, other_participant, type="shared_topic")

    def export_data(self) -> str:
        """Exports the graph data to JSON format for force-graph"""
        nodes = []
        links = []
        
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            label = data.get('label', str(node_id))
            
            # Different colors for different node types
            color = {
                'agent': '#ff6b6b',     # Red for agents
                'human': '#3399ff',     # Blue for human users
                'message': '#4ecdc4',   # Teal for messages
                'keyword': '#ffe66d'    # Yellow for keywords
            }.get(node_type, '#95a5a6')
            
            # Different sizes for different node types
            size = {
                'agent': 12,
                'human': 14,            # Slightly larger for human
                'message': 6,
                'keyword': 8
            }.get(node_type, 5)
            
            nodes.append({
                'id': node_id,
                'label': label,
                'type': node_type,
                'color': color,
                'val': size
            })
        
        for source, target, data in self.graph.edges(data=True):
            links.append({
                'source': source,
                'target': target
            })
        
        return json.dumps({'nodes': nodes, 'links': links}, ensure_ascii=False)
