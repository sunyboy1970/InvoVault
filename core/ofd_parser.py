"""OFD 电子发票解析器：XBRL 提取 + 版面文本回退
独立模块，供 pipeline.py 调用，替换 pipeline.py 中简易的 extract_text_ofd/extract_text_ofd_xbrl
"""
from __future__ import annotations
import zipfile
import xml.etree.ElementTree as ET
import tempfile
import re
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


# OFD 命名空间
NS = {
    "ofd": "http://www.ofdspec.org/2016",
    "xlink": "http://www.w3.org/1999/xlink",
    "xbrl": "http://www.xbrl.org/2003/instance",
    "xbrli": "http://www.xbrl.org/2003/instance",
    "link": "http://www.xbrl.org/2003/linkbase",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


# XBRL 税务数字账票常用命名空间
NS_TAX = {
    "fp": "http://www.chinatax.gov.cn/dataspec/fapiao/",  # 发票命名空间
    "cst": "http://www.chinatax.gov.cn/dataspec/common/tax/",  # 税务通用
    "cmn": "http://www.chinatax.gov.cn/dataspec/common/",  # 通用
    "cbu": "http://www.chinatax.gov.cn/dataspec/common/buyer/",  # 购买方
    "cse": "http://www.chinatax.gov.cn/dataspec/common/seller/",  # 销售方
    "cit": "http://www.chinatax.gov.cn/dataspec/common/item/",  # 项目明细
    "cin": "http://www.chinatax.gov.cn/dataspec/common/invoice/",  # 发票通用
}


@dataclass
class OFDParseResult:
    """OFD 解析结果"""
    text: str = ""                    # 完整版面文本
    xbrl_data: dict = field(default_factory=dict)  # XBRL 结构化字段
    pages: list[str] = field(default_factory=list)  # 页面文件列表
    error: Optional[str] = None       # 错误信息
    file_path: str = ""               # 源文件路径


class OFDParser:
    """OFD 发票解析器"""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.tmpdir: Path | None = None
        self._doc_root: str | None = None
        self._pages: list[str] = []
        self._xbrl_data: dict[str, Any] = {}
        self._full_text: str = ""
        self._parsed = False

    def parse(self) -> OFDParseResult:
        """解析 OFD 文件，返回结构化数据"""
        if self._parsed:
            return OFDParseResult(
                text=self._full_text,
                xbrl_data=self._xbrl_data,
                pages=self._pages,
                file_path=str(self.file_path),
            )

        result = OFDParseResult(file_path=str(self.file_path))
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tmpdir = Path(tmpdir)
            try:
                self._extract_zip()
                self._find_doc_root()
                self._parse_document()
                self._parse_pages()
                self._extract_xbrl()
                self._parsed = True

                result.text = self._full_text
                result.xbrl_data = self._xbrl_data
                result.pages = self._pages
            except Exception as e:
                result.error = str(e)
                result.text = self._full_text
                result.xbrl_data = self._xbrl_data
                result.pages = self._pages

        return result

    def _extract_zip(self) -> None:
        """解压 OFD (ZIP 格式)"""
        with zipfile.ZipFile(self.file_path, 'r') as zf:
            zf.extractall(self.tmpdir)

    def _find_doc_root(self) -> None:
        """读取 OFD.xml 找到 DocRoot 路径"""
        ofd_xml = self.tmpdir / "OFD.xml"
        if not ofd_xml.exists():
            raise ValueError("OFD.xml not found")

        tree = ET.parse(ofd_xml)
        root = tree.getroot()
        # 兼容多种路径
        doc_root_elem = (root.find(".//ofd:DocRoot", NS) or
                         root.find(".//ofd:DocBody/ofd:DocRoot", NS))
        if doc_root_elem is not None and doc_root_elem.text:
            # 去除前导 /，得到相对路径如 "Doc_0/Document.xml"
            self._doc_root = doc_root_elem.text.lstrip("/")
        else:
            raise ValueError("DocRoot not found in OFD.xml")

    def _parse_document(self) -> None:
        """解析 Document.xml 获取页面列表"""
        if not self._doc_root:
            return

        # _doc_root 已去除前导/，如 "Doc_0/Document.xml"
        doc_xml = self.tmpdir / self._doc_root
        if not doc_xml.exists():
            return

        tree = ET.parse(doc_xml)
        root = tree.getroot()

        for page_elem in root.findall(".//ofd:Page", NS):
            # 兼容 xlink:href, href 和 BaseLoc 三种属性
            href = (page_elem.get("{http://www.w3.org/1999/xlink}href") or
                    page_elem.get("href") or
                    page_elem.get("BaseLoc"))
            if href:
                self._pages.append(href)

    def _parse_pages(self) -> None:
        """解析所有页面提取文本，包括模板页"""
        if not self._doc_root or not self._pages:
            return

        # DocRoot 是 Document.xml 的路径（如 /Doc_0/Document.xml），需去除前导 /
        doc_root = self._doc_root.lstrip("/")
        doc_root_dir = Path(doc_root).parent
        texts = []

        def _extract_text_from_xml(xml_path: Path) -> None:
            """从单个 Content.xml 提取文本"""
            if not xml_path.exists():
                return
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for text_obj in root.findall(".//ofd:TextObject", NS):
                    for text_code in text_obj.findall(".//ofd:TextCode", NS):
                        c_attr = text_code.get("c") or text_code.get("{http://www.ofdspec.org/2016}c")
                        if c_attr:
                            texts.append(c_attr)
                        elif text_code.text and text_code.text.strip():
                            texts.append(text_code.text.strip())
            except ET.ParseError:
                pass

        # 提取页面内容
        for page_file in self._pages:
            page_path = self.tmpdir / doc_root_dir / page_file
            _extract_text_from_xml(page_path)

        # 提取模板页内容（Tpls目录）
        tpl_dir = self.tmpdir / doc_root_dir / "Tpls"
        if tpl_dir.exists():
            for tpl_file in tpl_dir.rglob("Content.xml"):
                _extract_text_from_xml(tpl_file)

        self._full_text = " ".join(texts)

    def _extract_xbrl(self) -> None:
        """提取嵌入的 XBRL 结构化发票数据

        XBRL 通常在：
        - CustomData/ 目录下
        - Attachments/ 目录下
        - 文件名包含 xbrl、invoice、发票、data、custom 等关键词
        """
        if not self.tmpdir:
            return

        xbrl_data = {}

        # 搜索所有 XML 文件
        for xml_file in self.tmpdir.rglob("*.xml"):
            # 跳过已知的结构文件
            rel_path = xml_file.relative_to(self.tmpdir)
            if any(skip in str(rel_path) for skip in
                   ["Document.xml", "Page_", "OFD.xml", "Res_", "Signatures",
                    "Template.xml", "PublicRes.xml"]):
                continue

            # 优先处理可能包含 XBRL 的文件
            name_lower = xml_file.name.lower()
            if not any(kw in name_lower for kw in
                       ["xbrl", "invoice", "发票", "data", "custom",
                        "attach", "invoice_", "fp_", "fpj", "fpb"]):
                continue

            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # XBRL instance 根元素
                if "xbrl" in root.tag.lower() or root.tag.endswith("}xbrl"):
                    self._parse_xbrl_instance(root, xbrl_data)
                else:
                    # 通用 XML 提取（税务数字账票格式）
                    self._parse_tax_xml(root, xbrl_data)

            except ET.ParseError:
                continue

        self._xbrl_data = xbrl_data

    def _parse_xbrl_instance(self, root: ET.Element, result: dict) -> None:
        """解析 XBRL Instance 文档"""
        NS_XBRL = "http://www.xbrl.org/2003/instance"

        # 提取所有 context
        contexts: dict[str, dict] = {}
        for context in root.findall(f".//{{{NS_XBRL}}}context"):
            ctx_id = context.get("id", "")
            ctx_data = {}

            # entity identifier (纳税人识别号等)
            entity = context.find(f".//{{{NS_XBRL}}}entity")
            if entity is not None:
                identifier = entity.find(f".//{{{NS_XBRL}}}identifier")
                if identifier is not None and identifier.text:
                    ctx_data["entity_identifier"] = identifier.text.strip()
                    scheme = identifier.get("scheme", "")
                    if scheme:
                        ctx_data["identifier_scheme"] = scheme

            # period (期间)
            period = context.find(f".//{{{NS_XBRL}}}period")
            if period is not None:
                for child in period:
                    if child.text:
                        tag = child.tag.split("}")[-1]
                        ctx_data[f"period_{tag}"] = child.text.strip()

            # segment / scenario (维度信息)
            for dim_elem in context.findall(f".//{{{NS_XBRL}}}explicitMember"):
                dim_name = dim_elem.get("dimension", "")
                dim_value = dim_elem.text.strip() if dim_elem.text else ""
                if dim_name and dim_value:
                    ctx_data[f"dim_{dim_name}"] = dim_value

            contexts[ctx_id] = ctx_data

        # 提取所有 unit (单位定义)
        units: dict[str, str] = {}
        for unit in root.findall(f".//{{{NS_XBRL}}}unit"):
            unit_id = unit.get("id", "")
            measure = unit.find(f".//{{{NS_XBRL}}}measure")
            if measure is not None and measure.text:
                units[unit_id] = measure.text.strip()

        # 遍历所有非标准命名空间的元素（实际业务数据）
        for elem in root.iter():
            # 跳过 XBRL 结构元素
            tag_lower = elem.tag.lower()
            if any(x in tag_lower for x in ["xbrl", "link", "context", "unit", "footnote"]):
                continue

            # 获取本地标签名
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # 有文本内容且不是空白
            if elem.text and elem.text.strip():
                value = elem.text.strip()

                # 尝试获取 contextRef
                ctx_ref = elem.get("contextRef", "")
                key = f"{ctx_ref}:{tag}" if ctx_ref else tag

                # 处理重复 key
                if key in result:
                    if not isinstance(result[key], list):
                        result[key] = [result[key]]
                    result[key].append(value)
                else:
                    result[key] = value

                # 同时存储不带 contextRef 的键，方便后续匹配
                if ctx_ref and tag not in result:
                    result[tag] = value

    def _parse_tax_xml(self, root: ET.Element, result: dict) -> None:
        """解析税务数字账票格式的 XML（非标准 XBRL）"""
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if elem.text and elem.text.strip():
                value = elem.text.strip()
                if tag in result:
                    if not isinstance(result[tag], list):
                        result[tag] = [result[tag]]
                    result[tag].append(value)
                else:
                    result[tag] = value


def parse_ofd(file_path: str | Path) -> dict[str, Any]:
    """便捷函数：解析 OFD 文件

    Returns:
        {
            "text": str,           # 完整版面文本
            "xbrl_data": dict,     # XBRL 结构化字段
            "pages": list[str],    # 页面文件列表
            "error": str | None    # 错误信息
        }
    """
    parser = OFDParser(file_path)
    result = parser.parse()
    return {
        "text": result.text,
        "xbrl_data": result.xbrl_data,
        "pages": result.pages,
        "error": result.error,
    }


# ===== 标准化字段映射（税务数字账票 XBRL 规范）=====

# 发票类型映射
INVOICE_TYPE_MAP = {
    "01": "增值税专用发票",
    "02": "增值税专用发票(货运运输业)",
    "03": "增值税专用发票(销售免税农产品)",
    "04": "增值税专用发票(成品油)",
    "05": "增值税专用发票(二手车销售)",
    "06": "增值税普通发票",
    "07": "增值税普通发票(卷票)",
    "08": "增值税普通发票(卷式)",
    "09": "增值税普通发票(货运运输业)",
    "10": "增值税普通发票(销售免税农产品)",
    "11": "增值税电子专用发票",
    "12": "增值税电子普通发票",
    "14": "增值税电子普通发票(通行费)",
    "15": "二手车销售统一发票",
    "16": "机动车销售统一发票",
    "20": "海关进口增值税专用缴款书",
    "51": "通行费电子发票",
    "52": "铁路电子客票",
    "53": "航空运输电子客票行程单",
    "54": "网约车电子发票",
    "55": "道路/水路运输电子客票",
    "56": "农产品收购发票",
    "57": "代扣代缴税款完税凭证",
}

# XBRL 字段映射表（税务数字账票规范）
# key: 标准字段名, value: XBRL 中可能的标签名列表（优先级从高到低）
XBRL_FIELD_MAP: dict[str, list[str]] = {
    # 基础信息
    "invoice_type": [
        "fpLx", "InvoiceType", "invoiceType", "发票类型",
        "FpLxDm", "发票种类代码", "InvoiceCategoryCode",
    ],
    "invoice_type_name": [
        "fpLxMc", "InvoiceTypeName", "invoiceTypeName", "发票类型名称",
    ],
    "invoice_code": [
        "fpDm", "InvoiceCode", "invoiceCode", "发票代码",
    ],
    "invoice_number": [
        "fpHm", "InvoiceNumber", "invoiceNumber", "发票号码",
    ],
    "invoice_date": [
        "kprq", "Kprq", "InvoiceDate", "invoiceDate", "开票日期", "开票时间",
    ],
    "invoice_time": [
        "kpsj", "Kpsj", "InvoiceTime", "invoiceTime", "开票时间",
    ],

    # 销售方信息
    "seller_name": [
        "xfMc", "XfMc", "SellerName", "sellerName", "销售方名称", "销方名称",
        "销货单位名称", "销售方单位名称",
    ],
    "seller_tax_id": [
        "xfNsrsbh", "XfNsrsbh", "SellerTaxId", "sellerTaxId", "销售方纳税人识别号",
        "销方识别号", "销售方纳税人识别号", "销货单位纳税人识别号",
    ],
    "seller_address_phone": [
        "xfDzdh", "XfDzdh", "SellerAddressPhone", "销售方地址电话",
        "销方地址电话", "销售方地址、电话",
    ],
    "seller_bank_account": [
        "xfYhzh", "XfYhzh", "SellerBankAccount", "销售方银行账号",
        "销方银行账号", "销售方开户银行及账号",
    ],

    # 购买方信息
    "buyer_name": [
        "gfMc", "GfMc", "BuyerName", "buyerName", "购买方名称", "购方名称",
        "购货单位名称", "购买方单位名称",
    ],
    "buyer_tax_id": [
        "gfNsrsbh", "GfNsrsbh", "BuyerTaxId", "buyerTaxId", "购买方纳税人识别号",
        "购方识别号", "购买方纳税人识别号", "购货单位纳税人识别号",
    ],
    "buyer_address_phone": [
        "gfDzdh", "GfDzdh", "BuyerAddressPhone", "购买方地址电话",
        "购方地址电话", "购买方地址、电话",
    ],
    "buyer_bank_account": [
        "gfYhzh", "GfYhzh", "BuyerBankAccount", "购买方银行账号",
        "购方银行账号", "购买方开户银行及账号",
    ],

    # 金额信息
    "total_amount": [
        "jeHj", "JeHj", "Hjje", "HjJe", "TotalAmount", "totalAmount",
        "价税合计", "合计金额", "价税合计(小写)", "价税合计小写",
    ],
    "total_amount_cn": [
        "jeHjdx", "JeHjdx", "TotalAmountCn", "totalAmountCn",
        "价税合计大写", "价税合计(大写)", "合计金额大写",
    ],
    "tax_amount": [
        "seHj", "SeHj", "Hjse", "HjSe", "TaxAmount", "taxAmount",
        "税额", "合计税额", "税额合计",
    ],
    "amount_no_tax": [
        "bhsje", "Bhsje", "Hjbhsje", "HjBhsje", "AmountNoTax", "amountNoTax",
        "不含税金额", "金额合计", "不含税金额合计", "金额合计(不含税)",
    ],

    # 税率/征收率
    "tax_rate": [
        "sl", "Sl", "TaxRate", "taxRate", "税率",
    ],
    "tax_rate_name": [
        "slMc", "SlMc", "TaxRateName", "税率名称",
    ],

    # 开票人/收款人/复核人
    "drawer": [
        "kpr", "Kpr", "Drawer", "drawer", "开票人",
    ],
    "payee": [
        "skr", "Skr", "Payee", "payee", "收款人",
    ],
    "reviewer": [
        "fhr", "Fhr", "Reviewer", "reviewer", "复核人",
    ],
    # 避免字段冲突的映射
    "invoice_check_code": [
        "jym", "Jym", "CheckCode", "checkCode", "校验码",
    ],

    # 备注/机器编号
    "remarks": [
        "bz", "Bz", "Remarks", "remarks", "备注",
    ],
    "machine_number": [
        "jqbh", "Jqbh", "MachineNumber", "machineNumber", "机器编号",
    ],

    # 明细项目
    "items": [
        "goods", "Goods", "Items", "items", "明细", "项目",
        "xmxx", "Xmxx", "ItemDetails",
    ],
    "item_name": [
        "xmmc", "Xmmc", "ItemName", "itemName", "货物或应税劳务名称",
        "项目名称", "商品名称",
    ],
    "item_spec": [
        "ggxh", "Ggxh", "ItemSpec", "itemSpec", "规格型号",
    ],
    "item_unit": [
        "dw", "Dw", "ItemUnit", "itemUnit", "单位",
    ],
    "item_quantity": [
        "sl", "Sl", "ItemQuantity", "itemQuantity", "数量",
    ],
    "item_price": [
        "dj", "Dj", "ItemPrice", "itemPrice", "单价",
    ],
    "item_amount_no_tax": [
        "je", "Je", "ItemAmountNoTax", "itemAmountNoTax", "金额",
        "不含税金额", "项目金额",
    ],
    "item_tax_rate": [
        "sl", "Sl", "ItemTaxRate", "itemTaxRate", "税率",
    ],
    "item_tax_amount": [
        "se", "Se", "ItemTaxAmount", "itemTaxAmount", "税额",
        "项目税额",
    ],
    "item_tax_pref": [
        "yzzce", "Yzzce", "ItemTaxPref", "itemTaxPref",
        "优惠政策标识", "免税/优惠税额",
    ],
}

# 带 contextRef 前缀的字段也要匹配
XBRL_FIELD_MAP_WITH_CTX = {}
for std_field, possible_keys in XBRL_FIELD_MAP.items():
    XBRL_FIELD_MAP_WITH_CTX[std_field] = possible_keys + [
        f"*:{k}" for k in possible_keys
    ] + [
        f"*_{k}" for k in possible_keys
    ]


def _find_in_xbrl(xbrl_data: dict, field: str) -> str | float | list | None:
    """在 XBRL 数据中查找字段（支持模糊匹配和 contextRef 前缀）"""
    possible_keys = XBRL_FIELD_MAP_WITH_CTX.get(field, [field])

    # 1. 精确匹配
    for key in possible_keys:
        if key in xbrl_data:
            value = xbrl_data[key]
            if isinstance(value, list):
                return value[0] if value else None
            return value

    # 2. 模糊匹配（不区分大小写，支持 contextRef 前缀）
    xbrl_lower = {k.lower(): v for k, v in xbrl_data.items()}
    for key in possible_keys:
        key_lower = key.lower()
        for k, v in xbrl_lower.items():
            # 精确匹配（忽略前缀）
            if k == key_lower or k.endswith(f":{key_lower}") or k.endswith(f"_{key_lower}"):
                value = v
                if isinstance(value, list):
                    return value[0] if value else None
                return value

    # 3. 包含匹配（字段名包含关键词）
    for key in possible_keys:
        key_lower = key.lower()
        for k, v in xbrl_lower.items():
            if key_lower in k:
                value = v
                if isinstance(value, list):
                    return value[0] if value else None
                return value

    return None


def _to_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # 处理中文数字、逗号、货币符号
        cleaned = value.replace(",", "").replace("￥", "").replace("¥", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            pass
    return default


def _parse_date(value: Any) -> str:
    """解析日期字符串，统一为 YYYY-MM-DD 格式"""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        value = str(int(value))
    value = str(value).strip()

    # 尝试多种格式
    patterns = [
        r"^(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?$",
        r"^(\d{4})(\d{2})(\d{2})$",
        r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$",
    ]
    for pattern in patterns:
        m = re.match(pattern, value)
        if m:
            year, month, day = m.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

    return value


def _parse_tax_rate(value: Any) -> str:
    """解析税率，统一为 '9%' 格式"""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        rate = float(value)
        if rate < 1:
            rate = rate * 100
        return f"{rate:.0f}%".replace(".0%", "%")
    value = str(value).strip().replace("％", "%")
    if not value.endswith("%"):
        try:
            rate = float(value)
            if rate < 1:
                rate = rate * 100
            return f"{rate:.0f}%".replace(".0%", "%")
        except ValueError:
            pass
    return value


def extract_xbrl_fields(xbrl_data: dict[str, Any]) -> dict[str, Any]:
    """从 XBRL 数据中提取发票关键字段（供识别器使用）

    返回标准化字段字典：
    {
        "invoice_type": "",           # 发票类型代码
        "invoice_type_name": "",      # 发票类型名称
        "invoice_code": "",           # 发票代码
        "invoice_number": "",         # 发票号码
        "invoice_date": "",           # 开票日期 (YYYY-MM-DD)
        "invoice_time": "",           # 开票时间
        "seller_name": "",            # 销售方名称
        "seller_tax_id": "",          # 销售方纳税人识别号
        "seller_address_phone": "",   # 销售方地址电话
        "seller_bank_account": "",    # 销售方银行账号
        "buyer_name": "",             # 购买方名称
        "buyer_tax_id": "",           # 购买方纳税人识别号
        "buyer_address_phone": "",    # 购买方地址电话
        "buyer_bank_account": "",     # 购买方银行账号
        "total_amount": 0.0,          # 价税合计
        "total_amount_cn": "",        # 价税合计大写
        "tax_amount": 0.0,            # 税额
        "amount_no_tax": 0.0,         # 不含税金额
        "tax_rate": "",               # 税率 (如 "9%")
        "tax_rate_name": "",          # 税率名称
        "drawer": "",                 # 开票人
        "payee": "",                  # 收款人
        "reviewer": "",               # 复核人
        "remarks": "",                # 备注
        "machine_number": "",         # 机器编号
        "items": [],                  # 明细列表
    }
    """
    result = {}

    # 基础字段
    result["invoice_type"] = str(_find_in_xbrl(xbrl_data, "invoice_type") or "")
    result["invoice_type_name"] = str(_find_in_xbrl(xbrl_data, "invoice_type_name") or "")
    # 如果只有代码，转换为名称
    if result["invoice_type"] and not result["invoice_type_name"]:
        result["invoice_type_name"] = INVOICE_TYPE_MAP.get(result["invoice_type"], "")

    result["invoice_code"] = str(_find_in_xbrl(xbrl_data, "invoice_code") or "")
    result["invoice_number"] = str(_find_in_xbrl(xbrl_data, "invoice_number") or "")
    result["invoice_date"] = _parse_date(_find_in_xbrl(xbrl_data, "invoice_date"))
    result["invoice_time"] = str(_find_in_xbrl(xbrl_data, "invoice_time") or "")

    result["seller_name"] = str(_find_in_xbrl(xbrl_data, "seller_name") or "")
    result["seller_tax_id"] = str(_find_in_xbrl(xbrl_data, "seller_tax_id") or "")
    result["seller_address_phone"] = str(_find_in_xbrl(xbrl_data, "seller_address_phone") or "")
    result["seller_bank_account"] = str(_find_in_xbrl(xbrl_data, "seller_bank_account") or "")

    result["buyer_name"] = str(_find_in_xbrl(xbrl_data, "buyer_name") or "")
    result["buyer_tax_id"] = str(_find_in_xbrl(xbrl_data, "buyer_tax_id") or "")
    result["buyer_address_phone"] = str(_find_in_xbrl(xbrl_data, "buyer_address_phone") or "")
    result["buyer_bank_account"] = str(_find_in_xbrl(xbrl_data, "buyer_bank_account") or "")

    result["total_amount"] = _to_float(_find_in_xbrl(xbrl_data, "total_amount"))
    result["total_amount_cn"] = str(_find_in_xbrl(xbrl_data, "total_amount_cn") or "")
    result["tax_amount"] = _to_float(_find_in_xbrl(xbrl_data, "tax_amount"))
    result["amount_no_tax"] = _to_float(_find_in_xbrl(xbrl_data, "amount_no_tax"))
    result["tax_rate"] = _parse_tax_rate(_find_in_xbrl(xbrl_data, "tax_rate"))
    result["tax_rate_name"] = str(_find_in_xbrl(xbrl_data, "tax_rate_name") or "")

    result["drawer"] = str(_find_in_xbrl(xbrl_data, "drawer") or "")
    result["payee"] = str(_find_in_xbrl(xbrl_data, "payee") or "")
    result["reviewer"] = str(_find_in_xbrl(xbrl_data, "reviewer") or "")
    result["remarks"] = str(_find_in_xbrl(xbrl_data, "remarks") or "")
    result["machine_number"] = str(_find_in_xbrl(xbrl_data, "machine_number") or "")

    # 如果 amount_no_tax 缺失，从 total_amount 和 tax_amount 推算
    if result["amount_no_tax"] == 0.0 and result["total_amount"] > 0:
        result["amount_no_tax"] = round(result["total_amount"] - result["tax_amount"], 2)

    # 如果 tax_amount 缺失，从 total_amount 和 amount_no_tax 推算
    if result["tax_amount"] == 0.0 and result["total_amount"] > 0 and result["amount_no_tax"] > 0:
        result["tax_amount"] = round(result["total_amount"] - result["amount_no_tax"], 2)

    # 明细项目提取
    items = _extract_items_from_xbrl(xbrl_data)
    result["items"] = items

    # 如果有明细，取第一个的项目名称作为主项目名称
    if items and not result.get("item_name"):
        result["item_name"] = items[0].get("name", "")

    return result


def _extract_items_from_xbrl(xbrl_data: dict) -> list[dict]:
    """从 XBRL 数据中提取明细项目"""
    items = []

    # XBRL 明细通常在同一 contextRef 下的重复元素中
    # 先收集所有可能的明细字段
    # 使用更具体的匹配：优先匹配完整字段名，避免 "sl" 同时匹配数量和税率
    item_fields = {
        "name": ["item_name", "xmmc", "Xmmc", "货物或应税劳务名称", "项目名称"],
        "spec": ["item_spec", "ggxh", "Ggxh", "规格型号"],
        "unit": ["item_unit", "dw", "Dw", "单位"],
        "quantity": ["item_quantity", "xmsl", "Xmsl", "sl", "Sl", "数量"],
        "price": ["item_price", "dj", "Dj", "单价"],
        "amount_no_tax": ["item_amount_no_tax", "je", "Je", "金额", "不含税金额", "xmje", "Xmje"],
        "tax_rate": ["item_tax_rate", "ssl", "Ssl", "sl", "Sl", "税率"],
        "tax_amount": ["item_tax_amount", "se", "Se", "税额", "xmse", "Xmse"],
        "tax_pref": ["item_tax_pref", "yzzce", "Yzzce", "优惠政策标识"],
    }

    # 找出所有可能的明细行（通过 contextRef 分组）
    contexts: dict[str, dict] = {}
    for key, value in xbrl_data.items():
        # 匹配 contextRef:tag 格式
        if ":" in key:
            ctx_ref, tag = key.split(":", 1)
            tag_lower = tag.lower()
            for field, possible_tags in item_fields.items():
                for pt in possible_tags:
                    # 精确匹配（不区分大小写）
                    if pt.lower() == tag_lower:
                        if ctx_ref not in contexts:
                            contexts[ctx_ref] = {}
                        contexts[ctx_ref][field] = value
                        break
                    # 包含匹配：但要避免误匹配（如 sl 匹配到 xmsl, ssl）
                    # 只在 tag 包含完整单词边界时匹配
                    elif pt.lower() in tag_lower:
                        # 检查是否为独立单词（前后是非字母数字字符或边界）
                        import re
                        pattern = r'(^|[^a-zA-Z0-9])' + re.escape(pt.lower()) + r'([^a-zA-Z0-9]|$)'
                        if re.search(pattern, tag_lower):
                            if ctx_ref not in contexts:
                                contexts[ctx_ref] = {}
                            contexts[ctx_ref][field] = value
                            break

    # 转换为列表
    for ctx_ref, fields in contexts.items():
        if fields.get("name") or fields.get("amount_no_tax"):
            item = {
                "name": str(fields.get("name", "")),
                "spec": str(fields.get("spec", "")),
                "unit": str(fields.get("unit", "")),
                "quantity": _to_float(fields.get("quantity", 1)),
                "price": _to_float(fields.get("price", 0)),
                "amount_no_tax": _to_float(fields.get("amount_no_tax", 0)),
                "tax_rate": _parse_tax_rate(fields.get("tax_rate", "")),
                "tax_amount": _to_float(fields.get("tax_amount", 0)),
                "tax_pref": str(fields.get("tax_pref", "")),
            }
            items.append(item)

    # 如果没有通过 contextRef 找到，尝试直接找数组
    if not items:
        for key in ["items", "goods", "明细", "项目", "xmxx", "Xmxx", "ItemDetails"]:
            if key in xbrl_data:
                val = xbrl_data[key]
                if isinstance(val, list):
                    for v in val:
                        if isinstance(v, dict):
                            items.append({
                                "name": str(v.get("name") or v.get("xmmc") or v.get("ItemName") or ""),
                                "spec": str(v.get("spec") or v.get("ggxh") or ""),
                                "unit": str(v.get("unit") or v.get("dw") or ""),
                                "quantity": _to_float(v.get("quantity") or v.get("sl") or 1),
                                "price": _to_float(v.get("price") or v.get("dj") or 0),
                                "amount_no_tax": _to_float(v.get("amount_no_tax") or v.get("je") or 0),
                                "tax_rate": _parse_tax_rate(v.get("tax_rate") or v.get("sl") or ""),
                                "tax_amount": _to_float(v.get("tax_amount") or v.get("se") or 0),
                                "tax_pref": str(v.get("tax_pref") or v.get("yzzce") or ""),
                            })
                break

    return items


# ===== 兼容旧接口 =====

def extract_text_ofd(file_path: str | Path) -> str:
    """兼容旧接口：仅提取文本"""
    result = parse_ofd(file_path)
    return result["text"]


def extract_text_ofd_xbrl(file_path: str | Path) -> dict[str, Any]:
    """兼容旧接口：提取文本 + XBRL"""
    result = parse_ofd(file_path)
    return {
        "text": result["text"],
        "xbrl": result["xbrl_data"],
    }


# ===== 单测入口 =====

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python ofd_parser.py <ofd_file>")
        sys.exit(1)

    ofd_path = sys.argv[1]
    print(f"Parsing: {ofd_path}")

    result = parse_ofd(ofd_path)
    print(f"\n=== Text (first 500 chars) ===")
    print(result["text"][:500])
    print(f"\n=== Pages ===")
    print(result["pages"])
    print(f"\n=== XBRL Fields ===")
    fields = extract_xbrl_fields(result["xbrl_data"])
    for k, v in fields.items():
        if v:
            print(f"  {k}: {v}")

    # 保存完整 XBRL 数据供调试
    with open("debug_xbrl.json", "w", encoding="utf-8") as f:
        json.dump(result["xbrl_data"], f, ensure_ascii=False, indent=2)
    print("\nFull XBRL data saved to debug_xbrl.json")