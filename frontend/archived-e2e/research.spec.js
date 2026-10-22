import {test,expect} from '@playwright/test';
const title='Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks';
test('Microsoft preserves anomaly capabilities and research evidence is accessible',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Research Validation',exact:true}).click();await expect(page.getByRole('heading',{level:1})).toHaveText(title);
 await page.getByLabel('Data source').selectOption('microsoft');
 await expect(page.getByRole('heading',{name:'Recorded performance timeline'})).toBeVisible({timeout:30000});
 await page.getByRole('button',{name:'End of recording',exact:true}).click();
 await expect(page.getByRole('button',{name:'Record investigation',exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:'Record investigation',exact:true}).click();
 await page.getByRole('button',{name:'Measured research results',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Measured research results'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Independent mechanism evaluation'})).toBeVisible();
 await expect(page.getByText(/All 30 V3 held-out RCAEval cases/)).toBeVisible();
});

for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
 test(`guided real-recording walkthrough at ${viewport.width}`,async({page})=>{
  test.setTimeout(120000);await page.setViewportSize(viewport);const errors=[];page.on('pageerror',e=>errors.push(e.message));let latest;
  page.on('response',async r=>{if(r.url().includes('/api/research/replay/')&&r.ok())latest=await r.json()});
  await page.goto('/');await page.getByRole('button',{name:'Research Validation',exact:true}).click();await page.getByLabel('Data source').selectOption('rcaeval');
  await expect(page.getByRole('heading',{name:'Recorded performance timeline'})).toBeVisible({timeout:45000});
  await page.getByRole('button',{name:'Guided Demo',exact:true}).click();
  await expect(page.getByRole('button',{name:'Play recorded observations',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Play recorded observations',exact:true}).click();
  await expect(page.getByRole('button',{name:'Pause replay',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Pause replay',exact:true}).click();
  await page.getByRole('button',{name:'End of recording',exact:true}).click();
  await expect(page.getByRole('button',{name:'Reveal published annotation',exact:true})).toBeEnabled({timeout:45000});
  await expect(page.getByRole('navigation',{name:'Investigation progress'})).toBeVisible();
  await page.getByRole('navigation',{name:'Investigation progress'}).getByRole('button').nth(1).click();
  await expect(page.getByRole('heading',{name:'Why this resource leads'})).toBeVisible();
  await page.locator('.rank-list button').first().click();
  await page.getByRole('navigation',{name:'Investigation progress'}).getByRole('button').nth(2).click();
  await expect(page.getByRole('heading',{name:'Why this happened'})).toBeVisible();
  await expect(page.getByRole('img',{name:'Measured values, historical reference, and distinct forecast'})).toBeVisible();
  await page.screenshot({path:`test-results/investigation-${viewport.width}.png`,fullPage:true});
  await page.getByRole('navigation',{name:'Investigation progress'}).getByRole('button').nth(3).click();
  await expect(page.getByRole('heading',{name:'What should be checked next'})).toBeVisible();
  await page.getByRole('navigation',{name:'Investigation progress'}).getByRole('button').nth(4).click();
  await page.getByRole('button',{name:'Reveal published annotation',exact:true}).click();
  await expect(page.getByText('Published injected type',{exact:true})).toBeVisible({timeout:45000});
  expect(latest.histories.every(s=>s.observations.every(p=>p.timestamp<=latest.as_of))).toBeTruthy();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);expect(overflow).toBeFalsy();expect(errors).toEqual([]);
 });
}

test('RE2 graph comes only from actual recorded spans',async({page})=>{
 test.setTimeout(90000);await page.goto('/');await page.getByRole('button',{name:'Research Validation',exact:true}).click();await page.getByLabel('Data source').selectOption('rcaeval');
 await page.getByRole('button',{name:'Guided Demo',exact:true}).click();
 await page.getByLabel('Published recording').selectOption({label:'Recorded trace dependencies (RE2)'});
 await expect(page.getByRole('button',{name:'End of recording',exact:true})).toBeVisible({timeout:45000});
 await page.getByRole('button',{name:'End of recording',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Recorded dependency evidence'})).toBeVisible({timeout:45000});
 await expect(page.getByRole('img',{name:'Recorded service relationships'})).toBeVisible();
 await page.screenshot({path:'test-results/re2-evidence-graph.png',fullPage:true});
});

test('authenticated AWS credentials never imply resource health',async({page})=>{
 await page.route('**/api/aws/status',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({connected:true,region:'us-east-1'})}));
 await page.route('**/api/aws/analyze',r=>r.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Resource discovery denied: EC2 UnauthorizedOperation; RDS AccessDenied (isolated UI test)'})}));
 await page.goto('/');await page.getByRole('button',{name:'Research Validation',exact:true}).click();await page.getByRole('button',{name:'Cloud Monitoring',exact:true}).click();
 await page.getByRole('button',{name:'Analyze observed data',exact:true}).click();
 await expect(page.getByText('Cloud resource monitoring unavailable.',{exact:true})).toBeVisible();
 await expect(page.getByText('Authenticated',{exact:true})).toBeVisible();
 await expect(page.getByText('Healthy',{exact:true})).toHaveCount(0);
});
for(const state of ['no_deviation_in_observed_metrics','insufficient_evidence']){
 test('compact state: '+state,async({page})=>{
  await page.route('**/api/research/replay/**',async route=>{
   const r=await route.fetch();const d=await r.json();d.incident.status=state;d.incident.candidates=[];d.incident.recommendations=[];
   await route.fulfill({response:r,json:d});
  });
  await page.goto('/');await page.getByRole('button',{name:'Research Validation',exact:true}).click();await page.getByLabel('Data source').selectOption('microsoft');
  await expect(page.getByRole('heading',{name:state==='insufficient_evidence'?'More recorded observations are required before this analysis can be performed.':'No significant deviation detected in the available measurements.'})).toBeVisible({timeout:30000});
  await expect(page.getByRole('heading',{name:'Why this happened'})).toHaveCount(0);
  await expect(page.getByRole('navigation',{name:'Investigation progress'})).toHaveCount(0);
 });
}
