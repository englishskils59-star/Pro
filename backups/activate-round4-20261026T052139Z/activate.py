from pathlib import Path
import sys,json,os,shutil,datetime,time,hashlib
from unittest.mock import patch
import pandas as pd,openpyxl
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import storage_manager as sm
import classification_engine as engine
import classification_context as context
from dashboard import sales_rep_kpi,customer_analytics_summary,executive_dashboard_data
OUT=Path(__file__).resolve().parent;DATA=sm.get_data_dir();STAGE=OUT/'staged_data'
manifest=json.loads((OUT/'backup_manifest.json').read_text(encoding='utf-8'))
for rel,h in manifest['hashes'].items():assert hashlib.sha256((OUT/rel).read_bytes()).hexdigest()==h,rel
for name in ['classified_data.parquet','overrides.parquet','metadata.json']:
 assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==manifest['hashes'][str(Path('data')/name)],('source changed',name)
shutil.copytree(OUT/'data',STAGE,dirs_exist_ok=True)
source=sm._parquet_to_df(DATA/'classified_data.parquet');source_keys=sm._visit_key_series(source);key_counts=source_keys.value_counts()
lookup={k:i for i,k in source_keys.items()};old=pd.read_parquet(DATA/'overrides.parquet');assert not old['Key'].duplicated().any()
w=openpyxl.load_workbook(OUT/'approved_review_input.xlsx',read_only=True,data_only=False);rows=list(w['مراجعة بشرية'].values);assert rows[0][:4]==('معرف الزيارة','النص الأصلي','التصنيف البشري المعتمد','ملاحظات المراجع')
approvals=[];audit=[];seen=set();blank=0;now=datetime.datetime.now().astimezone().isoformat();oldmap=old.set_index('Key').to_dict('index')
for row in rows[1:]:
 if not row[0]:continue
 k,note,label,comment=row[:4]
 if label is None or not str(label).strip():blank+=1;continue
 assert k not in seen and k in lookup and key_counts[k]==1,k;seen.add(k)
 assert label in engine.STATUS_DISPLAY.values(),(k,label)
 assert not any(isinstance(v,str) and v.startswith('=') for v in row[:4]),'formula input'
 i=lookup[k];assert note==source.at[i,'Visit Notes'],('text mismatch',k)
 approvals.append({'Key':k,'Customer Name':source.at[i,'Customer Name'],'Visit Date':sm._date_text(source.at[i,'Visit Date']),'Sales Rep Name':source.at[i,'Sales Rep Name'],'Manual Status':label,'Approval Source':'human_review_250_final.xlsx / مراجعة بشرية / C,D؛ اعتماد صاحب البرنامج','Reviewer Note':comment or '', 'Approved At':now})
 audit.append({'Visit ID':k,'Original Note':note,'Previous Override':oldmap.get(k,{}).get('Manual Status',''),'Previous Override Record':json.dumps(oldmap.get(k,{}),ensure_ascii=False,default=str),'Previous Saved Status':source.at[i,'Display Status'],'New Approved Status':label,'Reviewer Note':comment or '', 'Approved At':now,'Conflict Replaced':k in oldmap and oldmap[k]['Manual Status']!=label})
w.close();assert len(approvals)==250
pd.DataFrame(audit).to_csv(OUT/'approval_change_log.csv',index=False,encoding='utf-8-sig')
with patch.object(sm,'get_data_dir',return_value=STAGE):
 sm._save_overrides(pd.DataFrame(approvals))
 # Snapshot contains the pre-existing saved observations plus the explicitly approved corrections.
 refs=sm.load_classification_references()
 engine.set_custom_rules(sm.load_custom_rules());context.cached_decide.cache_clear();context.compile_rules.cache_clear()
 source['_activation_row']=range(len(source));start=time.perf_counter()
 result=engine.classify_dataframe(source,reference_records=refs).sort_values('_activation_row').drop(columns='_activation_row').reset_index(drop=True)
 source=source.drop(columns='_activation_row')
 result,n_manual=sm.apply_saved_overrides(result)
 assert list(sm._visit_key_series(result))==list(source_keys)
 result_fields={'Suggested Status','Display Status','Confidence Score','Raw Score','Matched Keywords','Classification Reason','Override Source'}
 cols=[c for c in source if c not in result_fields];pd.testing.assert_frame_equal(source[cols],result[cols],check_dtype=True)
 for a in approvals:
  i=lookup[a['Key']];assert result.at[i,'Display Status']==a['Manual Status'];assert result.at[i,'Matched Keywords']=='';assert a['Reviewer Note'] in result.at[i,'Classification Reason']
 journey=engine.build_customer_journey(result);rep,figs=sales_rep_kpi(result,journey)
 analytics=customer_analytics_summary(result,journey);executive=executive_dashboard_data(result,journey,rep)
 ok,msg=sm.save_session(classified_df=result,journey_df=journey,rep_kpi_df=rep,file_name=sm._load_metadata().get('file_name',''));assert ok,msg
 meta=sm._load_metadata();meta.update({'classification_engine_version':context.ENGINE_VERSION,'classification_definitions_version':context.DEFINITIONS_VERSION,'classification_activated_at':now,'approved_review_count':len(approvals)});sm._save_metadata(meta)
 ok,loaded=sm.load_session();assert ok,loaded
 for a in approvals:assert loaded['classified_df'].at[lookup[a['Key']],'Display Status']==a['Manual Status']
 assert (loaded['classified_df']['Classification Reason']==result['Classification Reason']).all()
 assert list(sm._visit_key_series(loaded['classified_df']))==list(source_keys)
 staged_overrides=pd.read_parquet(STAGE/'overrides.parquet').set_index('Key')
 for k,o in oldmap.items():
  assert k in staged_overrides.index
  if k not in seen:assert staged_overrides.at[k,'Manual Status']==o['Manual Status']
elapsed=time.perf_counter()-start
files=['classified_data.parquet','journey_data.parquet','rep_kpi_data.parquet','overrides.parquet','metadata.json']
state={'status':'prepared','files':files,'started_at':now};(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
try:
 with sm._write_lock():
  for name in files:
   assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==manifest['hashes'][str(Path('data')/name)],('concurrent change',name)
  state['status']='committing';(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
  for name in files:os.replace(STAGE/name,DATA/name)
  for name in files:assert (DATA/name).exists()
 state['status']='committed';(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
except BaseException:
 with sm._write_lock():
  for name in files:
   temp=DATA/(name+'.activation_rollback');shutil.copy2(OUT/'data'/name,temp);os.replace(temp,DATA/name)
 state['status']='rolled_back';(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8');raise
ok,loaded=sm.load_session();assert ok
assert list(sm._visit_key_series(loaded['classified_df']))==list(source_keys)
for a in approvals:assert loaded['classified_df'].at[lookup[a['Key']],'Display Status']==a['Manual Status']
for name in ['last_upload.xlsx','custom_rules.json','name_merges.parquet','gov_merges.parquet','rep_merges.parquet','removed_duplicates.parquet']:
 assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==manifest['hashes'][str(Path('data')/name)],name
summary={'engine':context.ENGINE_VERSION,'definitions':context.DEFINITIONS_VERSION,'visits':len(result),'distribution':result['Display Status'].value_counts().to_dict(),'recent_approvals':len(approvals),'blank_not_applied':blank,'old_conflicts_replaced':sum(x['Conflict Replaced'] for x in audit),'saved_overrides':len(staged_overrides),'manual_applied':n_manual,'classification_and_rebuild_seconds':elapsed,'data_dir':str(DATA),'backup':str(OUT),'reload_verified':True,'original_visits_ids_notes_unchanged':True,'raw_excel_unchanged':True,'transaction_status':'committed'}
(OUT/'activation_result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
