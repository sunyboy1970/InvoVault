"""增值税普通发票识别器（兜底，含通行费/住宿/餐饮分类）"""
from __future__ import annotations
from pathlib import Path
import re
from core.extractors.base import BaseExtractor, InvoiceRawData, RIDE_HAILING_KEYWORDS, RIDE_HAILING_SHORT_PLATFORMS


class VatNormalExtractor(BaseExtractor):
    """增值税普通发票识别器"""

    SUPPORTED_TYPES = ["vat_normal", "普通发票", "增值税普通发票", "增值税普通发票（电子）"]
    PRIORITY = 100  # 兜底，仅当其他识别器都不匹配时使用

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview_text(file_path)
        # 兜底：只要不是专用发票、不是通行费、不是网约车就接受
        # 兼容"增值税电子普通发票"（"电子"与"发票"可能不连续）
        has_electronic = "电子" in text and "发票" in text
        has_normal = "普通发票" in text or has_electronic
        not_special = "专用发票" not in text
        not_toll = "通行费" not in text
        # 使用与 RideHailingExtractor 同步的共享常量检查
        has_ride_hailing_kw = any(kw in text for kw in RIDE_HAILING_KEYWORDS)
        has_ride_hailing_short = any(kw in text for kw in RIDE_HAILING_SHORT_PLATFORMS)
        has_electronic_base = "电子" in text and "发票" in text
        not_ride_hailing = not (has_ride_hailing_kw or (has_ride_hailing_short and has_electronic_base))
        return has_normal and not_special and not_toll and not_ride_hailing

    def _extract_buyer_seller_names(self, text: str) -> tuple[str, str]:
        """从文本中提取买方和卖方名称"""
        buyer = ""
        seller = ""

        # 方法0：处理"名称:"在行中嵌入的旧版格式（如"买方名称 名称: 卖方名称买 名称: 售"）
        # 方法0：处理"名称:"在行中嵌入的旧版格式（如"买方公司名 名称: 卖方公司名买 名称: 售"）
        for line in text.split("\n"):
            if "名称:" in line and "名称:" != line.strip()[:3]:
                # 跳过"购 销 名称:"格式（由方法A处理）
                if line.strip().startswith("购 销"):
                    continue
                idx = line.find("名称:")
                if idx > 0:
                    # 名称:之前的内容可能有买方名称
                    before = line[:idx].strip()
                    before_clean = before
                    if before.startswith("购"): before_clean = before[1:].strip()
                    if before.startswith("买"): before_clean = before[1:].strip()
                    if before.startswith("售"): before_clean = before[1:].strip()
                    # 仅当"名称:"前是有效公司名时才设买家
                    if before_clean and not buyer and ("有限" in before_clean or "公司" in before_clean or len(before_clean) > 4):
                        buyer = before_clean
                    # 提取卖家：名称:后到"买/售/方"之间的文本
                    # 跳过"买/购/售"前缀开头的行（如"买 名称:XX 售 名称:YY"由方法2处理）
                    if before_clean and len(before_clean) <= 3:
                        pass  # 不是真正公司名,不提取seller
                    elif not before_clean:
                        pass  # 纯标记前缀（"买""购""售"），由方法1/2处理
                    else:
                        after = line[idx + 3:].strip()
                        m = re.search(r"([^\s][^买售方备汇]*)", after)
                        if m:
                            seller_candidate = m.group(1).strip()
                            for suf in ["买", "售", "方", "备", "汇", "信", "统一", "纳税", "下载"]:
                                i = seller_candidate.find(suf)
                                if i > 0:
                                    seller_candidate = seller_candidate[:i].strip()
                            if seller_candidate and not seller and len(seller_candidate) > 3:
                                seller = seller_candidate


        # 方法A：处理"购 销"同行的两个"名称:"（无前缀修饰的并列格式）
        pair_match = re.search(r"购\s*销\s+名称[：:]\s*[^\s][^名称]*\s+名称[：:]\s*[^\s][^名称]*", text)
        if pair_match:
            pair_text = pair_match.group(0)
            name_matches = re.findall(r"名称[：:]\s*([^\s][^名称]*)", pair_text)
            if len(name_matches) >= 2:
                if not buyer:
                    buyer = name_matches[0].strip()
                    for suf in ["信", "统一", "纳税", "识别号", "代码", "下载", "次数", "买", "售", "方"]:
                        idx = buyer.find(suf)
                        if idx > 0:
                            buyer = buyer[:idx].strip()
                if not seller:
                    seller = name_matches[-1].strip()
                    for suf in ["信", "统一", "纳税", "识别号", "代码", "下载", "次数", "买", "售", "方"]:
                        idx = seller.find(suf)
                        if idx > 0:
                            seller = seller[:idx].strip()
                if buyer or seller:
                    return buyer, seller

        # 方法1：处理"购 名称: XXXX 销 名称: YYYY"在同一行的格式（京东发票）
        m = re.search(r"购\s*名\s*称[：:]\s*([^\s][^销]*)", text)
        if m:
            buyer = m.group(1).strip()
            for suf in ["信", "统一", "纳税人", "识别号", "代码", "下载", "次数"]:
                idx = buyer.find(suf)
                if idx > 0:
                    buyer = buyer[:idx].strip()

        m = re.search(r"销\s*名\s*称[：:]\s*([^\n]+)", text)
        if m:
            seller = m.group(1).strip()
            # 只在"信"后面跟空格或其他已知分隔符时才截断
            for suf in ["信 ", "信\t", "统一", "纳税人", "识别号", "代码", "下载", "次数", "密"]:
                idx = seller.find(suf)
                if idx > 0:
                    seller = seller[:idx].strip()

        # 方法2：处理"买 名称: XXXX 售 名称: YYYY"格式
        if not buyer:
            m = re.search(r"买\s*名\s*称[：:]\s*([^售\n]+)", text)
            if m:
                buyer = m.group(1).strip()
                for suf in ["信 ", "信\t", "销", "统一", "纳税人", "识别号", "代码", "下载", "次数"]:
                    idx = buyer.find(suf)
                    if idx > 0:
                        buyer = buyer[:idx].strip()

        if not seller:
            m = re.search(r"售\s*名\s*称[：:]\s*([^\n]+)", text)
            if m:
                seller = m.group(1).strip()
                for suf in ["信 ", "信\t", "统一", "纳税人", "识别号", "代码", "下载", "次数", "密"]:
                    idx = seller.find(suf)
                    if idx > 0:
                        seller = seller[:idx].strip()

        # 方法2备选：找"售 名称"
        if not seller:
            m = re.search(r"售\s*名\s*称[：:]\s*([^\n]+)", text)
            if m:
                seller = m.group(1).strip()
                for suf in ["信", "统一", "纳税人", "识别号", "代码", "下载", "次数", "密"]:
                    idx = seller.find(suf)
                    if idx > 0:
                        seller = seller[:idx].strip()

        # 方法1备选：找所有"名 称"行（兼容"名 称:"和"名称:"，以及"购 名称"/"售 名称"）
        if not buyer or not seller:
            name_lines = []
            for line in text.split("\n"):
                if "名 称" in line and ("名 称:" in line or "名称:" in line):
                    name_lines.append(line.strip())
                elif "购 名称" in line or "售 名称" in line:
                    name_lines.append(line.strip())

            if len(name_lines) >= 2:
                # 第一个是买方，第二个（含汇总开具/销售方）是卖方
                buyer = name_lines[0].replace("名 称:", "").replace("名称:", "").strip()
                seller = name_lines[1].replace("名 称:", "").replace("名称:", "").strip()

                # 清理买方：截断在"买 码"、"统一社会信用"等之前
                for split_char in ["买 码", "统一社会信用", "纳税人识别", "信 统一", "信 息", "下载次数"]:
                    idx = buyer.find(split_char)
                    if idx > 0:
                        buyer = buyer[:idx].strip()

                # 清理卖方：截断在"汇总开具"、"销 备"、"售"、"地 址"、"电 话"、"开户行"等之前
                for split_char in ["汇总开具", "销 备", "售", "地 址", "电 话", "开户行", "账号", "收 款", "复 核", "开票人"]:
                    idx = seller.find(split_char)
                    if idx > 0:
                        seller = seller[:idx].strip()

                # 清理买方后缀
                for suf in ["买 码", "信", "统一", "纳税人", "识别号", "代码", "下载", "次数", "密"]:
                    idx = buyer.find(suf)
                    if idx > 0:
                        buyer = buyer[:idx].strip()

                return buyer, seller

        # 备选方法：找"购 名称"和"售 名称"
        if not buyer:
            m = re.search(r"购\s*名\s*称[：:]\s*([^售\n]+)", text)
            if m:
                buyer = m.group(1).strip()
                for suf in ["销", "信", "统一", "纳税人", "识别号", "代码", "下载", "次数"]:
                    idx = buyer.find(suf)
                    if idx > 0:
                        buyer = buyer[:idx].strip()

        if not seller:
            m = re.search(r"售\s*名\s*称[：:]\s*([^\n]+)", text)
            if m:
                seller = m.group(1).strip()
                for suf in ["信", "统一", "纳税人", "识别号", "代码", "下载", "次数", "密"]:
                    idx = seller.find(suf)
                    if idx > 0:
                        seller = seller[:idx].strip()

        # 方法2备选：找"售 名称"
        if not seller:
            m = re.search(r"售\s*名\s*称[：:]\s*([^\n]+)", text)
            if m:
                seller = m.group(1).strip()
                for suf in ["信", "统一", "纳税人", "识别号", "代码", "下载", "次数", "密"]:
                    idx = seller.find(suf)
                    if idx > 0:
                        seller = seller[:idx].strip()

        return buyer, seller

    def _extract_tax_ids(self, text: str) -> tuple[str, str]:
        ids = re.findall(r"统一社会信用代码/纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
        buyer_tax = ids[0] if len(ids) > 0 else ""
        seller_tax = ids[1] if len(ids) > 1 else ""

        if not seller_tax:
            m = re.search(r"(?:销售方|销货单位)纳税人识别号[：:]\s*([A-Z0-9]{15,20})", text)
            if m:
                seller_tax = m.group(1)
        return "", seller_tax  # 买方税号通常不需要，卖方税号取第二个

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "增值税普通发票"
        if "电子" in text and "普通" in text:
            invoice_type = "增值税普通发票（电子）"
        if "通行费" in text and "普通" in text:
            invoice_type = "通行费电子普通发票"

        # 提取买卖双方
        buyer_name, seller_name = self._extract_buyer_seller_names(text)
        buyer_tax_id, seller_tax_id = self._extract_tax_ids(text)

        # 提取金额、税率
        total_amount = self._find_total_amount(text)
        tax_amount = self._find_tax_amount(text)
        tax_rate_str = self._find_tax_rate(text)

        # 处理"不征税"发票
        if tax_rate_str == "不征税":
            amount_no_tax = total_amount
            tax_amount = 0.0
            tax_rate_str = "不征税"
        else:
            # 计算不含税金额
            if total_amount > 0 and tax_amount > 0:
                amount_no_tax = round(total_amount - tax_amount, 2)
            elif total_amount > 0:
                # 只有价税合计，尝试从税率反推
                try:
                    tr = float(tax_rate_str.replace("%", "").replace("％", "")) / 100
                    if tr > 0:
                        amount_no_tax = round(total_amount / (1 + tr), 2)
                    else:
                        amount_no_tax = 0.0
                except (ValueError, ZeroDivisionError):
                    amount_no_tax = 0.0
            else:
                amount_no_tax = 0.0

            tax_rate_str = tax_rate_str or "3%"
            tax_amount = self._find_tax_amount(text)
            if tax_amount == 0 and total_amount > 0:
                tax_amount = round(total_amount - amount_no_tax, 2) if total_amount > 0 else 0.0

        # 关键修复：total_amount 应在计算 amount_no_tax 之后重新获取，确保一致性
        # 但这里已经获取过了，保持原值

        item_name = self._find_item_name(text)

        items = [{
            "name": item_name or "*货物*货物",
            "unit": "",
            "quantity": 1,
            "unit_price": amount_no_tax,
            "amount_no_tax": amount_no_tax,
            "tax_rate": tax_rate_str or "3%",
            "tax_amount": tax_amount,
            "total_amount": total_amount,
        }]

        return InvoiceRawData(
            invoice_type=invoice_type,
            invoice_code=self._find_inv_code(text),
            invoice_number=self._find_inv_no(text),
            invoice_date=self._find_date(text),
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax_id,
            items=items,
            total_amount=total_amount,
            total_tax=tax_amount,
            tax_rate=tax_rate_str or "3%",
            item_name=item_name,
            raw_text=text[:2000],
        )

    def _find_inv_code(self, text: str) -> str:
        m = re.search(r"发票代码[：:]\s*(\d{10,12})", text)
        return m.group(1) if m else ""

    def _find_inv_no(self, text: str) -> str:
        m = re.search(r"\d{20,}", text)
        if m:
            return m.group()
        m = re.search(r"发票号码[：:]\s*(\d{8,20})", text)
        return m.group(1) if m else ""

    def _find_date(self, text: str) -> str:
        m = re.search(r"开票日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)", text)
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
        m = re.search(r"价\s*税\s*合\s*计[：:]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        m = re.search(r"[(（]\s*小\s*写\s*[)）]\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        return 0.0

    def _find_tax_amount(self, text: str) -> float:
        """提取税额合计"""
        # 模式1：税 额 合 计
        m = re.search(r"税\s*额\s*合\s*计[：:]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        # 模式2：税 额:
        m = re.search(r"税\s*额[：:]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        # 模式3：合计税额
        m = re.search(r"合计税额[：:]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(1).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        # 模式4：合 计 ¥金额 ¥税额（如"合 计 ¥61.53 ¥5.54"）
        m = re.search(r"合\s*计\s*[¥￥]?([\d,]+\.?\s*\d*)\s+[¥￥]?([\d,]+\.?\s*\d*)", text)
        if m:
            num_str = m.group(2).replace(",", "").replace(" ", "").replace("\u3000", "")
            try:
                return float(num_str)
            except ValueError:
                pass
        return 0.0

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
        # 先检查是否"不征税"
        if "不征税" in search_text:
            return "不征税"
        # 模式1：带分类的完整行
        m = re.search(r"\*[^*]+\*[^\s]+(?:\s+\S+){2,5}\s+(\d+%)\s+[\d.,]+(?:\s|$)", search_text)
        if m:
            return m.group(1)
        # 模式2：简洁行
        m = re.search(r"\*[^*]+\*[^\s]+\s+[\d.,]+\s+(\d+%)\s+[\d.,]+", search_text)
        if m:
            return m.group(1)
        return ""

    def _find_item_name(self, text: str) -> str:
        # 跳过加密区：只在"货物或应税劳务"或"项目名称"表头之后查找
        header_idx = text.find("货物或应税劳务")
        if header_idx < 0:
            header_idx = text.find("项目名称")
        if header_idx < 0:
            header_idx = text.find("合 计")
        search_text = text[header_idx:] if header_idx >= 0 else text

        # 从明细行提取 *分类*名称
        m = re.search(r"\*([^*]+?)\*([^\s]+)", search_text)
        if m:
            return f"*{m.group(1)}*{m.group(2)}"

        # 从表头下第一行提取
        lines = search_text.split("\n")
        for i, line in enumerate(lines):
            if "货物或应税劳务" in line or "项目名称" in line:
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    m = re.search(r"\*([^*]+?)\*([^\s]+)", next_line)
                    if m:
                        return f"*{m.group(1)}*{m.group(2)}"

        m = re.search(r"货物或应税劳务名称[：:]\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        return ""

    def _extract_preview_text(self, file_path: Path) -> str:
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text("text", sort=True)
                if len(text) > 500:
                    break
            return text[:500]
        except Exception:
            return ""


# 注册
from core.extractors.base import register_extractor
register_extractor(VatNormalExtractor())