import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=path.dirname(fileURLToPath(import.meta.url));
const p=JSON.parse(await fs.readFile(path.join(out,'workbooks.json'),'utf8'));
const summary=JSON.parse(await fs.readFile(path.join(out,'summary.json'),'utf8'));
function col(n){let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function literal(v){return typeof v==='string'&&v.startsWith('=')?"'"+v:v;}
function sheet(w,name,headers,rows,widths={}){
 const s=w.worksheets.add(name);s.showGridLines=false;
 s.getRange(`A1:${col(headers.length-1)}${rows.length+1}`).values=[headers,...rows.map(r=>r.map(literal))];
 const all=s.getUsedRange();all.format.font.name='Arial';all.format.font.size=10;all.format.wrapText=true;all.format.verticalAlignment='top';all.format.rowHeight=54;all.format.columnWidth=24;
 for(const [c,width] of Object.entries(widths))s.getRange(`${c}1:${c}${rows.length+1}`).format.columnWidth=width;
 const h=s.getRange(`A1:${col(headers.length-1)}1`);h.format.fill='#172033';h.format.font.bold=true;h.format.font.color='#FFFFFF';h.format.horizontalAlignment='center';h.format.rowHeight=42;
 s.freezePanes.freezeRows(1);return s;
}
const review=Workbook.create();
const s=sheet(review,'مراجعة جديدة',p.new_headers,p.new_rows,{A:28,B:18,C:80,D:30,E:50});
s.getRange('D2:E251').format.fill='#FFF4CE';s.getRange('D2:E251').format.font.color='#1D4ED8';
s.getRange('C2:E251').format.horizontalAlignment='right';
s.getRange('D2:D251').dataValidation={rule:{type:'list',values:['Current Customer','Potential Customer','Target Customer','New Customer','Former Customer','Not Interested','No Meeting','Unclassified']}};
s.tables.add('A1:E251',true,'FreshHumanReview');s.freezePanes.freezeColumns(3);
for(let i=0;i<p.new_rows.length;i++)s.getRange(`A${i+2}:E${i+2}`).format.rowHeight=Math.min(409,Math.max(56,Math.ceil(p.new_rows[i][2].length/75)*15));
const m=sheet(review,'طريقة الاختيار',['البند','التفاصيل'],p.new_methods,{A:28,B:110});m.getRange(`B2:B${p.new_methods.length+1}`).format.horizontalAlignment='right';
review.recalculate();
console.log((await review.inspect({kind:'region',sheetId:s.name,range:'C1:E4',maxChars:600})).ndjson);
for(const [name,range,file] of [[s.name,'B1:E5','fresh_review_preview.png'],[m.name,'A1:B6','fresh_method_preview.png']]){
 const img=await review.render({sheetName:name,range,scale:1.2,format:'png'});await fs.writeFile(path.join(out,file),new Uint8Array(await img.arrayBuffer()));
}
if (!(await fs.stat(path.join(out,'independent_human_review_250.xlsx')).catch(()=>null))) await (await SpreadsheetFile.exportXlsx(review)).save(path.join(out,'independent_human_review_250.xlsx'));
const analysis=Workbook.create();
const totals=['الإجمالي',summary.validated_human_rows,summary.agreement_before,summary.agreement_after,summary.agreement_before/summary.validated_human_rows,summary.agreement_after/summary.validated_human_rows];
const metric=sheet(analysis,'اتفاق عينة التطوير',p.metric_headers,[...p.metric_rows,totals],{A:29,B:20,C:20,D:20,E:20,F:20});metric.getRange('E2:F10').setNumberFormat('0.0%');
const ah=['صف الملف','معرف الزيارة','النص الأصلي','التصنيف البشري المعتمد','ملاحظة المراجع','قبل التعديل','بعد النص فقط','بعد مرجع الموزع','السبب الجديد','وسوم الاختلاف'];
const detail=sheet(analysis,'الاعتمادات والتفسير',ah,p.agreement_rows,{A:12,B:30,C:80,D:26,E:70,F:26,G:26,H:26,I:110,J:30});
const remaining=sheet(analysis,'اختلافات باقية',ah,p.remaining_rows,{A:12,B:30,C:80,D:26,E:70,F:26,G:26,H:26,I:110,J:30});
const trans=sheet(analysis,'انتقالات الحالات',p.transition_headers,p.transition_rows,{A:28,B:28,C:22});
const conflicts=sheet(analysis,'تعارض مع الحفظ اليدوي',p.manual_conflict_headers,p.manual_conflict_rows,{A:12,B:30,D:80,E:26,F:70,J:110});
const method=sheet(analysis,'دليل القياس',['البند','التفاصيل'],[
 ['اسم القياس','اتفاق على عينة التطوير. ليست دقة مستقلة بعد استخدام التصحيحات في ضبط القواعد.'],
 ['المرجع البشري','عمود التصنيف البشري المعتمد وملاحظات المراجع في النسخة المرجعية المحفوظة فقط.'],
 ['الاتفاق','المقارنة مع خرج القواعد ومرجع الموزع المؤرخ قبل تطبيق overrides المحفوظة؛ لا تدخل إجابات الملف كـoverrides.'],
 ['النص والمرجع','يعرض الاتفاق النصي وحده منفصلًا عن الاتفاق بعد مرجع الموزع، مع مصدر المرجع وتاريخه في السبب.'],
 ['التصحيحات المحفوظة','تظل 2603 تصحيحات أعمال كما هي. توجد 21 حالة يختلف اعتماد التطوير فيها عن override سابق؛ لم تُستبدل.'],
 ['العينة الجديدة','250 ملاحظة مستبعد منها سجلات ونصوص التطوير والتشابه >=0.90؛ لا إجابات أو اقتراحات محرك فيها.'],
 ['التوقيت','الأزمنة موثقة في REPORT.md وsummary.json، منفصلة عن قراءة Excel والتصدير.'],
 ['النطاق','لا تدريب ML ولا حفظ إعادة تصنيف أو استيراد فعلي.']
],{A:28,B:110});
analysis.recalculate();
console.log((await analysis.inspect({kind:'region',sheetId:metric.name,range:'A1:F10',maxChars:700})).ndjson);
for(const [name,range,file] of [[metric.name,'A1:F10','agreement_preview.png'],[remaining.name,'C1:F4','remaining_preview.png'],[trans.name,'A1:C8','transition_preview.png'],[detail.name,'C1:F4','development_preview.png'],[conflicts.name,'D1:G4','manual_conflict_preview.png'],[method.name,'A1:B5','analysis_method_preview.png']]){
 const img=await analysis.render({sheetName:name,range,scale:1.1,format:'png'});await fs.writeFile(path.join(out,file),new Uint8Array(await img.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(analysis)).save(path.join(out,'development_agreement_round3_final.xlsx'));
console.log('Both final XLSX files exported.');
