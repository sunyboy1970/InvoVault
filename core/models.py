"""核心数据模型：InvoiceRecord, TaxpayerType, InvoiceCategory, DeductibleStatus"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaxpayerType(Enum):
    """纳税人身份"""
    SMALL_SCALE = "small_scale"      # 小规模纳税人
    GENERAL = "general"              # 一般纳税人


class InvoiceCategory(Enum):
    """发票大类（用于抵扣判定）"""
    VAT_SPECIAL = "vat_special"              # 增值税专用发票
    VAT_NORMAL = "vat_normal"                # 增值税普通发票
    RAILWAY_ELECTRONIC = "railway_electronic"    # 铁路电子客票
    AIR_TRANSPORT = "air_transport"          # 航空运输电子客票行程单
    TOLL_ELECTRONIC = "toll_electronic"      # 通行费电子发票
    RIDE_HAILING = "ride_hailing"            # 网约车电子发票
    VEHICLE_SALES = "vehicle_sales"          # 机动车销售统一发票
    CUSTOMS_IMPORT = "customs_import"        # 海关进口增值税专用缴款书
    BRIDGE_TOLL = "bridge_toll"              # 桥闸通行费发票
    ROAD_WATER = "road_water"                # 公路/水路客票
    AGRICULTURAL = "agricultural"            # 农产品收购发票
    WITHHOLDING = "withholding"              # 代扣代缴完税凭证
    OTHER = "other"


class DeductibleStatus(Enum):
    """可抵扣状态"""
    FULL = "full"           # 全额抵扣 = 票面税额
    CALCULATED = "calculated"   # 计算抵扣 = 价税合计/(1+税率)*税率
    NONE = "none"           # 不可抵扣 = 0


@dataclass
class InvoiceRecord:
    """统一内部记录模型，导出器按模式选择字段"""
    # 通用基础字段
    invoice_type: str              # 原始识别文本：增值税专用发票/增值税普通发票/铁路电子客票...
    invoice_category: InvoiceCategory
    invoice_number: str
    invoice_date: str
    seller_name: str
    seller_tax_id: str = ""
    buyer_name: str = ""
    buyer_tax_id: str = ""
    item_name: str = ""            # *分类*项目名 格式
    tax_rate: str = ""             # 字符串 "9%" "6%" "3%" "1%"
    tax_rate_value: float = 0.0    # 数值 0.09 0.06 0.03 0.01
    amount_no_tax: float = 0.0     # 金额(不含税)
    tax_amount: float = 0.0        # 税额
    total_amount: float = 0.0      # 价税合计
    source_file: str = ""          # 源文件名

    # 计算字段（一般纳税人模式用）
    deductible_tax: float = 0.0          # 可抵扣税额
    deductible_status: DeductibleStatus = DeductibleStatus.NONE
    deductible_reason: str = ""

    # 元数据
    raw_data: dict[str, Any] = field(default_factory=dict)

    # ---- 导出行转换 ----
    def to_small_scale_row(self, seq: int) -> list:
        """小规模纳税人模式：[序号, 发票类型, 发票号码, 开票日期, 销售方名称, 项目名称, 价税合计(小写)]"""
        return [
            seq,
            self.invoice_type,
            self.invoice_number,
            self.invoice_date,
            self.seller_name,
            self.item_name,
            round(self.total_amount, 2),
        ]

    def to_general_row(self, seq: int) -> list:
        """一般纳税人模式：[序号, 发票类型, 发票号码, 开票日期, 销售方名称, 项目名称, 金额(不含税), 税率, 税额, 价税合计, 可抵扣税额, 源文件]"""
        return [
            seq,
            self.invoice_type,
            self.invoice_number,
            self.invoice_date,
            self.seller_name,
            self.item_name,
            round(self.amount_no_tax, 2),
            self.tax_rate,               # 保持 "9%" 字符串
            round(self.tax_amount, 2),
            round(self.total_amount, 2),
            round(self.deductible_tax, 2),
            self.source_file,
        ]

    def is_deductible_row(self) -> bool:
        """判断是否整行加粗"""
        return self.deductible_tax > 0.005

    def __lt__(self, other: "InvoiceRecord") -> bool:
        """主表排序：项目名称 + 销售方名称"""
        return (self.item_name, self.seller_name) < (other.item_name, other.seller_name)