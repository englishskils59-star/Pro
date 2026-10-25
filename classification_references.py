"""Dated supplier references from existing records; never a name-only answer."""
from bisect import bisect_left
import re
import pandas as pd
from utils import normalize_arabic

def apply_supplier_references(result,reference_records,competitor_pattern):
    if reference_records is None or not {'Customer Name','Visit Date','Display Status'}.issubset(reference_records):return result
    # Restrict reference preparation to names actually mentioned in eligible
    # relation phrases. The same exact predicates apply before/after indexing.
    eligible={};mentioned=set()
    for i,row in result.iterrows():
        if row.get('Display Status') not in {'Unclassified','Potential Customer','Target Customer'}:continue
        if row.get('Override Source')=='Manual':continue
        note=normalize_arabic(str(row.get('Visit Notes','')))
        if competitor_pattern.search(note) or re.search(r'(?<!\w)(?:لم|لن|لا|مش|ليس|غير)(?!\w)|غير مهتم|رفض|سيشتري|هيشتري|سيتم الطلب|اول طلبيه',note):continue
        if re.search(r'كان شغال|كان يتعامل|عميل سابق|عميل ساابق|حاليا مبطل|توقف',note):continue
        if not re.search(r'شغال من|شعال من|بيسحب.*من|سحب.*من|يشتري.*من|من تحت',note):continue
        eligible[i]=note
        for relation in re.finditer(r'(?:شغال من|شعال من|من تحت|من خلال|من الموزع|من التاجر)\s+(.+)',note):
            words=relation.group(1).split()
            mentioned.update(' '.join(words[:n]) for n in range(2,min(6,len(words))+1))
    if not mentioned:return result
    refs=reference_records.copy();refs['_date']=pd.to_datetime(refs['Visit Date'],errors='coerce',utc=True)
    refs['_name']=refs['Customer Name'].fillna('').astype(str).map(normalize_arabic)
    refs=refs[refs['_name'].isin(mentioned) & refs['_date'].notna() & ~refs['Display Status'].isin(['No Meeting','Unclassified'])]
    grouped={}
    for name,frame in refs.groupby('_name',sort=False):
        if len(name.split())<2:continue
        # Multiple governorates/full identities: do not merge by name spelling.
        if 'Governorate' in frame and frame['Governorate'].dropna().nunique()>1:continue
        grouped[name]=frame.sort_values('_date',kind='stable')
    out=result.copy()
    for i,note in eligible.items():
        row=out.loc[i]
        date=pd.to_datetime(row.get('Visit Date'),errors='coerce',utc=True)
        if pd.isna(date):continue
        matches=[]
        for relation in re.finditer(r'(?:شغال من|شعال من|من تحت|من خلال|من الموزع|من التاجر)\s+(.+)',note):
            words=relation.group(1).split()
            for n in range(2,min(6,len(words))+1):
                name=' '.join(words[:n])
                if name not in grouped:continue
                earlier=grouped[name];earlier=earlier[earlier['_date']<date]
                if earlier.empty:continue
                latest_date=earlier['_date'].max();latest=earlier[earlier['_date']==latest_date]
                if set(latest['Display Status'])!={'Current Customer'}:continue
                matches.append((name,latest_date,latest.iloc[-1]))
        if len(matches)!=1:continue
        name,when,ref=matches[0]
        source=str(ref.get('Override Source','')) or 'حالة محفوظة بالسجلات'
        reason=f'تعامل من موزع مثبت بالسجلات: {ref["Customer Name"]}؛ Current Customer بتاريخ {when.date()}؛ المصدر: {source}. المرجع سابق للزيارة وليس استنتاجا من الاسم وحده'
        out.at[i,'Suggested Status']='current';out.at[i,'Display Status']='Current Customer'
        out.at[i,'Confidence Score']=80.0;out.at[i,'Raw Score']=80
        out.at[i,'Matched Keywords']='تعامل مع موزع ذي حالة محفوظة مؤرخة'
        out.at[i,'Classification Reason']=reason+' | مؤشر أدلة وليس احتمال صحة إحصائي'
    return out
