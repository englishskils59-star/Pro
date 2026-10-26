import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=path.dirname(fileURLToPath(import.meta.url));
const payload=JSON.parse(await fs.readFile(path.join(out,'workbook_payload.json'),'utf8'));
const root=path.resolve(out,'../..');const dest=path.join(root,'outputs',path.basename(out));await fs.mkdir(dest,{recursive:true});
const headers={'Visit ID':'معرف الزيارة','Original Note':'النص الأصلي','Human Approved':'التصنيف البشري المعتمد','Reviewer Note':'ملاحظات المراجع','Old Human':'الاعتماد السابق','Updated Human':'الاعتماد المحدث','Old Reviewer Note':'التفسير السابق','Updated Reviewer Note':'التفسير المحدث','Text Evidence':'ما يدعمه نص الزيارة','Additional Reviewer Context':'معلومة المراجع الإضافية وحدودها','Status':'الحالة المعتمدة','Reviewed':'عدد المعتمد','Before text':'قبل — نص فقط','After text':'بعد — نص فقط','Before references':'قبل — مع المراجع','After references':'بعد — مع المراجع','After text Reason':'سبب النتيجة النصية','Reference Source':'مصدر المرجع المؤرخ أو عدم استخدامه','Reviewer Context Boundary':'حدود معلومات المراجع','Remaining Difference Reason':'سبب الاختلاف الباقي','Existing Business Override':'التصحيح اليدوي المحفوظ','Before':'قبل','After':'بعد','Count':'عدد الزيارات'};
function col(n){let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
const w=Workbook.create();let idx=0;
for(const [name,t] of Object.entries(payload)){
 let keys=t.headers;
 if(name==='المقارنة والتفسير'||name==='الاختلافات الباقية')keys=['Visit ID','Original Note','Human Approved','Reviewer Note','Before text','After text','Before references','After references','After text Reason','Reference Source','Reviewer Context Boundary','Remaining Difference Reason'];
 if(name==='تعارض الحفظ اليدوي')keys=['Visit ID','Original Note','Human Approved','Existing Business Override','Reviewer Note'];
 const ids=keys.map(k=>t.headers.indexOf(k));const rows=t.rows.map(r=>ids.map(i=>r[i]??''));
 if(name==='اتفاق عينة التطوير')rows.push(['الإجمالي',...keys.slice(1).map((_,i)=>rows.reduce((sum,r)=>sum+Number(r[i+1]),0))]);
 const s=w.worksheets.add(name);s.showGridLines=false;
 s.getRange(`A1:${col(keys.length-1)}${rows.length+1}`).values=[keys.map(k=>headers[k]??k),...rows.map(r=>r.map(v=>typeof v==='string'&&v.startsWith('=')?"'"+v:v))];
 const all=s.getUsedRange();all.format.font.name='Arial';all.format.font.size=11;all.format.wrapText=true;all.format.verticalAlignment='top';all.format.columnWidth=28;
 keys.forEach((key,i)=>{const wide=/Note|Reason|Evidence|Context|Source|البند|التوضيح/.test(key);const width=key==='Visit ID'?34:key==='التوضيح'?115:wide?75:28;s.getRange(`${col(i)}1:${col(i)}${rows.length+1}`).format.columnWidth=width;if(wide)s.getRange(`${col(i)}2:${col(i)}${rows.length+1}`).format.horizontalAlignment='right';});
 s.getRange(`A1:${col(keys.length-1)}1`).format.fill='#17314D';s.getRange(`A1:${col(keys.length-1)}1`).format.font.color='#FFFFFF';s.getRange(`A1:${col(keys.length-1)}1`).format.font.bold=true;s.getRange(`A1:${col(keys.length-1)}1`).format.rowHeight=58;
 for(let r=0;r<rows.length;r++){let lines=1;rows[r].forEach((v,i)=>{let chars=/Note|Reason|Evidence|Context|Source/.test(keys[i])?65:keys[i]==='التوضيح'?100:25;lines=Math.max(lines,Math.ceil(String(v).length/chars));});s.getRange(`A${r+2}:${col(keys.length-1)}${r+2}`).format.rowHeight=Math.max(45,Math.min(409,lines*18+12));}
 if(rows.length)s.tables.add(`A1:${col(keys.length-1)}${rows.length+1}`,true,`RoundFour${++idx}`);
 s.freezePanes.freezeRows(1);if(keys[0]==='Visit ID')s.freezePanes.freezeColumns(1);
}
w.recalculate();
console.log((await w.inspect({kind:'region',sheetId:'اتفاق عينة التطوير',range:'A1:F9',maxChars:1100})).ndjson);
console.log((await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},summary:'Final error check'})).ndjson);
await(await SpreadsheetFile.exportXlsx(w)).save(path.join(dest,'development_comparison_round4.xlsx'));
const views=[['التغييرات المعتمدة','C1:F4'],['اتفاق عينة التطوير','A1:F10'],['المقارنة والتفسير','B1:D4'],['الاختلافات الباقية','B1:D4'],['تعارض الحفظ اليدوي','B1:E4'],['انتقالات النص','A1:C6'],['انتقالات المراجع','A1:C5'],['دليل القياس','A1:B6'],['التغييرات المعتمدة','G1:H4']];
for(let i=0;i<views.length;i++){const [sheetName,range]=views[i];const blob=await w.render({sheetName,range,scale:i===6?1.2:1.1,format:'png'});await fs.writeFile(path.join(out,`workbook_preview_${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));}
console.log('EXPORTED '+path.join(dest,'development_comparison_round4.xlsx'));
