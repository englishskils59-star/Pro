from pathlib import Path
import sys,json,hashlib,subprocess,collections,re,time
import pandas as pd,openpyxl
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import storage_manager as sm,classification_engine as e,classification_context as ctx
from utils import normalize_arabic,safe_str
OUT=Path(__file__).resolve().parent;FILE=Path('C:/Users/eslam.abdelhay/Desktop/Unclassified_Visits (1).xlsx')
w=openpyxl.load_workbook(FILE,read_only=True,data_only=False);s=w['Unclassified Visits'];rows=list(s.values);df=pd.DataFrame(rows[1:],columns=rows[0]);df['_file_row']=range(2,len(df)+2);w.close()
assert df['Manual Status'].fillna('').eq('').all(),'New manual input requires explicit provenance handling'
source=sm._parquet_to_df(sm._paths()['classified']);source_keys=sm._visit_key_series(source)
# Row Number is intentionally never used to identify, select or disambiguate a source record.
def norm(v):return ' '.join(normalize_arabic(safe_str(v)).split()).casefold()
def identity(r,original):
 name=r.get('Customer Name Original') if original and safe_str(r.get('Customer Name Original')) else r.get('Customer Name')
 return (norm(name),sm._date_text(r.get('Visit Date')),norm(r.get('Sales Rep Name')),safe_str(r.get('Visit Notes')))
index=collections.defaultdict(list)
for i,r in source.iterrows():index[identity(r,True)].append(i)
match=[];isolated=[]
for _,r in df.iterrows():
 candidates=index.get(identity(r,True),[])
 if len(candidates)==1:
  i=candidates[0];match.append({'Excel Row':int(r['_file_row']),'Source Row':i,'Source Visit Key (computed)':source_keys[i],'Original Note':r['Visit Notes'],'Original Row Number (not ID)':r['Row Number']})
 else:isolated.append({'Excel Row':int(r['_file_row']),'Original Note':r['Visit Notes'],'Candidates':len(candidates),'Reason':'مطابقة مركبة ملتبسة' if candidates else 'لا تطابق مركب كامل؛ الاسم وحده غير مستخدم'})
matched=pd.DataFrame(match);pd.DataFrame(isolated,columns=['Excel Row','Original Note','Candidates','Reason']).to_csv(OUT/'isolated_matches.csv',index=False,encoding='utf-8-sig')
inputs=source.loc[matched['Source Row']].copy();inputs['_file_row']=matched['Excel Row'].values;inputs.to_parquet(OUT/'input_snapshot.parquet',index=False);source.to_parquet(OUT/'reference_snapshot.parquet',index=False)
notes=df[['Visit Notes']].drop_duplicates();notes.to_json(OUT/'notes.json',orient='records',force_ascii=False)
code=r"""
from pathlib import Path
import sys,json,time
sys.path[:0]=[sys.argv[1],sys.argv[2]]
import pandas as pd
import classification_engine as e,classification_context as c
out=Path(sys.argv[3]);inp=pd.read_parquet(out/'input_snapshot.parquet');refs=pd.read_parquet(out/'reference_snapshot.parquet');e.set_custom_rules(json.loads(sys.argv[4]));start=time.perf_counter();b=e.classify_dataframe(inp,reference_records=refs);b.to_parquet(out/'before.parquet',index=False)
notes=json.loads((out/'notes.json').read_text(encoding='utf-8'));g=[{'Original Note':r['Visit Notes'],'Normalized Note':c.normalize_note(r['Visit Notes']),**e.classify_note(r['Visit Notes'])} for r in notes];(out/'baseline_notes.json').write_text(json.dumps(g,ensure_ascii=False),encoding='utf-8');print(json.dumps({'before_seconds':time.perf_counter()-start}))
"""
p=subprocess.run([sys.executable,'-B','-c',code,str(OUT/'backup'),str(ROOT),str(OUT),json.dumps(sm.load_custom_rules())],check=True,capture_output=True,text=True,encoding='utf-8');(OUT/'baseline_timing.txt').write_text(p.stdout,encoding='utf-8')
before=pd.read_parquet(OUT/'before.parquet').set_index('_file_row');e.set_custom_rules(sm.load_custom_rules());start=time.perf_counter();after=e.classify_dataframe(inputs,reference_records=source);seconds=time.perf_counter()-start;after=after.set_index('_file_row');effective,n_manual=sm.apply_saved_overrides(after)
result=[]
for row in match:
 k=row['Excel Row'];b=before.loc[k];a=after.loc[k];f=effective.loc[k];i=row['Source Row'];manual=source.at[i,'Override Source']=='Manual' if 'Override Source' in source else False
 d={**row,'Stored Status':source.at[i,'Display Status'],'Before Engine':b['Display Status'],'Before Engine Reason':b['Classification Reason'],'After Engine':a['Display Status'],'After Engine Reason':a['Classification Reason'],'After Preserved Overrides':f['Display Status'],'Effective Reason':f['Classification Reason'],'Manual Preserved':manual,'Change Reason':'','Remaining Category':'','Category Basis':''}
 d['New Exit']=b['Display Status']=='Unclassified' and f['Display Status']!='Unclassified' and not manual
 if d['New Exit']:d['Change Reason']=a['Classification Reason']
 if f['Display Status']=='Unclassified':
  t=ctx.normalize_note(row['Original Note']);r=a['Classification Reason']
  if manual:cat='نقص معلومات';basis='اعتماد يدوي سابق لغير مصنف محفوظ؛ لم يتم استبداله باقتراح المحرك'
  elif 'أدلة متعارضة' in r and re.search(r'غير مهتم|رفض التعامل|رافض نهائيا',t) and any(not ctx._NEG.search(' '.join(t[:m.start()].split()[-3:])) for m in re.finditer(r'(?<!\w)(?:مهتم|يرغب|متعاقد|شغال الوادي|بيسحب الوادي)(?!\w)',t)):cat='تعارض حقيقي';basis='أدلة رفض وإيجابية مستقلة باقية بحسب المحرك؛ ليست مفاضلة تلقائية للحالات'
  elif 'أدلة متعارضة' in r:cat='صياغة غير مغطاة';basis='تعارض المحرك لا يثبت تعارض أعمال حقيقيًا؛ نطاق الجهة أو الزمن غير محسوم'
  elif re.search(r'(?:الوادي|معانا|معنا).*(?:علف|شغال|تعامل|يسحب|يبدا|شغل)|(?:شغال|تعامل|علف|سحب|يبدا).*(?:الوادي|معانا|معنا)|لم يكن|لم يتم ايجاده|لن يعمل',t):cat='صياغة غير مغطاة';basis='توجد ألفاظ تعامل/زمن/غياب محددة لم تنتج دليلًا كافيًا بالقواعد الحالية؛ دون تعميم بالاسم'
  else:cat='نقص معلومات';basis='النص لا يثبت حالة تعامل أو قبولًا أو غيابًا واضحًا؛ المتابعة أو المخزون مجهول الجهة لا يكفيان'
  d['Remaining Category']=cat;d['Category Basis']=basis
 result.append(d)
c=pd.DataFrame(result);c.to_csv(OUT/'comparison.csv',index=False,encoding='utf-8-sig');c[c['New Exit']].to_csv(OUT/'changes.csv',index=False,encoding='utf-8-sig');c[c['Remaining Category']!=''].to_csv(OUT/'remaining.csv',index=False,encoding='utf-8-sig')
base=json.loads((OUT/'baseline_notes.json').read_text(encoding='utf-8'));base={r['Original Note']:r for r in base};groups=collections.defaultdict(list)
for text in df['Visit Notes']:groups[base[text]['Normalized Note']].append(text)
group_rows=[]
for normalized,texts in groups.items():
 b=base[texts[0]];a=e.classify_note(texts[0]);group_rows.append({'Normalized Note Before':normalized,'Frequency':len(texts),'Original Example':texts[0],'Before Text Engine':b['display_status'],'Before Abstention Reason':b['reason'],'After Text Engine':a['display_status'],'After Reason':a['reason']})
pd.DataFrame(group_rows).sort_values('Frequency',ascending=False).to_csv(OUT/'normalized_patterns.csv',index=False,encoding='utf-8-sig')
changed=c[c['New Exit']];summary={'file':str(FILE),'file_rows':len(df),'normalized_groups_before':len(groups),'matched_rows':len(match),'isolated_rows':len(isolated),'isolated_ambiguous':sum(r['Candidates']>1 for r in isolated),'manual_preserved_rows':n_manual,'before_engine_distribution':c['Before Engine'].value_counts().to_dict(),'new_exits':len(changed),'new_exit_destinations':changed['After Preserved Overrides'].value_counts().to_dict(),'effective_after_distribution':c['After Preserved Overrides'].value_counts().to_dict(),'remaining':int(c['After Preserved Overrides'].eq('Unclassified').sum()),'remaining_categories':c.loc[c['Remaining Category']!='','Remaining Category'].value_counts().to_dict(),'after_seconds':seconds,'stored_before_nonunclassified':int(c['Stored Status'].ne('Unclassified').sum()),'source_saved':False,'engine':ctx.ENGINE_VERSION}
for path,h in json.loads((OUT/'protected_hashes.json').read_text()).items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,('Protected file changed',path)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
