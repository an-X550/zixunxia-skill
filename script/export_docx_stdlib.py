"""
咨询侠 — 专业推荐文档 DOCX 导出工具（纯标准库版）
用法: /usr/bin/python3 export_docx_stdlib.py '<json_path>'
"""
import json
import sys
import os
import zipfile
import uuid
from datetime import date
from xml.etree.ElementTree import Element, SubElement, tostring


def _q(name):
    """辅助: 返回带命名空间的 XML 标签"""
    return f'{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{name}'

def _r(name):
    """辅助: 返回带关系命名空间的 XML 标签"""
    return f'{{http://schemas.openxmlformats.org/officeDocument/2006/relationships}}{name}'

def _w(name):
    return f'{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{name}'


def make_element(tag, attrib=None, text=None):
    el = Element(tag, attrib or {})
    if text is not None:
        el.text = text
    return el


def add_run(para, text, bold=False, color=None, size=None, font='微软雅黑'):
    """在段落元素中添加 <w:r>"""
    r = SubElement(para, _w('r'))
    rPr = SubElement(r, _w('rPr'))
    if bold:
        b = SubElement(rPr, _w('b'))
        b.set(_w('val'), '1')
    if color:
        c = SubElement(rPr, _w('color'))
        c.set(_w('val'), color)
    if size:
        sz = SubElement(rPr, _w('sz'))
        sz.set(_w('val'), str(int(size * 2)))  # Pt → 半磅
    # 字体
    rFonts = SubElement(rPr, _w('rFonts'))
    rFonts.set(_w('ascii'), font)
    rFonts.set(_w('hAnsi'), font)
    rFonts.set(_w('eastAsia'), font)
    t = SubElement(r, _w('t'))
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text


def add_paragraph(doc_body, text='', bold=False, color=None, size=21, alignment=None, spacing_after=None, font='微软雅黑'):
    """添加段落，返回段落元素"""
    p = SubElement(doc_body, _w('p'))
    pPr = SubElement(p, _w('pPr'))
    if alignment is not None:
        jc = SubElement(pPr, _w('jc'))
        jc.set(_w('val'), alignment)
    if spacing_after is not None:
        sa = SubElement(pPr, _w('spacing'))
        sa.set(_w('after'), str(spacing_after))
    if text:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                # 换行
                r = SubElement(p, _w('r'))
                SubElement(r, _w('br'))
            add_run(p, line, bold=bold, color=color, size=size, font=font)
    return p


def make_table(doc_body, headers, rows, col_widths=None):
    """创建表格"""
    tbl = SubElement(doc_body, _w('tbl'))
    tblPr = SubElement(tbl, _w('tblPr'))
    tblW = SubElement(tblPr, _w('tblW'))
    tblW.set(_w('w'), '9000')
    tblW.set(_w('type'), 'dxa')
    borders = SubElement(tblPr, _w('tblBorders'))
    for border_name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        b = SubElement(borders, _w(border_name))
        b.set(_w('val'), 'single')
        b.set(_w('sz'), '4')
        b.set(_w('space'), '0')
        b.set(_w('color'), '999999')

    # 表头
    tr = SubElement(tbl, _w('tr'))
    for h in headers:
        tc = SubElement(tr, _w('tc'))
        tcPr = SubElement(tc, _w('tcPr'))
        shd = SubElement(tcPr, _w('shd'))
        shd.set(_w('val'), 'clear')
        shd.set(_w('fill'), '4472C4')
        p = add_paragraph(tc, h, bold=True, color='FFFFFF', size=18, font='微软雅黑')

    # 数据行
    for i, row_data in enumerate(rows):
        tr = SubElement(tbl, _w('tr'))
        for j, cell_val in enumerate(row_data):
            tc = SubElement(tr, _w('tc'))
            tcPr = SubElement(tc, _w('tcPr'))
            if i == 0:
                shd = SubElement(tcPr, _w('shd'))
                shd.set(_w('val'), 'clear')
                shd.set(_w('fill'), 'F0F8E8')
            p = add_paragraph(tc, str(cell_val), size=18, font='微软雅黑')

    return tbl


def build_docx_xml(data):
    """构建 document.xml 的 Element"""
    root = Element(_w('document'), {
        'xmlns:mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
        'xmlns:w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
        'xmlns:wp14': 'http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing',
        _w('mcIgnorable'): 'w14 wp14',
    })
    body = SubElement(root, _w('body'))

    student_name = data.get('student_name', '考生')
    doc_date = data.get('date', date.today().isoformat())
    majors = data.get('majors', [])
    comparison_table = data.get('comparison_table', {})
    pitfalls = data.get('pitfalls', [])
    summary = data.get('summary', '')

    # ===== 标题 =====
    add_paragraph(body, '高考志愿填报专业推荐文档', bold=True, size=36, alignment='center')
    add_paragraph(body, f'—— 为 {student_name} 定制 | {doc_date}', size=20, color='646464', alignment='center')
    add_paragraph(body, '')

    # ===== 推荐逻辑摘要 =====
    if summary:
        add_paragraph(body, '推荐逻辑摘要', bold=True, size=28)
        add_paragraph(body, summary, size=21, spacing_after=200)

    # ===== 推荐专业 =====
    add_paragraph(body, f'推荐专业（共 {len(majors)} 个）', bold=True, size=28)

    medals = ['🥇', '🥈', '🥉', '④', '⑤']
    strength_labels = {
        5: '⭐⭐⭐⭐⭐ 最高推荐',
        4: '⭐⭐⭐⭐ 强烈推荐',
        3: '⭐⭐⭐ 推荐',
        2: '⭐⭐ 可考虑',
        1: '⭐ 备选'
    }

    for i, m in enumerate(majors):
        name = m.get('name', '')
        strength = m.get('strength', 3)
        medal = medals[i] if i < len(medals) else '•'

        add_paragraph(body, f'{medal} {name}', bold=True, size=24, spacing_after=60)
        p = add_paragraph(body, '', size=21)
        add_run(p, f'推荐强度：{strength_labels.get(strength, f"推荐度 {strength}/5")}', bold=True, size=21)

        # 信息表格
        fields = [
            ('推荐原因', m.get('reason', '')),
            ('适合点', m.get('fit_points', '')),
            ('需要了解的现实面', m.get('reality_check', '')),
            ('可能发展方向', m.get('development', '')),
            ('赚钱路径类型', m.get('earning_type', '')),
            ('学校层次敏感度', m.get('prestige_sensitivity', '')),
            ('给你的行动建议', m.get('action_advice', '')),
        ]
        for label, value in fields:
            tbl = SubElement(body, _w('tbl'))
            tblPr = SubElement(tbl, _w('tblPr'))
            tblW = SubElement(tblPr, _w('tblW'))
            tblW.set(_w('w'), '9000')
            tblW.set(_w('type'), 'dxa')
            borders = SubElement(tblPr, _w('tblBorders'))
            for bn in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
                b = SubElement(borders, _w(bn))
                b.set(_w('val'), 'single')
                b.set(_w('sz'), '4')
                b.set(_w('space'), '0')
                b.set(_w('color'), 'BBBBBB')

            tr = SubElement(tbl, _w('tr'))
            # 标签列
            tc_label = SubElement(tr, _w('tc'))
            tcPr_label = SubElement(tc_label, _w('tcPr'))
            tcW_label = SubElement(tcPr_label, _w('tcW'))
            tcW_label.set(_w('w'), '1800')
            tcW_label.set(_w('type'), 'dxa')
            shd_label = SubElement(tcPr_label, _w('shd'))
            shd_label.set(_w('val'), 'clear')
            shd_label.set(_w('fill'), 'E8F0FE')
            add_paragraph(tc_label, label, bold=True, size=19)

            # 值列
            tc_val = SubElement(tr, _w('tc'))
            tcPr_val = SubElement(tc_val, _w('tcPr'))
            tcW_val = SubElement(tcPr_val, _w('tcW'))
            tcW_val.set(_w('w'), '7200')
            tcW_val.set(_w('type'), 'dxa')
            add_paragraph(tc_val, str(value), size=19)

        add_paragraph(body, '', spacing_after=120)

    # ===== 专业对比一览 =====
    if comparison_table:
        add_paragraph(body, '专业对比一览', bold=True, size=28)
        headers = comparison_table.get('headers', [])
        rows = comparison_table.get('rows', [])
        if headers and rows:
            make_table(body, headers, rows)
        add_paragraph(body, '')

    # ===== 避坑清单 =====
    if pitfalls:
        add_paragraph(body, '选专业避坑清单', bold=True, size=28)
        add_paragraph(body, '以下提醒基于你的个人画像定制，不是通用套话：', size=19, color='646464')
        for idx, pitfall in enumerate(pitfalls, 1):
            add_paragraph(body, f'⚠️ {idx}. {pitfall}', size=21, spacing_after=120)

    # ===== 页脚 =====
    add_paragraph(body, '')
    add_paragraph(body, '—— 问问大象 · 咨询侠 ——', size=16, color='969696', alignment='center')
    add_paragraph(body, '授人以渔，而非授人以鱼', size=16, color='969696', alignment='center')

    return root


def build_rels_xml():
    """构建根级 .rels 文件——只声明主文档"""
    rels = Element(_r('Relationships'), {})
    ri = SubElement(rels, _r('Relationship'))
    ri.set('Id', 'rId1')
    ri.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument')
    ri.set('Target', 'word/document.xml')
    return rels


def build_doc_rels_xml():
    """构建 word/_rels/document.xml.rels——声明文档级关系"""
    rels = Element(_r('Relationships'), {})
    ri = SubElement(rels, _r('Relationship'))
    ri.set('Id', 'rId1')
    ri.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles')
    ri.set('Target', 'styles.xml')
    return rels


def build_styles_xml():
    """构建最小 styles.xml"""
    styles = Element(_w('styles'), {})
    # Default style
    docDefaults = SubElement(styles, _w('docDefaults'))
    rPrDefault = SubElement(docDefaults, _w('rPrDefault'))
    rPr = SubElement(rPrDefault, _w('rPr'))
    rFonts = SubElement(rPr, _w('rFonts'))
    rFonts.set(_w('ascii'), '微软雅黑')
    rFonts.set(_w('hAnsi'), '微软雅黑')
    rFonts.set(_w('eastAsia'), '微软雅黑')
    sz = SubElement(rPr, _w('sz'))
    sz.set(_w('val'), '21')
    pPrDefault = SubElement(docDefaults, _w('pPrDefault'))
    pPr = SubElement(pPrDefault, _w('pPr'))
    return styles


def build_content_types_xml():
    """构建 [Content_Types].xml"""
    types = Element('{http://schemas.openxmlformats.org/package/2006/content-types}Types', {})
    ov = SubElement(types, '{http://schemas.openxmlformats.org/package/2006/content-types}Override')
    ov.set('PartName', '/word/document.xml')
    ov.set('ContentType', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml')
    ov2 = SubElement(types, '{http://schemas.openxmlformats.org/package/2006/content-types}Override')
    ov2.set('PartName', '/word/styles.xml')
    ov2.set('ContentType', 'application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml')
    # 默认 rels 类型
    d = SubElement(types, '{http://schemas.openxmlformats.org/package/2006/content-types}Default')
    d.set('Extension', 'rels')
    d.set('ContentType', 'application/vnd.openxmlformats-package.relationships+xml')
    return types


def to_xml_declaration(element):
    """将 Element 转为带 XML 声明和正确命名空间的字节串"""
    # 需要用 register_namespace 确保前缀一致
    from xml.etree.ElementTree import register_namespace
    register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
    register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
    register_namespace('ct', 'http://schemas.openxmlformats.org/package/2006/content-types')
    register_namespace('mc', 'http://schemas.openxmlformats.org/markup-compatibility/2006')

    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(element, encoding='utf-8', xml_declaration=False)


def main():
    if len(sys.argv) < 2:
        print("用法: /usr/bin/python3 export_docx_stdlib.py <json_path>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: file not found: {filepath}")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    student_name = data.get('student_name', '考生')
    version = data.get('version', '')

    # 输出路径
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
    skill_root = os.path.dirname(script_dir) if os.path.basename(script_dir) == 'script' else script_dir
    cases_dir = os.path.join(skill_root, 'cases')
    os.makedirs(cases_dir, exist_ok=True)
    ver_suffix = f'-{version}' if version else ''
    output_path = os.path.join(cases_dir, f'{student_name}-专业推荐文档{ver_suffix}.docx')

    # 构建 DOCX (ZIP)
    doc_xml = to_xml_declaration(build_docx_xml(data))
    rels_xml = to_xml_declaration(build_rels_xml())
    doc_rels_xml = to_xml_declaration(build_doc_rels_xml())
    styles_xml = to_xml_declaration(build_styles_xml())
    content_types_xml = to_xml_declaration(build_content_types_xml())

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types_xml)
        zf.writestr('_rels/.rels', rels_xml)
        zf.writestr('word/_rels/document.xml.rels', doc_rels_xml)
        zf.writestr('word/document.xml', doc_xml)
        zf.writestr('word/styles.xml', styles_xml)

    print(f'DOCX saved: {output_path}')


if __name__ == '__main__':
    main()