"""多 Sheet Excel 导出器：精确复刻两个样本文件格式
- 小规模纳税人：2 Sheet（发票明细、发票汇总-费用归类）
- 一般纳税人：4 Sheet（发票汇总、航空行程单明细、抵扣汇总、发票汇总-费用归类）
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import InvoiceRecord, TaxpayerType


class ExcelExporter:
    """精确复刻样本格式的多 Sheet 导出器"""

    _openpyxl = None
    _styles = None  # 缓存样式

    @classmethod
    def _ensure_styles(cls):
        """延迟加载 openpyxl，缓存样式常量和引用"""
        if cls._styles is not None:
            return cls._styles
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from openpyxl.utils import get_column_letter
        cls._openpyxl = openpyxl
        cls._Alignment = Alignment
        cls._openpyxl_utils = openpyxl.utils
        cls._styles = {
            "HEADER_FONT": Font(bold=True, size=11),
            "HEADER_FILL": PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid"),
            "HEADER_ALIGN": Alignment(horizontal="center", vertical="center", wrap_text=True),
            "BOLD_FONT": Font(bold=True, size=11),
            "NORMAL_FONT": Font(size=11),
            "THIN_BORDER": Border(
                left=Side(style="thin", color="D9D9D9"),
                right=Side(style="thin", color="D9D9D9"),
                top=Side(style="thin", color="D9D9D9"),
                bottom=Side(style="thin", color="D9D9D9"),
            ),
            "SUMMARY_FILL": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
            "SUMMARY_FONT": Font(bold=True, size=11),
            "NUMBER_FMT": "#,##0.00",
            "TEXT_FMT": "@",
        }
        return cls._styles

    # ---- 小规模纳税人表头 ----
    SMALL_HEADERS = ["序号", "发票类型", "发票号码", "开票日期", "销售方名称", "项目名称", "价税合计（小写）"]
    SMALL_WIDTHS = [6, 18, 22, 16, 38, 32, 16]
    SMALL_FMT_ALIGN = [
        ("General", "center"),
        ("General", "center"),
        ("General", "center"),
        ("General", "center"),
        ("General", "left"),
        ("General", "left"),
        ("#,##0.00", "right"),
    ]

    # ---- 一般纳税人表头 ----
    GENERAL_HEADERS = [
        "类型", "发票号码", "开票日期", "销售方名称", "项目名称",
        "金额（不含税）", "税率", "税额", "价税合计（小写）",
        "可抵扣税额", "填开单位", "填开日期", "源文件",
    ]
    GENERAL_WIDTHS = [18, 20, 16, 38, 32, 16, 10, 14, 16, 16, 24, 16, 60]
    GENERAL_FMT_ALIGN = [
        ("General", "center"),
        ("General", "center"),
        ("General", "center"),
        ("General", "left"),
        ("General", "left"),
        ("#,##0.00", "right"),   # 金额（不含税）
        ("General", "center"),   # 税率
        ("#,##0.00", "right"),   # 税额
        ("#,##0.00", "right"),   # 价税合计
        ("#,##0.00", "right"),   # 可抵扣税额
        ("General", "left"),
        ("General", "center"),
        ("General", "left"),
    ]

    def __init__(self, taxpayer_type):
        self.taxpayer_type = taxpayer_type

    def _write_header(self, ws, headers):
        r = self._styles
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = r["HEADER_FONT"]
            cell.fill = r["HEADER_FILL"]
            cell.alignment = r["HEADER_ALIGN"]
            cell.border = r["THIN_BORDER"]

    def _write_row(self, ws, row_idx, row_data, fmt_align, bold=False):
        r = self._styles
        font = r["BOLD_FONT"] if bold else r["NORMAL_FONT"]
        for col_idx, (val, (num_fmt, align)) in enumerate(zip(row_data, fmt_align), 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font
            cell.number_format = num_fmt
            cell.alignment = self._Alignment(horizontal=align, vertical="center")
            cell.border = r["THIN_BORDER"]

    def _set_widths(self, ws, widths):
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[self._openpyxl_utils.get_column_letter(i)].width = w

    def _build_general_sheets(self, wb, records):
        r = self._styles
        # ---- Sheet 1: 发票汇总 ----
        ws = wb.active
        ws.title = "发票汇总"
        headers = self.GENERAL_HEADERS
        self._write_header(ws, headers)
        self._set_widths(ws, self.GENERAL_WIDTHS)
        for i, rec in enumerate(records):
            row_data = [
                rec.invoice_type, rec.invoice_number, rec.invoice_date,
                rec.seller_name, rec.item_name,
                round(rec.amount_no_tax, 2), rec.tax_rate,
                round(rec.tax_amount, 2), round(rec.total_amount, 2),
                round(rec.deductible_tax, 2),
                "", "", rec.source_file,
            ]
            is_deduct = rec.deductible_tax > 0.005
            self._write_row(ws, i + 2, row_data, self.GENERAL_FMT_ALIGN, bold=is_deduct)
        # 合计行
        total_row = len(records) + 2
        total_nontax = sum(round(r.amount_no_tax, 2) for r in records)
        total_tax = sum(round(r.tax_amount, 2) for r in records)
        total_amt = sum(round(r.total_amount, 2) for r in records)
        total_deduct = sum(round(r.deductible_tax, 2) for r in records)
        total_data = [
            "合计", "", "", "", "",
            total_nontax, "", total_tax, total_amt, total_deduct,
            "", "", "",
        ]
        fmt_align_sum = [(nf, a) for nf, a in self.GENERAL_FMT_ALIGN]
        self._write_row(ws, total_row, total_data, fmt_align_sum, bold=True)
        # 合计行绿色填充
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=total_row, column=col_idx)
            cell.fill = r["SUMMARY_FILL"]
            cell.font = r["SUMMARY_FONT"]
        # 隐藏源文件列（第13列）
        ws.column_dimensions[self._openpyxl_utils.get_column_letter(len(headers))].hidden = True

        # ---- Sheet 2: 航空行程单明细 ----
        ws2 = wb.create_sheet("航空行程单明细")
        air_records = [rec for rec in records if rec.invoice_category and "航空" in (rec.invoice_category.name if hasattr(rec.invoice_category, 'name') else str(rec.invoice_category))]
        if not air_records:
            ws2.cell(row=1, column=1, value="无航空行程单数据")
            ws2.cell(row=1, column=1).font = r["NORMAL_FONT"]
        else:
            air_headers = ["序号", "开票日期", "乘机人", "航空公司", "航程", "金额（不含税）", "税额", "价税合计", "可抵扣税额"]
            self._write_header(ws2, air_headers)
            air_widths = [6, 16, 18, 20, 36, 18, 14, 18, 18]
            self._set_widths(ws2, air_widths)
            for i, rec in enumerate(air_records):
                order = i + 1
                raw = rec.raw_data or {}
                passenger = raw.get("passenger", "")
                airline = raw.get("airline_name", "")
                route = raw.get("route", "")
                row_data = [
                    order, rec.invoice_date, passenger, airline, route,
                    round(rec.amount_no_tax, 2), round(rec.tax_amount, 2),
                    round(rec.total_amount, 2), round(rec.deductible_tax, 2),
                ]
                air_fmt = [
                    ("General", "center"), ("General", "center"),
                    ("General", "center"), ("General", "center"),
                    ("General", "left"),
                    ("#,##0.00", "right"), ("#,##0.00", "right"),
                    ("#,##0.00", "right"), ("#,##0.00", "right"),
                ]
                self._write_row(ws2, i + 2, row_data, air_fmt, bold=rec.deductible_tax > 0.005)

        # ---- Sheet 3: 抵扣汇总 ----
        ws3 = wb.create_sheet("抵扣汇总")
        deduct_headers = ["序号", "发票类型", "发票号码", "开票日期", "销售方名称", "项目名称", "可抵扣税额", "原因"]
        self._write_header(ws3, deduct_headers)
        deduct_widths = [6, 18, 22, 16, 38, 32, 16, 30]
        self._set_widths(ws3, deduct_widths)
        deduct_records = [rec for rec in records if rec.deductible_tax > 0.005]
        for i, rec in enumerate(deduct_records):
            row_data = [
                i + 1, rec.invoice_type, rec.invoice_number,
                rec.invoice_date, rec.seller_name, rec.item_name,
                round(rec.deductible_tax, 2), rec.deductible_reason or "",
            ]
            deduct_fmt = [
                ("General", "center"), ("General", "center"),
                ("General", "center"), ("General", "center"),
                ("General", "left"), ("General", "left"),
                ("#,##0.00", "right"), ("General", "left"),
            ]
            self._write_row(ws3, i + 2, row_data, deduct_fmt)
        # 抵扣合计
        if deduct_records:
            d_total = sum(round(r.deductible_tax, 2) for r in deduct_records)
            d_row = len(deduct_records) + 2
            d_row_data = ["合计", "", "", "", "", "", d_total, ""]
            d_fmt_sum = [(nf, a) for nf, a in deduct_fmt]
            self._write_row(ws3, d_row, d_row_data, d_fmt_sum, bold=True)
            for col_idx in range(1, len(deduct_headers) + 1):
                cell = ws3.cell(row=d_row, column=col_idx)
                cell.fill = r["SUMMARY_FILL"]
                cell.font = r["SUMMARY_FONT"]

        # ---- Sheet 4: 费用归类汇总 ----
        ws4 = wb.create_sheet("发票汇总-费用归类")
        from collections import OrderedDict
        cat_pool = OrderedDict()
        for rec in records:
            key = (rec.item_name.strip(), rec.seller_name.strip())
            cur = cat_pool.get(key, {"item_name": rec.item_name.strip(), "seller": rec.seller_name.strip(),
                                      "count": 0, "nontax": 0.0, "tax": 0.0, "total": 0.0, "deduct": 0.0})
            cur["count"] += 1
            cur["nontax"] += round(rec.amount_no_tax, 2)
            cur["tax"] += round(rec.tax_amount, 2)
            cur["total"] += round(rec.total_amount, 2)
            cur["deduct"] += round(rec.deductible_tax, 2)
            cat_pool[key] = cur
        cat_headers = ["项目名称", "销售方名称", "张数", "金额（不含税）", "税额", "价税合计", "可抵扣税额"]
        cat_widths = [32, 38, 8, 18, 14, 18, 18]
        self._write_header(ws4, cat_headers)
        self._set_widths(ws4, cat_widths)
        cat_fmt = [
            ("General", "left"), ("General", "left"),
            ("General", "center"),
            ("#,##0.00", "right"), ("#,##0.00", "right"),
            ("#,##0.00", "right"), ("#,##0.00", "right"),
        ]
        cat_total_dict = {"count": 0, "nontax": 0.0, "tax": 0.0, "total": 0.0, "deduct": 0.0}
        for i, (key, cur) in enumerate(cat_pool.items()):
            row_data = [cur["item_name"], cur["seller"], cur["count"],
                        cur["nontax"], cur["tax"], cur["total"], cur["deduct"]]
            self._write_row(ws4, i + 2, row_data, cat_fmt)
            cat_total_dict["count"] += cur["count"]
            cat_total_dict["nontax"] += cur["nontax"]
            cat_total_dict["tax"] += cur["tax"]
            cat_total_dict["total"] += cur["total"]
            cat_total_dict["deduct"] += cur["deduct"]
        # 费用归类合计行
        cat_sum_row = len(cat_pool) + 2
        cat_sum_data = ["合计", "", cat_total_dict["count"],
                        round(cat_total_dict["nontax"], 2), round(cat_total_dict["tax"], 2),
                        round(cat_total_dict["total"], 2), round(cat_total_dict["deduct"], 2)]
        self._write_row(ws4, cat_sum_row, cat_sum_data, cat_fmt, bold=True)
        for col_idx in range(1, len(cat_headers) + 1):
            cell = ws4.cell(row=cat_sum_row, column=col_idx)
            cell.fill = r["SUMMARY_FILL"]
            cell.font = r["SUMMARY_FONT"]

    def _build_small_sheets(self, wb, records):
        r = self._styles
        # ---- Sheet 1: 发票明细 ----
        ws = wb.active
        ws.title = "发票明细"
        self._write_header(ws, self.SMALL_HEADERS)
        self._set_widths(ws, self.SMALL_WIDTHS)
        for i, rec in enumerate(records):
            row_data = [
                i + 1, rec.invoice_type, rec.invoice_number,
                rec.invoice_date, rec.seller_name, rec.item_name,
                round(rec.total_amount, 2),
            ]
            self._write_row(ws, i + 2, row_data, self.SMALL_FMT_ALIGN)
        # 合计行
        total_row = len(records) + 2
        total_amt = sum(round(r.total_amount, 2) for r in records)
        total_data = ["合计", "", "", "", "", "", total_amt]
        fmts = [(nf, a) for nf, a in self.SMALL_FMT_ALIGN]
        self._write_row(ws, total_row, total_data, fmts, bold=True)
        for col_idx in range(1, len(self.SMALL_HEADERS) + 1):
            cell = ws.cell(row=total_row, column=col_idx)
            cell.fill = r["SUMMARY_FILL"]
            cell.font = r["SUMMARY_FONT"]

        # ---- Sheet 2: 费用归类汇总 ----
        ws2 = wb.create_sheet("发票汇总-费用归类")
        from collections import OrderedDict
        cat_pool = OrderedDict()
        for rec in records:
            key = (rec.item_name.strip(), rec.seller_name.strip())
            cur = cat_pool.get(key, {"item_name": rec.item_name.strip(), "seller": rec.seller_name.strip(),
                                      "count": 0, "total": 0.0})
            cur["count"] += 1
            cur["total"] += round(rec.total_amount, 2)
            cat_pool[key] = cur
        cat_headers = ["项目名称", "销售方名称", "张数", "价税合计"]
        cat_widths = [32, 38, 8, 16]
        self._write_header(ws2, cat_headers)
        self._set_widths(ws2, cat_widths)
        cat_fmt = [
            ("General", "left"), ("General", "left"),
            ("General", "center"), ("#,##0.00", "right"),
        ]
        cat_total = {"count": 0, "total": 0.0}
        for i, (key, cur) in enumerate(cat_pool.items()):
            row_data = [cur["item_name"], cur["seller"], cur["count"], cur["total"]]
            self._write_row(ws2, i + 2, row_data, cat_fmt)
            cat_total["count"] += cur["count"]
            cat_total["total"] += cur["total"]
        # 合计行
        cat_sum_row = len(cat_pool) + 2
        cat_sum_data = ["合计", "", cat_total["count"], round(cat_total["total"], 2)]
        self._write_row(ws2, cat_sum_row, cat_sum_data, cat_fmt, bold=True)
        for col_idx in range(1, len(cat_headers) + 1):
            cell = ws2.cell(row=cat_sum_row, column=col_idx)
            cell.fill = r["SUMMARY_FILL"]
            cell.font = r["SUMMARY_FONT"]

    def export(self, records: list, output_path: str) -> str:
        """导出 Excel"""
        self._ensure_styles()
        wb = self._openpyxl.Workbook()

        if self.taxpayer_type.value == "general":
            self._build_general_sheets(wb, records)
        else:
            self._build_small_sheets(wb, records)

        wb.save(output_path)
        return str(output_path)
