import sys,json,sqlite3
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import quote
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
import operations
from state import get,eligible
from scheduling import POLICY
root=Path('tmp/contract-sept16'); rows=json.loads((root/'selected.json').read_text()); now=datetime.now(timezone.utc)
main_query='in:anywhere {enode.com enode.io axle.energy recycleye.com earthmover.io ferolabs.com fourgrowers.com rideco.com amperon.co earthsense.co gridraven.com agtonomy.com electriceratechnologies.com electricera.tech spare.com sparelabs.com weavegrid.com timefold.ai quantstack.net coiled.io sewerai.com goswift.ly inorbit.ai dustyrobotics.com rugged-robotics.com bearing.ai bonsairobotics.ai searoutes.com openoceanrobotics.com envelio.de takadu.com dryad.net piclo.energy}'
alias_query='in:anywhere {piclo.com envelio.com coiled.com timefold.com}'
snapshot={'complete':True,'source':'https://mail.google.com/mail/u/0/#search/'+quote(main_query),'tool_ref':'cua-gmail-selected-contracts-20260916-main-and-alias-search','account':'gordienko.adg@gmail.com','observed_at':now.isoformat(),'messages':[],'search_query':main_query,'additional_search':{'query':alias_query,'source':'https://mail.google.com/mail/u/0/#search/'+quote(alias_query),'result':'No exact matches'},'result':'No exact matches','scope_limit':'Current read-only Gmail search of listed domains in gordienko.adg@gmail.com, including Spam/Trash. Other-mailbox checks retained separately from September 15; unknown aliases and permanently deleted mail are not covered.'}
(root/'gmail-capture.json').write_text(json.dumps(snapshot,indent=2))
with sqlite3.connect('file:.runtime/outbound.sqlite3?mode=ro',uri=True) as src, sqlite3.connect(root/'before.sqlite3') as backup:src.backup(backup)
with sqlite3.connect(root/'before.sqlite3') as src, sqlite3.connect(root/'staged.sqlite3') as dest:src.backup(dest)
with operations.connect(root/'staged.sqlite3') as db:
 for row in rows:
  c=operations.sync_thread(db,row['id'],snapshot)
  ok,why=eligible(db,c,now);assert ok,(c['id'],why)
  operations.decide(db,c['id'],{'action':'SEND','reason':'Selected for Andrew\'s September 16 batch of 30 personal contract-work emails; preserve existing copy. Local recommendation only.','snapshot_at':c['snapshot_at'],'research_version':c['research_version']},now)
 result=operations.build_queue(db,'2026-09-16',30,now)
 (root/'staged-queue.json').write_text(json.dumps(result,indent=2))
 actual={x['contact_id'] for x in result['actions']};expected={r['id'] for r in rows}
 print(json.dumps({'count':len(actual),'unexpected':sorted(actual-expected),'missing':sorted(expected-actual),'times':[{k:x[k] for k in ('contact_id','send_at')} for x in result['actions']],'held_for_selected':[x for x in result['held'] if x['contact_id'] in expected]},indent=2))
