"""
文件处理器

支持多模态输入：
- 文档：Markdown、TXT、PDF
- 图片：PNG、JPG、WEBP
"""
import base64
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class ProcessedFile:
    """处理后的文件"""
    filename: str
    file_type: str  # "document" or "image"
    content_type: str  # "text/markdown", "image/png", etc.
    text_content: Optional[str] = None  # 文本内容（文档）
    base64_content: Optional[str] = None  # Base64编码（图片）
    size_bytes: int = 0
    
    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "file_type": self.file_type,
            "content_type": self.content_type,
            "text_content": self.text_content,
            "base64_content": self.base64_content[:100] + "..." if self.base64_content else None,
            "size_bytes": self.size_bytes
        }
    
    def get_context_for_llm(self) -> str:
        """生成用于LLM的上下文描述"""
        if self.file_type == "document":
            return f"【附件：{self.filename}】\n{self.text_content}"
        elif self.file_type == "image":
            return f"【附件：{self.filename}】（图片已上传，请在分析中考虑此图片内容）"
        return ""


class FileProcessor:
    """
    文件处理器
    
    处理上传的文档和图片
    """
    
    SUPPORTED_DOCUMENTS = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf"
    }
    
    SUPPORTED_IMAGES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_TEXT_LENGTH = 50000  # 文本最大字符数
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    def is_supported(self, filename: str) -> bool:
        """检查文件是否支持"""
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_DOCUMENTS or ext in self.SUPPORTED_IMAGES
    
    def get_file_type(self, filename: str) -> Tuple[str, str]:
        """获取文件类型"""
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_DOCUMENTS:
            return "document", self.SUPPORTED_DOCUMENTS[ext]
        elif ext in self.SUPPORTED_IMAGES:
            return "image", self.SUPPORTED_IMAGES[ext]
        return "unknown", "application/octet-stream"
    
    async def process_file(self, filename: str, file_content: bytes) -> ProcessedFile:
        """
        处理上传的文件
        
        Args:
            filename: 文件名
            file_content: 文件二进制内容
            
        Returns:
            ProcessedFile
        """
        file_type, content_type = self.get_file_type(filename)
        
        if file_type == "document":
            return await self._process_document(filename, file_content, content_type)
        elif file_type == "image":
            return self._process_image(filename, file_content, content_type)
        else:
            raise ValueError(f"Unsupported file type: {filename}")
    
    async def _process_document(
        self, 
        filename: str, 
        content: bytes, 
        content_type: str
    ) -> ProcessedFile:
        """处理文档"""
        ext = Path(filename).suffix.lower()
        
        if ext in [".md", ".txt"]:
            # 直接解码文本
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("gbk", errors="ignore")
        elif ext == ".pdf":
            # PDF解析
            text = await self._extract_pdf_text(content)
        else:
            text = f"[无法解析的文档格式: {ext}]"
        
        # 限制长度
        if len(text) > self.MAX_TEXT_LENGTH:
            text = text[:self.MAX_TEXT_LENGTH] + f"\n\n[内容已截断，原文共{len(text)}字符]"
        
        return ProcessedFile(
            filename=filename,
            file_type="document",
            content_type=content_type,
            text_content=text,
            size_bytes=len(content)
        )
    
    async def _extract_pdf_text(self, content: bytes) -> str:
        """从PDF提取文本"""
        try:
            import pdfplumber
            import io
            
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text_parts = []
                for page in pdf.pages[:50]:  # 最多处理50页
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return "\n\n".join(text_parts)
        except ImportError:
            return "[PDF解析需要安装pdfplumber: pip install pdfplumber]"
        except Exception as e:
            return f"[PDF解析失败: {str(e)}]"
    
    def _process_image(
        self, 
        filename: str, 
        content: bytes, 
        content_type: str
    ) -> ProcessedFile:
        """处理图片"""
        # Base64编码
        base64_content = base64.b64encode(content).decode("utf-8")
        
        return ProcessedFile(
            filename=filename,
            file_type="image",
            content_type=content_type,
            base64_content=base64_content,
            size_bytes=len(content)
        )
    
    def save_file(self, filename: str, content: bytes) -> str:
        """保存文件到uploads目录"""
        # 生成唯一文件名
        import uuid
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = self.upload_dir / unique_name
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return str(file_path)
    
    def get_supported_extensions(self) -> dict:
        """获取支持的文件扩展名"""
        return {
            "documents": list(self.SUPPORTED_DOCUMENTS.keys()),
            "images": list(self.SUPPORTED_IMAGES.keys())
        }


def format_attachments_for_prompt(files: List[ProcessedFile]) -> str:
    """
    将附件格式化为LLM提示词的一部分
    """
    if not files:
        return ""
    
    parts = ["【附件内容】\n"]
    
    for i, f in enumerate(files, 1):
        if f.file_type == "document":
            parts.append(f"## 附件{i}: {f.filename}\n")
            parts.append(f"```\n{f.text_content[:5000]}\n```\n\n")
        elif f.file_type == "image":
            parts.append(f"## 附件{i}: {f.filename} (图片)\n")
            parts.append("请在分析中考虑此图片的内容。\n\n")
    
    return "\n".join(parts)
