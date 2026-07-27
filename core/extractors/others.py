"""其他发票识别器：农产品收购/代扣代缴/桥闸费/公路水路客票"""
from __future__ import annotations
import re
from pathlib import Path
from core.extractors.base import BaseExtractor, InvoiceRawData


class AgriculturalProductExtractor(BaseExtractor):
    """农产品收购发票识别器
    
    特点：
    - 扣除率：9% 或 10%
    - 字段：收购单位名称、收购单位纳税人识别号、销售单位名称、销售单位身份证号
    - 收购金额、扣除率、扣除税额
    - 项目名称格式：*农产品*农产品名称
    """
    
    SUPPORTED_TYPES = ["农产品收购发票", "农产品收购"]
    PRIORITY = 5  # 更高优先级，优于专票
    
    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview(file_path)
        return "农产品收购" in text
    
    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "农产品收购发票"
        if "电子" in text:
            invoice_type = "农产品收购发票（电子）"
        
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)
        invoice_code = self._find_invoice_code(text)
        
        # 收购单位（销方）
        seller_name = self._find_buyer_unit(text)
        seller_tax_id = self._find_buyer_tax_id(text)
        
        # 销售方（购方）
        buyer_name = self._find_seller_unit(text)
        buyer_tax_id = self._find_seller_tax_id(text)
        
        # 收购金额（不含税金额）
        amount_no_tax = self._find_purchase_amount(text)
        
        # 扣除率 9% 或 10%
        deduction_rate = self._find_deduction_rate(text)
        tax_rate = f"{deduction_rate}%" if deduction_rate else "9%"
        
        # 扣除税额 = 收购金额 * 扣除率
        tax_amount = self._find_deduction_tax(text)
        if tax_amount == 0.0 and amount_no_tax > 0 and deduction_rate:
            tax_amount = round(amount_no_tax * deduction_rate / 100, 2)
        
        # 价税合计 = 收购金额 + 扣除税额
        total_amount = amount_no_tax + tax_amount
        
        # 项目名称：*农产品*农产品名称
        item_name = self._find_item_name(text)
        if item_name and not item_name.startswith("*"):
            item_name = f"*农产品*{item_name}"
        
        extra = {
            "deduction_rate": deduction_rate,
            "purchase_amount": amount_no_tax,
            "seller_unit": seller_name,
            "seller_tax_id": seller_tax_id,
            "buyer_unit": buyer_name,
            "buyer_tax_id": buyer_tax_id,
            "raw_text": text[:3000],
        }
        
        return InvoiceRawData(
            invoice_type=invoice_type,
            invoice_code=invoice_code,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax_id,
            items=[{
                "name": item_name or "*农产品*农产品",
                "amount_no_tax": amount_no_tax,
                "tax_amount": tax_amount,
                "tax_rate": tax_rate,
                "total_amount": total_amount,
            }],
            total_amount=total_amount,
            total_tax=tax_amount,
            tax_rate=tax_rate,
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
    
    def _find_invoice_code(self, text: str) -> str:
        m = re.search(r"发票代码[：:]\s*([\d]{10,12})", text)
        return m.group(1) if m else ""
    
    def _find_buyer_unit(self, text: str) -> str:
        """收购单位名称（销方）"""
        m = re.search(r"收购单位名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["纳税人识别号", "地址", "电话", "开户银行", "账号"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""
    
    def _find_buyer_tax_id(self, text: str) -> str:
        """收购单位纳税人识别号"""
        m = re.search(r"收购单位纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""
    
    def _find_seller_unit(self, text: str) -> str:
        """销售单位名称（购方）"""
        m = re.search(r"销售单位名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["身份证号", "证件号码", "地址", "电话"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""
    
    def _find_seller_tax_id(self, text: str) -> str:
        """销售单位身份证号/纳税人识别号"""
        m = re.search(r"销售单位身份证号码[：:]\s*([A-Z0-9]{15,20})", text)
        if not m:
            m = re.search(r"销售单位纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""
    
    def _find_purchase_amount(self, text: str) -> float:
        """收购金额（不含税金额）"""
        m = re.search(r"收购金额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"金额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0
    
    def _find_deduction_rate(self, text: str) -> int | None:
        """扣除率：9% 或 10%"""
        m = re.search(r"扣除率[：:]\s*(\d+)%", text)
        if m:
            return int(m.group(1))
        m = re.search(r"扣除率[：:]\s*(\d+)", text)
        if m:
            rate = int(m.group(1))
            return rate if rate in (9, 10) else None
        # 备选：税率字段
        m = re.search(r"税率[：:]\s*(\d+)%", text)
        if m:
            rate = int(m.group(1))
            return rate if rate in (9, 10) else None
        return None
    
    def _find_deduction_tax(self, text: str) -> float:
        """扣除税额"""
        m = re.search(r"扣除税额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"税额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0
    
    def _find_item_name(self, text: str) -> str:
        """农产品名称"""
        m = re.search(r"农产品名称[：:]\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        m = re.search(r"货物名称[：:]\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        return ""


class WithholdingTaxExtractor(BaseExtractor):
    """代扣代缴税款专用发票识别器
    
    特点：
    - 全额抵扣
    - 字段：扣缴义务人名称、扣缴义务人纳税人识别号、纳税人名称、纳税人识别号
    - 税款种类、税款所属期、扣缴税款金额
    - 项目名称格式：*代扣代缴*税款种类
    """
    
    SUPPORTED_TYPES = ["代扣代缴税款专用发票", "代扣代缴"]
    PRIORITY = 5  # 更高优先级，优于专票
    
    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview(file_path)
        # 必须包含"代扣代缴"且包含"税款专用发票"或"扣缴义务人"
        return "代扣代缴" in text and ("税款专用发票" in text or "扣缴义务人" in text)
    
    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "代扣代缴税款专用发票"
        if "电子" in text:
            invoice_type = "代扣代缴税款专用发票（电子）"
        
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)
        invoice_code = self._find_invoice_code(text)
        
        # 扣缴义务人（销方）
        seller_name = self._find_withholder_name(text)
        seller_tax_id = self._find_withholder_tax_id(text)
        
        # 纳税人（购方）
        buyer_name = self._find_taxpayer_name(text)
        buyer_tax_id = self._find_taxpayer_tax_id(text)
        
        # 扣缴税款金额（税额 = 全额抵扣）
        tax_amount = self._find_withheld_tax(text)
        total_amount = tax_amount  # 全额抵扣，不含税金额=0，税额=价税合计
        amount_no_tax = 0.0
        tax_rate = "全额抵扣"
        
        # 税款种类
        tax_category = self._find_tax_category(text)
        
        # 项目名称：*代扣代缴*税款种类
        item_name = f"*代扣代缴*{tax_category}" if tax_category else "*代扣代缴*税款"
        
        extra = {
            "tax_category": tax_category,
            "tax_period": self._find_tax_period(text),
            "withholder_name": seller_name,
            "withholder_tax_id": seller_tax_id,
            "taxpayer_name": buyer_name,
            "taxpayer_tax_id": buyer_tax_id,
            "raw_text": text[:3000],
        }
        
        return InvoiceRawData(
            invoice_type=invoice_type,
            invoice_code=invoice_code,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax_id,
            items=[{
                "name": item_name,
                "amount_no_tax": amount_no_tax,
                "tax_amount": tax_amount,
                "tax_rate": tax_rate,
                "total_amount": total_amount,
            }],
            total_amount=total_amount,
            total_tax=tax_amount,
            tax_rate=tax_rate,
            item_name=item_name,
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
    
    def _find_invoice_code(self, text: str) -> str:
        m = re.search(r"发票代码[：:]\s*([\d]{10,12})", text)
        return m.group(1) if m else ""
    
    def _find_withholder_name(self, text: str) -> str:
        """扣缴义务人名称"""
        m = re.search(r"扣缴义务人名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["纳税人识别号", "地址", "电话", "开户银行", "账号"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""
    
    def _find_withholder_tax_id(self, text: str) -> str:
        """扣缴义务人纳税人识别号"""
        m = re.search(r"扣缴义务人纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""
    
    def _find_taxpayer_name(self, text: str) -> str:
        """纳税人名称"""
        m = re.search(r"纳税人名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["纳税人识别号", "身份证号", "地址", "电话"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""
    
    def _find_taxpayer_tax_id(self, text: str) -> str:
        """纳税人识别号"""
        m = re.search(r"纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        if not m:
            m = re.search(r"身份证号码[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""
    
    def _find_withheld_tax(self, text: str) -> float:
        """扣缴税款金额"""
        m = re.search(r"扣缴税款金额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"税款金额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0
    
    def _find_tax_category(self, text: str) -> str:
        """税款种类"""
        m = re.search(r"税款种类[：:]\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        m = re.search(r"税种[：:]\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        return ""
    
    def _find_tax_period(self, text: str) -> str:
        """税款所属期"""
        m = re.search(r"税款所属期[：:]\s*(\d{4}[-年]\d{1,2}[-月]?)", text)
        return m.group(1) if m else ""


class TollBridgeWaterwayExtractor(BaseExtractor):
    """桥闸费/公路水路客票发票识别器
    
    特点：
    - 桥闸费、公路客票、水路客票：不可抵扣 / 计算抵扣
    - 字段：收费单位、收费项目、车牌号/船名、通行日期/旅客姓名
    - 项目名称格式：*桥闸费*收费项目、*公路客票*票种、*水路客票*票种
    - 税率：免税/不征税/不可抵扣
    """
    
    SUPPORTED_TYPES = ["过路费通行费发票", "桥闸费发票", "公路客票", "水路客票", "过桥费", "过路费"]
    PRIORITY = 20  # 优于通行费电子发票
    
    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview(file_path)
        keywords = ["桥闸费", "桥闸通行费", "过桥费", "公路客票", "水路客票", "船票", "客票"]
        # 专门匹配这些特定票种，避免与通用通行费发票冲突
        return any(kw in text for kw in keywords)
    
    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        # 识别具体票种
        if "公路客票" in text or "汽车客票" in text:
            invoice_type = "公路客票"
            tax_type = "不可抵扣"
        elif "水路客票" in text or "船票" in text or "客轮" in text:
            invoice_type = "水路客票"
            tax_type = "不可抵扣"
        elif "桥闸费" in text or "过桥费" in text:
            invoice_type = "桥闸费发票"
            tax_type = "不可抵扣"
        else:
            invoice_type = "通行费发票"
            tax_type = "不可抵扣"
        
        if "电子" in text:
            invoice_type += "（电子）"
        
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)
        invoice_code = self._find_invoice_code(text)
        
        # 收费单位/销售方
        seller_name = self._find_charge_unit(text)
        seller_tax_id = self._find_charge_unit_tax_id(text)
        
        # 购买方/旅客
        buyer_name = self._find_purchaser(text)
        buyer_tax_id = self._find_purchaser_id(text)
        
        # 金额
        total_amount = self._find_total_amount(text)
        tax_amount = 0.0  # 不可抵扣/免税
        amount_no_tax = total_amount
        tax_rate = "免税" if "免税" in text else "不征税" if "不征税" in text else "不可抵扣"
        
        # 项目名称
        item_name = self._find_item_name(text, invoice_type)
        
        extra = {
            "charge_unit": seller_name,
            "charge_item": self._find_charge_item(text),
            "vehicle_plate": self._find_vehicle_plate(text),
            "vessel_name": self._find_vessel_name(text),
            "pass_date": self._find_pass_date(text),
            "passenger_name": self._find_passenger_name(text),
            "ticket_type": self._find_ticket_type(text),
            "tax_type": tax_type,
            "raw_text": text[:3000],
        }
        
        return InvoiceRawData(
            invoice_type=invoice_type,
            invoice_code=invoice_code,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax_id,
            items=[{
                "name": item_name,
                "amount_no_tax": amount_no_tax,
                "tax_amount": tax_amount,
                "tax_rate": tax_rate,
                "total_amount": total_amount,
            }],
            total_amount=total_amount,
            total_tax=tax_amount,
            tax_rate=tax_rate,
            item_name=item_name,
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
    
    def _find_invoice_code(self, text: str) -> str:
        m = re.search(r"发票代码[：:]\s*([\d]{10,12})", text)
        return m.group(1) if m else ""
    
    def _find_charge_unit(self, text: str) -> str:
        """收费单位/销售方名称"""
        m = re.search(r"收费单位[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"销售方名称[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"销货单位名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["纳税人识别号", "地址", "电话", "开户银行", "账号"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""
    
    def _find_charge_unit_tax_id(self, text: str) -> str:
        """收费单位纳税人识别号"""
        m = re.search(r"收费单位纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        if not m:
            m = re.search(r"销售方纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""
    
    def _find_purchaser(self, text: str) -> str:
        """购买方/旅客名称"""
        m = re.search(r"购买方名称[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"旅客姓名[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"购票人[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["身份证", "证件", "电话", "手机"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""
    
    def _find_purchaser_id(self, text: str) -> str:
        """购买方身份证号"""
        m = re.search(r"购买方身份证号码[：:]\s*([A-Z0-9]{15,20})", text)
        if not m:
            m = re.search(r"旅客身份证号[：:]\s*([A-Z0-9]{15,20})", text)
        return m.group(1) if m else ""
    
    def _find_total_amount(self, text: str) -> float:
        """金额"""
        m = re.search(r"[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"金额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"价税合计\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0
    
    def _find_item_name(self, text: str, invoice_type: str) -> str:
        """项目名称：*分类*项目"""
        # 尝试从收费项目/票种提取
        charge_item = self._find_charge_item(text)
        ticket_type = self._find_ticket_type(text)
        
        if "公路客票" in invoice_type:
            return f"*公路客票*{ticket_type or '客票'}"
        elif "水路客票" in invoice_type:
            return f"*水路客票*{ticket_type or '客票'}"
        elif "桥闸费" in invoice_type or "过桥费" in invoice_type:
            return f"*桥闸费*{charge_item or '过桥费'}"
        else:
            return f"*通行费*{charge_item or '通行费'}"
    
    def _find_charge_item(self, text: str) -> str:
        """收费项目"""
        m = re.search(r"收费项目[：:]\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        m = re.search(r"项目名称[：:]\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        return ""
    
    def _find_vehicle_plate(self, text: str) -> str:
        """车牌号"""
        m = re.search(r"车牌号[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"号牌号码[：:]\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""
    
    def _find_vessel_name(self, text: str) -> str:
        """船名"""
        m = re.search(r"船名[：:]\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""
    
    def _find_pass_date(self, text: str) -> str:
        """通行日期/旅行日期"""
        m = re.search(r"通行日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        if not m:
            m = re.search(r"旅行日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        if not m:
            m = re.search(r"乘车日期[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)", text)
        return m.group(1) if m else ""
    
    def _find_passenger_name(self, text: str) -> str:
        """旅客姓名"""
        m = re.search(r"旅客姓名[：:]\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""
    
    def _find_ticket_type(self, text: str) -> str:
        """票种"""
        m = re.search(r"票种[：:]\s*([^\n]+)", text)
        if not m:
            m = re.search(r"客票种类[：:]\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""


# ===== 注册识别器 =====
from core.extractors.base import register_extractor

register_extractor(AgriculturalProductExtractor())
register_extractor(WithholdingTaxExtractor())
register_extractor(TollBridgeWaterwayExtractor())
