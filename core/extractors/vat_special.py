"""增值税专用发票识别器"""
from __future__ import annotations
from pathlib import Path
import re
from core.extractors.base import BaseExtractor, InvoiceRawData


class VatSpecialExtractor(BaseExtractor):
    """增值税专用发票识别器"""

    SUPPORTED_TYPES = ["vat_special", "专用发票", "增值税专用发票", "增值税专用发票（电子）"]
    PRIORITY = 10  # 最高优先级

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview_text(file_path)
        return "专用发票" in text and "普通发票" not in text

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "增值税专用发票"
        if "电子" in text and "专用" in text:
            invoice_type = "增值税专用发票（电子）"

        # 解析明细行
        items = self._extract_items(text)

        # 兜底：如果没有明细，从全文解析汇总信息
        if not items:
            total_amount = self._find_total_amount(text)
            tax_rate_str = self._find_tax_rate(text)
            tax_rate_val = float(tax_rate_str.replace("%", "").replace("％", "")) / 100 if tax_rate_str else 0.13
            tax_amount = round(total_amount / (1 + tax_rate_val) * tax_rate_val, 2) if tax_rate_val else 0.0
            amount_no_tax = total_amount - tax_amount

            items = [{
                "name": self._find_item_name(text) or "*货物*货物",
                "unit": "",
                "quantity": 1,
                "unit_price": 0,
                "amount_no_tax": amount_no_tax,
                "tax_rate": self._find_tax_rate(text) or "13%",
                "tax_amount": tax_amount,
                "total_amount": total_amount,
            }]

        # 提取基础信息
        invoice_code = self._find_inv_code(text)
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)
        seller_name = self._find_seller(text)
        seller_tax_id = self._find_seller_tax_id(text)
        buyer_name = self._find_buyer(text)
        buyer_tax_id = self._find_buyer_tax_id(text)
        total_amount = sum(item["total_amount"] for item in items)
        tax_amount = sum(item["tax_amount"] for item in items)

        # 抵扣判定
        from core.tax_rules import classify_invoice, compute_deductible_tax, DeductibleStatus
        category = classify_invoice("增值税专用发票", items[0].get("name", ""), self._find_tax_rate(text))
        
        # 计算平均税率值
        tax_rate_values = []
        for item in items:
            rate_str = item.get("tax_rate", "0%")
            try:
                rate_val = float(rate_str.replace("%", "").replace("％", "")) / 100
                tax_rate_values.append(rate_val)
            except (ValueError, ZeroDivisionError):
                pass
        avg_tax_rate = sum(tax_rate_values) / len(tax_rate_values) if tax_rate_values else 0
        
        deductible_tax, deductible_status, reason = compute_deductible_tax(
            category, sum(item["total_amount"] for item in items),
            sum(item["tax_amount"] for item in items),
            avg_tax_rate,
            items[0].get("name", ""), self._find_seller(text), {}
        )

        record = InvoiceRawData(
            invoice_type="增值税专用发票",
            invoice_code=invoice_code,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax_id,
            items=[
                {
                    "name": item["name"],
                    "unit": item.get("unit", ""),
                    "quantity": item.get("quantity", 1),
                    "unit_price": item.get("unit_price", 0),
                    "amount_no_tax": item["amount_no_tax"],
                    "tax_rate": item["tax_rate"],
                    "tax_amount": item["tax_amount"],
                    "total_amount": item["total_amount"],
                } for item in items
            ],
            total_amount=sum(item["total_amount"] for item in items),
            total_tax=sum(item["tax_amount"] for item in items),
            tax_rate=self._find_tax_rate(text),
            item_name=items[0]["name"] if items else "",
            deductible_tax=deductible_tax,
            deductible_status=deductible_status,
            deductible_reason=reason,
            raw_text=text[:2000],
        )
        return record

    def _extract_items(self, text: str) -> list[dict]:
        """解析明细行：支持多行明细"""
        items = []
        # 模式：*分类*名称 单位 数量 单价 金额 税率 税额
        pattern = r"\*([^*]+?)\*([^\s]+)\s+(\S+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+(\d+%?)\s+([\d.,]+)"
        matches = re.findall(pattern, text)
        for m in matches:
            category, name, unit, qty, price, amount, tax_rate, tax_amt = m
            try:
                items.append({
                    "name": f"*{category}*{name}",
                    "unit": unit,
                    "quantity": float(qty.replace(",", "")),
                    "unit_price": float(price.replace(",", "")),
                    "amount_no_tax": float(amount.replace(",", "")),
                    "tax_rate": tax_rate if tax_rate.endswith("%") else tax_rate + "%",
                    "tax_amount": float(tax_amt.replace(",", "")),
                    "total_amount": float(amount.replace(",", "")) + float(tax_amt.replace(",", "")),
                })
            except ValueError:
                continue
        return items

    def _find_inv_code(self, text: str) -> str:
        m = re.search(r"发票代码[：:]\s*(\d{10,12})", text)
        return m.group(1) if m else ""

    def _find_inv_no(self, text: str) -> str:
        m = re.search(r"发票号码[：:]\s*(\d{8,20})", text)
        return m.group(1) if m else ""

    def _find_date(self, text: str) -> str:
        m = re.search(r"开票日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)", text)
        return m.group(1) if m else ""

    def _find_seller(self, text: str) -> str:
        # 格式1：售 名称: XXX（通行费格式）
        m = re.search(r"售\s*名\s*称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["电话", "地址", "纳税人", "账号", "开户银行", "增值税", "主管税务", "或征收率", "信"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        # 格式2：销 名 称 / 销售方名称 / 销货单位名称
        m = re.search(r"(?:销\s*名\s*称|销售方名称|销货单位名称)[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["电话", "地址", "纳税人", "账号", "开户银行", "增值税", "主管税务", "或征收率"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""

    def _find_seller_tax_id(self, text: str) -> str:
        m = re.search(r"(?:销售方|销货单位)纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""

    def _find_buyer(self, text: str) -> str:
        # 优先精确匹配"购买方名称"
        m = re.search(r"购买方名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["身份证", "证件", "地址", "电话"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        # 匹配"购货单位名称"
        m = re.search(r"购货单位名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["身份证", "证件", "地址", "电话"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        # 匹配"购 名称:"格式（与销方同行）
        m = re.search(r"购\s*名\s*称[：:]\s*([^\s][^销]*)", text)
        if m:
            name = m.group(1).strip()
            return name
        return ""

    def _find_tax_rate(self, text: str) -> str:
        m = re.search(r"税率[：:]\s*(\d+%?|\d+%)", text)
        if m:
            rate = m.group(1)
            if not rate.endswith("%"):
                rate = rate + "%"
            return rate
        m = re.search(r"征收率[：:]\s*(\d+%?|\d+%)", text)
        if m:
            rate = m.group(1)
            if not rate.endswith("%"):
                rate = rate + "%"
            return rate
        # 从明细行提取税率（跳过加密区）
        header_idx = text.find("货物或应税劳务")
        if header_idx < 0:
            header_idx = text.find("项目名称")
        search_text = text[header_idx:] if header_idx >= 0 else text
        # 模式1：带分类的完整行
        m = re.search(r"\*[^*]+\*[^\s]+(?:\s+\S+){2,5}\s+(\d+%)\s+[\d.,]+(?:\s|$)", search_text)
        if m:
            return m.group(1)
        # 模式2：简洁行
        m = re.search(r"\*[^*]+\*[^\s]+\s+[\d.,]+\s+(\d+%)\s+[\d.,]+", search_text)
        if m:
            return m.group(1)
        return ""

    def _find_seller_tax_id(self, text: str) -> str:
        m = re.search(r"(?:销售方|销货单位)纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""

    def _find_buyer_tax_id(self, text: str) -> str:
        m = re.search(r"(?:购买方|购货单位)纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""

    def _find_total_amount(self, text: str) -> float:
        m = re.search(r"[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        m = re.search(r"价\s*税\s*合\s*计[：:]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        return 0.0

    def _find_tax_amount(self, text: str) -> float:
        m = re.search(r"税\s*额\s*合\s*计[：:]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        m = re.search(r"税\s*额[：:]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        return 0.0

    def _find_item_name(self, text: str) -> str:
        # 跳过加密区：只在"货物或应税劳务"或"项目名称"之后查找
        header_idx = text.find("货物或应税劳务")
        if header_idx < 0:
            header_idx = text.find("项目名称")
        search_text = text[header_idx:] if header_idx >= 0 else text
        m = re.search(r"\*([^*]+?)\*([^\s]+)", search_text)
        if m:
            return f"*{m.group(1)}*{m.group(2)}"
        # 从表头下第一行提取
        lines = search_text.split("\n")
        for i, line in enumerate(lines):
            if "货物或应税劳务" in line or "项目名称" in line:
                if i + 1 < len(lines):
                    m = re.search(r"\*([^*]+?)\*([^\s]+)", lines[i + 1])
                    if m:
                        return f"*{m.group(1)}*{m.group(2)}"
        return ""

    def _extract_preview_text(self, file_path: Path) -> str:
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                raw = page.get_text("text", sort=True)
                raw = re.sub(r"[ \t]{3,}", " ", raw)
                text += raw
                if len(text) > 500:
                    break
            return re.sub(r"[ \t]{2,}", " ", text[:800])
        except Exception:
            return ""


# 注册
from core.extractors.base import register_extractor
register_extractor(VatSpecialExtractor())