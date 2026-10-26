"""Round-two read-only comparison, timings and deterministic review sampling."""
from pathlib import Path
from datetime import datetime
import sys,json,hashlib,subprocess,time,statistics,re
from difflib import SequenceMatcher
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import classification_engine as engine
import classification_context as ctx
import storage_manager as storage
OUT=Path((ROOT/'reports/latest_classification_round2.txt').read_text())
PREVIOUS=Path((ROOT/'reports/latest_classification_review.txt').read_text())
DATA=Path(json.loads((ROOT/'wdi_config.json').read_text())['data_dir'])
manifest=json.loads((OUT/'initial_hashes.json').read_text())
source=pd.read_parquet(DATA/'classified_data.parquet');source['_source_row']=range(len(source))
cols=['Suggested Status','Display Status','Confidence Score','Raw Score','Matched Keywords','Classification Reason','Override Source']
raw=source.drop(columns=cols,errors='ignore')
raw.to_parquet(OUT/'input_snapshot.parquet',index=False)
baseline_file='before_round2-'+str(time.time_ns())+'.parquet'
custom=json.loads((DATA/'custom_rules.json').read_text()) if (DATA/'custom_rules.json').exists() else []
# Subprocess isolates the PRE-ROUND helper module and caches from current modules.
code=r'''
import sys,json,time
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
import pandas as pd
import classification_engine as e
import classification_context as c
out=Path(sys.argv[3]);raw=pd.read_parquet(out/'input_snapshot.parquet')
e.set_custom_rules(json.loads(sys.argv[4]));times=[]
for _ in range(3):
 c.cached_decide.cache_clear();c.compile_rules.cache_clear()
 start=time.perf_counter();result=e.classify_dataframe(raw);times.append(time.perf_counter()-start)
result.to_parquet(out/sys.argv[5],index=False)
(out/'before_timing.json').write_text(json.dumps({'seconds':times,'version':c.ENGINE_VERSION}))
'''
subprocess.run([sys.executable,'-B','-c',code,str(OUT/'backup'),str(ROOT),str(OUT),json.dumps(custom),baseline_file],check=True)
before=pd.read_parquet(OUT/baseline_file).set_index('_source_row').sort_index()
engine.set_custom_rules(custom);times=[]
for _ in range(3):
 ctx.cached_decide.cache_clear();ctx.compile_rules.cache_clear()
 start=time.perf_counter();after=engine.classify_dataframe(raw);times.append(time.perf_counter()-start)
after=after.set_index('_source_row').sort_index();stored=source.set_index('_source_row').sort_index()
# Compare previous saved comparison to this baseline, not merely version names.
previous=pd.read_csv(PREVIOUS/'comparison_before_after.csv',keep_default_na=False)
assert len(previous)==len(source)
assert (previous['New Rules Display Status'].to_numpy()==before['Display Status'].to_numpy()).all()
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in json.loads((PREVIOUS/'data_hashes_before.json').read_text()).items() if p.startswith(str(DATA)))
overrides=pd.read_parquet(DATA/'overrides.parquet')
assert 'Key' in overrides, 'Legacy overrides require separate approved migration; no migration performed'
valid=overrides[overrides['Manual Status'].isin(engine.STATUS_DISPLAY.values())].drop_duplicates('Key',keep='last')
manual=dict(zip(valid['Key'],valid['Manual Status']));effective=after.copy();keys=storage._visit_key_series(after)
for idx,key in keys.items():
 if key in manual:ctx.apply_manual_result(effective,idx,manual[key],engine.STATUS_DISPLAY)
assert all(effective.at[i,'Display Status']==manual[key] for i,key in keys.items() if key in manual)
pd.testing.assert_frame_equal(raw.set_index('_source_row').sort_index(),after.drop(columns=cols,errors='ignore'),check_dtype=True)
c=pd.DataFrame({'Visit ID':keys,'Customer Name':stored['Customer Name'],'Visit Date':stored['Visit Date'].astype(str),'Original Note':stored['Visit Notes']})
for prefix,frame in [('Stored',stored),('Before Round 2',before),('After Round 2',after),('After Overrides',effective)]:
 for column in cols:
  if column in frame:c[prefix+' '+column]=frame[column]
c['Has Saved Override']=[key in manual for key in keys]
c['Changed This Round']=before['Display Status']!=after['Display Status']
c['Changed vs Stored']=stored['Display Status']!=effective['Display Status']
c['Change Explanation']=c.apply(lambda row:('Changed rule decision; review required. ' if row['Changed This Round'] else 'Status unchanged. ')+row['After Round 2 Classification Reason']+(' | Saved manual status takes precedence; not overwritten.' if row['Has Saved Override'] else ''),axis=1)
c.to_csv(OUT/'comparison_round2.csv',index_label='Source Row',encoding='utf-8-sig')
t=pd.crosstab(before['Display Status'],after['Display Status'])
transitions=[{'Before':a,'After':b,'Count':int(t.at[a,b])} for a in t.index for b in t.columns if t.at[a,b]]
notes=[ctx.normalize_note(n) for n in stored['Visit Notes']]
categories={
 'التعامل غير المباشر':lambda i:bool(re.search(r'موزع|التاجر|من خلال|من الوكيل',notes[i]) and re.search(r'الوادي|مخزون|بيسحب|بيستخدم|يشتري',notes[i])),
 'الاتفاق على بداية التعامل':lambda i:bool(re.search(r'اتفق|الاتفاق|مستعد|موافق|وعد',notes[i]) and re.search(r'بدايه|بدء|طلبيه|التعامل|اول|العمل',notes[i])),
 'أول تعامل فعلي أو دليله المرشح':lambda i:after.at[i,'Suggested Status']=='new' or bool(re.search(r'(?<!\w)ك?اول\s+(?:طلب|طلبيه|سحب|تعامل|مره)(?!\w)',notes[i])),
 'التعارضات':lambda i:'متعارض' in str(before.at[i,'Classification Reason']) or 'متعارض' in str(after.at[i,'Classification Reason']),
 'غير المصنف':lambda i:after.at[i,'Suggested Status']=='unclassified',
 'النتائج التي لم تتغير':lambda i:not bool(c.at[i,'Changed This Round']),
}
quotas=dict(zip(categories,[45,45,30,50,40,40]))
# Stable seeded hash ordering. One normalized note, then near-duplicate rejection.
order=sorted(range(len(c)),key=lambda i:hashlib.sha256(('WDI-round2-250:'+str(c.at[i,'Visit ID'])+':'+str(i)).encode()).hexdigest())
pools={name:[i for i in order if pred(i) and notes[i]] for name,pred in categories.items()}
selected=[];chosen=set();chosen_notes=[];norms=set();rejected=0

def add(i,category):
 global rejected
 n=notes[i]
 if i in chosen or n in norms:return False
 for other in chosen_notes:
  if min(len(n),len(other))/max(len(n),len(other))<.8:continue
  sm=SequenceMatcher(None,n,other,autojunk=False)
  if sm.quick_ratio()>=.9 and sm.ratio()>=.9:
   rejected+=1;return False
 selected.append((i,category));chosen.add(i);norms.add(n);chosen_notes.append(n);return True
# Scarce category first, so it is not consumed by an overlapping broad category.
for name in sorted(categories,key=lambda name:len(pools[name])):
 count=0
 for i in pools[name]:
  if add(i,name):count+=1
  if count>=quotas[name]:break
# Redistribute unavailable/duplicate slots across actual categories, no fabricated notes.
for i in order:
 if len(selected)>=250:break
 for name,pred in categories.items():
  if pred(i) and add(i,name):break
assert len(selected)==250
sample=[]
for i,cat in selected:
 sample.append([c.at[i,'Visit ID'],str(c.at[i,'Original Note']),'','',cat,c.at[i,'Stored Display Status'],c.at[i,'Before Round 2 Display Status'],c.at[i,'After Round 2 Display Status'],c.at[i,'After Round 2 Classification Reason'],c.at[i,'After Overrides Display Status'],bool(c.at[i,'Has Saved Override']),c.at[i,'Visit Date']])
counts={name:sum(cat==name for _,cat in selected) for name in categories}
old_times=json.loads((OUT/'before_timing.json').read_text())['seconds']
summary={'rows':len(c),'same_dataset_as_round1':True,'baseline_matches_round1_comparison':True,'changed_this_round':int(c['Changed This Round'].sum()),'changed_stored_vs_effective':int(c['Changed vs Stored'].sum()),'manual_applied':int(c['Has Saved Override'].sum()),'all_manual_decisions_preserved':True,'old_seconds':old_times,'new_seconds':times,'old_median':statistics.median(old_times),'new_median':statistics.median(times),'speed_ratio_old_over_new':statistics.median(old_times)/statistics.median(times),'before_counts':before['Display Status'].value_counts().to_dict(),'after_counts':after['Display Status'].value_counts().to_dict(),'sample_counts':counts,'sample_eligible_unique':{name:len(set(notes[i] for i in pool)) for name,pool in pools.items()},'sample_requested':quotas,'sample_size':250,'sample_duplicate_threshold':.9,'near_duplicate_rejections':rejected,'engine_version':ctx.ENGINE_VERSION,'definitions_version':ctx.DEFINITIONS_VERSION,'accuracy':None,'previous_xlsx_missing':True}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
headers=['معرف الزيارة','النص الأصلي','التصنيف البشري المعتمد','ملاحظات المراجع','مجموعة المراجعة','النتيجة المحفوظة','قبل الجولة الثانية','بعد الجولة الثانية','سبب القرار الجديد','بعد التصحيحات اليدوية','يوجد تصحيح يدوي','تاريخ الزيارة']
compact=['Visit ID','Original Note','Stored Display Status','Before Round 2 Display Status','After Round 2 Display Status','After Overrides Display Status','After Round 2 Classification Reason','Has Saved Override','Changed This Round']
payload={'sample_headers':headers,'sample_rows':sample,'comparison_headers':compact,'comparison_rows':c[compact].fillna('').values.tolist(),'transitions_headers':['قبل الجولة','بعد الجولة','عدد الزيارات'],'transitions_rows':[[x['Before'],x['After'],x['Count']] for x in transitions],'sample_method':[['طريقة الاختيار','عينة تطوير ومراجعة بشرية. ليست اختبار دقة مستقلًا، ولا نتائج معتمدة.'],['المصدر','نفس 13503 زيارة من الجولة السابقة. النصوص الأصلية لم تتغير.'],['استقلال المراجعة','اكتب القرار البشري وملاحظاتك في العمودين C وD قبل قراءة اقتراحات المحرك. لا استيراد تلقائي.'],['الاختيار','ترتيب حتمي ببصمة SHA-256 وبذرة WDI-round2-250. اختيار الطبقات الأقل عددًا أولًا.'],['تقليل التشابه','ملاحظة واحدة لكل نص منظف، واستبعاد أي مرشح بتشابه SequenceMatcher لا يقل عن 0.90 مع أي ملاحظة مختارة.'],['نقص الطبقات','الحصص المبدئية 45/45/30/50/40/40. النقص يعاد توزيعه على ملاحظات حقيقية من المجموعات المتاحة.'],['أول تعامل','تشمل الطبقة أدلة مرشحة لأول تعامل، وقد تتضمن نفيًا أو مستقبلًا للمراجعة؛ ليست كل عناصرها New مثبتة.']]+[[name,f'مختار {counts[name]}؛ متاح {summary["sample_eligible_unique"][name]} نصًا منظفًا؛ حصة مبدئية {quotas[name]}'] for name in categories]}
(OUT/'workbooks.json').write_text(json.dumps(payload,ensure_ascii=False,default=str),encoding='utf-8')
# Protect all old reports and source files; only classification_context is authorized here.
for p,h in manifest.items():
 if Path(p)==ROOT/'classification_context.py':continue
 assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
