/**
 * 将 MD 文件上传到腾讯文档智能文档。
 * 用法: node upload_to_tdoc.js <md_file_path> [title]
 * 解决: Windows cmd /c type | mcporter 管道中文截断问题
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const mdPath = process.argv[2];
if (!mdPath) { console.error('Usage: node upload_to_tdoc.js <md_file> [title]'); process.exit(1); }

const title = process.argv[3] || path.basename(mdPath, '.md');
const content = fs.readFileSync(mdPath, 'utf-8');

// Step 1: Create shell
console.log('Creating shell document...');
const shellParams = JSON.stringify({ title, mdx: `# ${title}\n\n加载中...` });
const tmpShell = path.join(__dirname, '.tmp_shell.json');
fs.writeFileSync(tmpShell, shellParams, 'utf-8');

let result;
try {
    result = execSync(`cmd /c "type ${tmpShell} | mcporter call tencent-docs create_smartcanvas_by_mdx --args -"`, {
        encoding: 'utf-8', timeout: 30000, windowsHide: true
    });
} finally {
    fs.unlinkSync(tmpShell);
}

const { file_id, url } = JSON.parse(result.trim());
console.log(`Created: ${url}`);

// Step 2: Insert full content in chunks (max ~2000 chars per chunk to survive pipe)
const CHUNK_SIZE = 1800;
const chunks = [];
let remaining = content;

while (remaining.length > 0) {
    if (remaining.length <= CHUNK_SIZE) {
        chunks.push(remaining);
        break;
    }
    // Split at nearest double-newline before CHUNK_SIZE
    let cut = remaining.lastIndexOf('\n\n', CHUNK_SIZE);
    if (cut < CHUNK_SIZE / 2) cut = CHUNK_SIZE;
    chunks.push(remaining.slice(0, cut));
    remaining = remaining.slice(cut);
}

console.log(`Inserting ${chunks.length} chunks...`);
const tmpEdit = path.join(__dirname, '.tmp_edit.json');

for (let i = 0; i < chunks.length; i++) {
    const editParams = JSON.stringify({ file_id, action: 'INSERT_AFTER', content: chunks[i] });
    fs.writeFileSync(tmpEdit, editParams, 'utf-8');
    try {
        execSync(`cmd /c "type ${tmpEdit} | mcporter call tencent-docs smartcanvas.edit --args -"`, {
            encoding: 'utf-8', timeout: 30000, windowsHide: true
        });
        process.stdout.write(`.`);
    } catch (e) {
        console.error(`\nChunk ${i + 1} failed: ${e.message.slice(0, 100)}`);
        // Continue with remaining chunks
    }
}
fs.unlinkSync(tmpEdit);

console.log(`\nDone. ${url}`);
