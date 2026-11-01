from io import BytesIO
from uuid import uuid4
from pathlib import Path
import json, os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, text
from app.analysis import analyze_dataframe
from app.ai import generate_ai_summary
from app.report import create_pdf_report

BASE=Path(__file__).resolve().parents[1]
DB_URL=os.getenv('DATABASE_URL', f"sqlite:///{BASE / 'tracepoint.db'}")
engine=create_engine(DB_URL, connect_args={'check_same_thread':False} if DB_URL.startswith('sqlite') else {})
with engine.begin() as conn:
 conn.execute(text('CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, filename TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, payload TEXT NOT NULL)'))
app=FastAPI(title='TRACEPOINT API',description='Autonomous Data Intelligence Platform',version='2.0.0')
origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
MAX_FILE_SIZE=25*1024*1024; MAX_ROWS=250000; MAX_COLUMNS=200
@app.get('/')
def home(): return {'message':'TRACEPOINT Data Intelligence API is running','version':'2.0.0'}
@app.get('/api/health')
def health():
 with engine.connect() as c: c.execute(text('SELECT 1'))
 return {'status':'healthy','database':'connected'}
@app.post('/api/analyze')
async def analyze_file(file:UploadFile=File(...),use_ai:bool=False):
 filename=file.filename or 'dataset'; ext=filename.lower().rsplit('.',1)[-1]
 if ext not in ('csv','xlsx','xls'): raise HTTPException(400,'Upload a CSV, XLSX or XLS file.')
 content=await file.read()
 if not content: raise HTTPException(400,'The uploaded file is empty.')
 if len(content)>MAX_FILE_SIZE: raise HTTPException(413,'Maximum upload size is 25 MB.')
 try:
  if ext=='csv':
   try: df=pd.read_csv(BytesIO(content), low_memory=False)
   except UnicodeDecodeError: df=pd.read_csv(BytesIO(content),encoding='latin-1',low_memory=False)
  else: df=pd.read_excel(BytesIO(content),engine='openpyxl' if ext=='xlsx' else 'xlrd')
  if len(df)>MAX_ROWS or len(df.columns)>MAX_COLUMNS: raise ValueError(f'Limit is {MAX_ROWS:,} rows and {MAX_COLUMNS} columns.')
  df=df.dropna(axis=1,how='all')
  if df.empty or len(df.columns)==0: raise ValueError('No usable data was found.')
  analysis=analyze_dataframe(df); ai=generate_ai_summary(analysis) if use_ai else {'available':False,'summary':'Local statistical analysis only. Gemini is optional.'}
  aid=str(uuid4()); payload={'analysis_id':aid,'filename':filename,'analysis':analysis,'ai_summary':ai}
  with engine.begin() as conn: conn.execute(text('INSERT INTO analyses(id,filename,payload) VALUES(:id,:filename,:payload)'),{'id':aid,'filename':filename,'payload':json.dumps(payload,default=str)})
  return payload
 except HTTPException: raise
 except Exception as e: raise HTTPException(400,f'Could not analyze this file: {str(e)}')
@app.get('/api/analysis/{analysis_id}')
def get_analysis(analysis_id:str):
 with engine.connect() as c: row=c.execute(text('SELECT payload FROM analyses WHERE id=:id'),{'id':analysis_id}).fetchone()
 if not row: raise HTTPException(404,'Analysis not found.')
 return json.loads(row[0])
@app.get('/api/report/{analysis_id}')
def download_report(analysis_id:str):
 data=get_analysis(analysis_id); pdf=create_pdf_report(data['analysis'],data.get('ai_summary'))
 return StreamingResponse(pdf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="TRACEPOINT_Executive_Report.pdf"'})
