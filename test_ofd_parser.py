"""Test script for OFD parser - run with: python test_ofd_parser.py"""
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from core.ofd_parser import parse_ofd, extract_xbrl_fields, OFDParser, OFDParseResult


def create_test_ofd() -> Path:
    """Create a minimal valid OFD file for testing"""
    tmpdir = Path(tempfile.mkdtemp())

    # OFD.xml
    ofd_xml = tmpdir / "OFD.xml"
    ofd_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<ofd:OFD xmlns:ofd="http://www.ofdspec.org/2016" Version="1.0">
  <ofd:DocBody>
    <ofd:DocRoot>Doc_0/Document.xml</ofd:DocRoot>
  </ofd:DocBody>
</ofd:OFD>""", encoding="utf-8")

    # Doc_0 directory
    doc_dir = tmpdir / "Doc_0"
    doc_dir.mkdir()

    # Document.xml
    doc_xml = doc_dir / "Document.xml"
    doc_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<ofd:Document xmlns:ofd="http://www.ofdspec.org/2016" xmlns:xlink="http://www.w3.org/1999/xlink">
  <ofd:CommonData>
    <ofd:MaxUnitID>100</ofd:MaxUnitID>
    <ofd:PageArea>
      <ofd:PhysicalBox>0 0 1000 1000</ofd:PhysicalBox>
    </ofd:PageArea>
  </ofd:CommonData>
  <ofd:Pages>
    <ofd:Page xlink:href="Pages/Page_0.xml" />
  </ofd:Pages>
</ofd:Document>""", encoding="utf-8")

    # Pages directory
    pages_dir = doc_dir / "Pages"
    pages_dir.mkdir()

    # Page_0.xml with text content
    page_xml = pages_dir / "Page_0.xml"
    page_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<ofd:Page xmlns:ofd="http://www.ofdspec.org/2016">
  <ofd:Content>
    <ofd:Layer>
      <ofd:TextObject>
        <ofd:TextCode c="发票代码: 012345678901" />
        <ofd:TextCode c="发票号码: 12345678" />
        <ofd:TextCode c="开票日期: 2024-01-15" />
        <ofd:TextCode c="销售方: 测试销售方有限公司" />
        <ofd:TextCode c="购买方: 测试购买方有限公司" />
        <ofd:TextCode c="价税合计: 113.00" />
        <ofd:TextCode c="税额: 13.00" />
      </ofd:TextObject>
    </ofd:Layer>
  </ofd:Content>
</ofd:Page>""", encoding="utf-8")

    # XBRL data in CustomData
    custom_dir = doc_dir / "CustomData"
    custom_dir.mkdir()
    xbrl_xml = custom_dir / "InvoiceData.xml"
    xbrl_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:fp="http://www.chinatax.gov.cn/dataspec/fapiao/">
  <context id="ctx1">
    <entity>
      <identifier scheme="http://www.chinatax.gov.cn/taxpayerid">91110000123456789X</identifier>
    </entity>
    <period>
      <instant>2024-01-15</instant>
    </period>
  </context>
  <fp:fpDm contextRef="ctx1">012345678901</fp:fpDm>
  <fp:fpHm contextRef="ctx1">12345678</fp:fpHm>
  <fp:kprq contextRef="ctx1">2024-01-15</fp:kprq>
  <fp:xfMc contextRef="ctx1">测试销售方有限公司</fp:xfMc>
  <fp:xfNsrsbh contextRef="ctx1">91110000123456789X</fp:xfNsrsbh>
  <fp:gfMc contextRef="ctx1">测试购买方有限公司</fp:gfMc>
  <fp:gfNsrsbh contextRef="ctx1">91310000987654321Y</fp:gfNsrsbh>
  <fp:jeHj contextRef="ctx1">113.00</fp:jeHj>
  <fp:seHj contextRef="ctx1">13.00</fp:seHj>
  <fp:bhsje contextRef="ctx1">100.00</fp:bhsje>
  <fp:sl contextRef="ctx1">13%</fp:sl>
  <fp:xmmc contextRef="ctx1">*货物*测试商品</fp:xmmc>
  <fp:ggxh contextRef="ctx1">规格型号</fp:ggxh>
  <fp:dw contextRef="ctx1">个</fp:dw>
  <fp:xmsl contextRef="ctx1">2</fp:xmsl>
  <fp:dj contextRef="ctx1">50.00</fp:dj>
  <fp:je contextRef="ctx1">100.00</fp:je>
  <fp:ssl contextRef="ctx1">13%</fp:ssl>
  <fp:se contextRef="ctx1">13.00</fp:se>
</xbrl>""", encoding="utf-8")

    # Create OFD zip
    ofd_path = tmpdir / "test_invoice.ofd"
    with zipfile.ZipFile(ofd_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in tmpdir.rglob("*"):
            if file_path.is_file() and file_path != ofd_path:
                arcname = file_path.relative_to(tmpdir)
                zf.write(file_path, arcname)

    return ofd_path


def test_parse_ofd():
    """Test parsing OFD file"""
    print("Creating test OFD...")
    ofd_path = create_test_ofd()

    print(f"Parsing: {ofd_path}")
    result = parse_ofd(ofd_path)

    print(f"Error: {result.get('error')}")
    print(f"Text length: {len(result.get('text', ''))}")
    print(f"Text: {result.get('text', '')[:200]}...")
    print(f"Pages: {result.get('pages')}")
    print(f"XBRL keys: {list(result.get('xbrl_data', {}).keys())[:20]}")

    # Test extract_xbrl_fields
    xbrl_data = result.get('xbrl_data', {})
    fields = extract_xbrl_fields(xbrl_data)
    print(f"\nExtracted fields:")
    for k, v in fields.items():
        if v:
            print(f"  {k}: {v}")

    # Cleanup
    import shutil
    shutil.rmtree(ofd_path.parent)

    assert not result.get('error'), f"Parse error: {result.get('error')}"
    assert result.get('text'), "No text extracted"
    assert '发票代码' in result.get('text', ''), "Text doesn't contain expected content"
    assert xbrl_data, "No XBRL data extracted"
    assert fields.get('invoice_code') == '012345678901', f"Wrong invoice code: {fields.get('invoice_code')}"
    assert fields.get('invoice_number') == '12345678', f"Wrong invoice number: {fields.get('invoice_number')}"
    assert fields.get('total_amount') == 113.0, f"Wrong total: {fields.get('total_amount')}"
    assert fields.get('items'), "No items extracted"

    print("\n✅ All tests passed!")


def test_extract_xbrl_fields_directly():
    """Test extract_xbrl_fields with direct dict input"""
    print("\nTesting extract_xbrl_fields directly...")

    test_xbrl = {
        'fpDm': '012345678901',
        'fpHm': '12345678',
        'kprq': '2024-01-15',
        'xfMc': '测试销售方有限公司',
        'xfNsrsbh': '91110000123456789X',
        'gfMc': '测试购买方有限公司',
        'gfNsrsbh': '91310000987654321Y',
        'jeHj': '113.00',
        'seHj': '13.00',
        'bhsje': '100.00',
        'sl': '13%',
        # Items
        'item_1:xmmc': '*货物*测试商品',
        'item_1:ggxh': '规格1',
        'item_1:dw': '个',
        'item_1:xmsl': '2',
        'item_1:dj': '50.00',
        'item_1:je': '100.00',
        'item_1:ssl': '13%',
        'item_1:se': '13.00',
    }

    fields = extract_xbrl_fields(test_xbrl)
    print(f"Fields extracted: {len(fields)}")
    assert fields.get('invoice_code') == '012345678901'
    assert fields.get('invoice_number') == '12345678'
    assert fields.get('total_amount') == 113.0
    assert fields.get('tax_amount') == 13.0
    assert fields.get('amount_no_tax') == 100.0
    assert fields.get('tax_rate') == '13%'
    assert fields.get('items'), "No items extracted"
    print("✅ Direct test passed!")


def test_tax_rate_parsing():
    """Test tax rate parsing"""
    from core.ofd_parser import _parse_tax_rate

    test_cases = [
        ("13%", "13%"),
        ("9%", "9%"),
        ("6%", "6%"),
        ("3%", "3%"),
        ("0.13", "13%"),
        (0.13, "13%"),
        (13, "13%"),
        ("", ""),
        (None, ""),
    ]

    for inp, expected in test_cases:
        result = _parse_tax_rate(inp)
        assert result == expected, f"_parse_tax_rate({inp!r}) = {result!r}, expected {expected!r}"

    print("✅ Tax rate parsing test passed!")


def test_date_parsing():
    """Test date parsing"""
    from core.ofd_parser import _parse_date

    test_cases = [
        ("2024-01-15", "2024-01-15"),
        ("2024/01/15", "2024-01-15"),
        ("2024年1月15日", "2024-01-15"),
        ("20240115", "2024-01-15"),
        ("", ""),
        (None, ""),
    ]

    for inp, expected in test_cases:
        result = _parse_date(inp)
        assert result == expected, f"_parse_date({inp!r}) = {result!r}, expected {expected!r}"

    print("✅ Date parsing test passed!")


def test_float_conversion():
    """Test float conversion"""
    from core.ofd_parser import _to_float

    test_cases = [
        ("100.00", 100.0),
        ("1,000.00", 1000.0),
        ("￥100.00", 100.0),
        ("¥1,000.00", 1000.0),
        (100, 100.0),
        (100.5, 100.5),
        ("", 0.0),
        (None, 0.0),
        ("invalid", 0.0),
    ]

    for inp, expected in test_cases:
        result = _to_float(inp)
        assert result == expected, f"_to_float({inp!r}) = {result}, expected {expected}"

    print("✅ Float conversion test passed!")


if __name__ == "__main__":
    test_parse_ofd()
    test_extract_xbrl_fields_directly()
    test_tax_rate_parsing()
    test_date_parsing()
    test_float_conversion()
    print("\n🎉 All tests passed!")