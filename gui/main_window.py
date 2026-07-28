"""主窗口：发票提取工具的主界面"""
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QProgressBar, QRadioButton, QButtonGroup,
    QMessageBox, QSplitter, QStatusBar, QFrame,
    QApplication,
)
from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtGui import QIcon, QFont, QDesktopServices

from gui.invoice_table import InvoiceTable
from gui.preview_pane import PreviewPane
from gui.worker import InvoiceWorker

APP_NAME = "InvoVault"


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.records = []
        self.last_export_path = None
        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1200, 700)
        self.setStyleSheet("""
            QMainWindow { background: #f0f2f5; }
            QPushButton {
                padding: 6px 16px; border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit {
                padding: 5px 8px; border: 1px solid #ccc;
                border-radius: 4px; font-size: 13px;
            }
            QRadioButton { font-size: 13px; spacing: 8px; }
        """)

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧主区域
        left_panel = QWidget()
        left_panel.setMinimumWidth(450)  # 允许预览窗向右展开更大范围
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        # --- 顶部工具栏 ---
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame { background: white; border-radius: 8px;
                     border: 1px solid #d0d7de; }
        """)
        tool_layout = QVBoxLayout(toolbar)
        tool_layout.setContentsMargins(16, 12, 16, 12)
        tool_layout.setSpacing(10)

        # 第一行：输入文件夹
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("📂 发票文件夹:"))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("选择包含 PDF/OFD 发票的文件夹...")
        self.folder_edit.setToolTip("支持直接粘贴或拖入文件夹路径")
        row1.addWidget(self.folder_edit, stretch=1)
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse_folder)
        btn_browse.setStyleSheet("background: #3498db; color: white;")
        row1.addWidget(btn_browse)
        tool_layout.addLayout(row1)

        # 第二行：纳税人类型 + 输出文件夹
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("纳税人类型:"))
        self.tax_group = QButtonGroup(self)
        self.rb_general = QRadioButton("一般纳税人")
        self.rb_small = QRadioButton("小规模纳税人")
        self.rb_general.setChecked(True)
        self.tax_group.addButton(self.rb_general, 1)
        self.tax_group.addButton(self.rb_small, 2)
        row2.addWidget(self.rb_general)
        row2.addWidget(self.rb_small)
        row2.addSpacing(20)

        row2.addWidget(QLabel("📁 输出到:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("默认: 发票文件夹同级目录")
        row2.addWidget(self.output_edit, stretch=1)
        btn_out = QPushButton("选择...")
        btn_out.clicked.connect(self._browse_output)
        btn_out.setStyleSheet("background: #95a5a6; color: white;")
        row2.addWidget(btn_out)
        tool_layout.addLayout(row2)

        # 第三行：操作按钮 + 汇总信息
        row3 = QHBoxLayout()
        self.btn_process = QPushButton("▶ 开始提取")
        self.btn_process.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white; font-weight: bold;
                padding: 8px 28px; font-size: 15px; border-radius: 4px;
            }
            QPushButton:hover { background: #2ecc71; }
            QPushButton:disabled { background: #bdc3c7; }
        """)
        self.btn_process.clicked.connect(self._start_process)
        row3.addWidget(self.btn_process)

        self.btn_export = QPushButton("💾 导出 Excel")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: #2980b9; color: white; font-weight: bold;
                padding: 8px 20px; font-size: 14px; border-radius: 4px;
            }
            QPushButton:hover { background: #3498db; }
            QPushButton:disabled { background: #bdc3c7; }
        """)
        self.btn_export.clicked.connect(self._export_excel)
        self.btn_export.setEnabled(False)
        row3.addWidget(self.btn_export)

        # 汇总信息（右上角）
        self.summary_label = QLabel("就绪")
        self.summary_label.setStyleSheet("""
            QLabel {
                color: #2c3e50; font-size: 14px; font-weight: bold;
                padding: 6px 14px; background: #eaf2f8;
                border-radius: 4px; border: 1px solid #d4e6f1;
            }
        """)
        row3.addStretch()
        row3.addWidget(self.summary_label)
        tool_layout.addLayout(row3)

        left_layout.addWidget(toolbar)

        # --- 进度条 ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc; border-radius: 6px;
                text-align: center; height: 22px;
            }
            QProgressBar::chunk { background: #27ae60; border-radius: 6px; }
        """)
        left_layout.addWidget(self.progress_bar)

        # --- 表格 ---
        self.table = InvoiceTable("general")
        self.table.row_double_clicked.connect(self._show_preview)
        left_layout.addWidget(self.table, stretch=1)

        # --- 状态栏（含导出路径链接区）---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 右侧预览面板（可随 QSplitter 自由缩放）
        self.preview = PreviewPane()
        self.preview.btn_close.clicked.connect(self._hide_preview)

        # 用 QSplitter 组合左右（3:1 初始比例）
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([900, 0])  # 初始预览隐藏

        # 加宽分隔条手柄（整条竖线可拖拽），鼠标悬停变色提示
        self.splitter.setHandleWidth(8)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: #bdc3c7;
                border: none;
                width: 8px;
            }
            QSplitter::handle:hover {
                background: #3498db;
            }
            QSplitter::handle:pressed {
                background: #2980b9;
            }
        """)
        main_layout.addWidget(self.splitter)

    def _setup_menu(self):
        from PyQt5.QtWidgets import QAction
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件(&F)")
        act_export = QAction("导出 Excel(&E)", self)
        act_export.triggered.connect(self._export_excel)
        file_menu.addAction(act_export)
        file_menu.addSeparator()
        act_open = QAction("打开输出文件夹(&O)", self)
        act_open.triggered.connect(self._open_output_folder)
        file_menu.addAction(act_open)
        file_menu.addSeparator()
        act_exit = QAction("退出(&Q)", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

    def _update_summary(self):
        """更新右上角汇总信息"""
        if not self.records:
            self.summary_label.setText("就绪")
            return
        total = sum(r.total_amount for r in self.records)
        # 一般纳税人显示税额，小规模不显示
        if self.rb_general.isChecked():
            tax = sum(r.tax_amount for r in self.records)
            deduct = sum(r.deductible_tax for r in self.records)
            self.summary_label.setText(
                f"📊 共 {len(self.records)} 张  ·  "
                f"金额 ¥{total:,.2f}  ·  "
                f"税额 ¥{tax:,.2f}  ·  "
                f"可抵扣 ¥{deduct:,.2f}")
        else:
            self.summary_label.setText(
                f"📊 共 {len(self.records)} 张  ·  "
                f"金额 ¥{total:,.2f}")

    def _browse_folder(self):
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtCore import QDir
        dialog = QFileDialog(self, "选择发票文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        start_dir = self.folder_edit.text() or QDir.homePath()
        if QDir(start_dir).exists():
            dialog.setDirectory(start_dir)
        if dialog.exec_() == QFileDialog.Accepted:
            paths = dialog.selectedFiles()
            if paths:
                self.folder_edit.setText(paths[0])

    def _browse_output(self):
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtCore import QDir
        dialog = QFileDialog(self, "选择输出文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        start_dir = self.output_edit.text() or QDir.homePath()
        if QDir(start_dir).exists():
            dialog.setDirectory(start_dir)
        if dialog.exec_() == QFileDialog.Accepted:
            paths = dialog.selectedFiles()
            if paths:
                self.output_edit.setText(paths[0])

    def _start_process(self):
        folder = self.folder_edit.text().strip()
        if not folder or not Path(folder).exists():
            QMessageBox.warning(self, "提示", "请先选择有效的发票文件夹")
            return

        tp = "general" if self.rb_general.isChecked() else "small"
        self.table.taxpayer_type = tp

        self.btn_process.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.last_export_path = None
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("正在扫描发票文件...")
        self.summary_label.setText("处理中...")

        self.worker = InvoiceWorker(folder, tp)
        self.worker.progress.connect(self._on_progress)
        self.worker.row_ready.connect(self._on_row)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(msg)

    def _on_row(self, record):
        pass

    def _on_finished(self, records):
        self.records = records
        self.table.set_records(records)
        self.btn_process.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._update_summary()
        self.status_bar.showMessage(f"提取完成：{len(records)} 张发票")

    def _on_error(self, err_msg):
        self.btn_process.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.summary_label.setText("处理出错")
        self.status_bar.showMessage("处理出错")
        QMessageBox.critical(self, "错误", f"处理出错:\n{err_msg[:500]}")

    def _export_excel(self):
        if not self.records:
            QMessageBox.warning(self, "提示", "没有数据可导出")
            return

        from core.models import TaxpayerType
        from core.excel_exporter import ExcelExporter

        folder = self.output_edit.text().strip() or Path(self.folder_edit.text())
        if not Path(folder).exists():
            folder = Path.home() / "Desktop"
        out_path = str(Path(folder) / f"发票提取结果_{len(self.records)}张.xlsx")

        tp = TaxpayerType.GENERAL if self.rb_general.isChecked() else TaxpayerType.SMALL_SCALE
        exporter = ExcelExporter(tp)
        result = exporter.export(self.records, out_path)

        self.last_export_path = result
        self.status_bar.showMessage(f"✅ 已导出：{result}")

        # 弹出含超链接的对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("导出成功")
        dlg.setMinimumWidth(500)
        layout = QVBoxLayout(dlg)

        msg = QLabel(f"✅ Excel 已成功导出\n共 {len(self.records)} 张发票")
        msg.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(msg)

        # 可点击的路径链接
        link = QLabel(f'<a href="file://{result}" style="font-size:13px;">📄 {result}</a>')
        link.setOpenExternalLinks(True)
        link.setWordWrap(True)
        link.setStyleSheet("padding: 10px; background: #f8f9fa; border-radius: 4px;")
        layout.addWidget(link)

        btn_row = QHBoxLayout()
        btn_open = QPushButton("📂 打开文件")
        btn_open.setStyleSheet("background: #27ae60; color: white; font-weight: bold; padding: 8px 20px;")
        btn_open.clicked.connect(lambda: (QDesktopServices.openUrl(QUrl.fromLocalFile(result)), dlg.accept()))
        btn_row.addWidget(btn_open)

        btn_open_folder = QPushButton("📁 打开文件夹")
        btn_open_folder.setStyleSheet("background: #3498db; color: white; padding: 8px 20px;")
        btn_open_folder.clicked.connect(
            lambda: (QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(result).parent))), dlg.accept()))
        btn_row.addWidget(btn_open_folder)

        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet("padding: 8px 20px;")
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.exec_()

    def _open_output_folder(self):
        """打开输出文件夹"""
        if self.last_export_path:
            folder = str(Path(self.last_export_path).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            folder = self.output_edit.text().strip() or self.folder_edit.text().strip()
            if folder and Path(folder).exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _show_preview(self, row, source_file):
        folder = self.folder_edit.text()
        file_path = str(Path(folder) / source_file)
        if not Path(file_path).exists():
            self.status_bar.showMessage(f"找不到文件: {source_file}")
            return

        rec = self.records[row] if row < len(self.records) else None
        info = ""
        if rec:
            info = (f"📄 {rec.invoice_type}\n"
                    f"🔢 {rec.invoice_number}\n"
                    f"🏢 {rec.seller_name}\n"
                    f"💰 ¥{rec.total_amount:,.2f}")
        self.preview.show_preview(file_path, info)

        # 展开预览面板，总和精确等于分隔器总宽，避免抖动
        total_w = self.splitter.width()
        if total_w > 0:
            preview_w = max(int(total_w * 0.35), 280)
            left_w = total_w - preview_w
            self.splitter.setSizes([left_w, preview_w])

    def _hide_preview(self):
        self.preview.hide_preview()
        total_w = self.splitter.width()
        if total_w > 0:
            self.splitter.setSizes([total_w, 0])
