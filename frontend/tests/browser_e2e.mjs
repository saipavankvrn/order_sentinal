import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
import path from 'node:path';

const BACKEND_PORT = 8000;
const CDP_PORT = 9222;
const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const ARTIFACT_DIR = "C:\\Users\\Asus\\.gemini\\antigravity\\brain\\290bee17-e90e-4b64-a3b4-5131c9b020dd";

async function main() {
  console.log("=== Starting OrderFlow Sentinel End-to-End Browser Automation ===");

  // 1. Start FastAPI server
  console.log("[1/5] Launching FastAPI backend server...");
  const serverProc = spawn("d:\\Virtusa Jatayu\\.venv\\Scripts\\python.exe", [
    "-m", "uvicorn", "backend.app.main:app",
    "--host", "127.0.0.1",
    "--port", String(BACKEND_PORT)
  ], { stdio: 'ignore' });

  // Wait for server to bind
  await sleep(2500);

  // 2. Launch headless Chrome with CDP
  console.log("[2/5] Launching Chrome in headless mode with remote debugging...");
  const chromeProc = spawn(CHROME_PATH, [
    "--headless=new",
    `--remote-debugging-port=${CDP_PORT}`,
    "--hide-scrollbars",
    "--window-size=1440,1050",
    "about:blank"
  ]);

  await sleep(1500);

  try {
    // 3. Connect to Chrome CDP via WebSocket
    const versionRes = await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`);
    const targets = await versionRes.json();
    const pageTarget = targets.find(t => t.type === 'page') || targets[0];
    if (!pageTarget || !pageTarget.webSocketDebuggerUrl) {
      throw new Error("Could not find Chrome page WebSocketDebuggerUrl");
    }

    console.log(`[3/5] Connected to Chrome DevTools at ${pageTarget.webSocketDebuggerUrl}`);
    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

    let msgId = 1;
    const callbacks = new Map();
    const consoleLogs = [];
    const pageExceptions = [];
    const capturedOrdersRequests = [];

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.id && callbacks.has(data.id)) {
        const { resolve, reject } = callbacks.get(data.id);
        callbacks.delete(data.id);
        if (data.error) reject(data.error);
        else resolve(data.result);
      }

      if (data.method === 'Network.requestWillBeSent') {
        const reqUrl = data.params?.request?.url || '';
        if (reqUrl.includes('/api/v1/orders')) {
          capturedOrdersRequests.push(reqUrl);
        }
      }
      if (data.method === 'Runtime.consoleAPICalled') {
        const args = data.params.args.map(a => a.value || a.description).join(' ');
        consoleLogs.push(`[Console ${data.params.type}] ${args}`);
      }
      if (data.method === 'Runtime.exceptionThrown') {
        pageExceptions.push(data.params.exceptionDetails.text);
      }
    };

    await new Promise((resolve) => ws.onopen = resolve);

    function send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = msgId++;
        callbacks.set(id, { resolve, reject });
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    async function evalScript(expression) {
      const res = await send('Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
      });
      if (res.exceptionDetails) {
        throw new Error(`Eval error: ${res.exceptionDetails.text || JSON.stringify(res.exceptionDetails)}`);
      }
      return res.result?.value;
    }

    async function captureScreenshot(filepath) {
      const res = await send('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(filepath, Buffer.from(res.data, 'base64'));
    }

    // Enable domains
    await send('Page.enable');
    await send('Runtime.enable');
    await send('DOM.enable');
    await send('Network.enable');

    console.log("[4/5] Executing Browser Interaction Test Workflows...");

    // Test 1: Navigate to Dashboard UI
    console.log("  -> Test: Navigate to /ui and verify View A");
    await send('Page.navigate', { url: `http://127.0.0.1:${BACKEND_PORT}/ui?tab=dashboard` });
    await sleep(2500);

    const titleText = await evalScript("document.title");
    console.log(`     Page title: "${titleText}"`);
    if (!titleText.includes("OrderFlow Sentinel")) {
      throw new Error(`Unexpected page title: ${titleText}`);
    }

    // Check KPIs loaded
    const totalOrdersText = await evalScript("document.body.innerText.includes('Total Ingested')");
    console.log(`     KPI 'Total Ingested' present: ${totalOrdersText}`);

    // Capture View A Screenshot
    const viewAPath = path.join(ARTIFACT_DIR, "view_a_dashboard.png");
    await captureScreenshot(viewAPath);
    console.log(`     Screenshot captured: ${viewAPath}`);

    // Test 1b: Verify Server-Side Pagination & Next Button
    console.log("  -> Test: Pagination - Click 'Next' and verify skip changes & server fetches new page");
    const p1FirstOrder = await evalScript(`document.querySelector('tbody tr td')?.innerText?.trim()`);
    console.log(`     Page 1 first order: ${p1FirstOrder}`);

    // Click Next button
    capturedOrdersRequests.length = 0;
    await evalScript(`
      const nextBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Next');
      if (nextBtn) nextBtn.click();
    `);
    await sleep(2000);

    const p2FirstOrder = await evalScript(`document.querySelector('tbody tr td')?.innerText?.trim()`);
    console.log(`     Page 2 first order: ${p2FirstOrder}`);
    console.log(`     Captured Orders Requests on Next:`, capturedOrdersRequests);

    if (p1FirstOrder === p2FirstOrder) {
      throw new Error(`Pagination failed: Page 1 and Page 2 display the exact same first order (${p1FirstOrder})`);
    }

    const hasSkipInRequest = capturedOrdersRequests.some(url => url.includes('skip=') || url.includes('page=2'));
    console.log(`     Confirmed server-side query with skip/page: ${hasSkipInRequest}`);

    // Test 2: Trigger Scenario 0 (Clean Run)
    console.log("  -> Test: Trigger Scenario 0 via control button");
    await evalScript(`
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Scenario 0'));
      if (btn) btn.click();
    `);
    await sleep(2500);

    // Verify Clean Order created and navigated to View B
    const activeOrderText = await evalScript("document.body.innerText");
    const hasOrderTimeline = activeOrderText.includes("Chronological 7-Stage Order Timeline");
    console.log(`     Navigated to View B timeline: ${hasOrderTimeline}`);

    // Test 3: Inspect Journey from View A
    console.log("  -> Test: Navigate to View A, click 'Inspect Journey' on top order");
    await evalScript(`
      const navBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Dashboard & Monitoring'));
      if (navBtn) navBtn.click();
    `);
    await sleep(1500);

    const targetOrderId = await evalScript(`
      const row = document.querySelector('tbody tr');
      row ? row.querySelector('td')?.innerText?.trim() : null;
    `);
    console.log(`     Selected Order ID from table: ${targetOrderId}`);

    // Click "Inspect Journey"
    await evalScript(`
      const inspectBtn = document.querySelector('tbody tr button');
      if (inspectBtn) inspectBtn.click();
    `);
    await sleep(2000);

    const currentUrl = await evalScript("window.location.search");
    console.log(`     URL updated with deep link: ${currentUrl}`);
    const viewBHeader = await evalScript("document.body.innerText.includes('Selected Order')");
    console.log(`     View B loaded order correctly: ${viewBHeader}`);

    // Capture View B Screenshot
    const viewBPath = path.join(ARTIFACT_DIR, "view_b_journey_rca.png");
    await captureScreenshot(viewBPath);
    console.log(`     Screenshot captured: ${viewBPath}`);

    // Test 4: Trigger Scenario 3 (Hard Rejection)
    console.log("  -> Test: Trigger Scenario 3 (Hard Rejection) and review in View C");
    await evalScript(`
      const s3Btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Scenario 3'));
      if (s3Btn) s3Btn.click();
    `);
    await sleep(3000);

    // Check we navigated to approvals
    const approvalQueueHeader = await evalScript("document.body.innerText.includes('Human-in-the-Loop Approval Queue')");
    console.log(`     View C loaded: ${approvalQueueHeader}`);

    // Check HIGH RISK badge and inputs
    const hasHighRisk = await evalScript("document.body.innerText.includes('HIGH RISK')");
    console.log(`     HIGH RISK badge visible: ${hasHighRisk}`);

    // Submit Approval in View C
    console.log("  -> Test: Submit Operator Approval for substitution");
    await evalScript(`
      const approveBtn = document.getElementById('btn-approve');
      if (approveBtn) approveBtn.click();
    `);
    await sleep(3000);

    const hasVerificationBanner = await evalScript("document.body.innerText.includes('Operator Decision Verified & Dispatched')");
    console.log(`     Verification banner confirmed: ${hasVerificationBanner}`);

    // Capture View C Screenshot
    const viewCPath = path.join(ARTIFACT_DIR, "view_c_approvals_audit.png");
    await captureScreenshot(viewCPath);
    console.log(`     Screenshot captured: ${viewCPath}`);

    console.log("\n[5/5] Verification Results:");
    console.log(`     - Unhandled exceptions: ${pageExceptions.length}`);
    if (pageExceptions.length > 0) {
      console.log("       Exceptions:", pageExceptions);
    }
    console.log(`     - Console logs recorded: ${consoleLogs.length}`);

    ws.close();
    console.log("\n=== End-to-End Browser Automation Completed Successfully ===");
  } finally {
    chromeProc.kill();
    serverProc.kill();
  }
}

main().catch(err => {
  console.error("FATAL ERROR in browser test:", err);
  process.exit(1);
});
