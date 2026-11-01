"""Local, dataset-grounded profiling and business intelligence."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def _safe(v):
    if v is None or pd.isna(v): return None
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return float(v) if np.isfinite(v) else None
    if isinstance(v, (np.bool_,)): return bool(v)
    return v.item() if hasattr(v, 'item') else v


def analyze_dataframe(df: pd.DataFrame):
    if df.empty or len(df.columns) == 0: raise ValueError('The dataset has no usable rows or columns.')
    df = df.copy(); rows, cols = df.shape
    missing = int(df.isna().sum().sum()); duplicate = int(df.duplicated().sum())
    missing_pct = round(missing / max(rows * cols, 1) * 100, 2)
    numeric = df.select_dtypes(include=np.number)
    date_cols = []
    for c in df.columns:
        if c not in numeric.columns and any(t in str(c).lower() for t in ('date','time','timestamp')):
            parsed = pd.to_datetime(df[c], errors='coerce')
            if parsed.notna().sum() >= max(3, int(rows*.5)):
                df[c] = parsed; date_cols.append(c)
    numeric = df.select_dtypes(include=np.number)
    profiles=[]; stats={}; categorical=[]
    for c in df.columns:
        s=df[c]; typ='numeric' if pd.api.types.is_numeric_dtype(s) else ('datetime' if pd.api.types.is_datetime64_any_dtype(s) else 'categorical')
        p={'name':str(c),'dtype':str(s.dtype),'type':typ,'missing':int(s.isna().sum()),'missing_percent':round(float(s.isna().mean()*100),2),'unique':int(s.nunique(dropna=True))}
        if typ=='numeric':
            x=s.dropna(); q=x.quantile([.25,.5,.75]) if len(x) else pd.Series(dtype=float)
            p.update({'count':int(x.count()),'mean':_safe(x.mean()),'median':_safe(x.median()),'mode':_safe(x.mode().iloc[0]) if not x.mode().empty else None,'min':_safe(x.min()),'max':_safe(x.max()),'std':_safe(x.std()),'variance':_safe(x.var()),'q1':_safe(q.get(.25)),'q3':_safe(q.get(.75))})
            stats[str(c)] = {k:p[k] for k in ('count','mean','median','mode','min','max','std','variance','q1','q3')}
        elif typ=='categorical':
            p['top_values']={str(k):int(v) for k,v in s.value_counts().head(8).items()}; categorical.append(str(c))
        profiles.append(p)
    outliers=[]
    for c in numeric.columns:
        x=numeric[c].dropna()
        if len(x)>=4:
            q1,q3=x.quantile(.25),x.quantile(.75); iqr=q3-q1; lo=q1-1.5*iqr; hi=q3+1.5*iqr
            outliers.append({'column':str(c),'count':int(((x<lo)|(x>hi)).sum()),'lower_bound':_safe(lo),'upper_bound':_safe(hi)})
    correlations=[]
    if len(numeric.columns)>1:
        cm=numeric.corr(numeric_only=True)
        for i,a in enumerate(cm.columns):
            for b in cm.columns[i+1:]:
                v=cm.loc[a,b]
                if pd.notna(v): correlations.append({'column_1':str(a),'column_2':str(b),'correlation':round(float(v),3)})
    correlations.sort(key=lambda x:abs(x['correlation']),reverse=True)
    # Select a likely business metric only when column names support the interpretation.
    metric_col=next((c for c in numeric.columns if any(k in str(c).lower() for k in ('revenue','sales','amount','profit','price','cost','value','total'))), None)
    insights=[]; questions=[]
    insights.append(f'{rows:,} records and {cols} columns were profiled across {len(numeric.columns)} numeric fields and {len(categorical)} categorical fields.')
    insights.append(f'Data completeness is {round(100-missing_pct,2)}%; {missing:,} cells are missing and {duplicate:,} duplicate rows were detected.')
    if metric_col is not None:
        x=numeric[metric_col].dropna()
        insights.append(f'{metric_col} totals {_safe(x.sum()):,.2f} with an average of {_safe(x.mean()):,.2f}.' if len(x) else f'{metric_col} has no usable values.')
        questions += [{'question':f'What is the overall {metric_col} performance?','answer':f'Total: {_safe(x.sum()):,.2f}; average: {_safe(x.mean()):,.2f}; median: {_safe(x.median()):,.2f}.' if len(x) else 'Insufficient non-missing values.'}, {'question':f'Which category leads on {metric_col}?','answer':'No categorical dimension is available.'}]
        cat=next((c for c in categorical if df[c].nunique(dropna=True)<=100),None)
        if cat and len(x):
            grouped=df.groupby(cat,dropna=False)[metric_col].sum(min_count=1).dropna().sort_values(ascending=False)
            if len(grouped):
                insights.append(f'{grouped.index[0]} is the highest {cat} group by {metric_col} ({grouped.iloc[0]:,.2f}).')
                questions[-1]['answer']=f'Highest: {grouped.index[0]} ({grouped.iloc[0]:,.2f}); lowest: {grouped.index[-1]} ({grouped.iloc[-1]:,.2f}).'
    if outliers:
        total=sum(o['count'] for o in outliers); insights.append(f'IQR screening flagged {total} potential numeric outliers across {len(outliers)} columns. These are candidates for review, not confirmed errors.')
    if correlations:
        c=correlations[0]; insights.append(f'The strongest numeric association is {c["column_1"]} vs {c["column_2"]} (r={c["correlation"]:.3f}); correlation does not establish causation.')
    if not correlations: insights.append('At least two numeric columns are needed for correlation analysis.')
    questions += [
      {'question':'What is the biggest data quality concern?','answer':f'{missing:,} missing cells ({missing_pct}%) and {duplicate:,} duplicate rows were found.'},
      {'question':'Which areas require immediate attention?','answer':(f'Review missing values in {max(profiles,key=lambda p:p["missing"])["name"]}.' if profiles and max(p['missing'] for p in profiles)>0 else 'No missing values were detected; review flagged outliers and business context.')},
      {'question':'What factors are associated with better performance?','answer':(f'Top observed numeric association: {correlations[0]["column_1"]} and {correlations[0]["column_2"]} (r={correlations[0]["correlation"]}). This is not causal evidence.' if correlations else 'Insufficient numeric columns to assess associations.')},
      {'question':'What should management prioritize?','answer':f'Validate data quality, investigate the observed patterns, and confirm business context before acting. Dataset completeness: {100-missing_pct:.2f}%.'},
      {'question':'What is likely to happen in the future?','answer':'A reliable future forecast requires a suitable ordered time field and sufficient historical observations; see the prediction assessment.'},
      {'question':'What should be monitored over the next quarter?','answer':'Track the available numeric measures and category breakdowns consistently. The dataset does not establish targets or causal drivers.'}
    ]
    # Forecast only with a date-like column and sufficient distinct periods.
    forecast=None
    if date_cols and len(numeric.columns):
        d=date_cols[0]; target=metric_col or numeric.columns[0]
        temp=pd.DataFrame({'date':df[d],'value':df[target]}).dropna().groupby('date')['value'].sum().sort_index()
        if len(temp)>=8:
            x=np.arange(len(temp)).reshape(-1,1); y=temp.values.astype(float); model=LinearRegression().fit(x,y)
            pred=float(model.predict([[len(temp)]])[0]); resid=y-model.predict(x); sigma=float(np.std(resid)) if len(resid)>1 else 0
            forecast={'column':str(target),'date_column':str(d),'next_estimate':round(pred,2),'lower_estimate':round(pred-1.96*sigma,2),'upper_estimate':round(pred+1.96*sigma,2),'trend':'increasing' if model.coef_[0]>0 else 'decreasing' if model.coef_[0]<0 else 'stable','observations':len(temp),'method':'Linear regression over aggregated time periods','note':'Exploratory estimate, not a validated forecast. Interval is a residual-based approximation; seasonality and external drivers are not modelled.'}
        else: forecast={'available':False,'reason':'At least 8 distinct date periods with numeric observations are required.'}
    elif not date_cols: forecast={'available':False,'reason':'No sufficiently populated date/time column was detected. Row-order forecasting is intentionally disabled.'}
    # chart-ready category summaries
    category_charts=[]
    for c in categorical[:4]:
        vc=df[c].fillna('Missing').astype(str).value_counts().head(10)
        category_charts.append({'column':c,'data':[{'name':str(k),'value':int(v)} for k,v in vc.items()]})
    numeric_charts=[]
    for c in numeric.columns[:6]:
        s=numeric[c].dropna(); hist=pd.cut(s,bins=min(10,max(3,int(np.sqrt(max(len(s),1))))),duplicates='drop').value_counts().sort_index()
        numeric_charts.append({'column':str(c),'data':[{'range':str(k),'count':int(v)} for k,v in hist.items()]})
    preview=[]
    for _,r in df.head(12).iterrows(): preview.append({str(k):_safe(v) for k,v in r.items()})
    return {'dataset':{'rows':int(rows),'columns':int(cols),'numeric_columns':int(len(numeric.columns)),'categorical_columns':len(categorical),'date_columns':[str(c) for c in date_cols],'missing_cells':missing,'missing_percentage':missing_pct,'duplicate_rows':duplicate,'completeness':round(100-missing_pct,2)},'column_profiles':profiles,'column_statistics':stats,'numeric_columns':[str(c) for c in numeric.columns],'categorical_columns':categorical,'outliers':outliers,'correlations':correlations[:30],'insights':insights,'questions':questions,'forecast':forecast,'category_charts':category_charts,'numeric_distributions':numeric_charts,'preview':preview}
