import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=path.dirname(fileURLToPath(import.meta.url));
const p=JSON.parse(await fs.readFile(path.join(out,'workbooks.json'),'utf8'));
function col(n){let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function literal(v){return typeof v==='string'&&v.startsWith('=')?"'"+v:v;}
function sheet(w,name,headers,rows){
 const s=w.worksheets.add(name);s.showGridLines=false;
 s.getRange(`A1:${col(headers.length-1)}${rows.length+1}`).values=[headers,...rows.map(r=>r.map(literal))];
 const all=s.getUsedRange();all.format.font.name='Arial';all.format.font.size=10;all.format.verticalAlignment='top';all.format.wrapText=true;all.format.columnWidth=23;all.format.rowHeight=42;
 const h=s.getRange(`A1:${col(headers.length-1)}1`);h.format.fill='#172033';h.format.font.color='#FFFFFF';h.format.font.bold=true;h.format.rowHeight=42;h.format.horizontalAlignment='center';
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(2);
 return s;
}
const review=Workbook.create();
const s=sheet(review,'مراجعة بشرية',p.sample_headers,p.sample_rows);
s.getRange('B1:B251').format.columnWidth=70;s.getRange('B2:D251').format.horizontalAlignment='right';s.getRange('I2:I251').format.horizontalAlignment='right';
s.getRange('C1:C251').format.columnWidth=27;s.getRange('D1:D251').format.columnWidth=42;
s.getRange('I1:I251').format.columnWidth=100;
s.getRange('C2:D251').format.fill='#FFF4CE';s.getRange('C2:D251').format.font.color='#1D4ED8';
s.getRange('C2:C251').dataValidation={rule:{type:'list',values:['Current Customer','Potential Customer','Target Customer','New Customer','Former Customer','Not Interested','No Meeting','Unclassified']}};
s.tables.add('A1:L251',true,'HumanReviewTable');
for(let i=0;i<p.sample_rows.length;i++){
 const r=p.sample_rows[i];const height=Math.max(56,Math.ceil(r[1].length/65)*15,Math.ceil(r[8].length/95)*15);
 s.getRange(`A${i+2}:L${i+2}`).format.rowHeight=Math.min(409,height);
}
const m=sheet(review,'طريقة الاختيار',['البند','التفاصيل'],p.sample_method);m.getRange(`B1:B${p.sample_method.length+1}`).format.columnWidth=110;m.getRange(`A2:B${p.sample_method.length+1}`).format.rowHeight=48;
review.recalculate();
console.log((await review.inspect({kind:'region',sheetId:s.name,range:'A1:F4',maxChars:800,tableMaxCellChars:80})).ndjson);
for(const [name,range,file] of [[s.name,'B1:E5','review_preview.png'],[m.name,'A1:B7','method_preview.png']]){
 const img=await review.render({sheetName:name,range,scale:1.3,format:'png'});await fs.writeFile(path.join(out,file),new Uint8Array(await img.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(review)).save(path.join(out,'human_review_250_final.xlsx'));
console.log('human_review_250.xlsx exported');
const comparison=Workbook.create();
const t=sheet(comparison,'انتقالات الحالات',p.transitions_headers,p.transitions_rows);t.getRange('C2:C100').setNumberFormat('#,##0');
const a=sheet(comparison,'مقارنة كل الزيارات',p.comparison_headers,p.comparison_rows);
a.getRange(`B1:B${p.comparison_rows.length+1}`).format.columnWidth=70;
a.getRange(`G1:G${p.comparison_rows.length+1}`).format.columnWidth=100;
comparison.recalculate();
console.log((await comparison.inspect({kind:'region',sheetId:t.name,range:'A1:C8',maxChars:500})).ndjson);
for(const [name,range,file] of [[t.name,'A1:C10','transitions_preview.png'],[a.name,'B1:F5','comparison_preview.png']]){
 const img=await comparison.render({sheetName:name,range,scale:1.2,format:'png'});await fs.writeFile(path.join(out,file),new Uint8Array(await img.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(comparison)).save(path.join(out,'comparison_round2_final.xlsx'));
console.log('comparison_round2.xlsx exported');
