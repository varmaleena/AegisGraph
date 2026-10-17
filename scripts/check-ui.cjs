/* Explicit opt-in live-provider verification. No fixture responses and no claimed benchmark numbers. */
const {chromium,expect}=require(require("node:module").createRequire(require("node:path").resolve("frontend/package.json")).resolve("@playwright/test"));
const assert=require("node:assert/strict");
(async()=>{
 if(!process.argv.includes("--live"))throw Error("This check makes real model requests. Run node scripts/check-ui.cjs --live after configuring your free-tier key and resetting beta.");
 const config=await (await fetch("http://localhost:8000/api/evidence?tenant=tenant_beta")).json();
 if(!config.model.configured)throw Error("Configure a real model key first. No scripted fallback is available.");
 const browser=await chromium.launch({...(process.platform==="win32"?{channel:"msedge"}:{}),headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1100},recordVideo:{dir:"docs/recordings",size:{width:1440,height:1100}}});
  const page=await context.newPage();const errors=[];
  page.on("pageerror",e=>errors.push(e.message));page.setDefaultTimeout(240000);
  await page.goto("http://localhost:3001/?tenant=tenant_beta",{waitUntil:"domcontentloaded"});
  await page.getByText("FalkorDB connected").waitFor();
  await page.getByLabel("Simulate crash at step 3").check();
  await page.getByRole("button",{name:/Investigate checkout incident/}).click();
  await page.getByText(/CRASH_SIMULATED: worker stopped/).waitFor();
  await page.getByRole("button",{name:"Resume from FalkorDB",exact:true}).click();
  await expect(page.locator(".benchmark-scroll tbody tr").first()).toContainText("COMPLETED");
  await page.screenshot({path:"docs/v2-live-discovery.png",fullPage:true});
  await page.getByLabel("Simulate crash at step 3").uncheck();
  await page.getByRole("button",{name:/New session.*replay memory/}).click();
  await page.getByText(/Verified playbook replay restored/).waitFor();
  await expect(page.locator(".benchmark-scroll tbody tr").nth(1)).toContainText("COMPLETED");
  await page.getByRole("button",{name:/Inject security directive/}).click();
  await expect(page.getByRole("button",{name:/Inject security directive/})).toBeEnabled();
  await page.getByRole("button",{name:/Investigate checkout incident/}).click();
  await expect(page.locator(".benchmark-scroll tbody tr").nth(2)).toContainText("COMPLETED");
  await expect(page.locator(".benchmark-scroll tbody tr").nth(2)).toContainText("REJECTED_REPLAY_REINVESTIGATION");
  await page.screenshot({path:"docs/v2-live-benchmark.png",fullPage:true});
  assert.deepEqual(errors,[]);
  await context.close();await page.video().saveAs("docs/v2-live-demo.webm");
  console.log("PASS: live model discovery, real MCP, crash/resume, warm replay, stale-policy rejection and v2 recompilation");
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1});