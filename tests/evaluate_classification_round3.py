"""Round three: validated human labels, source-only comparisons, fresh review pool."""
from pathlib import Path
import sys,json,hashlib,time,statistics,subprocess,re
from difflib import SequenceMatcher
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import classification_engine as engine
import classification_context as ctx
import storage_manager as storage
OUT=Path((ROOT/'reports/latest_classification_round3.txt').read_text())
DATA=Path(json.loads((ROOT/'wdi_config.json').read_text())['data_dir'])
source=pd.read_parquet(DATA/'classified_data.parquet');source['_source_row']=range(len(source))
fields=['Suggested Status','Display Status','Confidence Score','Raw Score','Matched Keywords','Classification Reason','Override Source']
raw=source.drop(columns=fields,errors='ignore');raw.to_parquet(OUT/'input_snapshot.parquet',index=False)
custom=json.loads((DATA/'custom_rules.json').read_text()) if (DATA/'custom_rules.json').exists() else []
code=r'''
import sys,json,time
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
import pandas as pd
import classification_engine as e
import classification_context as c
out=Path(sys.argv[3]);raw=pd.read_parquet(out/'input_snapshot.parquet');e.set_custom_rules(json.loads(sys.argv[4]));times=[]
for _ in range(3):
 c.cached_decide.cache_clear();c.compile_rules.cache_clear();start=time.perf_counter();result=e.classify_dataframe(raw);times.append(time.perf_counter()-start)
result.to_parquet(out/'baseline_round2_release.parquet',index=False)
(out/'baseline_timing.json').write_text(json.dumps(times))
'''
subprocess.run([sys.executable,'-B','-c',code,str(OUT/'backup'),str(ROOT),str(OUT),json.dumps(custom)],check=True)
before=pd.read_parquet(OUT/'baseline_round2_release.parquet').set_index('_source_row').sort_index();stored=source.set_index('_source_row').sort_index()
engine.set_custom_rules(custom);new_times=[]
for _ in range(3):
 ctx.cached_decide.cache_clear();ctx.compile_rules.cache_clear();start=time.perf_counter();text_after=engine.classify_dataframe(raw);new_times.append(time.perf_counter()-start)
text_after=text_after.set_index('_source_row').sort_index()
ref_times=[]
for _ in range(3):
 ctx.cached_decide.cache_clear();ctx.compile_rules.cache_clear();start=time.perf_counter();after=engine.classify_dataframe(raw,reference_records=source);ref_times.append(time.perf_counter()-start)
after=after.set_index('_source_row').sort_index()
keys=storage._visit_key_series(after);by_id={}
for i,k in keys.items():by_id.setdefault(k,[]).append(i)
labels=json.loads((OUT/'human_labels.json').read_text(encoding='utf-8'))
valid_labels=set(engine.STATUS_DISPLAY.values());approved=[];validation={'filled':0,'blank':0,'unknown':[],'missing_id':[],'text_mismatch':[],'duplicate_ids':[],'formula_labels':[]}
seen=set()
for rowno,row in enumerate(labels,2):
 label=row['التصنيف البشري المعتمد'];key=row['معرف الزيارة'];note=row['النص الأصلي']
 if not label:validation['blank']+=1;continue
 validation['filled']+=1
 if key in seen:validation['duplicate_ids'].append(rowno)
 seen.add(key)
 if label not in valid_labels:validation['unknown'].append(rowno);continue
 if key not in by_id:validation['missing_id'].append(rowno);continue
 matched=[i for i in by_id[key] if str(stored.at[i,'Visit Notes'])==note]
 if not matched:validation['text_mismatch'].append(rowno);continue
 i=matched[0]
 assert before.at[i,'Display Status']==row['بعد الجولة الثانية'],('baseline mismatch',rowno)
 approved.append({'Workbook Row':rowno,'Visit ID':key,'Source Row':i,'Original Note':note,'Human Approved':label,'Reviewer Note':row['ملاحظات المراجع'],'Before':before.at[i,'Display Status'],'Text Only After':text_after.at[i,'Display Status'],'After':after.at[i,'Display Status'],'New Reason':after.at[i,'Classification Reason']})
a=pd.DataFrame(approved)
def cause(text):
 t=ctx.normalize_note(text);tags=[]
 for name,pattern in [('نفي',r'رفض|غير|لم |لن |مش |لا '),('مستقبل',r'سيتم|هيتم|هيطلب|غدا|قادمه|وعد|اتفق'),('جهة التعامل',r'كتكوت|تبريد|منافس|علف|الوادي'),('أول تعامل',r'اول|بدء|البدايه|تم البدء'),('تعامل من موزع',r'موزع|تاجر|من تحت|من خلال|شغال من'),('تفاوض',r'حديث|تكلم|التفاوض|عرض|خصم|اجل|تمويل')]:
  if re.search(pattern,t):tags.append(name)
 return '؛ '.join(tags) if tags else 'نقص سياق'
a['Difference Causes']=[cause(n) for n in a['Original Note']]
a['Agreed Before']=a['Before']==a['Human Approved'];a['Agreed After']=a['After']==a['Human Approved']
# User explicitly authorized dated supplier references and start+withdrawal; no ID-specific rules.
a['Needs Owner Context']=(a['Human Approved'].eq('Current Customer') & ~a['Agreed After'])
class_metrics=[]
for label in engine.STATUS_DISPLAY.values():
 sub=a[a['Human Approved']==label]
 class_metrics.append({'Human Status':label,'Reviewed':len(sub),'Agreed Before':int(sub['Agreed Before'].sum()),'Agreed After':int(sub['Agreed After'].sum()),'Before Rate':float(sub['Agreed Before'].mean()) if len(sub) else None,'After Rate':float(sub['Agreed After'].mean()) if len(sub) else None})
a.to_csv(OUT/'development_agreement.csv',index=False,encoding='utf-8-sig');a[~a['Agreed After']].to_csv(OUT/'remaining_disagreements.csv',index=False,encoding='utf-8-sig')
overrides=pd.read_parquet(DATA/'overrides.parquet');manual=dict(zip(overrides['Key'],overrides['Manual Status']));effective=after.copy()
for i,k in keys.items():
 if k in manual:ctx.apply_manual_result(effective,i,manual[k],engine.STATUS_DISPLAY)
manual_conflicts=[row for row in approved if row['Visit ID'] in manual and manual[row['Visit ID']]!=row['Human Approved']]
for row in manual_conflicts:row['Existing Business Override']=manual[row['Visit ID']]
pd.DataFrame(manual_conflicts).to_csv(OUT/'existing_manual_conflicts.csv',index=False,encoding='utf-8-sig')
assert all(effective.at[i,'Display Status']==manual[k] for i,k in keys.items() if k in manual)
pd.testing.assert_frame_equal(raw.set_index('_source_row').sort_index(),after.drop(columns=fields,errors='ignore'),check_dtype=True)
c=pd.DataFrame({'Visit ID':keys,'Original Note':stored['Visit Notes'],'Visit Date':stored['Visit Date'].astype(str)})
for prefix,frame in [('Stored',stored),('Before Round 3',before),('After Text',text_after),('After References',after),('After Overrides',effective)]:
 for col in fields:
  if col in frame:c[prefix+' '+col]=frame[col]
c['Changed']=before['Display Status']!=after['Display Status'];c['Has Saved Override']=[k in manual for k in keys]
c.to_csv(OUT/'comparison_round3.csv',index_label='Source Row',encoding='utf-8-sig')
trans=pd.crosstab(before['Display Status'],after['Display Status']);transrows=[[x,y,int(trans.at[x,y])] for x in trans.index for y in trans.columns if trans.at[x,y]]
# A new review set is chosen ONLY after rule changes; its labels remain empty.
dev_ids=set(r['معرف الزيارة'] for r in labels);dev_norms={ctx.normalize_note(r['النص الأصلي']) for r in labels}
new_selected=[];new_norms=set();new_texts=[];rejections={'development_id':0,'exact_development_text':0,'near_development_text':0,'duplicate_new_text':0}
new_order=sorted(range(len(c)),key=lambda i:hashlib.sha256(('WDI-round3-fresh250:'+str(keys[i])+':'+str(i)).encode()).hexdigest())
def near(a,b):
 if min(len(a),len(b))/max(len(a),len(b))<.8:return False
 sm=SequenceMatcher(None,a,b,autojunk=False)
 return sm.quick_ratio()>=.9 and sm.ratio()>=.9
for i in new_order:
 if len(new_selected)==250:break
 note=str(c.at[i,'Original Note']);norm=ctx.normalize_note(note)
 if keys[i] in dev_ids:rejections['development_id']+=1;continue
 if not norm:continue
 if norm in dev_norms:rejections['exact_development_text']+=1;continue
 if any(near(norm,other) for other in dev_norms):rejections['near_development_text']+=1;continue
 if norm in new_norms or any(near(norm,other) for other in new_texts):rejections['duplicate_new_text']+=1;continue
 new_selected.append([keys[i],c.at[i,'Visit Date'],note,'','']);new_norms.add(norm);new_texts.append(norm)
assert len(new_selected)==250
summary={'rows':len(c),'validated_human_rows':len(a),'validation':validation,'agreement_name':'اتفاق على عينة التطوير','agreement_before':int(a['Agreed Before'].sum()),'agreement_text_only':int((a['Text Only After']==a['Human Approved']).sum()),'agreement_after':int(a['Agreed After'].sum()),'remaining_disagreements':int((~a['Agreed After']).sum()),'class_agreement':class_metrics,'changed_full_dataset':int(c['Changed'].sum()),'reference_changed':int((after['Display Status']!=text_after['Display Status']).sum()),'manual_preserved':sum(k in manual for k in keys),'manual_vs_review_conflicts':len(manual_conflicts),'old_times':json.loads((OUT/'baseline_timing.json').read_text()),'new_text_times':new_times,'new_with_reference_times':ref_times,'new_review_size':250,'new_review_exclusions':rejections,'accuracy':None,'no_ml':True}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
metric_headers=['الحالة المعتمدة','عدد المعتمد','اتفاق قبل','اتفاق بعد','نسبة قبل','نسبة بعد']
metric_rows=[[r['Human Status'],r['Reviewed'],r['Agreed Before'],r['Agreed After'],r['Before Rate'],r['After Rate']] for r in class_metrics]
cols=['Workbook Row','Visit ID','Original Note','Human Approved','Reviewer Note','Before','Text Only After','After','New Reason','Difference Causes']
methods=[['الغرض','عينة مراجعة جديدة لم تدخل في ضبط الجولة الثالثة. لا توجد إجابات بشرية أو توقعات محرك في هذه الورقة.'],['المصدر','نفس بيانات الزيارات المركزية، دون تعديل أو استيراد.'],['الاستبعاد','استبعاد معرفات سجلات عينة التطوير وجميع نصوصها المنظفة والمتطابقة وشبه المتطابقة.'],['التشابه','SequenceMatcher بعد التطبيع العربي؛ يستبعد التشابه >= 0.90 مع أي نص تطوير أو نص سبق اختياره.'],['الاختيار','ترتيب حتمي SHA-256 ببذرة WDI-round3-fresh250، ثم أول 250 مؤهلة. لا موازنة حسب إجابات بشرية مجهولة.'],['الحقول','العمودان D وE مخصصان للتصنيف البشري وملاحظات المراجع، وتُركا فارغين.']]+[[k,str(v)] for k,v in rejections.items()]
payload={'new_headers':['معرف الزيارة','تاريخ الزيارة','النص الأصلي','التصنيف البشري المعتمد','ملاحظات المراجع'],'new_rows':new_selected,'new_methods':methods,'metric_headers':metric_headers,'metric_rows':metric_rows,'agreement_headers':cols,'agreement_rows':a[cols].fillna('').values.tolist(),'remaining_rows':a.loc[~a['Agreed After'],cols].fillna('').values.tolist(),'transition_headers':['قبل الجولة الثالثة','بعد الجولة الثالثة','العدد'],'transition_rows':transrows,'summary_rows':[['المقياس','القيمة'],['اتفاق قبل على عينة التطوير',summary['agreement_before']],['اتفاق بعد على عينة التطوير',summary['agreement_after']],['عدد المعتمد',len(a)],['تغير النتائج على جميع الزيارات',summary['changed_full_dataset']],['اختلافات تصحيح الأعمال المحفوظ عن مراجعة التطوير',len(manual_conflicts)]],'manual_conflict_headers':list(manual_conflicts[0]) if manual_conflicts else ['النتيجة'],'manual_conflict_rows':[[r[k] for k in manual_conflicts[0]] for r in manual_conflicts] if manual_conflicts else [['لا اختلافات']]}
(OUT/'workbooks.json').write_text(json.dumps(payload,ensure_ascii=False,default=str),encoding='utf-8')
allowed={'classification_engine.py','classification_context.py','classification_semantics.py'}
for p,h in json.loads((OUT/'initial_hashes.json').read_text()).items():
 if Path(p).parent==ROOT and Path(p).name in allowed:continue
 assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
