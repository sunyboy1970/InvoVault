"""识别器基类与注册表"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import threading

from core.models import InvoiceCategory, DeductibleStatus


@dataclass
class InvoiceRawData:
    """识别器返回的原始字段"""
    invoice_type: str              # 发票类型标识
    invoice_code: str = ""         # 发票代码（如有）
    invoice_number: str = ""       # 发票号码
    invoice_date: str = ""         # 开票日期
    seller_name: str = ""          # 销售方名称
    seller_tax_id: str = ""        # 销售方纳税人识别号
    buyer_name: str = ""           # 购买方名称
    buyer_tax_id: str = ""         # 购买方纳税人识别号
    items: list[dict] = field(default_factory=list)  # 明细项
    total_amount: float = 0.0      # 价税合计
    total_tax: float = 0.0         # 税额合计
    amount_in_words: str = ""      # 价税合计大写
    remarks: str = ""              # 备注
    tax_rate: str = ""             # 税率字符串 "9%" "6%" "3%" "1%"
    extra: dict[str, Any] = field(default_factory=dict)  # 票种特有字段
    raw_text: str = ""             # 原始全文
    # 兼容字段：单明细发票直接填 item_name
    item_name: str = ""            # *分类*项目名 格式
    # 抵扣相关字段（由识别器填充，供流水线使用）
    deductible_tax: float = 0.0          # 可抵扣税额
    deductible_status: DeductibleStatus = DeductibleStatus.NONE
    deductible_reason: str = ""          # 抵扣判定理由


class BaseExtractor(ABC):
    """所有票种识别器的抽象基类"""

    # 子类必须定义
    SUPPORTED_TYPES: list[str] = []        # 如 ["vat_special"]
    FILE_EXTENSIONS: list[str] = [".pdf", ".ofd"]
    PRIORITY: int = 100                    # 优先级：越小越优先

    @abstractmethod
    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        """判断是否能处理该文件（通过文件头、关键字、视觉特征）"""
        pass

    @abstractmethod
    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        """提取发票信息
        Args:
            file_path: 文件路径
            text: 已提取的文本内容
            xbrl_data: OFD 内嵌 XBRL 数据（如有）
        """
        pass

    # 通用工具方法
    def _find_inv_no(self, text: str) -> str:
        """提取发票号码（20位+数字）"""
        import re
        match = re.search(r"\d{20,}", text)
        return match.group() if match else ""

    def _find_date(self, text: str) -> str:
        """提取开票日期"""
        import re
        match = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text)
        return match.group() if match else ""

    def _find_seller(self, text: str) -> str:
        """提取销售方名称（兼容全角空格）"""
        import re
        # 匹配 "销 名 称" / "销售方名称" / "销货单位名称" 等
        match = re.search(
            r"(?:销[\s\u3000]*名[\s\u3000]*称|销售方名称|销货单位名称)\s*[：:]\s*([^\n]+)",
            text
        )
        if match:
            name = match.group(1).strip()
            # 清理后缀：电话、地址、纳税人识别号、账号、开户银行等
            suffixes = ["电话", "地址", "纳税人", "账号", "开户银行", "增值税", "主管税务", "或征收率"]
            for suf in suffixes:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""

    def _find_total_amount(self, text: str) -> float:
        """提取价税合计（小写）"""
        import re
        # 优先匹配 （小写） 后的金额
        match = re.search(r"[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if match:
            return float(match.group(1).replace(",", ""))
        # 备选：价税合计
        match = re.search(r"价\s*税\s*合\s*计\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if match:
            return float(match.group(1).replace(",", ""))
        return 0.0

    def _find_tax_rate(self, text: str) -> str:
        """提取税率"""
        import re
        match = re.search(r"税率[\s:：]*(\d+%?)", text)
        if match:
            rate = match.group(1)
            if not rate.endswith("%"):
                rate += "%"
            return rate
        # 备选：征收率
        match = re.search(r"征收率[\s:：]*(\d+%?)", text)
        if match:
            rate = match.group(1)
            if not rate.endswith("%"):
                rate += "%"
            return rate
        return ""

    def _find_item_name(self, text: str) -> str:
        """提取项目名称：*分类*项目名"""
        import re
        match = re.search(r"\*([^*]+)\*([^\s(]+)", text)
        if match:
            return f"*{match.group(1)}*{match.group(2)}"
        return ""


    @staticmethod
    def _normalize_brackets(name: str) -> str:
        """将半角括号 ( ) 统一替换为全角括号 （ ）
        中国税控系统在名称中使用全角括号，OCR/PDF提取可能产生半角
        """
        return name.replace("(", "（").replace(")", "）")


# ===== 共享常量 =====
# 网约车平台关键词（必须与 RideHailingExtractor 同步）
# 用于 dispatch 确认检查 + VatNormalExtractor 排除
RIDE_HAILING_KEYWORDS: list[str] = [
    "网约车", "曹操出行", "滴滴出行", "享道出行", "首汽约车",
    "T3出行", "花小猪", "万顺叫车", "美团打车",
    "如祺出行", "风韵出行", "腾飞出行", "及时用车",
    "妥妥E行", "鞍马出行", "启滴出行", "雷利出行",
    "容祥出行", "哈哈出行", "飞马出行", "立道出行",
    "鲸志出行", "喜行约车", "星徽出行", "美程出行",
]
RIDE_HAILING_SHORT_PLATFORMS: list[str] = [
    "滴滴", "曹操", "哈啰", "哈罗",
    "高德", "享道",
]


# ===== 注册表（按 PRIORITY 升序，专票优先）=====
_EXTRACTOR_REGISTRY: list[BaseExtractor] = []
_REGISTRY_INITIALIZED = False
_REGISTRY_LOCK = threading.Lock()


def register_extractor(extractor: BaseExtractor):
    """注册识别器，按 PRIORITY 排序"""
    _EXTRACTOR_REGISTRY.append(extractor)
    _EXTRACTOR_REGISTRY.sort(key=lambda e: e.PRIORITY)


def _ensure_registry_initialized():
    """延迟初始化：导入所有已知识别器模块以触发注册（线程安全）"""
    global _REGISTRY_INITIALIZED, _REGISTRY_LOCK
    if _REGISTRY_INITIALIZED:
        return
    with _REGISTRY_LOCK:
        if _REGISTRY_INITIALIZED:
            return
        try:
            import core.extractors.vat_special      # noqa: F401
            import core.extractors.vat_normal       # noqa: F401
            import core.extractors.railway          # noqa: F401
            import core.extractors.air              # noqa: F401
            import core.extractors.toll             # noqa: F401
            import core.extractors.ride_hailing     # noqa: F401
            import core.extractors.vehicle_sales    # noqa: F401
            import core.extractors.customs          # noqa: F401
            import core.extractors.others           # noqa: F401
        except ImportError:
            pass  # 部分识别器可能尚未创建
        _REGISTRY_INITIALIZED = True


def get_extractor_for_file(file_path: Path, preview_text: str = "") -> BaseExtractor:
    """自动分发：按 PRIORITY 顺序尝试 can_handle
    
    两阶段调度：
      1. 遍历所有已注册识别器，收集 can_handle 返回 True 的候选项
      2. 从候选项中选 PRIORITY 最小的（最优先）
      3. 如果候选项是 VatNormalExtractor (兜底)，做二次确认：
         检查文本/文件名中是否有网约车等关键词，若存在则优先使用 RideHailingExtractor
    """
    _ensure_registry_initialized()
    
    # 提取文本和文件名信息
    text = preview_text or ""
    fname_lower = str(file_path).lower()
    
    # 通过文件名辅助检测网约车
    ride_hailing_in_filename = any(kw in fname_lower for kw in ["网约车", "didihc", "ride", "hailing"])
    
    candidates: list[BaseExtractor] = []
    
    for ext in _EXTRACTOR_REGISTRY:
        try:
            if ext.can_handle(file_path, preview_text):
                candidates.append(ext)
        except Exception:
            continue
    
    if candidates:
        # 按 PRIORITY 升序排列，取最优
        candidates.sort(key=lambda e: e.PRIORITY)
        best = candidates[0]
        
        # 二次确认：如果 best 是 VatNormalExtractor (PRIORITY=100),
        # 检查是否有 RideHailingExtractor 应该匹配的迹象（文本或文件名中）
        from .vat_normal import VatNormalExtractor
        if isinstance(best, VatNormalExtractor) or best.PRIORITY >= 100:
            # 检查文本中是否有网约车平台关键词
            has_ride_hailing = any(kw in text for kw in RIDE_HAILING_KEYWORDS)
            has_platform = any(kw in text for kw in RIDE_HAILING_SHORT_PLATFORMS)
            # 兼容"增值税电子普通发票"（"电子"与"发票"可能不连续）
            has_electronic = "电子" in text and "发票" in text
            text_indicates_ride = (has_ride_hailing or (has_platform and has_electronic))
            
            if text_indicates_ride or ride_hailing_in_filename:
                # 尝试找 RideHailingExtractor
                for ext in _EXTRACTOR_REGISTRY:
                    if hasattr(ext, 'SUPPORTED_TYPES') and any(
                        t in ["ride_hailing_electronic", "网约车电子发票"] 
                        for t in ext.SUPPORTED_TYPES
                    ):
                        return ext
        return best
    
    # 文件名辅助调度：文件名含网约车关键词 → 尝试 RideHailingExtractor
    if ride_hailing_in_filename:
        for ext in _EXTRACTOR_REGISTRY:
            if hasattr(ext, 'SUPPORTED_TYPES') and any(
                t in ["ride_hailing_electronic", "网约车电子发票"] 
                for t in ext.SUPPORTED_TYPES
            ):
                return ext
    
    # 兜底：普通发票识别器（优先级最低）
    from .vat_normal import VatNormalExtractor
    return VatNormalExtractor()