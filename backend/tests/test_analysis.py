import pandas as pd
from app.analysis import analyze_dataframe

def test_profile_and_questions():
    df=pd.DataFrame({'date':pd.date_range('2025-01-01',periods=12,freq='MS'),'revenue':range(100,112),'region':['East','West']*6})
    out=analyze_dataframe(df)
    assert out['dataset']['rows']==12
    assert out['dataset']['completeness']==100
    assert out['forecast']['next_estimate'] is not None
    assert len(out['questions'])>=5

def test_missing_duplicate_and_no_date_forecast():
    df=pd.DataFrame({'amount':[1,2,None,2], 'team':['A','A','B','A']})
    out=analyze_dataframe(df)
    assert out['dataset']['missing_cells']==1
    assert out['dataset']['duplicate_rows']==1
    assert out['forecast']['available'] is False
