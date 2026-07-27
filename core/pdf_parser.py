"""PDF 三引擎解析管线封装类

Engine 1: pdftotext -layout -enc UTF-8 (首选，保留版面)
Engine 2: PyMuPDF sort=True (处理全角空格、中文排版，规避 Windows 中文路径崩溃)
Engine 3: 视觉大模型 GLM-4V-Flash (渲染首页 PNG -> Vision API)
"""
from __future__ import annotations
import base64
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class PDFParser:
    """PDF 三引擎解析管线封装类
    
    回退顺序：
    1. pdftotext -layout -enc UTF-8 (首选，保留版面)
    2. PyMuPDF sort=True (处理全角空格、中文排版，规避 Windows 中文路径崩溃)
    3. Vision LLM (GLM-4V-Flash，渲染首页 PNG -> API)
    
    Vision 配置格式:
        vision_config = {
            "enabled": True,
            "api_key": "...",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4v-flash"
        }
    """
    
    # 发票关键字段正则
    _INV_NO_PATTERN = re.compile(r"\d{20}")                           # 发票号码 20位
    _SELLER_PATTERN = re.compile(r"销\s*售\s*方?\s*名\s*称")            # 销售方名称 (匹配 销售方名称、销售名称)
    _DATE_PATTERN = re.compile(r"开\s*票\s*日\s*期")                    # 开票日期
    _TOTAL_PATTERN = re.compile(r"[（(]\s*小\s*写\s*[）)]")              # 价税合计(小写) (匹配中英文括号)
    
    def __init__(self, vision_config: Optional[dict] = None):
        """初始化 PDF 解析器
        
        Args:
            vision_config: Vision API 配置，包含 enabled, api_key, base_url, model
        """
        self.vision_config = vision_config or {}
        self._ascii_temp_dir = Path(tempfile.gettempdir()) / "inv_ascii"
        self._ascii_temp_dir.mkdir(exist_ok=True)
    
    def _get_ascii_path(self, pdf_path: str) -> Path:
        """获取 ASCII 安全路径：如果路径包含非 ASCII 字符，复制到临时目录"""
        if any(ord(c) > 127 for c in pdf_path):
            import threading
            ascii_path = self._ascii_temp_dir / f"inv_{os.getpid()}_{threading.get_ident()}.pdf"
            shutil.copy2(pdf_path, ascii_path)
            return ascii_path
        return Path(pdf_path)
    
    def _is_text_usable(self, text: str) -> bool:
        """检测提取文本是否包含关键发票字段
        
        检测字段：
        - 发票号码 (20位数字)
        - 销售方名称 (含"销售方名称"或"销售名称")
        - 开票日期 (含"开票日期")
        - 价税合计(小写) (含"(小写)")
        
        Args:
            text: 提取的文本内容
            
        Returns:
            是否包含所有关键字段
        """
        if not text or not text.strip():
            return False
        
        has_inv_no = bool(self._INV_NO_PATTERN.search(text))
        has_seller = bool(self._SELLER_PATTERN.search(text))
        has_date = bool(self._DATE_PATTERN.search(text))
        has_total = bool(self._TOTAL_PATTERN.search(text))
        
        return has_inv_no and has_seller and has_date and has_total
    
    # ===== Engine 1: pdftotext =====
    def _extract_pdftotext(self, pdf_path: str) -> str:
        """Engine 1: pdftotext -layout -enc UTF-8 (首选，保留版面)"""
        try:
            result = subprocess.run(
                ["pdftotext", "-enc", "UTF-8", "-layout", pdf_path, "-"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30
            )
            return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError, UnicodeDecodeError):
            return ""
    
    # ===== Engine 2: PyMuPDF =====
    def _extract_pymupdf(self, pdf_path: str) -> str:
        """Engine 2: PyMuPDF sort=True (处理全角空格、中文排版，规避 Windows 中文路径崩溃)"""
        import fitz  # 延迟加载，节省启动时间
        ascii_path = self._get_ascii_path(pdf_path)
        
        doc = fitz.open(str(ascii_path))
        try:
            texts = [page.get_text("text", sort=True) for page in doc]
            raw_text = "\n".join(texts)
            # 后处理：规范化全角空格、修复常见排版问题
            return self._normalize_pdf_text(raw_text)
        finally:
            doc.close()
    
    def _normalize_pdf_text(self, text: str) -> str:
        """规范化 PDF 提取文本：全角空格、换行、字符修复"""
        if not text:
            return ""
        # 全角空格 -> 半角空格
        text = text.replace('\u3000', ' ')
        # 全角冒号 -> 半角冒号
        text = text.replace('：', ':')
        # 全角括号 -> 半角括号
        text = text.replace('（', '(').replace('）', ')')
        # 连续多空格压缩为单空格（保留换行）
        lines = text.split('\n')
        normalized_lines = []
        for line in lines:
            # 行内多空格压缩
            line = re.sub(r'[ \t]+', ' ', line)
            normalized_lines.append(line.strip())
        # 合并，去除空行
        result = '\n'.join([l for l in normalized_lines if l.strip()])
        return result
    
    # ===== Engine 3: Vision LLM =====
    def _extract_vision(self, pdf_path: str) -> str:
        """Engine 3: Vision LLM (渲染首页 PNG -> GLM-4V-Flash API)"""
        if not self.vision_config.get("enabled") or not self.vision_config.get("api_key"):
            return ""
        
        import fitz  # 延迟加载
        import requests  # 延迟加载
        ascii_path = self._get_ascii_path(pdf_path)
        
        doc = fitz.open(str(ascii_path))
        try:
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            png_bytes = pix.tobytes("png")
        finally:
            doc.close()
        
        b64 = base64.b64encode(png_bytes).decode()
        
        prompt = (
            "请完整提取这张发票上的所有文字信息，包括："
            "发票号码、开票日期、销售方名称、项目名称、价税合计（小写）、"
            "金额、税率、税额等所有字段。只返回纯文本，不要markdown。"
        )
        
        api_key = self.vision_config["api_key"]
        base_url = self.vision_config.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        model = self.vision_config.get("model", "glm-4v-flash")
        
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }],
                "max_tokens": 2048
            },
            timeout=120
        )
        resp.raise_for_status()
        
        return resp.json()["choices"][0]["message"]["content"]
    
    # ===== Public API =====
    def extract_text_pdf(self, pdf_path: str, vision_config: Optional[dict] = None) -> str:
        """PDF 三引擎自动回退提取文本
        
        回退顺序：
        1. pdftotext -layout -enc UTF-8
        2. PyMuPDF sort=True
        3. Vision LLM (GLM-4V-Flash)
        
        Args:
            pdf_path: PDF 文件路径
            vision_config: 可选，覆盖实例配置的 Vision 配置
            
        Returns:
            提取的文本内容 (若都失败返回最佳尝试结果)
        """
        # 允许运行时覆盖 vision_config
        if vision_config is not None:
            self.vision_config = vision_config
        
        # Engine 1: pdftotext
        text = self._extract_pdftotext(pdf_path)
        if self._is_text_usable(text):
            return text
        
        # Engine 2: PyMuPDF
        text = self._extract_pymupdf(pdf_path)
        if self._is_text_usable(text):
            return text
        
        # Engine 3: Vision LLM
        if self.vision_config.get("enabled") and self.vision_config.get("api_key"):
            try:
                return self._extract_vision(pdf_path)
            except Exception:
                pass  # 失败则回退返回最佳尝试
        
        return text  # 返回最好的尝试结果（可能为空）


# ===== 便捷函数：保持向后兼容 =====
def extract_text_pdf(pdf_path: str, vision_config: dict) -> str:
    """便捷函数：PDF 三引擎自动回退提取文本
    
    供 pipeline.py 直接替换原有 extract_text_pdf 函数使用。
    
    Args:
        pdf_path: PDF 文件路径
        vision_config: Vision 配置 {"enabled": true, "api_key": "...", "base_url": "...", "model": "..."}
        
    Returns:
        提取的文本内容
    """
    parser = PDFParser(vision_config)
    return parser.extract_text_pdf(pdf_path)