"""Read-only old/new classification evaluation; outputs only to reports/."""
from pathlib import Path
import sys,json,hashlib,time,statistics,importlib.util,platform
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import classification_engine as new
import classification_context as ctx
import storage_manager as sm
OUT=Path((ROOT/'reports'/'latest_classification_review.txt').read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('classification_baseline',OUT/'backup'/'classification_engine.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
DATA=Path(json.loads((ROOT/'wdi_config.json').read_text(encoding='utf-8'))['data_dir'])
source=pd.read_parquet(DATA/'classified_data.parquet')
source['_review_row_id']=range(len(source))
custom=json.loads((DATA/'custom_rules.json').read_text(encoding='utf-8')) if (DATA/'custom_rules.json').exists() else []
new.set_custom_rules(custom);old.set_custom_rules(custom)
result_cols=['Suggested Status','Display Status','Confidence Score','Raw Score','Matched Keywords','Classification Reason','Override Source']
raw=source.drop(columns=result_cols,errors='ignore')
# Excel I/O, merge/override application and exports are outside these timings.
def timed(engine):
 samples=[];out=None
 for _ in range(3):
  ctx.cached_decide.cache_clear();ctx.compile_rules.cache_clear()
  start=time.perf_counter();out=engine.classify_dataframe(raw);samples.append(time.perf_counter()-start)
 return out,samples
baseline,old_times=timed(old)
updated,new_times=timed(new)
start=time.perf_counter();new.classify_dataframe(raw);warm=time.perf_counter()-start
baseline=baseline.set_index('_review_row_id').sort_index();updated=updated.set_index('_review_row_id').sort_index()
stored=source.set_index('_review_row_id').sort_index()
# Reapply only keyed persisted overrides in memory. No load_session/migration/save.
overrides=pd.read_parquet(DATA/'overrides.parquet') if (DATA/'overrides.parquet').exists() else pd.DataFrame()
effective=updated.copy();key_map={}
if not overrides.empty and 'Key' in overrides:
 valid=overrides[overrides['Manual Status'].isin(new.STATUS_DISPLAY.values())].drop_duplicates('Key',keep='last')
 key_map=dict(zip(valid['Key'],valid['Manual Status']))
 keys=sm._visit_key_series(effective)
 for idx,key in keys.items():
  if key in key_map:ctx.apply_manual_result(effective,idx,key_map[key],new.STATUS_DISPLAY)
else:
 keys=sm._visit_key_series(effective)
manual_count=sum(key in key_map for key in keys)
# Original record attributes remain exactly the same (apart from ordering).
pd.testing.assert_frame_equal(raw.set_index('_review_row_id').sort_index(),updated.drop(columns=result_cols,errors='ignore'),check_dtype=True)
assert len(effective)==len(source)
assert set(effective['Suggested Status']).issubset(new.STATUS_DISPLAY)
assert pd.api.types.is_numeric_dtype(effective['Confidence Score'])
comparison=pd.DataFrame(index=updated.index)
comparison['Record ID']=keys
for col in ['Customer Name','Visit Date','Sales Rep Name','Visit Notes']:
 if col in stored:comparison[col]=stored[col]
for prefix,frame in [('Stored',stored),('Old Engine',baseline),('New Rules',updated),('New Effective',effective)]:
 for col in result_cols:
  if col in frame:comparison[prefix+' '+col]=frame[col]
comparison['Has Saved Override']=[key in key_map for key in keys]
comparison['Status Changed (Rules)']=baseline['Display Status']!=updated['Display Status']
comparison['Status Changed (Stored vs Effective)']=stored['Display Status']!=effective['Display Status']
comparison['Review Note']=comparison.apply(lambda r:'Persisted manual decision retained; reason metadata aligned' if r['Has Saved Override'] else ('Rules output changed; review required, not human-approved correction' if r['Status Changed (Rules)'] else 'Status unchanged; evidence metadata may differ'),axis=1)
comparison.to_csv(OUT/'comparison_before_after.csv',index_label='Source Row',encoding='utf-8-sig')
with pd.ExcelWriter(OUT/'comparison_before_after.xlsx',engine='xlsxwriter',engine_kwargs={'options':{'strings_to_formulas':False,'strings_to_urls':False}}) as writer:
 comparison.to_excel(writer,index_label='Source Row',sheet_name='All Records')
 comparison[comparison['Status Changed (Rules)']].to_excel(writer,index_label='Source Row',sheet_name='Changed Rules')
 transition=pd.crosstab(baseline['Display Status'],updated['Display Status']);transition.to_excel(writer,sheet_name='Transitions')
 for ws in writer.sheets.values():ws.freeze_panes(1,1);ws.autofilter(0,0,ws.dim_rowmax,ws.dim_colmax);ws.set_column(0,ws.dim_colmax,22)
# Diagnosis is evidence about this snapshot only, not the missing historical Excel.
kw=stored.get('Matched Keywords',pd.Series('',index=stored.index)).fillna('').astype(str)
reason=stored.get('Classification Reason',pd.Series('',index=stored.index)).fillna('').astype(str)
inconsistent=(stored['Display Status']!='Unclassified') & kw.eq('') & reason.str.contains('غير مصنف|لا توجد كلمات',regex=True)
manual_source=stored.get('Override Source',pd.Series('',index=stored.index)).fillna('').eq('Manual')
followup=kw.map(lambda s:ctx.normalize_note(s) == ctx.normalize_note('متابعة')) & stored['Display Status'].eq('Current Customer')
manifest=json.loads((OUT/'data_hashes_before.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in manifest.items()),'Original business data changed'
summary={'source':str(DATA/'classified_data.parquet'),'rows':len(source),'unique_normalized_notes':len({ctx.normalize_note(n) for n in raw['Visit Notes']}),
 'custom_rules':len(custom),'persisted_override_rows':len(overrides),'persisted_override_columns':list(overrides.columns),
 'manual_overrides_applied_in_memory':manual_count,'rules_status_changed':int(comparison['Status Changed (Rules)'].sum()),
 'stored_vs_effective_status_changed':int(comparison['Status Changed (Stored vs Effective)'].sum()),
 'stored_status_without_keyword_and_unclassified_reason':int(inconsistent.sum()),'of_these_manual_marker':int((inconsistent&manual_source).sum()),
 'stored_current_followup_only':int(followup.sum()),'stored_no_meeting':int(stored['Display Status'].eq('No Meeting').sum()),
 'stored_confidence_100':int(stored['Confidence Score'].eq(100).sum()),'stored_100_manual':int((stored['Confidence Score'].eq(100)&manual_source).sum()),
 'old_seconds':old_times,'new_cold_seconds':new_times,'new_warm_seconds':warm,
 'median_speedup':statistics.median(old_times)/statistics.median(new_times),
 'runtime':{'python':sys.version,'pandas':pd.__version__,'platform':platform.platform()},
 'input_and_data_hashes_unchanged':True,'historical_results_xlsx_found':False,'historical_audit_xlsx_found':False,
 'accuracy':None,'accuracy_reason':'No independently verified labeled evaluation corpus; changes are not correctness estimates',
 'engine_version':ctx.ENGINE_VERSION,'definitions_version':ctx.DEFINITIONS_VERSION}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
