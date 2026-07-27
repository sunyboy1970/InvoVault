"""费用归类器：项目名称 → 管理费用二级明细科目
- 关键词按长度降序匹配（长优先）
- seller 参数区分：航空/铁路→差旅费，网约车→市内交通费
- 与 general-taxpayer-invoice 技能 category_mapper.py 逻辑完全一致
"""
from __future__ import annotations

# 科目 → [(关键词, 归类名), ...]  关键词按长度降序
CATEGORY_RULES: dict[str, list[tuple[str, str]]] = {
    "差旅费": [
        ("经纪代理服务*机票款", "差旅费"),   # 13字，必先于"代理服务"
        ("经纪代理服务", "差旅费"),
        ("代订房费", "差旅费"),
        ("代订房", "差旅费"),
        ("机票款", "差旅费"),
        ("代订机票", "差旅费"),
        ("住宿费", "差旅费"),
        ("客运服务费", "差旅费"),
        ("铁路客票", "差旅费"),
        ("航空运输", "差旅费"),
    ],
    "市内交通费": [
        ("网约车", "市内交通费"),
        ("滴滴", "市内交通费"),
        ("曹操", "市内交通费"),
        ("高德", "市内交通费"),
        ("出租车", "市内交通费"),
        ("公交", "市内交通费"),
        ("地铁", "市内交通费"),
    ],
    "业务招待费": [
        ("餐饮服务", "业务招待费"),
        ("餐费", "业务招待费"),
        ("茶楼", "业务招待费"),
        ("酒楼", "业务招待费"),
        ("饭店", "业务招待费"),
        ("预付卡销售*储值卡", "业务招待费"),
    ],
    "办公费": [
        ("电子计算机", "办公费"),
        ("移动通信设备", "办公费"),
        ("纸制品", "办公费"),
        ("办公用品", "办公费"),
        ("打印", "办公费"),
        ("复印", "办公费"),
        ("纸张", "办公费"),
    ],
    "通讯费": [
        ("话费", "通讯费"),
        ("宽带", "通讯费"),
        ("流量", "通讯费"),
    ],
    "中介/咨询费": [
        ("代理服务*咨询费", "中介/咨询费"),
        ("咨询服务", "中介/咨询费"),
        ("技术服务", "中介/咨询费"),
        ("设计服务", "中介/咨询费"),
    ],
    "车辆使用费": [
        ("经营租赁*通行费", "车辆使用费"),
        ("生产生活服务*通行费", "车辆使用费"),
        ("通行费", "车辆使用费"),
        ("高速", "车辆使用费"),
        ("ETC", "车辆使用费"),
    ],
    "燃料费": [
        ("汽油", "燃料费"),
        ("柴油", "燃料费"),
        ("石油制品", "燃料费"),
        ("燃料", "燃料费"),
    ],
    "维修费": [
        ("维修", "维修费"),
        ("修理", "维修费"),
        ("保养", "维修费"),
    ],
    "劳务费": [
        ("人力资源服务*服务费", "劳务费"),
        ("劳务派遣", "劳务费"),
        ("人力资源服务", "劳务费"),
    ],
}

# 扁平化为 [(keyword, category), ...] 按 keyword 长度降序
_FLAT_RULES: list[tuple[str, str]] = []
for cat, rules in CATEGORY_RULES.items():
    for kw, _ in rules:
        _FLAT_RULES.append((kw, cat))
_FLAT_RULES.sort(key=lambda x: -len(x[0]))


def classify_item(item_name: str, seller: str = "") -> str:
    """
    返回费用归类科目名。

    seller 用于区分：
      - 含"航空" → 差旅费（航空行程单）
      - 含"铁路"或"中国铁路" → 差旅费（铁路客票，远途）
      - 网约车/滴滴/曹操/高德/出租车 → 市内交通费
    """
    name = (item_name or "").replace(" ", "")
    seller_clean = (seller or "").replace(" ", "")

    # 航空行程单：seller含"航空" + 项目含"客运"或"运输服务"
    if "航空" in seller_clean and ("客运" in name or "运输服务" in name):
        return "差旅费"

    # 铁路客票：seller含"铁路"或"中国铁路"
    if "铁路" in seller_clean or "中国铁路" in seller_clean:
        if "客运" in name or "运输服务" in name:
            return "差旅费"

    # 网约车：seller或项目名含关键词
    ride_kws = ["网约车", "滴滴", "曹操", "高德", "出租车"]
    if any(kw in name for kw in ride_kws) or any(kw in seller_clean for kw in ride_kws):
        return "市内交通费"

    # 通用关键词匹配（长度降序）
    for kw, cat in _FLAT_RULES:
        if kw in name:
            return cat

    return "其他费用"


def build_expense_sheet_data(records: list["InvoiceRecord"], mode: str) -> dict:
    """
    构建"发票汇总-费用归类"Sheet所需分组数据。
    返回: {subject: {"items": [...], "subtotal": {...}}}
    """
    from collections import defaultdict
    from core.models import InvoiceRecord

    grouped = defaultdict(list)
    for rec in records:
        subject = classify_item(rec.item_name, rec.seller_name)
        grouped[subject].append(rec)

    # 科目排序：按预定义顺序，未定义的放最后
    subject_order = list(CATEGORY_RULES.keys()) + ["其他费用"]
    ordered = {s: grouped[s] for s in subject_order if s in grouped}

    return ordered