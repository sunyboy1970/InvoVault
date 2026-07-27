"""海关进口增值税专用缴款书识别器"""
from __future__ import annotations
import re
from pathlib import Path
from core.extractors.base import BaseExtractor, InvoiceRawData


class CustomsImportExtractor(BaseExtractor):
    """海关进口增值税专用缴款书识别器"""

    SUPPORTED_TYPES = ["海关进口增值税专用缴款书", "海关缴款书"]

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview(file_path)
        return "海关" in text and "缴款书" in text and "进口" in text

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "海关进口增值税专用缴款书"
        
        # 缴款书号码 - 22位数字
        invoice_number = self._find_payment_no(text)
        
        # 填发日期
        invoice_date = self._find_issue_date(text)
        
        # 进口口岸
        import_port = self._find_import_port(text)
        
        # 完税价格
        taxable_price = self._find_taxable_price(text)
        
        # 关税
        customs_duty = self._find_customs_duty(text)
        
        # 增值税税额
        vat_amount = self._find_vat_amount(text)
        
        # 完税价格 + 关税 = 价税合计基数
        # 价税合计 = 完税价格 + 关税 + 增值税
        total_amount = taxable_price + customs_duty + vat_amount
        
        # 税率 - 通常为征收率或税率
        tax_rate = self._find_tax_rate(text)
        
        # 进口货物名称/项目名称
        item_name = self._find_item_name(text)
        
        # 纳税人名称
        seller_name = self._find_taxpayer_name(text)
        
        # 纳税人识别号
        seller_tax_id = self._find_taxpayer_tax_id(text)
        
        # 海关代码
        customs_code = self._find_customs_code(text)
        
        # 报关单号
        declaration_no = self._find_declaration_no(text)
        
        # 税款所属期
        tax_period = self._find_tax_period(text)
        
        # 汇总缴款书号
        summary_payment_no = self._find_summary_payment_no(text)
        
        # 进口日期
        import_date = self._find_import_date(text)
        
        # 货币代码
        currency = self._find_currency(text)
        
        extra = {
            "import_port": import_port,
            "taxable_price": taxable_price,
            "customs_duty": customs_duty,
            "vat_amount": vat_amount,
            "customs_code": customs_code,
            "declaration_no": declaration_no,
            "tax_period": tax_period,
            "summary_payment_no": summary_payment_no,
            "import_date": import_date,
            "currency": currency,
            "raw_text": text[:3000],
        }

        # 项目名称格式：*进口货物*货物名称
        if item_name and not item_name.startswith("*"):
            item_name = f"*进口货物*{item_name}"

        return InvoiceRawData(
            invoice_type=invoice_type,
            invoice_code="",  # 缴款书无发票代码
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            buyer_name="",  # 海关缴款书无购买方
            buyer_tax_id="",
            items=[{
                "name": item_name or "*进口货物*进口货物",
                "tax_rate": tax_rate or "13%",
                "amount_no_tax": taxable_price,
                "tax_amount": vat_amount,
                "total_amount": total_amount,
            }],
            total_amount=total_amount,
            total_tax=vat_amount + customs_duty,  # 总税额 = 关税 + 增值税
            tax_rate=tax_rate or "13%",
            item_name=item_name or "*进口货物*进口货物",
            extra=extra,
            raw_text=text[:3000],
        )

    def _extract_preview(self, file_path: Path) -> str:
        if file_path.suffix.lower() == ".pdf":
            try:
                import fitz
                doc = fitz.open(file_path)
                text = doc[0].get_text("text", sort=True)
                doc.close()
                return text
            except Exception:
                return ""
        return ""

    def _find_payment_no(self, text: str) -> str:
        """缴款书号码 - 22位数字"""
        # 海关缴款书号码通常为22位数字
        m = re.search(r"缴款书号码[：:]\s*(\d{22})", text)
        if not m:
            m = re.search(r"缴款书\s*号[：:]\s*(\d{22})", text)
        if not m:
            # 备选：查找22位连续数字
            m = re.search(r"\b(\d{22})\b", text)
        return m.group(1) if m else ""

    def _find_issue_date(self, text: str) -> str:
        """填发日期"""
        # 格式：2024年01月15日 或 2024-01-15
        m = re.search(r"填发日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        if not m:
            m = re.search(r"开票日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        if not m:
            m = re.search(r"日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        return m.group(1) if m else ""

    def _find_import_port(self, text: str) -> str:
        """进口口岸"""
        m = re.search(r"进口口岸[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"口岸[：:]\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""

    def _find_taxable_price(self, text: str) -> float:
        """完税价格"""
        # 完税价格 / 完税价格合计
        m = re.search(r"完税价格\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if not m:
            m = re.search(r"完税价格合计\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if not m:
            m = re.search(r"价格\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        return float(m.group(1).replace(",", "")) if m else 0.0

    def _find_customs_duty(self, text: str) -> float:
        """关税"""
        m = re.search(r"关\s*税\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if not m:
            m = re.search(r"关税\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        return float(m.group(1).replace(",", "")) if m else 0.0

    def _find_vat_amount(self, text: str) -> float:
        """增值税税额"""
        m = re.search(r"增值税\s*税额\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if not m:
            m = re.search(r"增值税\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if not m:
            m = re.search(r"进口增值税\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        return float(m.group(1).replace(",", "")) if m else 0.0

    def _find_tax_rate(self, text: str) -> str:
        """税率/征收率"""
        m = re.search(r"税率[：:]\s*(\d+%?)", text)
        if m:
            rate = m.group(1)
            return rate if rate.endswith("%") else rate + "%"
        m = re.search(r"征收率[：:]\s*(\d+%?)", text)
        if m:
            rate = m.group(1)
            return rate if rate.endswith("%") else rate + "%"
        return ""

    def _find_item_name(self, text: str) -> str:
        """进口货物名称/项目名称"""
        m = re.search(r"货物名称[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"商品名称[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"项目名称[：:]\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""

    def _find_taxpayer_name(self, text: str) -> str:
        """纳税人名称"""
        m = re.search(r"纳税人名称[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"单位名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            # 清理后缀
            for suf in ["纳税人识别号", "地址", "电话", "开户银行", "账号"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""

    def _find_taxpayer_tax_id(self, text: str) -> str:
        """纳税人识别号"""
        m = re.search(r"纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        if not m:
            m = re.search(r"统一社会信用代码[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""

    def _find_customs_code(self, text: str) -> str:
        """海关代码"""
        m = re.search(r"海关代码[：:]\s*(\d{4,})", text)
        return m.group(1) if m else ""

    def _find_declaration_no(self, text: str) -> str:
        """报关单号"""
        m = re.search(r"报关单号[：:]\s*([A-Z0-9]{18,})", text)
        return m.group(1) if m else ""

    def _find_tax_period(self, text: str) -> str:
        """税款所属期"""
        m = re.search(r"税款所属期[：:]\s*(\d{4}[-年]\d{1,2}[-月]?)", text)
        return m.group(1) if m else ""

    def _find_summary_payment_no(self, text: str) -> str:
        """汇总缴款书号"""
        m = re.search(r"汇总缴款书号[：:]\s*(\d{22})", text)
        return m.group(1) if m else ""

    def _find_import_date(self, text: str) -> str:
        """进口日期"""
        m = re.search(r"进口日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        return m.group(1) if m else ""

    def _find_currency(self, text: str) -> str:
        """币制"""
        m = re.search(r"币制[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"货币[：:]\s*([^\n]+)", text)
        return m.group(1).strip() if m else "人民币"


from core.extractors.base import register_extractor
register_extractor(CustomsImportExtractor())
