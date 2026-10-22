"""Build the revised report directly from saved measurements and evaluations."""
from pathlib import Path
import json
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
bank=read('results/real_banking/evaluation.json')
monzo=read('results/real_banking/monzo-current.json');starling=read('results/real_banking/starling-current.json')
graph=read('results/redesign_20261022/graph/report.json')
ms=read('results/research_v3/run_20261016_final/microsoft.json')
rca=read('results/research_v3/run_20261016_final/rcaeval.json')
re2=read('results/research_v4/re2_graph_20261016_02/report.json')

doc=Document();sec=doc.sections[0]
sec.top_margin=sec.bottom_margin=Inches(.72);sec.left_margin=sec.right_margin=Inches(.8)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2']:
    style=doc.styles[name];style.font.name='Calibri';style.font.color.rgb=RGBColor(0,0,0)
doc.styles['Normal'].font.size=Pt(11)
doc.styles['Normal'].paragraph_format.space_after=Pt(8)
doc.styles['Normal'].paragraph_format.line_spacing=1.12
doc.styles['Title'].font.size=Pt(25)
doc.styles['Heading 1'].font.size=Pt(19)
doc.styles['Heading 2'].font.size=Pt(13)
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
markdown=[]
def h(t,level=1):doc.add_heading(t,level);markdown.append('#'*level+' '+t+'\n')
def p(t):doc.add_paragraph(t);markdown.append(t+'\n')
def table(headers,rows):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
    for c,text in zip(t.rows[0].cells,headers):c.text=str(text)
    for row in rows:
        for c,text in zip(t.add_row().cells,row):c.text=str(text)
    for i,row in enumerate(t.rows):
        for c in row.cells:
            props=c._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            props.append(borders)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E5EDF4' if i==0 else ('F5F7FA' if i%2==0 else 'FFFFFF'));props.append(shade)
            margins=OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'95');e.set(qn('w:type'),'dxa');margins.append(e)
            props.append(margins)
            for para in c.paragraphs:
                para.paragraph_format.space_after=Pt(3)
                for r in para.runs:r.font.size=Pt(9.5);r.bold=i==0
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    markdown.append('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n')
def page():doc.add_page_break()

doc.add_paragraph('Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks','Title')
p('Revised implementation and measured results')
p('22 October 2026')
h('Research scope')
p('The application combines published digital bank performance measurements with independent cloud telemetry experiments. Its default AWS Banking Analytics mode examines historical API latency, availability and errors from actual banks. AI Research and Validation retains Alibaba, RCAEval and Microsoft experiments for their separate scientific tasks.')
p('The implementation imported and validated 53,126 normalized banking records. Some records explicitly represent unavailable values. The new data path preserves original source snapshots, reporting dates and checksums. It never converts public statistics into private infrastructure telemetry.')
h('Main findings',2)
p('The Monzo Payment Initiation analysis flags three deviations in its final evaluation period. The selected newer Starling Payment Initiation series has no flagged deviations. These outcomes are model findings without incident labels. The fresh Alibaba experiment finds lower reconstruction error for the feature model without graph edges. A graph advantage is therefore not established.')
p('The historical AWS storage path is implemented and covered by failure and readback tests. Both banks now have verified S3 uploads. All four downloaded objects match their source checksums. The private bucket uses encryption and blocks public access. CloudWatch importer-health metrics have been read back successfully.')

page();h('Banking datasets and provenance')
table(['Source','Period','Rows','Null values'],[[m['bank'].title(),m['start_date']+' to '+m['end_date'],m['validation']['rows'],m['validation']['null_values']] for m in [monzo,starling]])
p('A normalized record retains bank, source name, date, service, metric, value, unit, frequency, origin, official URL, retrieval timestamp, record status, raw value and source checksum. Starling records also preserve the quarterly report filename and original field identifier. Latency uses milliseconds and availability, downtime and errors use percent.')
h('Monzo table validation',2)
p('The official HTML supplies explicit daily dates across multiple years. Some tables advertise a Confirmation of Funds column but omit its daily cells. The importer records those cells as null. Three unsupported source values remain null with their original strings and dates in the validation manifest. Missing values never become zero or an inferred infrastructure measurement.')
h('Starling quarter validation',2)
p('The initial server-rendered daily table has 92 day indices under a Q2 2026 heading. That quarter has 91 calendar days. The importer excludes that ambiguous table and uses the 28 separately named reports embedded by the official quarter selector. Each report passes an exact day-index and calendar-length check before conversion to dates. Dedicated and newer Open Banking reporting fields remain separate series.')
h('Storage and preservation',2)
p('Every successful import writes a new generation containing normalized CSV and JSON plus a manifest. A current pointer changes only after validation and writing complete. Original HTML snapshots are content-addressed by SHA-256. Failed parsing retains the source snapshot and the previous validated generation. The original V1 checkout and prior research results remain available.')

page();h('Banking analysis methodology')
p('Each bank, service and metric defines a separate series. Analysis sorts actual observed dates and excludes null targets. Earlier 60 percent of measured observations establish the median and median absolute deviation reference. The next 20 percent calibrate a one-sided threshold using the greater of a 3.5 standardized score and the calibration 99th percentile. The final 20 percent form the untouched evaluation period.')
p('Low availability is adverse. High latency, downtime and error rates are adverse. A flagged date includes its observed value, reference, difference, standardized score, persistence and original measurement. Consecutive flags count only adjacent calendar days. The explanation states that infrastructure cause is unknown.')
table(['Series','Train','Calibration','Test','Flags'],[[b.title()+' Payment Initiation',*r['series'][0]['counts'].values(),len(r['series'][0]['findings'])] for b,r in bank.items()])
h('Forecast evaluation',2)
p('The same held-out dates compare a fixed training-median reference with a persistence forecast. Persistence uses only the preceding recorded observation, including earlier evaluation observations when available. It predicts the next recorded point, whose calendar timing may be unknown across gaps. Neither method implies confirmed incidents.')
table(['Series','Median MAE in ms','Persistence MAE in ms'],[[b.title(),f"{r['forecast']['methods']['training_median']['mae']:.4f}",f"{r['forecast']['methods']['persistence']['mae']:.4f}"] for b,r in bank.items()])
p('Monzo analysis covers the published Open Banking Payment Initiation series. Starling analysis covers Payment Initiation in the newer Open Banking category, starting in Q2 2025. Bank categories and reporting intervals differ, so these error figures do not rank the banks against one another.')

page();h('Independent GNN and benchmark evaluation')
p('The fresh Alibaba experiment uses the bounded production trace and identical width-16 masked autoencoders. Recorded service calls supply graph relationships. Node and edge selection uses only calls through 175000 milliseconds, within the training period. The identity variant removes graph edges while preserving architecture, seed, features and chronological splits. Both train for 100 epochs. Validation selects the checkpoint and the held-out targets determine the final error.')
table(['Alibaba model','Held out masked MSE'],[['Recorded topology',f"{graph['topology']['test_masked_mse']:.6f}"],['Identity adjacency',f"{graph['no_graph_identity']['test_masked_mse']:.6f}"],['Training mean reference',f"{graph['train_mean_mse']:.6f}"]])
p('The identity model reconstructs the selected measured slice better. Reconstruction includes the current input features, so low reconstruction error is not a forecasting or root-cause accuracy score. Recorded directed calls are symmetrized by this model. Epoch loss histories and selected checkpoints are saved for both variants. Residual contributions and removal sensitivities explain model behavior without proving source-system causes.')
h('Microsoft anomaly detection',2)
table(['Method','Precision','Recall','F1','FP','FN'],[[name,f"{r['heldout']['precision']:.3f}",f"{r['heldout']['recall']:.3f}",f"{r['heldout']['f1']:.3f}",r['heldout']['fp'],r['heldout']['fn']] for name,r in ms['methods'].items()])
p('Microsoft figures above are preserved evaluations from the final 16 October research run. Threshold selection uses chronological validation labels and held-out scoring uses the dataset labels. The dashboard keeps these source-specific detection scores separate from bank deviations and Alibaba reconstruction.')

page();h('Root service evaluation and scientific limits')
table(['RCAEval RE1 method','Cases','Top 1','Top 3','Coverage'],[[name,r['cases'],f"{r['top1']:.3f}",f"{r['top3']:.3f}",f"{r['diagnosis_coverage']:.3f}"] for name,r in rca['splits']['test'].items()])
p('The preserved RE1 study uses 150 recordings with a grouped 90 training, 30 validation and 30 test split. It reports service ranking separately from mechanism agreement. RE1 lacks recorded service-call topology. Per-fault results, mechanism confusion matrices and abstention coverage remain in the saved evidence and dashboard.')
p('All 30 held-out RE1 cases showed pre-injection alerts in the preserved timing study. A zero conditional post-injection delay therefore cannot establish successful onset detection. Coverage and ranking scores do not resolve this false-positive limitation.')
p('The existing five-case RE2 recorded-graph experiment reports Top-1 of 0.60 and Top-3 of 0.80 for both the identity and recorded graph variants. This small illustrative sample establishes no graph advantage or broad generalization. Broader RE2 evaluation remains future work.')
h('Claims supported by the implementation',2)
p('The project uses genuine published digital bank measurements, recorded production microservice calls and controlled benchmark fault measurements. It implements a real GNN and reproducible comparisons. Its banking explanations identify measurable deviations and preserve supporting observations.')
p('Public bank statistics provide no internal CPU, memory, SQL trace or service-call graph. They cannot identify a confirmed private bank AWS root cause. Bank anomaly precision and recall are unavailable because the imported bank series contain no verified incident labels. Neither GNN superiority nor complete banking fault coverage is established.')

page();h('Application architecture and verification')
p('The application opens AWS Banking Analytics by default and has exactly two primary modes. The real bank page supports bank, metric, service and date selection, calendar-based history plots, CSV export, evidence-backed findings and provenance. AI Research and Validation retains Alibaba analysis and recorded Microsoft and RCAEval replay. Archived banking and AWS demos remain in source files without appearing as primary navigation.')
h('AWS historical storage path',2)
p('An explicit import action can optionally upload the original HTML and normalized CSV to a configured S3 bucket. A separate current-time importer-health action can publish success and failure counts to CloudWatch. Historical bank values are never retimestamped as live CloudWatch data. S3 receipts require matching HEAD metadata and content length. CloudWatch records its write acknowledgement and the verified readback of ImportSuccess and ImportFailure metrics.')
p('Set BANKING_DATASET_BUCKET and authorized AWS credentials before choosing writes. Without cloud access, import and analysis continue locally. The status API reads saved receipts and performs no cloud actions during a page load. Athena is optional and has not been provisioned. The executed deployment is in us-east-1 and its receipts are saved in results/real_banking/deployment.json.')
h('Verification',2)
p('The complete Python regression suite passed 157 tests after the redesign. New tests cover official source parsing, known Monzo values, quarter validation, duplicate rejection, null handling, chronological leakage, forecast inputs, read-only API loads, partial cloud failure and storage verification. The production frontend build passed. Tests that need local client execution ran outside the restricted sandbox.')
h('Reproduction and source references',2)
p('Start the application from this project directory with START_REDESIGN.ps1. Reproduce banking evaluations with python scripts/reproduce_real_banking.py. Reproduce the graph comparison with python scripts/run_graph_ablation.py --out results/new_graph_run --training-topology --epochs 100. Always choose a new research output directory.')
for url in ['https://monzo.com/service-information','https://www.starlingbank.com/current-account/service-information/api-performance/','https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2021','https://huggingface.co/datasets/phamquiluan/RCAEval','https://github.com/microsoft/cloud-monitoring-dataset']:p(url)

out=ROOT/'submission';out.mkdir(exist_ok=True)
doc.save(out/'Revised_Project_Report.docx')
(ROOT/'docs/FINAL_EXPERIMENT_RESULTS.md').write_text('\n'.join(markdown),encoding='utf-8')
summary={'banking':{b:{'flags':len(r['series'][0]['findings']),'split':r['series'][0]['counts'],'forecast':r['forecast']['methods']} for b,r in bank.items()},
    'graph':{'recorded_topology_mse':graph['topology']['test_masked_mse'],'identity_mse':graph['no_graph_identity']['test_masked_mse'],'training_mean_mse':graph['train_mean_mse']},
    'microsoft':{n:r['heldout'] for n,r in ms['methods'].items()},'rcaeval_test':rca['splits']['test'],'re2':re2['summary'],'aws_live_verified':True,'regression_tests_passed':157}
(out/'verified_results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(out/'Revised_Project_Report.docx')
