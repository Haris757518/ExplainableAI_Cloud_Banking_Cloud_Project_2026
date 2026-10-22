import {test,expect} from '@playwright/test';

test('default banking page reads saved records without mutation',async({page})=>{
 const mutations=[];page.on('request',r=>{if(r.method()==='POST')mutations.push(r.url());});
 await page.goto('/');
 await expect(page.locator('.primary-nav button')).toHaveCount(2);
 await expect(page.getByRole('button',{name:'AWS Banking Analytics',exact:true})).toHaveAttribute('aria-current','page');
 await expect(page.getByText('2,482 published records in selection')).toBeVisible();
 await expect(page.getByRole('heading',{name:'Dataset evidence'})).toBeVisible();
 expect(mutations).toEqual([]);
});

test('Monzo and Starling findings retain source evidence',async({page})=>{
 await page.goto('/');await page.getByLabel('Service',{exact:true}).selectOption('Open Banking Payment Initiation');
 await page.getByRole('button',{name:'Analyze selected history'}).click();
 await expect(page.getByText('3 model-flagged deviations on the untouched final period.')).toBeVisible();
 await page.getByRole('button',{name:/2025-04-26/}).click();
 await expect(page.getByRole('heading',{name:'Evidence for 2025-04-26'})).toBeVisible();
 await expect(page.locator('aside').getByText(/Internal infrastructure cause is unknown:/)).toBeVisible();
 const url=await page.getByRole('link',{name:'Export selected CSV'}).getAttribute('href');
 const csv=await (await page.request.get(url)).text();expect(csv).toContain('published_real_bank');expect(csv).toContain('snapshot_sha256');
 await page.getByLabel('Bank',{exact:true}).selectOption('starling');
 await expect(page.getByText('28,306 records')).toBeVisible();
 await page.getByLabel('Service',{exact:true}).selectOption('Payment Initiation (Open Banking)');
 await page.getByRole('button',{name:'Analyze selected history'}).click();
 await expect(page.getByText('0 model-flagged deviations on the untouched final period.')).toBeVisible();
});

test('research preserves recorded sources and fresh GNN comparison',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.getByRole('button',{name:'AI Research & Validation',exact:true}).click();
 await expect(page.getByLabel('Data source')).toHaveValue('alibaba');
 await page.getByRole('button',{name:'Measured research results',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Compatible Alibaba graph comparison'})).toBeVisible();
 await expect(page.getByRole('img',{name:'Training and validation reconstruction loss by epoch'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Independent mechanism evaluation'})).toBeVisible();
 expect(errors).toEqual([]);
});

