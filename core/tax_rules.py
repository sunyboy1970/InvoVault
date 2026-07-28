"""2026年增值税新规抵扣判定引擎
依据：财政部 税务总局公告2026年第13号、财税〔2016〕36号、财税〔2017〕37号、财税〔2019〕39号等
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from core.models import InvoiceCategory, DeductibleStatus


@dataclass(frozen=True)
class DeductionRule:
    category: InvoiceCategory
    status: DeductibleStatus
    calc_rate: Optional[float] = None      # 计算抵扣时的税率
    condition: str = ""                    # 判定依据说明


# 2026新规抵扣规则表
DEDUCTION_RULES: dict[InvoiceCategory, DeductionRule] = {
    # ===== 全额抵扣 = 票面税额 =====
    InvoiceCategory.VAT_SPECIAL: DeductionRule(
        InvoiceCategory.VAT_SPECIAL, DeductibleStatus.FULL,
        condition="增值税专用发票，按票面税额全额抵扣"
    ),
    InvoiceCategory.VEHICLE_SALES: DeductionRule(
        InvoiceCategory.VEHICLE_SALES, DeductibleStatus.FULL,
        condition="机动车销售统一发票，注明购买方纳税人识别号"
    ),
    InvoiceCategory.CUSTOMS_IMPORT: DeductionRule(
        InvoiceCategory.CUSTOMS_IMPORT, DeductibleStatus.FULL,
        condition="海关进口增值税专用缴款书，按税额抵扣"
    ),
    InvoiceCategory.TOLL_ELECTRONIC: DeductionRule(
        InvoiceCategory.TOLL_ELECTRONIC, DeductibleStatus.FULL,
        condition="通行费电子普通发票，按票面税额抵扣"
    ),
    InvoiceCategory.WITHHOLDING: DeductionRule(
        InvoiceCategory.WITHHOLDING, DeductibleStatus.FULL,
        condition="代扣代缴完税凭证，按税额抵扣"
    ),
    InvoiceCategory.AGRICULTURAL: DeductionRule(
        InvoiceCategory.AGRICULTURAL, DeductibleStatus.FULL,
        condition="农产品收购发票，按买价×扣除率(9%/10%)"
    ),

    # ===== 计算抵扣 = 价税合计/(1+税率)×税率 =====
    InvoiceCategory.RAILWAY_ELECTRONIC: DeductionRule(
        InvoiceCategory.RAILWAY_ELECTRONIC, DeductibleStatus.CALCULATED, 0.09,
        condition="铁路电子客票，含旅客身份信息，票价÷1.09×9%"
    ),
    InvoiceCategory.AIR_TRANSPORT: DeductionRule(
        InvoiceCategory.AIR_TRANSPORT, DeductibleStatus.CALCULATED, 0.09,
        condition="航空运输电子客票行程单，(票价+燃油附加费)÷1.09×9%"
    ),
    InvoiceCategory.ROAD_WATER: DeductionRule(
        InvoiceCategory.ROAD_WATER, DeductibleStatus.CALCULATED, 0.03,
        condition="公路/水路客票，含旅客身份信息，票面÷1.03×3%"
    ),

    # ===== 明确不可抵扣（2026新规）=====
    InvoiceCategory.RIDE_HAILING: DeductionRule(
        InvoiceCategory.RIDE_HAILING, DeductibleStatus.NONE,
        condition="网约车电子普通发票，2026新规不可抵扣"
    ),
    InvoiceCategory.BRIDGE_TOLL: DeductionRule(
        InvoiceCategory.BRIDGE_TOLL, DeductibleStatus.NONE,
        condition="桥闸通行费纸质发票，2026新规不再允许抵扣"
    ),
}


def classify_invoice(invoice_type: str, item_name: str, tax_rate: str) -> InvoiceCategory:
    """根据发票类型文本、项目名称、税率判定大类"""
    it = (invoice_type or "").strip()
    iname = (item_name or "").strip()
    tr = (tax_rate or "").strip().replace("%", "").replace("％", "")

    if "专用发票" in it:
        return InvoiceCategory.VAT_SPECIAL

    if "普通发票" in it or "电子发票" in it:
        # 普通发票细分
        if "通行费" in iname or "高速" in iname or "收费" in iname:
            return InvoiceCategory.TOLL_ELECTRONIC
        if "网约车" in it or "滴滴" in iname or "曹操" in iname or "高德" in iname:
            return InvoiceCategory.RIDE_HAILING
        return InvoiceCategory.VAT_NORMAL

    if "铁路" in it and "客票" in it:
        return InvoiceCategory.RAILWAY_ELECTRONIC

    if "航空" in it and "行程单" in it:
        return InvoiceCategory.AIR_TRANSPORT

    if "机动车销售" in it:
        return InvoiceCategory.VEHICLE_SALES

    if "海关" in it and "缴款书" in it:
        return InvoiceCategory.CUSTOMS_IMPORT

    if "桥" in it or "闸" in it:
        return InvoiceCategory.BRIDGE_TOLL

    if "公路" in it or "水路" in it:
        return InvoiceCategory.ROAD_WATER

    if "农产品" in it:
        return InvoiceCategory.AGRICULTURAL

    if "代扣代缴" in it or "完税凭证" in it:
        return InvoiceCategory.WITHHOLDING

    return InvoiceCategory.OTHER


def compute_deductible_tax(
    category: InvoiceCategory,
    total_amount: float,      # 价税合计
    tax_amount: float,        # 发票上税额
    tax_rate_value: float,    # 发票税率数值 0.09/0.06/0.03/0.01
    item_name: str = "",
    seller_name: str = "",
    raw_extra: dict | None = None,
) -> tuple[float, DeductibleStatus, str]:
    """
    返回: (可抵扣税额, 状态, 理由)
    注意：小规模纳税人上层直接返回 0，不调用此函数
    """
    rule = DEDUCTION_RULES.get(category)
    if not rule:
        return 0.0, DeductibleStatus.NONE, f"未识别票种类别: {category.value}"

    if rule.status == DeductibleStatus.FULL:
        # 农产品特殊：需从 raw_extra 取扣除率
        if category == InvoiceCategory.AGRICULTURAL and raw_extra:
            rate = raw_extra.get("deduction_rate", 0.09)
            return round(total_amount / (1 + rate) * rate, 2), DeductibleStatus.FULL, rule.condition
        return round(tax_amount, 2), DeductibleStatus.FULL, rule.condition

    if rule.status == DeductibleStatus.CALCULATED:
        rate = rule.calc_rate
        # 航空行程单特殊：需(票价+燃油)÷1.09×9%
        if category == InvoiceCategory.AIR_TRANSPORT and raw_extra:
            ticket = raw_extra.get("ticket_price", 0)
            fuel = raw_extra.get("fuel_surcharge", 0)
            base = ticket + fuel
            if base > 0:
                return round(base / (1 + rate) * rate, 2), DeductibleStatus.CALCULATED, rule.condition
        # 铁路/公路水路：按价税合计反推
        return round(total_amount / (1 + rate) * rate, 2), DeductibleStatus.CALCULATED, rule.condition

    return 0.0, DeductibleStatus.NONE, rule.condition