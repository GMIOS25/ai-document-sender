import fs from 'node:fs';
import path from 'node:path';

const TARGET_DIR = path.resolve('c:/Workspaces/ai-document-sender/resources/văn bản mẫu/vpub/Hợp lệ');

console.log('Running comprehensive verification audit on cleaned dataset...');
const t0 = Date.now();

const entries = fs.readdirSync(TARGET_DIR, { withFileTypes: true });
const remainingFolders = entries.filter(e => e.isDirectory()).map(e => e.name);

console.log(`Total remaining folders: ${remainingFolders.length}`);

let perfectlyCompliant = 0;
let missingViewCpx = 0;
let missingTxt = 0;
let wrongPdfCount = 0;
let nonPdfFound = 0;
const anomalies = [];

for (const folderName of remainingFolders) {
  const folderPath = path.join(TARGET_DIR, folderName);
  let files;
  try {
    files = fs.readdirSync(folderPath);
  } catch (e) {
    anomalies.push({ folder: folderName, error: e.message });
    continue;
  }

  const hasViewCpx = files.includes('view.cpx');
  const hasTxt = files.includes('kết_quả_gửi_đi.txt');
  const attFiles = files.filter(f => f !== 'view.cpx' && f !== 'kết_quả_gửi_đi.txt');
  const pdfFiles = attFiles.filter(f => f.toLowerCase().endsWith('.pdf'));
  const otherFiles = attFiles.filter(f => !f.toLowerCase().endsWith('.pdf'));

  if (!hasViewCpx) missingViewCpx++;
  if (!hasTxt) missingTxt++;
  if (pdfFiles.length !== 1) wrongPdfCount++;
  if (otherFiles.length > 0) nonPdfFound++;

  if (hasViewCpx && hasTxt && pdfFiles.length === 1 && otherFiles.length === 0) {
    perfectlyCompliant++;
  } else {
    if (anomalies.length < 10) {
      anomalies.push({
        folder: folderName,
        files,
        pdfCount: pdfFiles.length,
        otherCount: otherFiles.length
      });
    }
  }
}

console.log(`\n=== VERIFICATION AUDIT RESULTS ===`);
console.log(`Duration: ${Date.now() - t0}ms`);
console.log(`Total folders: ${remainingFolders.length}`);
console.log(`Perfect folders (exactly view.cpx + kết_quả_gửi_đi.txt + 1 PDF): ${perfectlyCompliant}`);
console.log(`Missing view.cpx: ${missingViewCpx}`);
console.log(`Missing kết_quả_gửi_đi.txt: ${missingTxt}`);
console.log(`Folders with PDF count != 1: ${wrongPdfCount}`);
console.log(`Folders with non-PDF files: ${nonPdfFound}`);
console.log(`Total anomalies: ${anomalies.length}`);

if (anomalies.length > 0) {
  console.log('Sample anomalies:', JSON.stringify(anomalies, null, 2));
}

// Check sample folders from user prompt
const samplesToCheck = [
  '01BC-UBND', '01CV-TGV', '01GCN-UBND',
  '01BB-UBND', '01CV-BCH', '01KL-UBND', '01QĐ-BCĐVP',
  '01GUQ-UBND', '01PA-UBND', '01PC-UBND',
  '01KH-UBND', '01HD-UBND', '01CTr-UBND', '01CT-UBND',
  '01BC-TCT57', '01TB-HCTC', '01ĐA-UBND'
];

console.log('\n=== USER SAMPLES VERIFICATION ===');
for (const s of samplesToCheck) {
  const p = path.join(TARGET_DIR, s);
  if (fs.existsSync(p)) {
    console.log(`Folder [${s}]: EXISTS ->`, fs.readdirSync(p));
  } else {
    console.log(`Folder [${s}]: DELETED (as expected for empty folder)`);
  }
}
