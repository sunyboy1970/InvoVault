"""发票数据表格组件"""
from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont


class InvoiceTable(QTableWidget):
    """展示提取结果的表格组件"""

    row_double_clicked = pyqtSignal(int, str)  # row_index, source_file

    def __init__(self, taxpayer_type="general", parent=None):
        super().__init__(parent)
        self.taxpayer_type = taxpayer_type
        self._records = []
        self._setup_table()

    def _setup_table(self):
        self.setAlternatingRowColors(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(255, 255, 255))
        alt_color = QColor(245, 248, 252)
        self.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #d0d7de;
                font-size: 12px;
                alternate-background-color: {alt_color.name()};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QHeaderView::section {{
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 8px;
                border: 1px solid #34495e;
            }}
        """)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        self.cellDoubleClicked.connect(self._on_double_click)

    def set_records(self, records):
        """填入发票记录列表 + 末行合计"""
        self._records = records
        self.setSortingEnabled(False)

        bold_font = QFont()
        bold_font.setBold(True)

        if self.taxpayer_type == "general":
            headers = ["序号", "发票类型", "发票号码", "开票日期", "销售方名称",
                       "项目名称", "金额(不含税)", "税率", "税额", "价税合计",
                       "可抵扣税额"]
            data_cols = len(headers)
            self.setColumnCount(data_cols + 1)  # +1 隐藏源文件列
            self.setHorizontalHeaderLabels(headers)
            self.setRowCount(len(records) + 1)  # +1 合计行

            for i, rec in enumerate(records):
                is_deduct = rec.deductible_tax > 0.005
                font = bold_font if is_deduct else QFont()

                values = [
                    str(i + 1), rec.invoice_type, rec.invoice_number,
                    rec.invoice_date, rec.seller_name, rec.item_name,
                    f"{rec.amount_no_tax:,.2f}", rec.tax_rate,
                    f"{rec.tax_amount:,.2f}", f"{rec.total_amount:,.2f}",
                    f"{rec.deductible_tax:,.2f}",
                ]
                for col, val in enumerate(values):
                    item = QTableWidgetItem(val)
                    item.setFont(font)
                    if col in (6, 8, 9, 10):
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    elif col == 7:
                        item.setTextAlignment(Qt.AlignCenter)
                    else:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.setItem(i, col, item)

                # 隐藏列存源文件路径（最后一列）
                src_item = QTableWidgetItem(rec.source_file)
                self.setItem(i, data_cols, src_item)

            # 合计行
            sum_row = len(records)
            total_amt = sum(r.total_amount for r in records)
            total_tax = sum(r.tax_amount for r in records)
            total_deduct = sum(r.deductible_tax for r in records)
            sum_values = [
                "合计", "", "", "", "", "",
                f"{sum(r.amount_no_tax for r in records):,.2f}", "",
                f"{total_tax:,.2f}", f"{total_amt:,.2f}", f"{total_deduct:,.2f}",
            ]
            for col, val in enumerate(sum_values):
                item = QTableWidgetItem(val)
                item.setFont(bold_font)
                item.setBackground(QColor(226, 239, 218))  # 浅绿色 E2EFDA
                if col in (6, 8, 9, 10):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif col == 7:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.setItem(sum_row, col, item)

            # 隐藏源文件列（最后一列）
            self.setColumnHidden(data_cols, True)

        else:
            headers = ["序号", "发票类型", "发票号码", "开票日期", "销售方名称",
                       "项目名称", "价税合计"]
            data_cols = len(headers)
            self.setColumnCount(data_cols + 1)  # +1 隐藏源文件列
            self.setHorizontalHeaderLabels(headers)
            self.setRowCount(len(records) + 1)  # +1 合计行

            for i, rec in enumerate(records):
                values = [
                    str(i + 1), rec.invoice_type, rec.invoice_number,
                    rec.invoice_date, rec.seller_name, rec.item_name,
                    f"{rec.total_amount:,.2f}",
                ]
                for col, val in enumerate(values):
                    item = QTableWidgetItem(val)
                    if col == 6:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.setItem(i, col, item)

                # 隐藏列存源文件
                src_item = QTableWidgetItem(rec.source_file)
                self.setItem(i, data_cols, src_item)

            # 合计行
            sum_row = len(records)
            total_amt = sum(r.total_amount for r in records)
            sum_values = ["合计", "", "", "", "", "", f"{total_amt:,.2f}"]
            for col, val in enumerate(sum_values):
                item = QTableWidgetItem(val)
                item.setFont(bold_font)
                item.setBackground(QColor(226, 239, 218))
                if col == 6:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.setItem(sum_row, col, item)

            self.setColumnHidden(data_cols, True)

        self.setSortingEnabled(True)

        # 自动调整列宽
        header = self.horizontalHeader()
        for c in range(data_cols):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
            if header.sectionSize(c) > 300:
                header.setSectionResizeMode(c, QHeaderView.Stretch)

    def _on_double_click(self, row, col):
        """双击行触发预览（跳过合计行）"""
        if row >= len(self._records):
            return  # 合计行不触发预览
        data_cols = self.columnCount() - 1  # 源文件在最后一列
        src_item = self.item(row, data_cols)
        if src_item and src_item.text():
            self.row_double_clicked.emit(row, src_item.text())
