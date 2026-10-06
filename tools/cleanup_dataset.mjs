import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const TARGET_DIR = path.resolve('c:/Workspaces/ai-document-sender/resources/văn bản mẫu/vpub/Hợp lệ');

const SEALED_KEYWORDS = ['dadongdau', 'daky'];
const normalizeText = (str) =>
  (str || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[\s\-_]/g, '');

const extractDocNumber = (str) => {
  if (!str) return null;
  const s = String(str).trim();
  const slash = s.match(/^(\d{1,7})\s*\/[A-Za-zÀ-ỹ]/);
  if (slash) return parseInt(slash[1], 10).toString();
  const cv = s.match(/CV[-_\s]?0*(\d+)/i) || s.match(/S[ôoố][^\d]{0,3}0*(\d+)/i);
  if (cv) return parseInt(cv[1], 10).toString();
  const nums = [...s.matchAll(/\d+/g)].map(m => m[0]);
  for (const n of nums) {
    if (n.length !== 8) return parseInt(n, 10).toString();
  }
  return nums.length ? parseInt(nums[0], 10).toString() : null;
};

const isPdfByName = (name) => (name || '').toLowerCase().endsWith('.pdf');
const isSigned = (att) => att.signed === 'Y';

function isPdfFile(filePath, fileName) {
  if (isPdfByName(fileName)) return true;
  try {
    const fd = fs.openSync(filePath, 'r');
    const buf = Buffer.alloc(5);
    fs.readSync(fd, buf, 0, 5, 0);
    fs.closeSync(fd);
    return buf.toString('utf8').startsWith('%PDF');
  } catch (e) {
    return false;
  }
}

function selectAttachment(doc) {
  const attachments = doc.attachments || [];
  if (attachments.length === 0) return null;
  let candidates = attachments.filter(att => (att.format === 'pdf' || isPdfByName(att.name)) && isSigned(att));
  if (candidates.length === 0) candidates = attachments.filter(isSigned);
  if (candidates.length === 0) candidates = attachments.filter(att => att.format === 'pdf' || isPdfByName(att.name));
  if (candidates.length === 0) candidates = attachments;

  if (candidates.length === 1) return candidates[0];

  const sealedMatch = candidates.find(att =>
    SEALED_KEYWORDS.some(kw => normalizeText(att.name).includes(kw))
  );
  if (sealedMatch) return sealedMatch;

  const signDigits = extractDocNumber(doc.ed?.signNumber || doc.signNumber || '');
  if (signDigits) {
    const matchedByNum = candidates.find(att => extractDocNumber(att.name) === signDigits);
    if (matchedByNum) return matchedByNum;
  }

  const bySize = [...candidates].sort((a, b) => (b.size || 0) - (a.size || 0))[0];
  return bySize || candidates[0];
}

function sanitizeFilename(name) {
  return (name || 'file')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .trim();
}

// Special edge cases verified manually via PDF inspection
const KNOWN_EDGE_CASES = {
  '1021UBND-KTTH': 'Van ban.pdf',
  '10889UBND-KTTH': '11. Van ban bo sung ho so.pdf',
  '1457UBND-XDCT': 'lam viec',
  '3468UBND-NC': '25.3 Giao SNV',
  '3500UBND-KGVX': '105. CVUB ve kiem tra tinh hieu qua thiet thuc khi giam so luong dien thoai ve tinh sau sap nhap.pdf',
  '367UBND-KTTH': 'Van ban.pdf',
  '4193UBND-TD': 'NGUYEN XUAN NGHIEP DAI DIEN 32 HO FLC HOME 24.9.2025.pdf',
  '4928UBND-NC': '04.20 CV 154 giao CA tinh thong nhat noi dung va ky Vb cua BC dao PCCC _mua hanh kho.pdf',
  '692TTr-UBND': '1. TTr_UBND_To trinh HDND_du an khu du lich_Cat Tien.pdf',
  '7892UBND-KGVX': '217. tham muu XD ke hoach di hoc nuoc ngoai.pdf',
  '8651UBND-KGVX': '191. tham muu giao dat mo rong Truong PTDT Noi tru.pdf'
};

export function planCleanup(dryRun = true) {
  console.log(`Starting dataset cleanup analysis (dryRun = ${dryRun})...`);
  const t0 = Date.now();

  const entries = fs.readdirSync(TARGET_DIR, { withFileTypes: true });
  const folders = entries.filter(e => e.isDirectory()).map(e => e.name);

  console.log(`Total folders to inspect: ${folders.length}`);

  const actions = {
    foldersToDelete: [],
    filesToDelete: [],
    filesToRename: [],
    foldersPreserved: 0,
    foldersAlreadyClean: 0,
    foldersWithNonPdfsRemoved: 0,
    foldersWithMultiPdfsResolved: 0,
    issues: []
  };

  for (const folderName of folders) {
    const folderPath = path.join(TARGET_DIR, folderName);
    let files;
    try {
      files = fs.readdirSync(folderPath);
    } catch (e) {
      actions.issues.push({ folder: folderName, error: e.message });
      continue;
    }

    const attsOnDisk = files.filter(f => f !== 'view.cpx' && f !== 'kết_quả_gửi_đi.txt');

    // Case 1: Folder has NO attachment files at all
    if (attsOnDisk.length === 0) {
      actions.foldersToDelete.push(folderPath);
      continue;
    }

    // Detect PDF files (by name or by magic bytes %PDF)
    const pdfFiles = [];
    const nonPdfFiles = [];

    for (const f of attsOnDisk) {
      const fPath = path.join(folderPath, f);
      if (isPdfFile(fPath, f)) {
        pdfFiles.push(f);
      } else {
        nonPdfFiles.push(f);
      }
    }

    // If folder has NO PDF files at all (e.g. only a .zip file)
    if (pdfFiles.length === 0) {
      // Per user rules: noisy non-pdf files should be removed. Since there are 0 valid PDFs,
      // the entire folder becomes attachment-empty and should be deleted.
      actions.foldersToDelete.push(folderPath);
      continue;
    }

    // Exactly 1 PDF file
    if (pdfFiles.length === 1) {
      const keepPdf = pdfFiles[0];
      if (nonPdfFiles.length === 0) {
        actions.foldersAlreadyClean++;
      } else {
        actions.foldersWithNonPdfsRemoved++;
        for (const nonPdf of nonPdfFiles) {
          actions.filesToDelete.push(path.join(folderPath, nonPdf));
        }
      }

      // If the kept file does not end in .pdf, plan rename
      if (!keepPdf.toLowerCase().endsWith('.pdf')) {
        actions.filesToRename.push({
          from: path.join(folderPath, keepPdf),
          to: path.join(folderPath, `${keepPdf}.pdf`)
        });
      }

      actions.foldersPreserved++;
      continue;
    }

    // Multiple PDF files on disk (pdfFiles.length > 1)
    let selectedMainPdf = null;

    if (KNOWN_EDGE_CASES[folderName]) {
      const edgeName = KNOWN_EDGE_CASES[folderName];
      if (pdfFiles.includes(edgeName)) {
        selectedMainPdf = edgeName;
      }
    }

    if (!selectedMainPdf) {
      const viewPath = path.join(folderPath, 'view.cpx');
      let viewData = null;
      try {
        if (fs.existsSync(viewPath)) {
          viewData = JSON.parse(fs.readFileSync(viewPath, 'utf8'));
        }
      } catch (e) {}

      if (viewData) {
        const mainAtt = selectAttachment(viewData);
        if (mainAtt) {
          const secondaryNames = new Set(
            (viewData.attachments || [])
              .filter(a => a.contentUid !== mainAtt.contentUid)
              .map(a => sanitizeFilename(a.name).toLowerCase())
          );

          const nonSecondary = pdfFiles.filter(f => !secondaryNames.has(f.toLowerCase()));
          if (nonSecondary.length === 1) {
            selectedMainPdf = nonSecondary[0];
          } else if (nonSecondary.length > 1) {
            // Pick the one closest to signNumber or largest size
            selectedMainPdf = nonSecondary[0];
          }
        }
      }
    }

    if (!selectedMainPdf) {
      actions.issues.push({
        folder: folderName,
        error: `Could not identify main PDF among: ${pdfFiles.join(', ')}`
      });
      continue;
    }

    actions.foldersWithMultiPdfsResolved++;
    actions.foldersPreserved++;

    // Mark all other PDFs and non-PDFs for deletion
    for (const f of attsOnDisk) {
      if (f !== selectedMainPdf) {
        actions.filesToDelete.push(path.join(folderPath, f));
      }
    }

    // If selected main PDF lacks .pdf extension, rename it
    if (!selectedMainPdf.toLowerCase().endsWith('.pdf')) {
      actions.filesToRename.push({
        from: path.join(folderPath, selectedMainPdf),
        to: path.join(folderPath, `${selectedMainPdf}.pdf`)
      });
    }
  }

  console.log(`\n=== CLEANUP ANALYSIS SUMMARY ===`);
  console.log(`Duration: ${(Date.now() - t0)}ms`);
  console.log(`Total folders scanned: ${folders.length}`);
  console.log(`Folders to delete completely (0 attachments / non-PDF only): ${actions.foldersToDelete.length}`);
  console.log(`Folders preserved (with exactly 1 main PDF): ${actions.foldersPreserved}`);
  console.log(`  - Already clean (1 PDF, 0 non-PDF): ${actions.foldersAlreadyClean}`);
  console.log(`  - 1 PDF + non-PDFs removed: ${actions.foldersWithNonPdfsRemoved}`);
  console.log(`  - Multi-PDFs resolved to 1 main PDF: ${actions.foldersWithMultiPdfsResolved}`);
  console.log(`Total files to delete: ${actions.filesToDelete.length}`);
  console.log(`Files to rename to add .pdf extension: ${actions.filesToRename.length}`);
  console.log(`Issues / unhandled folders: ${actions.issues.length}`);

  if (actions.issues.length > 0) {
    console.log(`Issues details:`, JSON.stringify(actions.issues, null, 2));
  }

  return actions;
}

// If executed directly
const isDryRun = !process.argv.includes('--execute');
const actions = planCleanup(isDryRun);

if (!isDryRun) {
  console.log('\nEXECUTING CLEANUP OPERATIONS...');
  const tStart = Date.now();

  // 1. Delete files
  console.log(`Deleting ${actions.filesToDelete.length} extra files...`);
  let deletedFilesCount = 0;
  for (const filePath of actions.filesToDelete) {
    try {
      fs.unlinkSync(filePath);
      deletedFilesCount++;
    } catch (e) {
      console.error(`Failed to delete ${filePath}: ${e.message}`);
    }
  }

  // 2. Rename files (e.g. adding .pdf extension)
  console.log(`Renaming ${actions.filesToRename.length} files...`);
  for (const item of actions.filesToRename) {
    try {
      if (fs.existsSync(item.from) && !fs.existsSync(item.to)) {
        fs.renameSync(item.from, item.to);
      }
    } catch (e) {
      console.error(`Failed to rename ${item.from} -> ${item.to}: ${e.message}`);
    }
  }

  // 3. Delete folders
  console.log(`Deleting ${actions.foldersToDelete.length} empty folders...`);
  let deletedFoldersCount = 0;
  for (const folderPath of actions.foldersToDelete) {
    try {
      fs.rmSync(folderPath, { recursive: true, force: true });
      deletedFoldersCount++;
    } catch (e) {
      console.error(`Failed to delete folder ${folderPath}: ${e.message}`);
    }
  }

  console.log(`\nExecution completed in ${(Date.now() - tStart)}ms!`);
  console.log(`Deleted files: ${deletedFilesCount}`);
  console.log(`Deleted folders: ${deletedFoldersCount}`);
}
