import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const CONFIG = {
  baseUrl: 'https://vpdt.gialai.gov.vn',
  casUrl: 'https://cas.gialai.gov.vn/cas/login?service=https://vpdt.gialai.gov.vn/vpub/shiro-cas',
  username: process.env.IDESK_USERNAME || 'Vanthu@vpub.gialai.gov.vn',
  password: process.env.IDESK_PASSWORD || 'Vanthu@123789@',
  exeacode: 'b45656bc-0146-1000-e3f0-150813121982',
  books: 'VPUB-BCH-DI;VPUB-BCD-DI;UBND-BB-DI;UBND-BC-DI;UBND-CTr-DI;UBND-CT-DI;UBND-CCNVBX-DI;UBND-BCĐ-DI;UBND-CV-DI;VPUBND-CV-DI;UBND-CD-DI;VPUB-DM-DI;UBND-GCN-DI;UBND-GM-DI;VPUB-GM-DI;UBND-GP-DI;UBND-GUQ-DI;UBND-HD-DI;UBND-HĐ-DI;UBND-KH-DI;UBND-KL-DI;UBND-PC-DI;UBND-PT-DI;UBND-PA-DI;UBND-QC-DI;UBND-QĐQPPL-DI;VPUBND-QĐ;UBND-QĐ-DI;UBND-SL-DI;UBND-SY-DI;VPUB-SY-DI;SO-KHONG-SO;UBND-TB-DI;UBND-TTr-DI;UBND-DL-DI;ĐCT-ĐKT;UBND-DKT-DI;UBND-DA-DI',
  outputDir: path.resolve('c:/Workspaces/ai-document-sender/resources/văn bản mẫu/vpub/Hợp lệ'),
  stateFile: path.resolve('c:/Workspaces/ai-document-sender/tools/crawler_state.json'),
  logFile: path.resolve('c:/Workspaces/ai-document-sender/tools/crawler.log'),
  pageSize: 100,
  concurrency: 5
};

let currentJsessionId = '';

function log(msg) {
  const ts = new Date().toISOString().replace('T', ' ').substring(0, 19);
  const line = `[${ts}] ${msg}`;
  console.log(line);
  try {
    fs.appendFileSync(CONFIG.logFile, line + '\n', 'utf8');
  } catch (e) {}
}

async function login() {
  log(`Logging in as ${CONFIG.username}...`);
  const res1 = await fetch(CONFIG.casUrl);
  const html = await res1.text();
  const rawCookies1 = res1.headers.getSetCookie ? res1.headers.getSetCookie() : [];

  const ltMatch = html.match(/name="lt"\s+value="([^"]+)"/);
  const execMatch = html.match(/name="execution"\s+value="([^"]+)"/);

  if (!ltMatch || !execMatch) {
    throw new Error('Could not find lt or execution token on CAS page');
  }

  const lt = ltMatch[1];
  const execution = execMatch[1];

  const params = new URLSearchParams();
  params.append('username', CONFIG.username.toLowerCase());
  params.append('password', CONFIG.password);
  params.append('lt', lt);
  params.append('execution', execution);
  params.append('_eventId', 'submit');

  const res2 = await fetch('https://cas.gialai.gov.vn/cas/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Cookie': rawCookies1.map(c => c.split(';')[0]).join('; ')
    },
    body: params.toString(),
    redirect: 'manual'
  });

  const redirectUrl = res2.headers.get('location');
  if (!redirectUrl || !redirectUrl.includes('ticket=')) {
    throw new Error(`Login failed, unexpected status ${res2.status}, location: ${redirectUrl}`);
  }

  const res3 = await fetch(redirectUrl, { redirect: 'manual' });
  const shiroCookies = res3.headers.getSetCookie ? res3.headers.getSetCookie() : [];
  let jsessionId = '';
  for (const c of shiroCookies) {
    const m = c.match(/JSESSIONID=([^;]+)/);
    if (m) jsessionId = m[1];
  }

  if (!jsessionId) {
    const nextLoc = res3.headers.get('location');
    if (nextLoc) {
      const res4 = await fetch(nextLoc, {
        headers: { 'Cookie': shiroCookies.map(c => c.split(';')[0]).join('; ') },
        redirect: 'manual'
      });
      const c4 = res4.headers.getSetCookie ? res4.headers.getSetCookie() : [];
      for (const c of [...shiroCookies, ...c4]) {
        const m = c.match(/JSESSIONID=([^;]+)/);
        if (m) jsessionId = m[1];
      }
    }
  }

  if (!jsessionId) {
    throw new Error('Failed to extract JSESSIONID after authentication');
  }

  currentJsessionId = jsessionId;
  log(`Authentication successful. JSESSIONID: ${currentJsessionId.substring(0, 20)}...`);
  return currentJsessionId;
}

async function requestWithAuth(url, options = {}, isRetry = false) {
  if (!currentJsessionId) {
    await login();
  }

  options.headers = options.headers || {};
  options.headers['Cookie'] = `JSESSIONID=${currentJsessionId}`;

  const res = await fetch(url, options);

  // Check if session expired or redirected to login
  if (res.status === 401 || res.status === 403 || res.url.includes('/cas/login')) {
    if (!isRetry) {
      log('Session may have expired, re-authenticating...');
      await login();
      return requestWithAuth(url, options, true);
    }
    throw new Error(`Request to ${url} failed with auth issue (status: ${res.status})`);
  }

  return res;
}

// Algorithm from Script-Idesk for selecting main attachment
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

const isPdf = (att) => att.format === 'pdf' || (att.name || '').toLowerCase().endsWith('.pdf');
const isSigned = (att) => att.signed === 'Y';

function selectAttachment(doc) {
  const attachments = doc.attachments || [];
  if (attachments.length === 0) return null;

  let candidates = attachments.filter(att => isPdf(att) && isSigned(att));
  if (candidates.length === 0) candidates = attachments.filter(isSigned);
  if (candidates.length === 0) candidates = attachments.filter(isPdf);
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

function sanitizeFolderName(signNumber) {
  return (signNumber || 'unnamed')
    .replace(/\//g, '')
    .replace(/[\\:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .trim();
}

async function fetchPage(pageNumber, pageSize = CONFIG.pageSize) {
  const url = `${CONFIG.baseUrl}/vpub/smartcloud/document/edocs/qsoutbook.cpx`;
  const params = new URLSearchParams();
  params.append('exeacode', CONFIG.exeacode);
  params.append('key', '');
  params.append('books', CONFIG.books);
  params.append('inOutDateFrom', '');
  params.append('inOutDateTo', '');
  params.append('pageSize', pageSize.toString());
  params.append('pageNumber', pageNumber.toString());

  const res = await requestWithAuth(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json'
    },
    body: params.toString()
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch page ${pageNumber}: HTTP ${res.status}`);
  }

  return await res.json();
}

async function processDocument(item) {
  const docId = item.id;
  const edDto = item.edSearchDto || {};
  const signNumber = edDto.signNumber || `doc_${docId}`;
  const folderName = sanitizeFolderName(signNumber);
  const targetDir = path.join(CONFIG.outputDir, folderName);

  // Check if already completely downloaded
  const viewPath = path.join(targetDir, 'view.cpx');
  const txtPath = path.join(targetDir, 'kết_quả_gửi_đi.txt');

  if (fs.existsSync(viewPath) && fs.existsSync(txtPath)) {
    const files = fs.readdirSync(targetDir);
    const hasPdf = files.some(f => f.toLowerCase().endsWith('.pdf'));
    if (hasPdf) {
      // Already complete
      return { skipped: true, signNumber };
    }
  }

  // 1. Fetch view.cpx
  const viewUrl = `${CONFIG.baseUrl}/vpub/smartcloud/document/edocs/view.cpx?exeacode=${CONFIG.exeacode}&id=${docId}`;
  const viewRes = await requestWithAuth(viewUrl);
  if (!viewRes.ok) {
    throw new Error(`Failed to fetch view.cpx for doc ${docId}: HTTP ${viewRes.status}`);
  }
  const viewData = await viewRes.json();

  if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
  }

  // 2. Save view.cpx
  fs.writeFileSync(viewPath, JSON.stringify(viewData, null, 4), 'utf8');

  // 3. Extract 3 fields and save kết_quả_gửi_đi.txt
  const mainHandlers = [];
  const watchers = [];
  (viewData.proInfos || []).forEach(pi => {
    const title = (pi.receiverAname || '').trim();
    const name = pi.receiverName ? ` (${pi.receiverName.trim()})` : '';
    const str = `${title}${name}`.trim();
    if (str && !str.startsWith('Văn thư')) {
      if (pi.responsibility === 'main') {
        if (!mainHandlers.includes(str)) mainHandlers.push(str);
      } else if (pi.responsibility === 'watch') {
        if (!watchers.includes(str)) watchers.push(str);
      }
    }
  });

  const receiver = viewData.book ? (viewData.book.receiver || '') : '';
  const txtContent = `Người xử lí:${mainHandlers.join('; ')}\nNgười theo dõi:${watchers.join('; ')}\nĐơn vị nhận:${receiver}\n`;
  fs.writeFileSync(txtPath, txtContent, 'utf8');

  // 4. Download main attachment
  const attachments = viewData.attachments || [];
  const mainAtt = selectAttachment(viewData);
  const downloadedContentUids = new Set();

  if (mainAtt && mainAtt.contentUid) {
    const dlUrl = `${CONFIG.baseUrl}/vpub/smartcloud/docx/download.cpx?docID=${encodeURIComponent(mainAtt.contentUid)}&view=pdf&t=${Date.now()}`;
    try {
      const dlRes = await requestWithAuth(dlUrl);
      if (dlRes.ok) {
        let filename = '';
        const cd = dlRes.headers.get('content-disposition');
        if (cd) {
          const m = cd.match(/filename=["']?([^"';]+)["']?/i);
          if (m) filename = m[1];
        }
        if (!filename) {
          const docNum = extractDocNumber(signNumber);
          filename = docNum ? `${docNum}cv_0001.pdf` : (mainAtt.name || 'document.pdf');
        }
        filename = sanitizeFilename(filename);
        const buffer = Buffer.from(await dlRes.arrayBuffer());
        fs.writeFileSync(path.join(targetDir, filename), buffer);
        downloadedContentUids.add(mainAtt.contentUid);
      } else {
        log(`[Warn] Download main doc failed for ${signNumber}: HTTP ${dlRes.status}`);
      }
    } catch (e) {
      log(`[Warn] Error downloading main doc for ${signNumber}: ${e.message}`);
    }
  }

  // 5. Secondary attachments download disabled (only main document is kept for AI training dataset)


  return { success: true, signNumber, filesCount: downloadedContentUids.size };
}

function loadState() {
  if (fs.existsSync(CONFIG.stateFile)) {
    try {
      return JSON.parse(fs.readFileSync(CONFIG.stateFile, 'utf8'));
    } catch (e) {}
  }
  return {
    currentPage: 0,
    totalRecords: 0,
    totalPages: 0,
    crawledInternal: 0,
    skipped: 0,
    errors: 0,
    startedAt: new Date().toISOString(),
    lastUpdated: new Date().toISOString()
  };
}

function saveState(state) {
  state.lastUpdated = new Date().toISOString();
  fs.writeFileSync(CONFIG.stateFile, JSON.stringify(state, null, 2), 'utf8');
}

async function run() {
  if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
  }

  const state = loadState();
  log(`Starting crawler. Resuming from page ${state.currentPage}...`);
  log(`Target output directory: ${CONFIG.outputDir}`);

  // Fetch page 0 to discover total records
  const initPage = await fetchPage(0, 10);
  state.totalRecords = initPage.total || 0;
  state.totalPages = Math.ceil(state.totalRecords / CONFIG.pageSize);
  log(`Total records: ${state.totalRecords} (Total pages: ${state.totalPages} at pageSize=${CONFIG.pageSize})`);
  saveState(state);

  for (let page = state.currentPage; page < state.totalPages; page++) {
    state.currentPage = page;
    log(`--- Processing Page ${page + 1}/${state.totalPages} (records ${page * CONFIG.pageSize} - ${Math.min((page + 1) * CONFIG.pageSize, state.totalRecords)}) ---`);

    let pageData;
    let retries = 3;
    while (retries > 0) {
      try {
        pageData = await fetchPage(page, CONFIG.pageSize);
        break;
      } catch (err) {
        retries--;
        log(`[Error] Fetching page ${page} failed: ${err.message}. Retries left: ${retries}`);
        if (retries === 0) throw err;
        await new Promise(r => setTimeout(r, 3000));
      }
    }

    const items = pageData.items || [];
    if (items.length === 0) {
      log(`No more items found at page ${page}. Finished.`);
      break;
    }

    // Filter only documents with internalTransfer > 0 (gửi nội bộ)
    const internalItems = items.filter(it => it.edSearchDto && it.edSearchDto.internalTransfer > 0);
    log(`Page ${page + 1}: Found ${internalItems.length}/${items.length} internal transfer documents.`);

    // Process internal items with controlled concurrency
    for (let i = 0; i < internalItems.length; i += CONFIG.concurrency) {
      const chunk = internalItems.slice(i, i + CONFIG.concurrency);
      await Promise.all(chunk.map(async (item) => {
        try {
          const res = await processDocument(item);
          if (res.skipped) {
            state.skipped++;
          } else {
            state.crawledInternal++;
            log(`[Saved] ${res.signNumber} (${res.filesCount} files)`);
          }
        } catch (err) {
          state.errors++;
          log(`[Error] Failed doc ${item.edSearchDto?.signNumber || item.id}: ${err.message}`);
        }
      }));
    }

    saveState(state);
    log(`Page ${page + 1} completed. Summary: Crawled=${state.crawledInternal}, Skipped=${state.skipped}, Errors=${state.errors}`);

    // Small delay between pages to keep server load polite
    await new Promise(r => setTimeout(r, 500));
  }

  log(`CRAWLER COMPLETED! Total internal documents crawled: ${state.crawledInternal}, Skipped: ${state.skipped}, Errors: ${state.errors}`);
}

run().catch(err => {
  log(`[Fatal Error] ${err.stack || err.message}`);
  process.exit(1);
});
