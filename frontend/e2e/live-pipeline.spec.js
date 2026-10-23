import {test,expect} from '@playwright/test';
test('live graph, selected fault, GNN, deeper lock cause and integrity verification',async({page})=>{
 test.skip(process.env.RUN_LIVE_DEMO!=='1','Explicit approved live AWS test only');test.setTimeout(180000);
 await page.goto('/');
 await expect(page.getByRole('status')).toHaveText('Normal',{timeout:60000});
 await page.getByLabel('Fault type').selectOption('fault');
 await page.getByRole('button',{name:'Inject fault',exact:true}).click();
 await expect(page.getByRole('status')).toHaveText('Anomaly',{timeout:60000});
 await expect(page.getByText('Symptom rank:',{exact:false})).toBeVisible({timeout:30000});
 await expect(page.getByText('An open transaction holds an exclusive lock',{exact:false})).toBeVisible({timeout:30000});
 await expect(page.getByRole('img',{name:'Measured payment latency and alert threshold over time'})).toBeVisible();
 await page.screenshot({path:'test-results/final-live-pipeline.png',fullPage:true});
 await expect(page.getByRole('note')).toHaveText('Complete',{timeout:60000});
 await expect(page.getByRole('status')).toHaveText('Normal',{timeout:60000});
 await page.getByRole('button',{name:'Verify recovery',exact:true}).click();
 await expect(page.getByRole('note')).toHaveText('Balances match the ledger. No duplicate history IDs or database blocking.',{timeout:60000});
});
