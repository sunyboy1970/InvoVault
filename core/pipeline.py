"""批量处理流水线：去重扫描 → 并发识别 → 提取 → 判定 → 导出
- 三引擎回退：pdftotext → pymupdf(sort=True) → 视觉AI (core/pdf_parser.py)
- OFD 原生解析 (core/ofd_parser.py)
- ThreadPoolExecutor 线程池并发
- 增量缓存（文件哈希）
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional

from core.models import InvoiceRecord, TaxpayerType, InvoiceCategory, DeductibleStatus
from core.tax_rules import classify_invoice, compute_deductible_tax
from core.category_mapper import classify_item
from core.extractors.base import BaseExtractor, InvoiceRawData, get_extractor_for_file
from core.pdf_parser import extract_text_pdf
from core.ofd_parser import parse_ofd, extract_xbrl_fields


# ===== OFD 解析（使用独立模块）=====
def extract_text_ofd(ofd_path: str) -> str:
    """OFD 原生解析：提取完整版面文本"""
    result = parse_ofd(ofd_path)
    return result.get("text", "")


def extract_text_ofd_xbrl(ofd_path: str) -> dict:
    """OFD 内嵌 XBRL 结构化数据提取"""
    result = parse_ofd(ofd_path)
    return extract_xbrl_fields(result.get("xbrl_data", {}))


# ===== 缓存管理 =====
class CacheManager:
    """基于文件哈希的增量缓存"""
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _file_hash(self, path: str) -> str:
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        except FileNotFoundError:
            # 文件不存在时基于路径哈希（仅用于测试）
            h.update(path.encode())
        return h.hexdigest()[:16]

    def get(self, path: str, taxpayer_type: Optional[str] = None) -> Optional[InvoiceRecord]:
        fhash = self._file_hash(path)
        mode = taxpayer_type or "default"
        cache_file = self.cache_dir / f"{fhash}_{mode}.json"
        if cache_file.exists():
            import json
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                # Convert string enum values back to enum objects
                from core.models import TaxpayerType, InvoiceCategory, DeductibleStatus
                if 'taxpayer_type' in data and isinstance(data['taxpayer_type'], str):
                    data['taxpayer_type'] = TaxpayerType(data['taxpayer_type'])
                if 'invoice_category' in data and isinstance(data['invoice_category'], str):
                    data['invoice_category'] = InvoiceCategory(data['invoice_category'])
                if 'deductible_status' in data and isinstance(data['deductible_status'], str):
                    data['deductible_status'] = DeductibleStatus(data['deductible_status'])
                return InvoiceRecord(**data)
            except Exception:
                pass
        return None

    def set(self, path: str, record: InvoiceRecord, taxpayer_type: Optional[str] = None):
        fhash = self._file_hash(path)
        mode = taxpayer_type or "default"
        cache_file = self.cache_dir / f"{fhash}_{mode}.json"
        import json
        with self._lock:
            # 构建可序列化的字典
            data = {}
            for k, v in record.__dict__.items():
                if hasattr(v, 'value'):  # Enum
                    data[k] = v.value
                else:
                    data[k] = v
            cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ===== 单文件处理 =====
def process_single_file(
    file_path: str,
    taxpayer_type: TaxpayerType,
    vision_config: dict,
    cache=None,
) -> InvoiceRecord:
    """处理单个 PDF/OFD 文件，返回 InvoiceRecord"""
    ext = Path(file_path).suffix.lower()

    # 缓存命中
    if cache:
        cached = cache.get(file_path, taxpayer_type.value if taxpayer_type else None)
        if cached:
            return cached

    # 1. 提取文本
    if ext == ".pdf":
        text = extract_text_pdf(file_path, vision_config)
        xbrl_data = None
    elif ext == ".ofd":
        text = extract_text_ofd(file_path)
        xbrl_data = extract_text_ofd_xbrl(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    # 2. 选择识别器
    extractor = get_extractor_for_file(file_path, text)
    raw_data: InvoiceRawData = extractor.extract(file_path, text, xbrl_data)

    # 标准化括号：半角( ) → 全角（ ）
    raw_data.seller_name = BaseExtractor._normalize_brackets(raw_data.seller_name)
    raw_data.buyer_name = BaseExtractor._normalize_brackets(raw_data.buyer_name)

    # 3. 分类
    category = classify_invoice(raw_data.invoice_type, raw_data.item_name, raw_data.tax_rate)

    # 4. 计算金额字段（一般纳税人模式）
    tax_rate_value = 0.0  # 初始化
    if taxpayer_type == TaxpayerType.GENERAL:
        # 优先使用提取器计算的明细汇总值
        items_nontax_total = sum(
            item.get("amount_no_tax", 0) for item in (raw_data.items or [])
        )
        items_tax_total = sum(
            item.get("tax_amount", 0) for item in (raw_data.items or [])
        )

        # 当提取器已提供有效明细值时优先使用
        if items_nontax_total > 0.005 and items_tax_total > 0.005:
            amount_no_tax = round(items_nontax_total, 2)
            tax_amount = round(items_tax_total, 2)
        else:
            # 税率解析
            tr = raw_data.tax_rate.replace("%", "").replace("％", "")
            try:
                tax_rate_value = float(tr) / 100 if tr else 0.0
            except ValueError:
                tax_rate_value = 0.0

            if tax_rate_value > 0:
                amount_no_tax = round(raw_data.total_amount / (1 + tax_rate_value), 2)
                tax_amount = round(raw_data.total_amount - amount_no_tax, 2)
            else:
                # 不征税/免税等：全额即为不含税金额
                amount_no_tax = raw_data.total_amount
                tax_amount = 0.0

        # 抵扣判定
        deductible_tax, deductible_status, reason = compute_deductible_tax(
            category, raw_data.total_amount, tax_amount, tax_rate_value,
            raw_data.item_name, raw_data.seller_name, raw_data.extra
        )
    else:
        tax_rate_value = 0.0
        amount_no_tax = 0.0
        tax_amount = 0.0
        deductible_tax = 0.0
        deductible_status = DeductibleStatus.NONE
        reason = ""

    # 5. 构建记录
    record = InvoiceRecord(
        invoice_type=raw_data.invoice_type,
        invoice_category=category,
        invoice_number=raw_data.invoice_number,
        invoice_date=raw_data.invoice_date,
        seller_name=raw_data.seller_name,
        seller_tax_id=raw_data.seller_tax_id,
        buyer_name=raw_data.buyer_name,
        buyer_tax_id=raw_data.buyer_tax_id,
        item_name=raw_data.item_name,
        tax_rate=raw_data.tax_rate,
        tax_rate_value=tax_rate_value,
        amount_no_tax=amount_no_tax,
        tax_amount=tax_amount,
        total_amount=raw_data.total_amount,
        source_file=Path(file_path).name,
        deductible_tax=deductible_tax,
        deductible_status=deductible_status,
        deductible_reason=reason,
        raw_data=raw_data.extra,
    )

    # 缓存
    if cache:
        cache.set(file_path, record, taxpayer_type.value if taxpayer_type else None)

    return record


# ===== 批量流水线 =====
def process_invoices(
    folder: str,
    taxpayer_type: TaxpayerType,
    vision_config: dict,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    row_callback: Optional[Callable[[InvoiceRecord], None]] = None,
    skip_duplicates: bool = True,
) -> list[InvoiceRecord]:
    """
    批量处理文件夹下所有 PDF/OFD 发票
    Returns: 排序后的 InvoiceRecord 列表
    """
    folder_path = Path(folder)
    files = [f for f in folder_path.rglob("*") if f.suffix.lower() in (".pdf", ".ofd")]

    # 1. 去重扫描（发票号码）
    if skip_duplicates:
        seen = {}
        unique_files = []
        for f in files:
            # 从文件名快速提取 20位+ 数字
            match = re.search(r"\d{20,}", f.name)
            inv_no = match.group() if match else None
            if inv_no and inv_no in seen:
                print(f"⚠ 重复发票号码跳过: {inv_no} ({f.name})")
                continue
            if inv_no:
                seen[inv_no] = f
            unique_files.append(f)
        files = unique_files

    total = len(files)
    records = []
    cache = CacheManager(vision_config.get("cache_dir", "~/.cache/invoice-extractor"))

    # 2. 并发处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, str(f), taxpayer_type, vision_config, cache): f
            for f in files
        }

        for i, future in enumerate(as_completed(future_to_file), 1):
            f = future_to_file[future]
            try:
                rec = future.result()
                records.append(rec)
                if row_callback:
                    row_callback(rec)
            except Exception as e:
                print(f"❌ 处理失败 {f.name}: {e}")

            if progress_callback:
                progress_callback(i, total, f.name)

    # 3. 排序：项目名称 + 销售方名称
    records.sort()
    return records