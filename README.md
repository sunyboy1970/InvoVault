# 发票提取工具 - Invoice Extractor

> 中国电子发票批量识别提取工具，支持 PDF/OFD 双格式，小规模/一般纳税人双模式，GUI 界面操作，一键导出 Excel。

## ✨ 功能特性

### 📄 多格式支持
- **PDF**：三引擎回退（pdftotext → PyMuPDF sort=True → 视觉大模型 GLM-4V-Flash）
- **OFD**：原生 ZIP+XML 解析，XBRL 结构化字段提取

### 🧾 全票种覆盖（11 大类）
| 发票类型 | 识别器 | 抵扣规则 |
|---------|--------|----------|
| 增值税专用发票 | VatSpecialExtractor | 全额抵扣 = 票面税额 |
| 增值税普通发票 | VatNormalExtractor | 通行费/住宿/餐饮分类 |
| 铁路电子客票 | RailwayExtractor | 9% 计算抵扣 |
| 航空运输电子客票行程单 | AirExtractor | (票价+燃油)÷1.09×9% |
| 通行费电子发票 | TollExtractor | 票面税额全额抵扣 |
| 网约车电子发票 | RideHailingExtractor | **2026新规：不可抵扣** |
| 机动车销售统一发票 | VehicleSalesExtractor | 不可抵扣 |
| 海关进口增值税专用缴款书 | CustomsImportExtractor | 全额抵扣 |
| 农产品收购发票 | AgriculturalProductExtractor | 9%/10% 扣除率计算 |
| 代扣代缴税款专用发票 | WithholdingTaxExtractor | 全额抵扣 |
| 桥闸费/公路水路客票 | TollBridgeWaterwayExtractor | 不可抵扣/免税 |

### 🎯 双纳税人模式
| 模式 | 输出字段 | Sheet 数 |
|------|---------|----------|
| **小规模纳税人** | 序号、发票号码、开票日期、销售方名称、项目名称、价税合计 | 2 (发票明细、发票汇总-费用归类) |
| **一般纳税人** | 序号、发票类型、发票号码、开票日期、销售方名称、项目名称、金额(不含税)、税率、税额、价税合计、可抵扣税额、源文件 | 4 (发票汇总、航空行程单明细、抵扣汇总、发票汇总-费用归类) |

### 📊 Excel 精确复刻样本格式
- ✅ 金额列：千分位 `#,##0.00` 右对齐
- ✅ 税率列：字符串 `"9%"` 居中
- ✅ 序号/号码/日期/税率：居中
- ✅ 可抵扣行：整行加粗
- ✅ 合计行：`E2EFDA` 背景、加粗、前缀 `"  【科目】小计 共N笔"`
- ✅ 源文件列（L列）：隐藏
- ✅ 排序：项目名称 + 销售方名称

### 🖥️ 现代化 GUI
- **虚拟化表格**：QTableView + QAbstractTableModel，10万行流畅
- **右侧预览面板**：PDF.js / 图片 / OFD 提示，缩放、翻页、打印
- **双击/空格预览**，Enter 打开文件夹，Esc 关闭预览
- **进度条实时更新**，支持取消
- **浅色/深色主题**，QSS 样式系统

## 🚀 快速开始

### 环境要求
- Python 3.9+
- macOS 10.15+ / Windows 10+ / Linux
- 系统依赖：`pdftotext` (poppler-utils)

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
# 下载 poppler 二进制包，将 pdftotext.exe 加入 PATH
```

### 安装运行
```bash
# 克隆/进入项目
cd invoice-extractor-gui

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"

# 运行
python -m gui.main_window
# 或
invoice-extractor
```

### 打包分发
```bash
# 安装 PyInstaller
pip install pyinstaller

# 单文件打包
pyinstaller invoice_extractor.spec --clean --noconfirm

# 产物
# macOS: dist/InvoiceExtractor.app
# Windows: dist/InvoiceExtractor.exe
# Linux: dist/InvoiceExtractor
```

## 📁 项目结构

```
invoice-extractor-gui/
├── config.yaml                 # 配置文件
├── pyproject.toml              # 依赖管理
├── invoice_extractor.spec      # PyInstaller 打包配置
├── README.md
├── core/                       # 核心业务层（零 GUI 依赖）
│   ├── models.py               # 数据模型
│   ├── tax_rules.py            # 2026 抵扣规则引擎
│   ├── excel_exporter.py       # 多 Sheet Excel 导出
│   ├── category_mapper.py      # 费用归类映射
│   ├── pipeline.py             # 批量流水线
│   ├── pdf_parser.py           # PDF 三引擎解析
│   ├── ofd_parser.py           # OFD XBRL 解析
│   └── extractors/             # 11 个票种识别器
│       ├── base.py
│       ├── vat_special.py
│       ├── vat_normal.py
│       ├── railway.py
│       ├── air.py
│       ├── toll.py
│       ├── ride_hailing.py
│       ├── vehicle_sales.py
│       ├── customs.py
│       └── others.py
└── gui/                        # GUI 表现层
    ├── main_window.py          # 主窗口
    ├── invoice_table.py        # 虚拟化表格
    ├── preview_pane.py         # 预览面板
    ├── worker.py               # 后台线程
    └── components/             # 组件库
        ├── theme.py
        ├── buttons.py
        └── ...
```

## ⚙️ 配置说明

编辑 `config.yaml`：

```yaml
vision:
  enabled: true
  api_key: "your-glm-4v-flash-key"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  model: "glm-4v-flash"

processing:
  max_workers: 4
  skip_duplicates: true

taxpayer:
  default_type: "general"  # general / small_scale
```

## 🔧 开发指南

### 新增票种识别器
```python
# core/extractors/new_type.py
from core.extractors.base import BaseExtractor, InvoiceRawData

class NewTypeExtractor(BaseExtractor):
    SUPPORTED_TYPES = ["新票种名称"]
    PRIORITY = 15  # 优先级越小越优先

    def can_handle(self, file_path, preview_text):
        return "新票种关键字" in preview_text

    def extract(self, file_path, text, xbrl_data=None):
        # 解析逻辑
        return InvoiceRawData(...)

# 自动注册
from core.extractors.base import register_extractor
register_extractor(NewTypeExtractor())
```

### 费用归类规则
编辑 `core/category_mapper.py` 中的 `KEYWORD_MAP`，按关键词长度降序匹配。

### 运行测试
```bash
pytest tests/ -v --cov=core
```

## 📋 2026 增值税抵扣规则速查

| 发票类型 | 可抵扣 | 计算方式 | 备注 |
|---------|-------|----------|------|
| 专用发票 | ✅ | 票面税额 | 全额抵扣 |
| 普通发票-通行费 | ✅ | 票面税额 | 9%/3% |
| 普通发票-网约车 | ❌ | 0 | **2026新规** |
| 铁路客票 | ✅ | 价税合计÷1.09×9% | 旅客身份证号后4位 |
| 航空行程单 | ✅ | (票价+燃油)÷1.09×9% | 民航基金不抵扣 |
| 机动车销售 | ❌ | 0 | 车辆购置税单独处理 |
| 海关缴款书 | ✅ | 票面税额 | 进口环节 |
| 农产品收购 | ✅ | 采购金额×扣除率 | 9%/10% |
| 代扣代缴 | ✅ | 票面税额 | 个税手续费返还等 |

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🤝 贡献

欢迎 PR 和 Issue！

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## ⚠️ 免责声明

本工具仅供会计人员辅助处理发票数据，**不替代专业税务判断**。抵扣规则依据 2026 年最新增值税法规实现，具体业务请以税务局最终认定为准。使用前请务必核对输出结果。