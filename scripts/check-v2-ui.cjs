const {chromium}=require(require("node:module").createRequire(require("node:path").resolve("frontend/package.json")).resolve("@playwright/test"));
const assert=require("node:assert/strict");
(async()=>{
 const browser=await chromium.launch({...(process.platform==="win32"?{channel:"msedge"}:{}),headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on("pageerror",e=>errors.push(e.message));
  await page.goto("http://localhost:3001/?tenant=tenant_beta",{waitUntil:"domcontentloaded"});
  await page.getByText("FalkorDB connected").waitFor();
  await page.getByText("EMPIRICAL TELEMETRY & REPLAY BENCHMARK",{exact:true}).waitFor();
  const config=await (await fetch("http://localhost:8000/api/evidence?tenant=tenant_beta")).json();
  await page.getByText(config.model.configured?/MODEL CONFIGURED/:/API KEY REQUIRED/).waitFor();
  await page.getByLabel("Simulate crash at step 3").check();
  if(!config.model.configured){
   await page.getByRole("button",{name:/Investigate checkout incident/}).click();
   await page.getByRole("alert").filter({hasText:/Configure.*API key/}).waitFor();
   await page.getByRole("button",{name:"Dismiss error"}).click();
  }
  const response=page.waitForResponse(r=>r.url().includes("/api/security-policy")&&r.request().method()==="POST");
  await page.getByRole("button",{name:/Inject security directive/}).click();
  assert.equal((await response).status(),200);
  await page.waitForFunction(()=>!document.querySelector(".v2-controls button").disabled);
  await page.screenshot({path:"docs/v2-desktop.png",fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:"docs/v2-mobile.png",fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);
  console.log("PASS: V2 telemetry/evidence, honest missing-key error, crash toggle, security action, mobile overflow, no page errors");
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});