"""通行费电子发票识别器"""
from __future__ import annotations
from pathlib import Path
import re
from core.extractors.base import BaseExtractor, InvoiceRawData


class TollExtractor(BaseExtractor):
    """通行费电子发票识别器

    规则：
    - 通行费普票（不征税/免税/3%/9%）
    - 项目名：*经营租赁*通行费
    - 可抵扣税额 = 票面税额（仅征税发票可抵扣）
    """

    SUPPORTED_TYPES = ["toll_electronic", "通行费电子发票", "通行费电子普通发票"]
    PRIORITY = 25

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview_text(file_path)
        has_toll = "通行费" in text
        return has_toll

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "通行费电子普通发票"

        # 金额提取
        total_amount = self._find_total_amount(text)
        total_tax = self._find_total_tax(text)
        is_non_taxable = "不征税" in text

        # 税率
        tax_rate_str = self._find_tax_rate(text)

        # 不含税金额
        if is_non_taxable:
            # 不征税：全额就是不含税金额，税额为0
            amount_no_tax = total_amount
            total_tax = 0.0
        elif total_amount > 0 and total_tax > 0:
            amount_no_tax = round(total_amount - total_tax, 2)
        elif total_amount > 0:
            try:
                tr = float(tax_rate_str.replace("%", "")) / 100
                amount_no_tax = round(total_amount / (1 + tr), 2)
            except (ValueError, ZeroDivisionError):
                amount_no_tax = 0.0
        else:
            amount_no_tax = 0.0

        # 项目名从明细行提取
        item_name = self._find_item_name(text)
        if not item_name:
            item_name = "*经营租赁*通行费"

        # 销售方、购买方
        seller_name = self._find_seller(text)
        buyer_name = self._find_buyer(text)

        # 发票号码、日期
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)
        invoice_code = self._find_inv_code(text)

        # 可抵扣税额（仅征税发票可抵扣）
        if is_non_taxable:
            deductible_tax = 0.0
        else:
            deductible_tax = total_tax

        return InvoiceRawData(
            invoice_type=invoice_type,
            invoice_code=invoice_code,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            seller_name=seller_name,
            seller_tax_id=self._find_seller_tax_id(text),
            buyer_name=buyer_name,
            buyer_tax_id=self._find_buyer_tax_id(text),
            items=[{
                "name": item_name,
                "unit": "项",
                "quantity": 1,
                "unit_price": amount_no_tax,
                "amount_no_tax": amount_no_tax,
                "tax_rate": tax_rate_str or "不征税",
                "tax_amount": total_tax,
                "total_amount": total_amount,
            }],
            total_amount=total_amount,
            total_tax=total_tax,
            tax_rate=tax_rate_str or "不征税",
            item_name=item_name,
            deductible_tax=deductible_tax,
            raw_text=text[:2000],
        )

    def _find_inv_code(self, text: str) -> str:
        m = re.search(r"发票代码[：:]*\s*(\d{10,12})", text)
        return m.group(1) if m else ""

    def _find_inv_no(self, text: str) -> str:
        m = re.search(r"发票号码[：:]*\s*(\d{20})", text)
        if m:
            return m.group(1)
        m = re.search(r"发票号码[：:]*\s*(\d{8,12})", text)
        return m.group(1) if m else ""

    def _find_date(self, text: str) -> str:
        m = re.search(r"开票日期[：:]*\s*(\d{4}年\d{1,2}月\d{1,2}日)", text)
        return m.group(1) if m else ""

    def _find_total_amount(self, text: str) -> float:
        """提取价税合计"""
        m = re.search(r"[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        m = re.search(r"价\s*税\s*合\s*计[（(]\s*大\s*写\s*[）)].+[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        # 从"合 计"行提取总金额（有空格版本）
        m = re.search(r"合\s*计\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        return 0.0

    def _find_total_tax(self, text: str) -> float:
        """提取税额（通行费发票有：税额字段，不征税发票税额为0）"""
        # 检查是否不征税
        if "不征税" in text:
            return 0.0
        # 检查是否有 "＊" 占位符（表示无明细税额）
        if "＊＊＊" in text or "***" in text:
            return 0.0
        # 正常提取税额：匹配 "税额" 后的数字
        m = re.search(
            r'税\s*额[\s：:]*[¥￥]?\s*([\d,]+\.[\d]{2})',
            text
        )
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
        # 备选：从价税合计和税率反推
        total = self._find_total_amount(text)
        tax_rate = self._find_tax_rate(text)
        if total > 0 and tax_rate and tax_rate not in ("不征税", "免税", "0%"):
            try:
                tr = float(tax_rate.replace("%", "")) / 100
                return round(total - total / (1 + tr), 2)
            except (ValueError, ZeroDivisionError):
                pass
        return 0.0

    def _find_seller(self, text: str) -> str:
        """提取销售方名称"""
        # 方法1：处理"售 名称: YY公司"（同行格式）
        m = re.search(r"售\s*名\s*称[：:]\s*([^\n]+)", text)
        if m:
            seller = m.group(1).strip()
            for suf in ["信", "统一", "纳税人", "识别号", "代码", "下载", "次数", "方", "备", "汇", "地", "电", "开", "收"]:
                idx = seller.find(suf)
                if idx > 0:
                    seller = seller[:idx].strip()
            if seller:
                return seller

        # 方法2：从"名 称:"行提取第二个匹配项（第一个是购方，第二个是销方）
        name_lines = re.findall(r"名\s*称[：:]\s*([^\n]+)", text)
        if len(name_lines) >= 2:
            seller = name_lines[1].strip()
            # 清理后缀
            for suf in ["汇", "销", "备", "售", "地", "电", "开", "收", "信"]:
                idx = seller.find(suf)
                if idx > 0:
                    seller = seller[:idx].strip()
            if seller:
                return seller

        # 方法3：从"销方"区域提取
        m = re.search(r"名\s*称[：:]\s*([^\n]+)\n*销\s*备", text)
        if m:
            seller = m.group(1).strip()
            if seller:
                return seller

        return ""

    def _find_buyer(self, text: str) -> str:
        """提取购买方名称"""
        name_lines = re.findall(r"名\s*称[：:]\s*([^\n]+)", text)
        if name_lines:
            buyer = name_lines[0].strip()
            # 清理后缀（购方名称后跟着加密代码）
            for suf in ["购", "密", "信", "纳税人", "识别号"]:
                idx = buyer.find(suf)
                if idx > 0:
                    buyer = buyer[:idx].strip()
            return buyer
        return ""

    def _find_seller_tax_id(self, text: str) -> str:
        """提取销售方纳税人识别号"""
        ids = re.findall(r"纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        if len(ids) >= 2:
            return ids[1]
        if len(ids) == 1:
            return ids[0]
        return ""

    def _find_buyer_tax_id(self, text: str) -> str:
        ids = re.findall(r"纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return ids[0] if ids else ""

    def _find_tax_rate(self, text: str) -> str:
        for rate_marker in ["不征税", "免税", "0%", "3%", "6%", "9%", "13%"]:
            if rate_marker in text:
                return rate_marker
        return "不征税"

    def _find_item_name(self, text: str) -> str:
        """从明细行提取项目名称"""
        # 跳过加密区：只在"货物或应税劳务"表头之后查找
        header_idx = text.find("货物或应税劳务")
        if header_idx < 0:
            header_idx = text.find("合 计")

        search_text = text[header_idx:] if header_idx >= 0 else text

        # 模式：*分类*名称
        m = re.search(r"\*([^*]+?)\*([^\s]+)", search_text)
        if m:
            return f"*{m.group(1)}*{m.group(2)}"

        # 从表头下一行提取
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
                # 压缩连续空白，减少padding占用
                raw = re.sub(r"[ \t]{3,}", " ", raw)
                text += raw
                if len(text) > 500:
                    break
            # 再次压缩空白确保不会因padding截断
            return re.sub(r"[ \t]{2,}", " ", text[:800])
        except Exception:
            return ""


# 注册
from core.extractors.base import register_extractor
register_extractor(TollExtractor())