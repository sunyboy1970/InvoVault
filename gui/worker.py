"""后台处理线程：不阻塞UI的情况下处理发票"""
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

class InvoiceWorker(QThread):
    """发票处理后台线程"""
    progress = pyqtSignal(int, int, str)  # 当前, 总数, 状态消息
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    row_ready = pyqtSignal(object)  # 每张发票提取完毕立即发送

    def __init__(self, folder, taxpayer_type, vision_config=None):
        super().__init__()
        self.folder = folder
        self.taxpayer_type = taxpayer_type
        self.vision_config = vision_config or {"enabled": False}

    def run(self):
        try:
            from core.pipeline import process_invoices
            from core.models import TaxpayerType

            tp = TaxpayerType.GENERAL if self.taxpayer_type == "general" else TaxpayerType.SMALL_SCALE

            def on_progress(current, total, msg):
                self.progress.emit(current, total, msg)

            def on_row(record):
                self.row_ready.emit(record)

            records = process_invoices(
                folder=self.folder,
                taxpayer_type=tp,
                vision_config=self.vision_config,
                max_workers=4,
                progress_callback=on_progress,
                row_callback=on_row,
            )
            self.finished.emit(records)
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")
