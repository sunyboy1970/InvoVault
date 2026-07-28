"""铁路电子客票识别器"""
from __future__ import annotations
from pathlib import Path
import re
from core.extractors.base import BaseExtractor, InvoiceRawData


class RailwayExtractor(BaseExtractor):
    """铁路电子客票识别器"""

    SUPPORTED_TYPES = ["railway_electronic", "铁路电子客票", "铁路电子客票（报销凭证）"]
    PRIORITY = 10

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview_text(file_path)
        return "铁路电子客票" in text or ("铁路" in text and "客票" in text)

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "铁路电子客票"
        if "报销凭证" in text:
            invoice_type = "铁路电子客票（报销凭证）"

        total_amount = self._find_total_amount(text)
        tax_rate_val = 0.09
        tax_rate_str = "9%"
        amount_no_tax = round(total_amount / (1 + tax_rate_val), 2)
        tax_amount = round(total_amount - amount_no_tax, 2)
        item_name = "*运输服务*客运服务费"
        seller_name = self._find_seller(text)
        buyer_name = self._find_buyer(text)
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)

        # 提取旅客信息
        passenger = self._extract_passenger(text)

        items = [{
            "name": item_name, "unit": "张", "quantity": 1,
            "unit_price": amount_no_tax, "amount_no_tax": amount_no_tax,
            "tax_rate": tax_rate_str, "tax_amount": tax_amount, "total_amount": total_amount
        }]

        extra = {"passenger_name": passenger, "ticket_price": total_amount}
        if passenger:
            extra["passenger_name"] = passenger

        return InvoiceRawData(
            invoice_type=invoice_type, invoice_code="", invoice_number=invoice_number,
            invoice_date=invoice_date, seller_name=seller_name, seller_tax_id="",
            buyer_name=buyer_name, buyer_tax_id="",
            items=items, total_amount=total_amount, total_tax=tax_amount,
            tax_rate=tax_rate_str, item_name=item_name, extra=extra, raw_text=text[:2000]
        )

    def _find_total_amount(self, text: str) -> float:
        m = re.search(r"[¥￥]([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        m = re.search(r"([\d,]+\.?\s*\d{2})(?!\d)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        return 0.0

    def _find_inv_no(self, text: str) -> str:
        m = re.search(r"发票号码[：:]\s*(\d{20,})", text)
        if m: return m.group(1)
        m = re.search(r"(\d{20,})", text)
        return m.group(1) if m else ""

    def _find_date(self, text: str) -> str:
        m = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text)
        return m.group() if m else ""

    def _find_seller(self, text: str) -> str:
        # 从出发/到达站提取
        m = re.search(r"([\u4e00-\u9fa5]+站)\s", text)
        if m: return f"中国铁路{m.group(1)}"
        return "中国铁路"

    def _find_buyer(self, text: str) -> str:
        m = re.search(r"购买方名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for c in ["统一", "纳税人", "识别号"]:
                idx = name.find(c)
                if idx > 0: name = name[:idx].strip()
            return name
        return ""

    def _extract_passenger(self, text: str) -> str:
        for line in text.split("\n"):
            if "****" in line or "***" in line:
                m = re.search(r"\d+\*\**\d+\s+(.+)", line)
                if m: return m.group(1).strip().split()[0] if m.group(1).strip() else ""
        return ""

    def _extract_preview_text(self, file_path: Path) -> str:
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text("text", sort=True)
                if len(text) > 500: break
            return text[:500]
        except Exception: return ""


from core.extractors.base import register_extractor
register_extractor(RailwayExtractor())