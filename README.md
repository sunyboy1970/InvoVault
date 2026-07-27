# 🧾 InvoVault 发票宝 — 电子发票智能提取工具

**中文电子发票 → 结构化 Excel，一站式搞定。**

InvoVault 是一款面向中国会计从业人员的桌面端工具，专门用于处理员工报销场景下的大量电子发票。支持 PDF / OFD 双格式，覆盖现行中国税收法规下全部常见发票类型，自动识别、提取关键字段并按"一般纳税人"/"小规模纳税人"双模式输出标准化 Excel。

---

## 功能特性

### 📄 多格式全覆盖
- **PDF** 电子发票（三引擎智能回退：pdftotext → PyMuPDF → 视觉大模型）
- **OFD** 电子发票（原生 XBRL 结构化数据提取 + 版面文本回退）

### 🏷️ 支持 11+ 发票类型

| 类型 | 说明 |
|:---|:---|
| 增值税专用发票 | 国家税务总局标准版 |
| 增值税普通发票 | 含电子普通发票 |
| 全面数字化的电子发票 | 数电票 / 全电发票 |
| 铁路电子客票 | 12306 电子客票（PDF/OFD） |
| 航空运输电子客票行程单 | 民航电子行程单 |
| 高速公路通行费发票 | ETC 通行费电子发票 |
| 网约车电子发票 | 滴滴/高德等平台 |
| 机动车销售统一发票 | 机动车购置发票 |
| 海关进口增值税专用缴款书 | 海关缴款书 |
| 二手车销售统一发票 | 二手车交易发票 |
| 通用电子发票 / 区块链发票 | 其他合规电子发票 |

### 👥 双纳税人模式

一键切换，自动适配输出字段：

| 输出字段 | 小规模纳税人 | 一般纳税人 |
|:---------|:-----------:|:---------:|
| 序号 | ✅ | ✅ |
| 发票类型 | ✅ | ✅ |
| 发票号码 | ✅ | ✅ |
| 开票日期 | ✅ | ✅ |
| 销售方名称 | ✅ | ✅ |
| 项目名称 | ✅ | ✅ |
| 金额(不含税) | — | ✅ |
| 税率 | — | ✅ |
| 税额 | — | ✅ |
| 价税合计 | ✅ | ✅ |
| 可抵扣税额 | — | ✅ |

- ✅ **可抵扣税额**根据 2026 年最新增值税法规自动判定计算
- ✅ **可抵扣行自动加粗**显示，一眼识别
- ✅ 金额列千分位符 + 保留两位小数 + 水平居右
- ✅ 税率列水平居中
- ✅ 按项目名称+销售方名称排序

### 📊 费用分类与多工作表

- 自动按**费用类别**分类（交通费、办公费、差旅费、福利费等）
- 一般纳税人模式：4 张工作表（抵扣明细、不抵扣明细、费用归类汇总、合计）
- 小规模纳税人模式：2 张工作表（发票明细、费用归类汇总）
- 分类汇总行绿色背景（E2EFDA）区分

### 🖥️ 图形化界面

- **PyQt5** 现代界面，发票文件夹拖放/浏览
- 提取进度实时显示，每张发票处理完后立即展示
- **双击发票行**右侧滑出发票图片预览，支持自适应缩放
- 同文件夹去重处理，避免重复发票

### ⚡ 性能优化

- 三引擎自动回退，准确率最大化
- 线程池并发处理，253 张发票约 4 秒完成
- 文件哈希增量缓存，重复扫描秒级返回
- 延迟加载策略，启动仅 53ms（常规方式约 469ms）

---

## 快速开始

### 下载预编译版本

| 平台 | 下载 | 说明 |
|:---|:---|:---|
| **macOS** | [InvoVault.dmg]() | macOS 10.15+，Intel / Apple Silicon |
| **Windows** | [InvoVault-Windows.zip]() | Windows 10 / 11，x64 |

> 从 [GitHub Actions](https://github.com/sunyboy1970/InvoVault/actions) 下载最新构建产物。
>
> Windows 首次运行如遇安全提示，点击"更多信息 → 仍要运行"即可。

### 从源码运行

```bash
git clone git@github.com:sunyboy1970/InvoVault.git
cd InvoVault

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 使用流程

1. 启动程序，点击 **浏览** 选择含发票 PDF/OFD 的文件夹
2. 选择 **纳税人类型**（一般纳税人 / 小规模纳税人）
3. 可选：指定输出路径（默认在发票文件夹同级生成）
4. 点击 **开始提取**，进度条实时反馈
5. 处理完成后：
   - 左侧表格显示所有提取结果
   - **双击行**可预览对应发票图片
   - 点击 **导出 Excel** 生成结构化报表
   - 点击 **打开文件夹** 直达输出位置

---

## 架构设计

```
InvoVault/
├── main.py                     # 入口 + Windows 离屏渲染修复
├── requirements.txt            # Python 依赖
│
├── core/                       # 核心逻辑
│   ├── pipeline.py             # 批量处理流水线（去重→并发→缓存→导出）
│   ├── pdf_parser.py           # PDF 三引擎解析器
│   ├── ofd_parser.py           # OFD 原生解析器（XBRL + 版面文本）
│   ├── excel_exporter.py       # Excel 多工作表导出
│   ├── tax_rules.py            # 2026 增值税抵扣规则引擎
│   ├── category_mapper.py      # 费用类别映射
│   └── models.py               # 数据模型（InvoiceRecord 等）
│
├── core/extractors/            # 各类发票专用提取器
│   ├── base.py                 # 提取器基类 + 注册机制
│   ├── vat_special.py          # 增值税专用发票
│   ├── vat_normal.py           # 增值税普通发票
│   ├── railway.py              # 铁路电子客票
│   ├── air.py                  # 航空行程单
│   ├── toll.py                 # 高速通行费发票
│   ├── ride_hailing.py         # 网约车电子发票
│   ├── vehicle_sales.py        # 机动车销售发票
│   ├── customs.py              # 海关缴款书
│   └── others.py               # 其他发票（数电票/区块链等）
│
├── gui/                        # 图形界面
│   ├── main_window.py          # 主窗口
│   ├── invoice_table.py        # 发票数据表格
│   ├── preview_pane.py         # 发票预览面板
│   ├── worker.py               # 后台处理线程
│   └── components/             # 子组件
│       ├── file_drop_zone.py   # 文件拖放区域
│       ├── settings_panel.py   # 设置面板
│       ├── notifications.py    # 通知组件
│       └── misc.py             # 杂项组件
│
├── fapiaobao.spec              # macOS PyInstaller 配置
├── fapiaobao_win.spec          # Windows PyInstaller 配置
├── fapiaobao.icns              # macOS 应用图标
├── fapiaobao.ico               # Windows 应用图标
└── .github/workflows/
    └── build-windows.yml       # GitHub Actions 自动构建
```

### 核心流程

```
发票文件夹 (PDF/OFD)
    │
    ├── 去重扫描 (文件哈希 / 发票号码)
    │
    ├── 并发提取 (ThreadPoolExecutor × 4)
    │   ├── PDF → pdftotext 版面提取
    │   │     └─ 失败 → PyMuPDF sort=True
    │   │           └─ 失败 → GLM-4V-Flash 视觉 AI
    │   ├── OFD → XBRL 结构化数据 / 版面文本
    │   └── 缓存检查 (SHA256 哈希)
    │
    ├── 智能判定
    │   ├── 发票类型识别 (正则 + 特征字段)
    │   ├── 纳税人模式适配字段
    │   └── 可抵扣税额计算 (2026 增值税法规)
    │
    └── 输出 Excel
        ├── 一般纳税人 (4 工作表) / 小规模纳税人 (2 工作表)
        ├── 千分位 / 居右 / 加粗 / 绿色汇总行
        └── 费用类别归类 + 分类小计
```

---

## 技术栈

| 组件 | 技术 |
|:---|:---|
| 语言 | Python 3.10+ |
| GUI 框架 | PyQt5 |
| PDF 解析 | PyMuPDF (fitz)、pdftotext (poppler) |
| OFD 解析 | 原生 XML / XBRL 解析 |
| Excel 输出 | openpyxl |
| 视觉 AI 回退 | GLM-4V-Flash（智谱 API） |
| 打包分发 | PyInstaller (onedir 模式) |
| CI/CD | GitHub Actions (Windows 自动构建) |
| 图标 | 多尺寸 ICO + ICNS，透明圆角设计 |

---

## 构建与打包

### macOS

```bash
# 确保虚拟环境已激活
pip install pyinstaller
pyinstaller fapiaobao.spec
# 输出: dist/InvoVault.app
```

### Windows

```bash
# 在 Windows 环境或通过 GitHub Actions
pip install pyinstaller
pyinstaller fapiaobao_win.spec
# 输出: dist/InvoVault/
```

> Windows 交叉打包从 macOS 不可行，已配置 GitHub Actions CI 自动构建。
> 每次推送至 `main` 分支自动触发构建，产物上传至 Actions Artifacts。

---

## 许可证

本项目仅供会计从业人员学习与工作效率提升使用。

**⚠️ 注意**：发票数据处理涉及企业财务信息，请遵守相关法律法规，确保数据安全与合规使用。

---

## 致谢

- 感谢所有提供发票样本用于测试的合作伙伴
- 感谢 PyMuPDF、PyQt5、openpyxl 等开源项目的卓越贡献
- 特别感谢 [Nous Research Hermes Agent](https://hermes-agent.nousresearch.com) 提供 AI 辅助开发支持
