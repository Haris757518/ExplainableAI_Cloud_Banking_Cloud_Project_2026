import {test,expect} from '@playwright/test';
test('approved live demo controls execute a bounded fault and verify integrity',async({page})=>{
 test.skip(process.env.RUN_LIVE_DEMO!=='1','Requires the explicitly approved running AWS research instance');
 test.setTimeout(240000);
 await page.goto('/');
 await page.getByRole('button',{name:'Run test',exact:true}).click();
 await expect(page.getByRole('note')).toHaveText('Complete',{timeout:60000});
 await expect.poll(async()=>{const r=await page.request.get('/api/live-banking/status');return (await r.json()).status;},{timeout:90000}).toBe('normal');
 await page.getByRole('button',{name:'Inject fault',exact:true}).click();
 await expect(page.getByRole('status')).toHaveText('Anomaly',{timeout:60000});
 await page.screenshot({path:'test-results/live-anomaly.png',fullPage:true});
 await expect(page.getByRole('note')).toHaveText('Complete',{timeout:60000});
 await expect(page.getByRole('status')).toHaveText('Normal',{timeout:90000});
 await page.getByRole('button',{name:'Verify recovery',exact:true}).click();
 await expect(page.getByRole('note')).toHaveText('Balances match the ledger. No duplicate history IDs or database blocking.',{timeout:60000});
 await page.screenshot({path:'test-results/live-verified.png',fullPage:true});
});
