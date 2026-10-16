import {test,expect} from '@playwright/test';
test('banking is primary; real balance, atomic transfer, duplicate retry and history work',async({page})=>{
 test.setTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/');
 await expect(page.getByRole('button',{name:'Digital Banking',exact:true})).toHaveAttribute('aria-current','page');
 await expect(page.getByRole('heading',{name:'Digital Banking Performance Intelligence'})).toBeVisible();
 await expect(page.getByText('Cart Service',{exact:true})).toHaveCount(0);
 await page.getByLabel('Transaction type').selectOption('balance');
 await expect(page.getByRole('button',{name:'Execute test operation',exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:'Execute test operation',exact:true}).click();await expect(page.getByText(/test units$/)).toBeVisible();
 await page.getByLabel('Transaction type').selectOption('transfer');
 await expect(page.getByRole('button',{name:'Execute test operation',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Execute test operation',exact:true}).click();await expect(page.getByText(/Ledger and both balances updated/)).toBeVisible();
 await page.getByRole('button',{name:'Retry same transfer ID'}).click();await expect(page.getByText(/no second debit/)).toBeVisible();
 await page.getByLabel('Transaction type').selectOption('history');await expect(page.getByRole('button',{name:'Execute test operation',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Execute test operation',exact:true}).click();
 await expect(page.getByText(/most recent test transfers/)).toBeVisible();expect(errors).toEqual([]);
});

for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
 test(`measured banking investigation and independent verification ${viewport.width}`,async({page})=>{
  test.setTimeout(180000);await page.setViewportSize(viewport);const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/');
  await expect(page.getByRole('button',{name:'Run 12-second application delay',exact:true})).toBeEnabled({timeout:60000});
  const triggered=page.waitForResponse(r=>r.url().endsWith('/api/banking/experiments/application-delay')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Run 12-second application delay',exact:true}).click();const job=(await (await triggered).json()).job_id;
  await expect.poll(async()=>{const response=await page.request.get('/api/banking/state');const d=await response.json();return d.jobs.find(j=>j.id===job)?.status},{timeout:90000,intervals:[2000]}).toBe('completed');
  await expect(page.getByRole('button',{name:'Reveal completed experiment annotation',exact:true})).toBeEnabled({timeout:30000});
  const verifiedResponse=page.waitForResponse(r=>r.url().includes('/api/banking/verify/'+job));
  await page.getByRole('button',{name:'Reveal completed experiment annotation',exact:true}).click();const verified=await (await verifiedResponse).json();
  expect(verified.detection_status).toBe('deviation_detected');expect(verified.service_match).toBe(true);expect(verified.mechanism_match).toBe(true);
  await expect(page.getByText('Matches independently recorded condition',{exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Independent verification and recovery'})).toBeVisible();
  await page.getByRole('navigation',{name:'Investigation progress'}).getByRole('button').nth(2).click();
  await expect(page.getByRole('heading',{name:'Why this happened'})).toBeVisible();
  await page.getByRole('heading',{name:'Why this happened'}).scrollIntoViewIfNeeded();
  await page.screenshot({path:`test-results/banking-investigation-${viewport.width}.png`,fullPage:true});
  await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:`test-results/banking-overview-${viewport.width}.png`});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBeFalsy();expect(errors).toEqual([]);
 });
}

test('banking study and preserved benchmark evidence are separately accessible',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Research Validation',exact:true}).click();await page.getByRole('button',{name:'Measured research results',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Independent measured banking validation'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Measured research results'})).toBeVisible();
 await expect(page.getByText(/All 30 V3 held-out RCAEval cases/)).toBeVisible();
});
