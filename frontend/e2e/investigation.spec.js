import {test,expect} from '@playwright/test';
test('observed dashboard renders and controlled controls are absent',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/');
 await expect(page.getByLabel('Data source')).toHaveValue('alibaba');
 await expect(page.getByText('Controlled Incident Lab',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Analyze observed data'}).click();
 await page.getByText('Source-specific metrics, topology and reconstruction evidence',{exact:true}).click();
 await expect(page.getByRole('heading',{name:'Observed metric histories'})).toBeVisible({timeout:90000});
 await page.screenshot({path:'test-results/observed-dashboard.png',fullPage:true});expect(errors).toEqual([]);
});

for(const state of ['empty','normal','deviation','unavailable']){
 test(`isolated UI fixture: ${state}`,async({page})=>{
  await page.route('**/api/alibaba/analyze',async route=>{
   if(state==='unavailable')return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Source unavailable (test fixture)'})});
   const body={source:'test_fixture_only',is_anomaly:state==='deviation',anomaly_score:state==='deviation'?.9:null,root_causes:[],affected_nodes:[],transaction:{path:[]},explanation:{narrative:'Software rendering fixture; not research evidence.'},cfao:{causal_frontier:[]},assessment:{status:state==='empty'?'insufficient_evidence':state==='normal'?'no_deviation_in_observed_metrics':'deviation_detected',evidence:[]},graph:{nodes:[],edges:[],telemetry:[],metadata:{series:{}}}};
   return route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto('/');await page.getByRole('button',{name:'Analyze observed data'}).click();
  if(state!=='unavailable')await page.getByText('Source-specific metrics, topology and reconstruction evidence',{exact:true}).click();
  await expect(page.getByText(state==='unavailable'?'Evidence unavailable':state==='empty'?'insufficient evidence':state==='normal'?'no deviation in observed metrics':'deviation detected',{exact:true})).toBeVisible();
 });
}
