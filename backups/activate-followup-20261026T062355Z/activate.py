from pathlib import Path
import sys,json,os,shutil,datetime,time,hashlib
from unittest.mock import patch
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import storage_manager as sm
import classification_engine as engine
import classification_context as context
from dashboard import sales_rep_kpi,customer_analytics_summary,executive_dashboard_data
OUT=Path(__file__).resolve().parent;DATA=sm.get_data_dir();STAGE=OUT/'staged_data'
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
for rel,h in manifest['hashes'].items():assert hashlib.sha256((OUT/rel).read_bytes()).hexdigest()==h,rel
for name in ['classified_data.parquet','overrides.parquet','metadata.json']:
 assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==manifest['hashes'][str(Path('data')/name)],('source changed',name)
shutil.copytree(OUT/'data',STAGE)
source=sm._parquet_to_df(DATA/'classified_data.parquet');source_keys=sm._visit_key_series(source)
old=pd.read_parquet(DATA/'overrides.parquet');assert not old['Key'].duplicated().any()
now=datetime.datetime.now().astimezone().isoformat()
released=old[old['Manual Status'].eq('Unclassified')].copy()
released['Policy Action']='Retained in audit; no longer overrides a commercial classification'
released['Effective At']=now
released.to_csv(OUT/'released_unclassified_audit.csv',index=False,encoding='utf-8-sig')
with patch.object(sm,'get_data_dir',return_value=STAGE):
 refs=sm.load_classification_references()
 engine.set_custom_rules(sm.load_custom_rules());context.cached_decide.cache_clear();context.compile_rules.cache_clear()
 source['_activation_row']=range(len(source));start=time.perf_counter()
 result=engine.classify_dataframe(source,reference_records=refs).sort_values('_activation_row').drop(columns='_activation_row').reset_index(drop=True)
 source=source.drop(columns='_activation_row')
 result,n_manual=sm.apply_saved_overrides(result)
 assert list(sm._visit_key_series(result))==list(source_keys)
 fields={'Suggested Status','Display Status','Confidence Score','Raw Score','Matched Keywords','Classification Reason','Override Source','Classification Basis'}
 cols=[c for c in source if c not in fields];pd.testing.assert_frame_equal(source[cols],result[cols],check_dtype=True)
 assert not result['Display Status'].eq('Unclassified').any()
 assert result['Classification Reason'].fillna('').str.len().gt(0).all()
 for _,a in old[~old['Manual Status'].eq('Unclassified')].iterrows():
  mask=source_keys.eq(a['Key'])
  assert result.loc[mask,'Display Status'].eq(a['Manual Status']).all()
  assert result.loc[mask,'Matched Keywords'].eq('').all()
  assert result.loc[mask,'Classification Basis'].eq('Manual').all()
 journey=engine.build_customer_journey(result);rep,figs=sales_rep_kpi(result,journey)
 analytics=customer_analytics_summary(result,journey);executive=executive_dashboard_data(result,journey,rep)
 ok,msg=sm.save_session(classified_df=result,journey_df=journey,rep_kpi_df=rep,file_name=sm._load_metadata().get('file_name',''));assert ok,msg
 meta=sm._load_metadata();meta.update({'classification_engine_version':context.ENGINE_VERSION,'classification_definitions_version':context.DEFINITIONS_VERSION,'classification_activated_at':now,'released_manual_unclassified_count':len(released)});sm._save_metadata(meta)
 ok,loaded=sm.load_session();assert ok,loaded
 check=loaded['classified_df']
 assert list(sm._visit_key_series(check))==list(source_keys)
 assert not check['Display Status'].eq('Unclassified').any()
 for c in ['Display Status','Classification Reason','Classification Basis']:assert check[c].equals(result[c]),c
 assert hashlib.sha256((STAGE/'overrides.parquet').read_bytes()).hexdigest()==manifest['hashes'][str(Path('data')/'overrides.parquet')]
elapsed=time.perf_counter()-start
files=['classified_data.parquet','journey_data.parquet','rep_kpi_data.parquet','metadata.json']
state={'status':'prepared','files':files,'started_at':now};(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
try:
 with sm._write_lock():
  for name in files:
   assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==manifest['hashes'][str(Path('data')/name)],('concurrent change',name)
  state['status']='committing';(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
  for name in files:os.replace(STAGE/name,DATA/name)
  ok,loaded=sm.load_session();assert ok
  assert list(sm._visit_key_series(loaded['classified_df']))==list(source_keys)
  assert not loaded['classified_df']['Display Status'].eq('Unclassified').any()
  assert loaded['classified_df']['Display Status'].equals(result['Display Status'])
 state['status']='committed';(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
except BaseException:
 with sm._write_lock():
  for name in files:
   tmp=DATA/(name+'.activation_rollback');shutil.copy2(OUT/'data'/name,tmp);os.replace(tmp,DATA/name)
 state['status']='rolled_back';(OUT/'transaction.json').write_text(json.dumps(state,indent=2),encoding='utf-8');raise
for p in (OUT/'data').iterdir():
 if p.is_file() and p.name not in files:assert hashlib.sha256((DATA/p.name).read_bytes()).hexdigest()==hashlib.sha256(p.read_bytes()).hexdigest(),p.name
summary={'engine':context.ENGINE_VERSION,'visits':len(result),'distribution':result['Display Status'].value_counts().to_dict(),'basis_counts':result['Classification Basis'].value_counts().to_dict(),'manual_applied':n_manual,'manual_unclassified_released':len(released),'seconds':elapsed,'backup':str(OUT),'data_dir':str(DATA),'reload_verified':True,'original_fields_and_ids_unchanged':True,'overrides_and_excel_unchanged':True,'transaction_status':'committed','tests_passed':138}
(OUT/'activation_result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
