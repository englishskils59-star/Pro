"""Offline round-four audit. No imports/saves to business data or holdout reads."""
from pathlib import Path
import sys,json,hashlib,time,subprocess,statistics,re
import pandas as pd
import openpyxl
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import classification_engine as engine
import classification_context as ctx
import storage_manager as storage
OUT=Path((ROOT/'reports/latest_classification_round4.txt').read_text(encoding='utf-8'))
PREV=ROOT/'reports/classification-round3-20261025T132616Z'
DATA=Path(json.loads((ROOT/'wdi_config.json').read_text())['data_dir'])
def read_review(path):
 w=openpyxl.load_workbook(path,read_only=True,data_only=False);s=w['مراجعة بشرية'];rows=list(s.values);head=rows[0]
 assert head[:4]==('معرف الزيارة','النص الأصلي','التصنيف البشري المعتمد','ملاحظات المراجع')
 result={};blank=0;unknown=[]
 for row in rows[1:]:
  if not any(v is not None for v in row):continue
  k=str(row[0]);assert k not in result,('duplicate',k)
  assert not any(isinstance(v,str) and v.startswith('=') for v in row[:4]),('formula',k)
  if row[2] is None or not str(row[2]).strip():blank+=1
  elif row[2] not in engine.STATUS_DISPLAY.values():unknown.append([k,row[2]])
  result[k]={'Visit ID':k,'Original Note':row[1],'Human Approved':row[2],'Reviewer Note':row[3]}
 w.close();return result,{'rows':len(result),'filled':len(result)-blank,'blank':blank,'unknown':unknown}
old,_=read_review(PREV/'approved_review_reference.xlsx');review,validation=read_review(OUT/'approved_review_reference.xlsx')
assert old.keys()==review.keys();assert not validation['unknown']
changes=[]
for k,r in review.items():
 o=old[k];assert r['Original Note']==o['Original Note'],('review text changed',k)
 if (o['Human Approved'],o['Reviewer Note'])!=(r['Human Approved'],r['Reviewer Note']):
  changes.append({'Visit ID':k,'Original Note':r['Original Note'],'Old Human':o['Human Approved'],'Updated Human':r['Human Approved'],'Old Reviewer Note':o['Reviewer Note'],'Updated Reviewer Note':r['Reviewer Note']})
# These annotations describe provenance only. They are never sent to the engine.
provenance={
 '639741b363975ae79810bf285e7ed95e':('النص يسمي هايدا للتجربة ثم يعرض البريمو ويتفق على المتابعة؛ لا يثبت أول تعامل للوادي.','تعريف فرصة الوادي في تعليق المراجع؛ لا إضافة لخريطة أسماء المنتجات.'),
 '9d843d46227e0d3f7c80d9d940e4be5d':('النص يذكر توقف التعامل ورغبة بصيغة نرجع؛ لا ينسب قبول العودة للعميل.','تحديد أن الرغبة تخص المندوب معلومة مراجعة إضافية؛ المحرك لا يحدد المتكلم من النص.'),
 'a03be55009383fa67c63720a96ad354a':('النص يذكر تعاملًا سابقًا واتفقنا معه على التركيز على عنابر سابقة؛ هذا تفاوض دون إثبات التنفيذ.','التأكيد بأن العميل وافق على العودة معلومة أعمال إضافية من المراجع؛ لا يدعي المحرك استخراج هذه الموافقة حرفيًا.')}
for c in changes:c['Text Evidence'],c['Additional Reviewer Context']=provenance[c['Visit ID']]
pd.DataFrame(changes).to_csv(OUT/'review_changes_by_visit_id.csv',index=False,encoding='utf-8-sig')
source=pd.read_parquet(DATA/'classified_data.parquet');source['_source_row']=range(len(source))
fields=['Suggested Status','Display Status','Confidence Score','Raw Score','Matched Keywords','Classification Reason','Override Source']
raw=source.drop(columns=fields,errors='ignore');raw.to_parquet(OUT/'input_snapshot.parquet',index=False)
source.to_parquet(OUT/'reference_snapshot.parquet',index=False)
custom=json.loads((DATA/'custom_rules.json').read_text()) if (DATA/'custom_rules.json').exists() else []
code=r"""
import sys,json,time
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
import pandas as pd
import classification_engine as e
import classification_context as c
out=Path(sys.argv[3]);raw=pd.read_parquet(out/'input_snapshot.parquet');refs=pd.read_parquet(out/'reference_snapshot.parquet');e.set_custom_rules(json.loads(sys.argv[4]));times={}
for mode in ['text','references']:
 tt=[]
 for _ in range(3):
  c.cached_decide.cache_clear();c.compile_rules.cache_clear();start=time.perf_counter();result=e.classify_dataframe(raw,reference_records=refs if mode=='references' else None);tt.append(time.perf_counter()-start)
 result.to_parquet(out/('baseline_round3_'+mode+'.parquet'),index=False);times[mode]=tt
(out/'baseline_timing.json').write_text(json.dumps(times))
"""
subprocess.run([sys.executable,'-B','-c',code,str(OUT/'backup'),str(ROOT),str(OUT),json.dumps(custom)],check=True)
frames={};times={'before':json.loads((OUT/'baseline_timing.json').read_text()),'after':{}}
for mode in ['text','references']:
 frames['Before '+mode]=pd.read_parquet(OUT/('baseline_round3_'+mode+'.parquet')).set_index('_source_row').sort_index()
 engine.set_custom_rules(custom);tt=[]
 for _ in range(3):
  ctx.cached_decide.cache_clear();ctx.compile_rules.cache_clear();start=time.perf_counter();res=engine.classify_dataframe(raw,reference_records=source if mode=='references' else None);tt.append(time.perf_counter()-start)
 frames['After '+mode]=res.set_index('_source_row').sort_index();times['after'][mode]=tt
stored=source.set_index('_source_row').sort_index();keys=storage._visit_key_series(stored)
by_id={}
for i,k in keys.items():by_id.setdefault(k,[]).append(i)
assert len(stored)==13503,'Source dataset changed since round 3; check before comparing'
# Confirm the baseline release matches the preserved round-3 output on this same dataset.
prior=pd.read_csv(PREV/'comparison_round3.csv',encoding='utf-8-sig').set_index('Source Row').sort_index()
assert list(prior['Visit ID'])==list(keys)
for mode,oldcol in [('text','After Text Display Status'),('references','After References Display Status')]:
 assert frames['Before '+mode]['Display Status'].equals(prior[oldcol]),('baseline release drift',mode)
rows=[]
for k,r in review.items():
 assert k in by_id and len(by_id[k])==1,('missing or ambiguous ID',k)
 i=by_id[k][0];assert stored.at[i,'Visit Notes']==r['Original Note'],('source note mismatch',k)
 if not r['Human Approved']:continue
 d={**r,'Old Human':old[k]['Human Approved'],'Changed Human Label':old[k]['Human Approved']!=r['Human Approved']}
 for name,f in frames.items():d[name]=f.at[i,'Display Status'];d[name+' Reason']=f.at[i,'Classification Reason']
 d['Reference Source']=d['After references Reason'] if d['After references']!=d['After text'] else 'لا مرجع إضافي مؤثر؛ النتيجة نصية'
 d['Reviewer Context Boundary']=provenance.get(k,('','تعليق المراجع مرجع للمقارنة فقط؛ لا يمرر إلى المحرك'))[1]
 d['Remaining Difference Reason']=''
 if d['After references']!=r['Human Approved']:
  t=ctx.normalize_note(r['Original Note'])
  if r['Human Approved']=='Current Customer':why='تحتاج جهة التعامل أو إثبات الاستمرار من مرجع مؤرخ؛ الوصف السياقي في تعليق المراجع لا يكفي لاستخراجه من النص وحده.'
  elif r['Human Approved']=='Not Interested':why='سياق رفض الشروط أو التمويل لا يطابق رفضًا صريحًا آمنًا في القواعد؛ تعميمه قد يحول تفاوضًا إلى رفض.'
  elif r['Human Approved']=='Target Customer':why='وصف نشاط أو منتج/مورد لا يغطيه مرجع الأسماء المعتمد، أو صياغة مستهدف غير مغطاة؛ لا تضاف هوية مورد بالافتراض.'
  elif r['Human Approved']=='Former Customer':why='إسناد التعامل السابق أو نطاق توقفه غير كافٍ في قواعد النص الحالية.'
  else:why='استعداد أو ترتيب مستقبلي/تفاوض بصياغة غير مغطاة، أو جهة/فاعل غير صريح؛ يحتاج قاعدة محددة بأمثلة مضادة أو سياق موثوق.'
  d['Remaining Difference Reason']=why
 rows.append(d)
a=pd.DataFrame(rows);a.to_csv(OUT/'development_agreement.csv',index=False,encoding='utf-8-sig')
remaining=a[a['After references']!=a['Human Approved']];remaining.to_csv(OUT/'remaining_disagreements.csv',index=False,encoding='utf-8-sig')
overrides=pd.read_parquet(DATA/'overrides.parquet');manual=dict(zip(overrides['Key'],overrides['Manual Status']))
effective=frames['After references'].copy()
for i,k in keys.items():
 if k in manual:ctx.apply_manual_result(effective,i,manual[k],engine.STATUS_DISPLAY)
conflicts=a[a['Visit ID'].isin(manual)].copy();conflicts['Existing Business Override']=conflicts['Visit ID'].map(manual);conflicts=conflicts[conflicts['Existing Business Override']!=conflicts['Human Approved']];conflicts.to_csv(OUT/'existing_manual_conflicts.csv',index=False,encoding='utf-8-sig')
assert all(effective.at[i,'Display Status']==manual[k] for i,k in keys.items() if k in manual)
for f in frames.values():pd.testing.assert_frame_equal(raw.set_index('_source_row').sort_index(),f.drop(columns=fields,errors='ignore'),check_dtype=True)
c=pd.DataFrame({'Visit ID':keys,'Original Note':stored['Visit Notes'],'Visit Date':stored['Visit Date'].astype(str)})
for name,f in [('Stored',stored),*frames.items(),('After Saved Overrides',effective)]:
 for col in fields:
  if col in f:c[name+' '+col]=f[col]
c.to_csv(OUT/'comparison_round4_full.csv',index_label='Source Row',encoding='utf-8-sig')
metrics=[]
for status in engine.STATUS_DISPLAY.values():
 sub=a[a['Human Approved']==status];m={'Status':status,'Reviewed':len(sub)}
 for name in frames:m[name]=int((sub[name]==sub['Human Approved']).sum())
 metrics.append(m)
transitions={};changed={}
for mode in ['text','references']:
 b=frames['Before '+mode]['Display Status'];n=frames['After '+mode]['Display Status'];mask=b!=n
 changed[mode]=int(mask.sum());tr=pd.DataFrame({'Before':b[mask],'After':n[mask]}).value_counts().reset_index(name='Count');transitions[mode]=tr.to_dict('records');tr.to_csv(OUT/('transitions_'+mode+'.csv'),index=False,encoding='utf-8-sig')
summary={'metric_name':'اتفاق على عينة التطوير','validation':validation,'source_rows':len(c),'review_changes':len(changes),'classification_changes':sum(x['Old Human']!=x['Updated Human'] for x in changes),'comment_changes':sum(x['Old Reviewer Note']!=x['Updated Reviewer Note'] for x in changes),'agreement':{name:int((a[name]==a['Human Approved']).sum()) for name in frames},'by_class':metrics,'remaining':len(remaining),'changed_full':changed,'transitions':transitions,'references_effect':int((frames['After text']['Display Status']!=frames['After references']['Display Status']).sum()),'manual_conflicts':len(conflicts),'manual_preserved':sum(k in manual for k in keys),'timings_seconds':times,'timing_medians':{phase:{mode:statistics.median(t) for mode,t in modes.items()} for phase,modes in times.items()}}
for path,digest in json.loads((OUT/'preservation_hashes.json').read_text()).items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,('changed protected file',path)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
# Focused workbook payload: only explicit owner labels, no inferred labels or reviewer-only rule inputs.
def table(df):return {'headers':list(df.columns),'rows':df.fillna('').values.tolist()}
workbook={'التغييرات المعتمدة':table(pd.DataFrame(changes)),'اتفاق عينة التطوير':table(pd.DataFrame(metrics)),'المقارنة والتفسير':table(a),'الاختلافات الباقية':table(remaining),'تعارض الحفظ اليدوي':table(conflicts),'انتقالات النص':table(pd.DataFrame(transitions['text'])),'انتقالات المراجع':table(pd.DataFrame(transitions['references'])),'دليل القياس':{'headers':['البند','التوضيح'],'rows':[['المقياس','اتفاق على عينة التطوير؛ ليست دقة مستقلة.'],['الاعتماد','C وD فقط من مراجعة بشرية؛ المطابقة بمعرف الزيارة والتحقق من النص الأصلي.'],['المصدر',str(OUT/'approved_review_reference.xlsx')],['مرجع الجولة الثالثة',str(PREV/'approved_review_reference.xlsx')],['حدود المعلومات','تعليقات المراجع معلومات أعمال معتمدة للمقارنة، لا تدخل كمدخل نصي أو overrides. تحديد متكلم أو تأكيد موافقة خارج النص يظهر منفصلًا.'],['المراجع','نتائج references تستخدم فقط سجلات المورد المركزية المحفوظة قبل تاريخ الزيارة، مع المصدر والتاريخ في سبب القرار؛ لا تستخدم تعليقات المراجع كمرجع خفي.'],['الحفظ اليدوي','التعارضات مدرجة ولم تستبدل التصحيحات؛ تطبيقها للمقارنة في الذاكرة فقط.'],['العينة المستقلة','لم تفتح أو تستخدم لضبط القواعد ولم تعدل؛ تحقق SHA-256 للحفظ فقط.'],['البيانات','لم يحدث استيراد أو حفظ إعادة تصنيف أو تعديل بيانات الأعمال.'],['التوقيت',json.dumps(summary['timing_medians'],ensure_ascii=False)]]}}
(OUT/'workbook_payload.json').write_text(json.dumps(workbook,ensure_ascii=False,default=str),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
