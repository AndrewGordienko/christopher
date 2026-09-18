#!/usr/bin/env python3
"""Optional broad discovery adapter. Run with .venv-jobs/bin/python.
Results are candidates, not trusted company or hiring-budget facts.
"""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
from jobspy import scrape_jobs
p=argparse.ArgumentParser();p.add_argument('search');p.add_argument('--location',default='Canada');p.add_argument('--country',default='Canada');p.add_argument('--limit',type=int,default=25);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if not 1<=a.limit<=100:raise SystemExit('Discovery limit must be 1–100')
frame=scrape_jobs(site_name=['indeed'],search_term=a.search,location=a.location,country_indeed=a.country,results_wanted=a.limit,hours_old=168,verbose=0)
result={'observed_at':datetime.now(timezone.utc).isoformat(),'query':a.search,'location':a.location,'tool':'JobSpy','jobs':json.loads(frame.to_json(orient='records',date_format='iso')),'status':'unqualified_discovery','instruction':'Verify employer and full JD at official careers source, then assess mission fit; never apply to jobs automatically.'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'path':str(a.output),'candidates':len(result['jobs'])}))
