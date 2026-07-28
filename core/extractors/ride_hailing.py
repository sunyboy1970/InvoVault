"""网约车电子发票识别器"""
from __future__ import annotations
from pathlib import Path
from core.extractors.base import BaseExtractor, InvoiceRawData, RIDE_HAILING_KEYWORDS, RIDE_HAILING_SHORT_PLATFORMS


class RideHailingExtractor(BaseExtractor):
    """网约车电子发票识别器
    
    规则（2026新规）：
    - 网约车普票，2026新规不可抵扣
    - 项目名：*交通运输服务*网约车服务费
    - 税率通常6%或9%，但不可抵扣
    - 可抵扣税额 = 0
    """

    SUPPORTED_TYPES = ["ride_hailing_electronic", "网约车电子发票", "网约车电子普通发票"]
    PRIORITY = 30

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview_text(file_path)
        # 使用共享常量中的网约车平台关键词
        haling_company = any(kw in text for kw in RIDE_HAILING_KEYWORDS)
        
        # 平台短名（来自共享常量）
        platform = any(kw in text for kw in RIDE_HAILING_SHORT_PLATFORMS)
        
        # 电子发票标识（兼容"增值税电子普通发票"中"电子"与"发票"不连续的情况）
        has_electronic = "电子" in text and "发票" in text
        has_electronic_and_plain = has_electronic and "普通" in text
        
        # 旅客运输服务 + 电子发票格式
        passenger_transport = "旅客运输服务" in text and has_electronic
        
        return ("网约车电子发票" in text or 
                "网约车电子普通发票" in text or
                ("网约车" in text and has_electronic_and_plain) or
                (haling_company and has_electronic_and_plain) or
                (platform and passenger_transport))

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "网约车电子普通发票"

        # 价税合计、税额
        total_amount = self._find_total_amount(text)
        total_tax = self._find_total_tax(text)
        
        # 税率
        tax_rate_str = self._find_tax_rate(text)
        tax_rate_val = float(tax_rate_str.replace("%", "")) / 100 if tax_rate_str else 0.06

        # 不含税金额
        amount_no_tax = round(total_amount - total_tax, 2) if total_amount and total_tax else 0.0

        # 项目名强制：*交通运输服务*网约车服务费
        item_name = "*交通运输服务*网约车服务费"

        # 2026新规：网约车不可抵扣
        deductible_tax = 0.0
        tax_rate_str = tax_rate_str or "6%"

        # 发票基础信息
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)

        # 销售方/购买方
        seller_name = self._find_seller(text)
        buyer_name = self._find_buyer(text)

        # 明细
        items = [{
            "name": item_name,
            "unit": "项",
            "quantity": 1,
            "unit_price": amount_no_tax,
            "amount_no_tax": amount_no_tax,
            "tax_rate": tax_rate_str,
            "tax_amount": total_tax,
            "total_amount": total_amount,
        }]

        # 额外字段
        extra = {
            "tax_rate_value": tax_rate_val,
            "deductible_tax": deductible_tax,
            "invoice_category": "网约车电子普通发票",
            "deductible": False,  # 2026新规：不可抵扣
            "deductible_reason": "2026新规：网约车电子普通发票不可抵扣进项税额",
        }

        return InvoiceRawData(
            invoice_type=invoice_type,
            invoice_code=self._find_inv_code(text),
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            seller_name=seller_name,
            seller_tax_id=self._find_seller_tax_id(text),
            buyer_name=buyer_name,
            buyer_tax_id=self._find_buyer_tax_id(text),
            items=items,
            total_amount=total_amount,
            total_tax=total_tax,
            tax_rate=tax_rate_str,
            item_name=items[0].get("name", "") if items else self._find_item_name(text),
            extra=extra,
            raw_text=text[:2000],
        )

    def _find_total_amount(self, text: str) -> float:
        """提取价税合计"""
        import re
        m = re.search(r"[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        # 价税合计（支持中文冒号）
        m = re.search(r"价\s*税\s*合\s*计[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0

    def _find_total_tax(self, text: str) -> float:
        """提取税额合计"""
        import re
        m = re.search(r"税\s*额\s*合\s*计[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"税\s*额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0

    def _find_tax_rate(self, text: str) -> str:
        """提取税率：优先找税率标签，其次从明细行提取，最后用列表匹配"""
        import re
        # 1. 从"税率:"标签提取
        m = re.search(r"税率[：:]\s*(\d+%|\d+)", text)
        if m:
            rate = m.group(1)
            return rate + "%" if not rate.endswith("%") else rate
        # 2. 从"征收率:"标签提取
        m = re.search(r"征收率[：:]\s*(\d+%|\d+)", text)
        if m:
            rate = m.group(1)
            return rate + "%" if not rate.endswith("%") else rate
        # 3. 从明细行提取（跳过加密区）
        for header in ["货物或应税劳务", "项目名称"]:
            idx = text.find(header)
            if idx >= 0:
                search = text[idx:]
                m = re.search(r"\*[^*]+\*[^\s]+(?:\s+\S+){1,5}\s+(\d+)%\s+[\d.,]+", search)
                if m:
                    return m.group(1) + "%"
        # 4. 简单字符串匹配
        for rate in ["13%", "9%", "6%", "3%", "1%", "0%"]:
            if rate in text:
                return rate
        return "6%"

    def _find_inv_code(self, text: str) -> str:
        """发票代码"""
        import re
        m = re.search(r"发票代码[：:]\s*(\d{10,12})", text)
        return m.group(1) if m else ""

    def _find_inv_no(self, text: str) -> str:
        """发票号码"""
        import re
        m = re.search(r"发票号码[：:]\s*(\d{8,20})", text)
        return m.group(1) if m else ""

    def _find_date(self, text: str) -> str:
        """开票日期"""
        import re
        m = re.search(r"开票日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        return m.group(1) if m else ""

    def _find_seller(self, text: str) -> str:
        """销售方名称"""
        import re
        # 格式1（优先）：两个"名称:"条目 —— 按"名称:"分割取最后一个段
        # 适用于：
        #   " 名称:买方 名称:卖方"
        #   " 名称:买方名称:卖方"
        #   "购 名称:买方 销 名称:卖方"
        # 优先于"售/销 名称:"前缀格式，因为前缀格式可能误匹配含买方名称的行
        parts = re.split(r"名称\s*[：:]\s*", text)
        if len(parts) >= 3:
            seller_raw = parts[-1].strip()
            seller = seller_raw.split("\n")[0].strip()
            for suf in ["信", "统一", "纳税", "识别号", "代码", "下载", "次数", "方", "备"]:
                idx = seller.find(suf)
                if idx > 0:
                    seller = seller[:idx].strip()
            if seller and len(seller) > 3:
                return seller
        # 格式2：售 名称: XXX（网约车/通行费格式）
        m = re.search(r"售\s*名\s*称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["电话", "地址", "纳税人", "账号", "开户银行", "信"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        # 格式3：销 名称: XXX
        m = re.search(r"销\s*名\s*称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["电话", "地址", "纳税人", "账号", "开户银行"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        # 格式4：销售方名称/销售方
        m = re.search(r"(?:销售方名称|销售方)\s*[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["电话", "地址", "纳税人", "账号", "开户银行"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""

    def _find_seller_tax_id(self, text: str) -> str:
        import re
        m = re.search(r"销售方纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""

    def _find_buyer(self, text: str) -> str:
        """购买方名称"""
        import re
        m = re.search(r"(?:购买方名称|购买方)\s*[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["电话", "地址", "纳税人", "账号", "开户银行"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        # 回退：从"名称:买方 名称:卖方"格式取第一个作为购方
        parts = re.split(r"名称\s*[：:]\s*", text)
        if len(parts) >= 3:
            buyer_raw = parts[1].strip()
            buyer = buyer_raw.split("\n")[0].strip()
            for suf in ["信", "统一", "纳税", "识别号", "代码", "下载", "次数", "方", "备"]:
                idx = buyer.find(suf)
                if idx > 0:
                    buyer = buyer[:idx].strip()
            if buyer and len(buyer) > 2:
                return buyer
        return ""

    def _find_buyer_tax_id(self, text: str) -> str:
        import re
        m = re.search(r"购买方纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""

    def _extract_preview_text(self, file_path: Path) -> str:
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
                if len(text) > 500:
                    break
            return text[:500]
        except Exception:
            return ""


# 注册
from core.extractors.base import register_extractor
register_extractor(RideHailingExtractor())
