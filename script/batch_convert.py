"""Batch convert PDF/DOCX/DOC files from 知识库补充 to MD."""
import fitz  # PyMuPDF
import docx
import os
import re

SRC = r'D:\vscode.project\.claude\skills\咨询侠\知识库补充'
OUT = r'D:\vscode.project\.claude\skills\咨询侠\知识库\数据层'

os.makedirs(OUT, exist_ok=True)

def pdf_to_md(src_path, dst_path):
    """Convert PDF to Markdown using PyMuPDF."""
    doc = fitz.open(src_path)
    lines = []
    for page in doc:
        text = page.get_text('text')
        if text.strip():
            lines.append(text.strip())
    doc.close()
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(lines))
    return len(lines)

def docx_to_md(src_path, dst_path):
    """Convert DOCX to Markdown using python-docx."""
    doc = docx.Document(src_path)
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
        else:
            lines.append('')
    # Tables
    for table in doc.tables:
        lines.append('')
        for row_idx, row in enumerate(table.rows):
            cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
            lines.append('| ' + ' | '.join(cells) + ' |')
            if row_idx == 0:
                lines.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
    result = '\n'.join(lines)
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write(result)
    return len(doc.paragraphs)

results = []
for fname in os.listdir(SRC):
    src_path = os.path.join(SRC, fname)
    if not os.path.isfile(src_path):
        continue

    base = os.path.splitext(fname)[0]
    ext = os.path.splitext(fname)[1].lower()
    dst_path = os.path.join(OUT, base + '.md')

    try:
        if ext == '.pdf':
            n = pdf_to_md(src_path, dst_path)
            results.append(f'PDF: {fname} → {base}.md ({n} pages)')
        elif ext == '.docx':
            n = docx_to_md(src_path, dst_path)
            results.append(f'DOCX: {fname} → {base}.md ({n} paragraphs)')
        elif ext == '.doc':
            # Try python-docx first (might be .docx in disguise)
            try:
                n = docx_to_md(src_path, dst_path)
                results.append(f'DOC(as DOCX): {fname} → {base}.md ({n} paragraphs)')
            except Exception:
                results.append(f'DOC FAILED: {fname} — needs Word/LibreOffice conversion')
        elif ext == '.md':
            results.append(f'MD: {fname} — skip, already MD')
        else:
            results.append(f'SKIP: {fname} (unknown format)')
    except Exception as e:
        results.append(f'ERROR: {fname} — {str(e)[:100]}')

for r in results:
    print(r)
print(f'\nDone. {len(results)} files processed.')