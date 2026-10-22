import {test,expect} from '@playwright/test';

test('banking replay explains deeper causes and separates recovery from permanent correction',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await page.getByRole('button',{name:'Run banking investigation',exact:true}).click();
 await expect(page.getByRole('heading',{name:'The displayed balance missed a committed transfer',exact:true})).toBeVisible();
 for(const title of ['What went wrong?','Where did it start?','Why did it happen?','What is the deeper cause?','What should be done?','Did recovery work?'])await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible();
 await expect(page.getByText('A permanent application fix has not been implemented.',{exact:false}).first()).toBeVisible();
 const selector=page.getByLabel('Choose a finding');
 await selector.selectOption('capacity');
 await expect(page.getByRole('heading',{name:'Payments slowed while processing capacity fell',exact:true})).toBeVisible();
 await expect(page.getByText('The recorded processor allowance fell from 0.5 to 0.02 CPU cores.',{exact:false})).toBeVisible();
 await selector.selectOption('database');
 await expect(page.getByRole('heading',{name:'Payments waited for the database',exact:true})).toBeVisible();
 await selector.selectOption('traffic');
 await expect(page.getByRole('heading',{name:'More payment requests arrived and responses slowed',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Download the readable investigation report'})).toHaveAttribute('href','/api/cloud-investigation/banking-report');
 await expect(page.locator('pre:visible')).toHaveCount(0);
 expect(errors).toEqual([]);
});

test('Banking Investigation shows verified recorded AWS evidence without live-health claims or writes',async({page})=>{
 const writes=[];page.on('request',r=>{if(r.method()==='POST')writes.push(r.url());});
 await page.goto('/');
 await expect(page.locator('.primary-nav button')).toHaveCount(2);
 await expect(page.getByRole('button',{name:'Banking Investigation',exact:true})).toHaveAttribute('aria-current','page');
 await expect(page.getByRole('heading',{name:'Banking Investigation Monitor'})).toBeVisible();
 await expect(page.locator('.health-metrics strong')).toHaveText(['8','Unknown','1769','1']);
 await expect(page.getByText('Retained measurements · not a live health feed',{exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Verified first AWS banking transfer',exact:true})).toBeVisible();
 await expect(page.locator('pre:visible')).toHaveCount(0);
 expect(writes).toEqual([]);
});

test('recorded investigation explains evidence and abstains from invented recovery',async({page})=>{
 test.setTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.getByRole('button',{name:'Explore recorded root-cause investigations'}).click();
 await page.getByRole('button',{name:'Run guided investigation'}).click();
 await expect(page.getByRole('heading',{name:'Incident investigation',exact:true})).toBeVisible({timeout:60000});
 for(const name of ['What happened?','Why did it happen?','What should we do?','Did it work?'])await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();
 await expect(page.getByText('Not verified',{exact:true})).toBeVisible();
 await expect(page.locator('pre:visible')).toHaveCount(0);
 await page.getByRole('button',{name:'All evidence',exact:true}).click();
 await expect(page.getByRole('heading',{name:'How PROBE-XAI investigated'})).toBeVisible();
 await page.getByText('Competing explanations and missing measurements',{exact:true}).click();
 await expect(page.getByText('demand exceeds capacity',{exact:true})).toBeVisible();
 expect(errors).toEqual([]);
});

test('research results and public banking reference remain separate',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Research & Validation',exact:true}).click();
 await page.getByRole('button',{name:'Model results',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Completed PROBE-XAI comparisons'})).toBeVisible();
 await expect(page.getByText('gnn probe xai',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Datasets',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Separate research partitions'})).toBeVisible();
 await page.getByText('Explore published bank performance history',{exact:true}).click();
 await expect(page.getByRole('heading',{name:'Real Banking Performance',exact:true})).toBeVisible();
});
