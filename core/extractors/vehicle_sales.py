"""机动车销售统一发票识别器"""
from __future__ import annotations
from pathlib import Path
from core.extractors.base import BaseExtractor, InvoiceRawData
import re


class VehicleSalesExtractor(BaseExtractor):
    """机动车销售统一发票识别器（电子版）"""

    SUPPORTED_TYPES = ["机动车销售统一发票", "车辆购置"]
    PRIORITY = 50  # 高于VatNormal的100

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview(file_path)
        return "机动车销售统一发票" in text or "车辆购置税" in text

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "机动车销售统一发票"
        if "电子" in text:
            invoice_type = "机动车销售统一发票（电子）"

        # 发票号码
        invoice_number = self._find_inv_no(text)
        invoice_date = self._find_date(text)
        invoice_code = self._find_invoice_code(text)

        # 销方/购方
        seller_name = self._find_seller_vehicle(text)
        seller_tax_id = self._find_seller_tax_id(text)
        buyer_name = self._find_buyer(text)
        buyer_tax_id = self._find_buyer_tax_id(text)

        # 金额字段
        total_amount = self._find_total_amount_vehicle(text)
        amount_no_tax = self._find_amount_no_tax_vehicle(text)
        tax_amount = self._find_tax_amount_vehicle(text)
        tax_rate = self._find_tax_rate_vehicle(text)

        # 推算缺失值
        if total_amount > 0 and amount_no_tax > 0 and tax_amount == 0:
            tax_amount = round(total_amount - amount_no_tax, 2)
        elif total_amount > 0 and tax_amount > 0 and amount_no_tax == 0:
            amount_no_tax = round(total_amount - tax_amount, 2)

        # 项目名称
        item_name = "*车辆购置*车辆购置费"

        extra = {
            "vehicle_type": self._find_vehicle_type(text),
            "vehicle_brand": self._find_vehicle_brand(text),
            "vehicle_vin": self._find_vehicle_vin(text),
            "engine_no": self._find_engine_no(text),
            "certificate_no": self._find_certificate_no(text),
            "import_certificate_no": self._find_import_certificate_no(text),
            "tonnage": self._find_tonnage(text),
            "passenger_count": self._find_passenger_count(text),
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
        return ""

    def _find_invoice_code(self, text: str) -> str:
        m = re.search(r"发票代码[：:]\s*(\d{10,12})", text)
        return m.group(1) if m else ""

    def _find_inv_no(self, text: str) -> str:
        m = re.search(r"发票号码[：:]\s*(\d{20})", text)
        return m.group(1) if m else ""
        m2 = re.search(r"(\d{20})", text)
        return m2.group(1) if m2 else ""

    def _find_date(self, text: str) -> str:
        m = re.search(r"开票日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)", text)
        return m.group(1) if m else ""

    def _find_seller_vehicle(self, text: str) -> str:
        m = re.search(r"销货单位名称[：:]?\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["电话", "地址", "纳税人", "账号", "开户银行", "增值税", "主管税务"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name if name else ""
        return ""

    def _find_seller_tax_id(self, text: str) -> str:
        m = re.search(r"纳税人识别号[：:]?\s*([A-Z0-9]{15,20})", text)
        if m:
            return m.group(1)
        return ""

    def _find_buyer(self, text: str) -> str:
        # 格式：购买方名称 XXX 身份证号
        m = re.search(r"购买方名称[：:]?\s*([^\d\n]+)", text)
        if m:
            name = m.group(1).strip()
            for suf in ["身份证", "证件", "识别号"]:
                idx = name.find(suf)
                if idx > 0:
                    name = name[:idx].strip()
            return name if name else ""
        # 格式：购买方名称 XXX 372526...
        m = re.search(r"购买方名称\s+([\u4e00-\u9fff]{2,8})", text)
        if m:
            return m.group(1).strip()
        return ""

    def _find_buyer_tax_id(self, text: str) -> str:
        # 在"购买方名称"后面找身份证号
        m = re.search(r"购买方名称[^0-9]*(\d{15,20})", text)
        if m:
            return m.group(1)
        m = re.search(r"(?:身份证号码|身份证号)[：:]?\s*(\d{15,20})", text)
        if m:
            return m.group(1)
        return ""

    def _find_total_amount_vehicle(self, text: str) -> float:
        # 格式：小写 96500.00
        m = re.search(r"小\s*写\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                val = float(num_str)
                if val > 100:  # 合理的总价
                    return val
            except ValueError:
                pass
        # 格式：价税合计
        m = re.search(r"价\s*税\s*合\s*计\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0

    def _find_tax_amount_vehicle(self, text: str) -> float:
        # 格式：13% 11101.77
        m = re.search(r"\d+%\s*([\d,]+\.\d{2})", text)
        if m:
            val = float(m.group(1).replace(",", ""))
            if val < 100000:  # 税额不会大于总价
                return val
        m = re.search(r"税\s*额[：:]?\s*[¥￥]?\s*([\d,]+\.\d{2})", text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0

    def _find_amount_no_tax_vehicle(self, text: str) -> float:
        # 格式：不含税价 小写 85398.23
        m = re.search(r"不含税价[^0-9]*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        return 0.0

    def _find_tax_rate_vehicle(self, text: str) -> str:
        # 格式：增值税税率 13%
        m = re.search(r"增值税税率[^0-9]*(\d+)%", text)
        if m:
            return m.group(1) + "%"
        m = re.search(r"(\d+)%", text)
        if m:
            return m.group(1) + "%"
        return ""

    def _find_vehicle_type(self, text: str) -> str:
        m = re.search(r"车辆类型[：:]?\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""

    def _find_vehicle_brand(self, text: str) -> str:
        m = re.search(r"厂牌型号[：:]?\s*([^\n]+)", text)
        return m.group(1).strip() if m else ""

    def _find_vehicle_vin(self, text: str) -> str:
        m = re.search(r"(?:车辆识别代号|车架号码)[：:]?\s*([A-Z0-9]{10,})", text)
        return m.group(1) if m else ""

    def _find_engine_no(self, text: str) -> str:
        m = re.search(r"发动机号码[：:]?\s*([A-Z0-9]+)", text)
        return m.group(1) if m else ""

    def _find_certificate_no(self, text: str) -> str:
        m = re.search(r"合格证号[：:]?\s*(\w+)", text)
        return m.group(1) if m else ""

    def _find_import_certificate_no(self, text: str) -> str:
        m = re.search(r"进口证明书号[：:]?\s*(\w+)", text)
        return m.group(1) if m else ""

    def _find_tonnage(self, text: str) -> str:
        m = re.search(r"吨位[：:]?\s*([\d.]+)", text)
        return m.group(1) if m else ""

    def _find_passenger_count(self, text: str) -> str:
        m = re.search(r"(?:限乘人数|乘坐人数)[：:]?\s*(\d+)", text)
        return m.group(1) if m else ""


# 注册
from core.extractors.base import register_extractor
register_extractor(VehicleSalesExtractor())