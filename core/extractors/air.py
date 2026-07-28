"""航空运输电子客票行程单识别器"""
from __future__ import annotations
from pathlib import Path
import re
from core.extractors.base import BaseExtractor, InvoiceRawData


class AirExtractor(BaseExtractor):
    """航空运输电子客票行程单识别器"""

    SUPPORTED_TYPES = ["air_electronic", "航空运输电子客票行程单", "航空电子客票"]
    PRIORITY = 20

    def can_handle(self, file_path: Path, preview_text: str = "") -> bool:
        text = preview_text or self._extract_preview_text(file_path)
        if "航空运输电子客票" in text or "航空电子客票" in text:
            return True
        # OFD 扁平格式：不含标准标题但含国内国际标识和20位号码
        if "国内国际标识" in text and re.search(r"\b\d{20}\b", text):
            return True
        return False

    def _to_float(self, s: str) -> float:
        try:
            return float(s.replace(",", "").replace(" ", "").replace("\u3000", ""))
        except (ValueError, TypeError):
            return 0.0

    def extract(self, file_path: Path, text: str, xbrl_data: dict | None = None) -> InvoiceRawData:
        invoice_type = "航空运输电子客票行程单"
        
        # OFD 航空行程单检测：文件扩展名为 .ofd
        # OFD 的版面文本混入了模板标题和实际数据，走专门扁平解析路径
        fp = file_path if isinstance(file_path, Path) else Path(file_path)
        if fp.suffix.lower() == ".ofd":
            return self._extract_ofd_flat(invoice_type, text, fp)
        
        invoice_number = self._find_inv_no(text)
        passenger_name = self._find_passenger_name(text)
        id_number = self._find_id_number(text)
        route_summary = self._find_route_summary(text)
        segment_count = self._find_segment_count(text)

        ticket_price, fuel_surcharge, tax_rate_pct, vat_tax, civil_fund, other_taxes, total = \
            self._parse_amounts(text)

        if ticket_price == 0 and fuel_surcharge == 0:
            amounts = re.findall(r"CNY\s+([\d,]+\.?\s*\d*)", text)
            if amounts:
                cny_vals = []
                for a in amounts:
                    try:
                        cny_vals.append(float(a.replace(",", "").replace(" ", "").replace("\u3000", "")))
                    except ValueError:
                        pass
                if cny_vals:
                    ticket_price = cny_vals[0]
                    fuel_surcharge = cny_vals[1] if len(cny_vals) > 1 else 0
                    vat_tax = cny_vals[2] if len(cny_vals) > 2 else 0
                    civil_fund = cny_vals[3] if len(cny_vals) > 3 else 0
                    total = cny_vals[-1]
                    if len(cny_vals) >= 6:
                        other_taxes = cny_vals[-2]
                        total = cny_vals[-1]

        total_amount = total if total > 0 else self._find_total_amount(text)
        fill_unit = self._find_fill_unit(text)
        fill_date = self._find_fill_date(text)
        seller_name = fill_unit

        deductible_base = ticket_price + fuel_surcharge
        tax_rate_str = "9%"
        amount_no_tax = round(deductible_base / (1 + 0.09), 2)
        tax_amount = round(deductible_base - amount_no_tax, 2)
        deductible_tax = round(deductible_base / 1.09 * 0.09, 2)
        buyer_name = self._find_buyer_name(text)

        item_name = "*运输服务*航空运输服务"
        items = [{
            "name": item_name, "unit": "张", "quantity": 1,
            "unit_price": amount_no_tax, "amount_no_tax": amount_no_tax,
            "tax_rate": tax_rate_str, "tax_amount": tax_amount, "total_amount": total_amount,
        }]

        extra = {
            "旅客姓名": passenger_name, "证件号码": id_number,
            "航程简述": route_summary, "航段数": segment_count,
            "票价": ticket_price, "民航发展基金": civil_fund,
            "燃油附加费": fuel_surcharge, "其他税费": other_taxes,
            "合计": total_amount, "可抵扣税额": deductible_tax,
            "填开单位": fill_unit, "填开日期": fill_date,
            "ticket_price": ticket_price, "fuel_surcharge": fuel_surcharge,
            "civil_aviation_fund": civil_fund, "deductible_base": deductible_base,
            "flight_info": {"route": route_summary, "segments": segment_count},
        }

        return InvoiceRawData(
            invoice_type=invoice_type, invoice_code="", invoice_number=invoice_number,
            invoice_date=fill_date, seller_name=seller_name, seller_tax_id="",
            buyer_name=buyer_name, buyer_tax_id="",
            items=items, total_amount=total_amount, total_tax=deductible_tax,
            tax_rate=tax_rate_str, item_name=item_name, extra=extra, raw_text=text[:2000],
        )

    def _extract_ofd_flat(self, invoice_type: str, text: str, file_path: Path) -> InvoiceRawData:
        """解析OFD航空行程单扁平文本（单行，不含标准PDF标题）"""
        fill_unit = ""
        fill_date = ""
        
        # 提取20位发票号码
        inv_no = ""
        m = re.search(r"\b(\d{20})\b", text)
        if m:
            inv_no = m.group(1)
        
        # 提取证件号码（带掩码）：6位数字 + 不限量星号 + 不限量数字
        id_number = ""
        m = re.search(r"(\d{6}\*+\d+)", text)
        if m:
            id_number = m.group(1)
        
        # 提取旅客姓名：在发票号之后、ID之前的中文名（2-4汉字）
        passenger_name = ""
        m = re.search(r"\d{20}\s+([\u4e00-\u9fff]{2,4})", text)
        if m:
            passenger_name = m.group(1)
        
        # 提取所有CNY金额序列
        cny_vals = []
        for m in re.finditer(r"CNY\s+([\d,.]+)", text):
            try:
                cny_vals.append(float(m.group(1).replace(",", "")))
            except ValueError:
                pass
        
        ticket_price = cny_vals[0] if len(cny_vals) >= 1 else 0.0
        fuel_surcharge = cny_vals[1] if len(cny_vals) >= 2 else 0.0
        vat_tax = cny_vals[2] if len(cny_vals) >= 3 else 0.0
        civil_fund = cny_vals[3] if len(cny_vals) >= 4 else 0.0
        other_taxes = cny_vals[4] if len(cny_vals) >= 5 else 0.0
        total = cny_vals[5] if len(cny_vals) >= 6 else 0.0
        
        # 提取税率
        tax_rate_pct = ""
        m = re.search(r"(\d+)%", text)
        if m:
            tax_rate_pct = f"{m.group(1)}%"
        
        # 提取填开单位（销售方）：查找姓名+日期+姓名模式
        # OFD格式数据段: ... 公司名 2026年04月28日 购买方名 ...
        fill_unit_m = re.search(r"([\u4e00-\u9fff]{4,}(?:有限公司|股份有限公司|航空公司|航空))\s+\d{4}年\d{1,2}月\d{1,2}日", text)
        if fill_unit_m:
            fill_unit = fill_unit_m.group(1)
        else:
            # 备选：从CNY后文本取第一个公司名
            cny_end = text.rfind("CNY")
            if cny_end >= 0:
                tail = text[cny_end:]
                tail_m = re.findall(r"([\u4e00-\u9fff]{4,}(?:有限公司|股份有限公司|航空|公司))", tail)
                if tail_m:
                    fill_unit = tail_m[0]
        
        # 提取填开日期
        m = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", text)
        if m:
            fill_date = m.group(1)
        
        # 提取航程简述：从数据段解析出发到达机场+城市
        # OFD数据段格式: [3字母机场码] [城市名] [航司缩写] [航班号] [座位] [日期] [时间] [预定号] [生效日] [截止日] [行李额度] [3字母机场码] [城市名]
        # 如: TAO 青岛 南航 CZ3536 V 2026年04月23日 18:00 VRE0WNNP 2026年04月23日 2026年04月23日 20K CAN 广州
        route_summary = ""
        # 在CNY数据之后找飞行航段数据
        cny_end = text.rfind("CNY")
        if cny_end >= 0:
            flight_data = text[cny_end:]
            # 找两对机场码+城市名，第一对=出发，第二对=到达
            route_matches = re.findall(r"([A-Z]{3})\s+([\u4e00-\u9fff]{2,4})", flight_data)
            if len(route_matches) >= 2:
                # 过滤掉模板段中的"至："误匹配 — 取CNY后最后两对有效对
                # 跳过 "至： 00K 000" 这种无效匹配
                valid_pairs = [(c, city) for c, city in route_matches 
                              if city != "至" and not city.isdigit()]
                if len(valid_pairs) >= 2:
                    dep_city = valid_pairs[0][1]
                    arr_city = valid_pairs[-1][1]
                    dep_code = valid_pairs[0][0]
                    arr_code = valid_pairs[-1][0]
                    route_summary = f"{dep_city}-{arr_city}"
                    # 如果能判断是否同一机场，可加机场码：f"{dep_city} {dep_code}-{arr_city} {arr_code}"
        
        seller_name = fill_unit if fill_unit else str(file_path.stem)[:20]
        
        # 计算可抵扣税额（票价+燃油）/1.09*9%
        deductible_base = ticket_price + fuel_surcharge
        tax_rate_str = tax_rate_pct or "9%"
        amount_no_tax = round(deductible_base / (1 + 0.09), 2)
        tax_amount = round(deductible_base - amount_no_tax, 2)
        deductible_tax = round(deductible_base / 1.09 * 0.09, 2)
        total_amount = total if total > 0 else round(amount_no_tax + tax_amount, 2)
        
        buyer_name = ""
        # 购买方：从填开日期后取公司名（限于第一家公司名，不取到模板段）
        buyer_m = re.search(r"\d{4}年\d{1,2}月\d{1,2}日\s+([\u4e00-\u9fff]{4,}(?:有限公司|股份有限公司))", text)
        if buyer_m:
            buyer_name = buyer_m.group(1)
        
        item_name = "*运输服务*航空运输服务"
        items = [{
            "name": item_name, "unit": "张", "quantity": 1,
            "unit_price": amount_no_tax, "amount_no_tax": amount_no_tax,
            "tax_rate": tax_rate_str, "tax_amount": tax_amount, "total_amount": total_amount,
        }]
        extra = {
            "旅客姓名": passenger_name, "证件号码": id_number,
            "航程简述": route_summary, "航段数": 1,
            "票价": ticket_price, "民航发展基金": civil_fund,
            "燃油附加费": fuel_surcharge, "其他税费": other_taxes,
            "合计": total_amount, "可抵扣税额": deductible_tax,
            "填开单位": fill_unit, "填开日期": fill_date,
            "ticket_price": ticket_price, "fuel_surcharge": fuel_surcharge,
            "civil_aviation_fund": civil_fund, "deductible_base": deductible_base,
            "flight_info": {"route": route_summary, "segments": 1},
        }
        return InvoiceRawData(
            invoice_type=invoice_type, invoice_code="", invoice_number=inv_no,
            invoice_date=fill_date, seller_name=seller_name, seller_tax_id="",
            buyer_name=buyer_name, buyer_tax_id="",
            items=items, total_amount=total_amount, total_tax=deductible_tax,
            tax_rate=tax_rate_str, item_name=item_name, extra=extra, raw_text=text[:2000],
        )

    def _find_passenger_name(self, text: str) -> str:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "旅客姓名" in line and "有效身份证" in line:
                if i + 1 < len(lines):
                    m = re.match(r"([\u4e00-\u9fff]{2,4})\s+", lines[i + 1].strip())
                    if m:
                        return m.group(1)
        m = re.search(r"旅客姓名\s+([\u4e00-\u9fff]{2,4})", text)
        if m:
            return m.group(1)
        return ""

    def _find_id_number(self, text: str) -> str:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "旅客姓名" in line and "有效身份证" in line:
                if i + 1 < len(lines):
                    m = re.search(r"(\d{6}\*+\d{4})", lines[i + 1].strip())
                    if m:
                        return m.group(1)
        m = re.search(r"旅客姓名\s+\S+\s+(\S+)", text)
        if m:
            return m.group(1)
        return ""

    def _find_route_summary(self, text: str) -> str:
        # PDF 格式：自:成都 双流 ... T2 航班 ... \n 至:杭州 萧山 T3
        # 用 [\s\S]*? 跳过中间的非空白字符（航站楼、航班号、日期等）
        m = re.search(r"自[：:]\s*([^\s]+(?:\s+[^\s]+)?)[\s\S]*?至[：:]\s*([^\s]+(?:\s+[^\s]+)?)", text)
        if m:
            from_ = m.group(1).strip()
            to_ = m.group(2).strip()
            return f"{from_}-{to_}"
        return ""

    def _find_segment_count(self, text: str) -> int:
        origins = re.findall(r"自[：:]\s*[^\n]+", text)
        return len(origins) if origins else 1

    def _parse_amounts(self, text: str):
        header = r"票价\s+燃油附加费\s+增值税税率增值税税额\s+民航发展基金\s+其他税费\s+合计"
        m = re.search(header + r"[\s\n]*([^\n]+)", text)
        if not m:
            return 0.0, 0.0, "", 0.0, 0.0, 0.0, 0.0
        amounts_line = m.group(1).strip()
        normalized = amounts_line.replace(" ", "").replace("\u3000", "")
        cny_amounts = re.findall(r"CNY\s*([\d.]+)", normalized)
        cny_floats = [round(float(a), 2) for a in cny_amounts]
        pcts = re.findall(r"(\d+)%", normalized)
        tax_rate_pct = f"{pcts[0]}%" if pcts else ""
        if not cny_floats:
            return 0.0, 0.0, "", 0.0, 0.0, 0.0, 0.0
        ticket_price = cny_floats[0]
        fuel_surcharge = cny_floats[1] if len(cny_floats) > 1 else 0.0
        vat_tax = cny_floats[2] if len(cny_floats) > 2 else 0.0
        civil_fund = cny_floats[3] if len(cny_floats) > 3 else 0.0
        other_taxes = 0.0
        total = cny_floats[-1]
        if len(cny_floats) >= 6:
            other_taxes = cny_floats[-2]
            total = cny_floats[-1]
        return ticket_price, fuel_surcharge, tax_rate_pct, vat_tax, civil_fund, other_taxes, total

    def _find_fill_unit(self, text: str) -> str:
        """提取填开单位（销售方）—— 支持OFD空格连接格式"""
        m = re.search(r"填开单位[：:]?\s*([^填]+?)(?:填开日期|购买方|发票号码|$)", text)
        if m:
            name = m.group(1).strip()
            for c in ["销售", "电话", "地址", "统一", "纳税人", "识别号"]:
                idx = name.find(c)
                if idx > 0:
                    name = name[:idx].strip()
            name = re.sub(r"\s+\d{4}年.*$", "", name)
            if len(name) > 2:
                return name
        # OFD格式：从全文抓取第一个非买方公司名
        buyer_kw = ["海言世纪", "阿加莎", "数字科技", "信息技术"]
        for m in re.finditer(r"([一-龥]{2,}(?:有限公司|股份有限公司|航空公司|航空|股份|集团))", text):
            name = m.group(1).strip()
            if not any(kw in name for kw in buyer_kw):
                return name
        return ""

    def _find_fill_date(self, text: str) -> str:
        m = re.search(r"填开日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)", text)
        if m:
            return m.group(1)
        m = re.search(r"填开日期[：:]?\s*(\d{4}年\d{1,2}月\d{1,2}日)", text)
        if m:
            return m.group(1)
        m = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", text)
        if m:
            date = m.group(1)
            pos = text.find(str(date))
            if pos > 20 and "开票日期" not in text[max(0, pos - 20):pos]:
                return date
        return ""

    def _find_buyer_name(self, text: str) -> str:
        m = re.search(r"购买方名称[：:]\s*([^\n]+)", text)
        if m:
            name = m.group(1).strip()
            for c in ["统一", "纳税人", "识别号"]:
                idx = name.find(c)
                if idx > 0:
                    name = name[:idx].strip()
            return name
        return ""

    def _find_inv_no(self, text: str) -> str:
        m = re.search(r"发票号码[：:]\s*(\d{20,})", text)
        if m:
            return m.group(1)
        m = re.search(r"发票号码[：:]?\s*(\d{20})", text)
        if m:
            return m.group(1)
        m = re.search(r"(\d{20,})", text)
        return m.group(1) if m else ""

    def _find_total_amount(self, text: str) -> float:
        _, _, _, _, _, _, total = self._parse_amounts(text)
        if total > 0:
            return total
        m = re.search(r"[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            return self._to_float(m.group(1))
        m = re.search(r"合\s*计\s*[¥￥]?\s*([\d,]+\.?\s*\d*)", text)
        if m:
            return self._to_float(m.group(1))
        m = re.search(r"([\d,]+\.\d{2})\s*$", text, re.MULTILINE)
        if m:
            return self._to_float(m.group(1))
        return 0.0

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


from core.extractors.base import register_extractor
register_extractor(AirExtractor())