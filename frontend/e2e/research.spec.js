import {test,expect} from '@playwright/test';

test('official title, Microsoft replay and recorded investigation work with official data',async({page})=>{
 test.setTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.getByRole('heading',{level:1})).toHaveText('Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks');
 await page.getByLabel('Data source').selectOption('microsoft');
 await expect(page.getByRole('heading',{name:'Connected incident investigation'})).toBeVisible({timeout:30000});
 await expect(page.getByRole('heading',{name:'Recorded performance timeline'})).toBeVisible();
 await page.getByRole('button',{name:'End of recording',exact:true}).click();
 await expect(page.getByRole('button',{name:'Record investigation',exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:'Record investigation',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Recorded investigation history'})).toBeVisible();
 await page.screenshot({path:'test-results/microsoft-investigation.png',fullPage:true});await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'test-results/research-overview.png'});expect(errors).toEqual([]);
});

test('RCAEval replay returns only recorded prefixes, supports pause and scores after prediction',async({page})=>{
 test.setTimeout(120000);const errors=[];page.on('pageerror',e=>errors.push(e.message));let frame;
 page.on('response',async response=>{if(response.url().includes('/api/research/replay/')&&response.ok()){const data=await response.json();frame=data;}});
 await page.goto('/');await page.getByLabel('Data source').selectOption('rcaeval');
 await expect(page.getByRole('heading',{name:'Connected incident investigation'})).toBeVisible({timeout:45000});
 await page.getByRole('button',{name:'Play recorded observations',exact:true}).click();
 await expect(page.getByRole('button',{name:'Pause replay',exact:true})).toBeVisible();await page.getByRole('button',{name:'Pause replay',exact:true}).click();
 await page.getByRole('button',{name:'End of recording',exact:true}).click();
 await expect(page.getByRole('button',{name:'Score completed recording against original labels'})).toBeEnabled({timeout:45000});
 await page.getByRole('button',{name:'Score completed recording against original labels'}).click();
 await expect(page.getByText(/Official RCAEval case index/)).toBeVisible({timeout:45000});
 expect(frame).toBeTruthy();expect(frame.histories.every(s=>s.observations.every(p=>p.timestamp<=frame.as_of))).toBeTruthy();
 await page.screenshot({path:'test-results/rcaeval-investigation.png',fullPage:true});expect(errors).toEqual([]);
});
