import json,shutil
from pathlib import Path
root=Path('tmp/contract-revision-2026-09-16');rows=json.load(open(root/'drafts.json'));shutil.copy2(root/'drafts.json',root/'writer-before-critic.json')
edits={
'takadu':[("TaKaDu's event detection caught my attention because the input history matters as much as any individual reading. A missing pressure reading is a useful case to test: does the surrounding data still produce the right event, and how late does it appear?","For TaKaDu's event detection, I could help test how missing pressure readings affect the time it takes to identify a leak. The useful result would be a repeatable input sequence for each missed or delayed event.")],
'enode':[("If a charger misses a command, the next plan has to account for the charge that never happened.","After a missed charging command, the next plan needs to use the charge actually delivered.")],
'beebop':[("The useful result would be a repeatable case showing which commitments can still be met, rather than just a different dispatch score.","Each test would show which commitments can still be met and preserve the exact dropout sequence for debugging.")],
'envelio':[("generating difficult network scenarios for the solver","generating load and generation combinations near the network's operating limits")],
'quantstack':[("Building the simulation has made me appreciate how much time goes into the tooling around a numerical workflow. With QuantStack's Jupyter work, I could take on a contained issue where the same calculation behaves differently in the browser and native Python.","I could help on the numerical tooling around QuantStack's Jupyter work. One bounded task would be fixing a case where the same calculation behaves differently in the browser and native Python.")],
'earthmover':[("I'm a UofT student on co-op in London, UK, working on search and recovery for lab automation. I've built a system that finds deadlocks and searches for a way out of them.","I'm a UofT student on co-op in London, UK, building search and recovery tools for lab automation.")],
}
ml="I'm a UofT student on co-op in London, UK, working on lab automation. I've also distilled a vision-language-action model, evaluated it against the original and deployed it on physical robotic hardware."
for r in rows:
 before=r['body']
 for a,b in edits.get(r['account'],[]):
  assert a in r['body'];r['body']=r['body'].replace(a,b)
 if r['account'] in ('recycleye','sewerai'):
  ps=r['body'].split('\n\n');ps[1]=ml;r['body']='\n\n'.join(ps)
 r['critic_edit_reason']=({'takadu':'Remove an extra research question; make the artifact and yes/no backlog ask clear.','enode':'Avoid assuming the missed command delivered no energy at all.','beebop':'Remove unnecessary comparison with an unspecified dispatch score.','envelio':'Name load/generation inputs instead of abstract difficult scenarios.','quantstack':'Remove reflective filler; connect simulation background directly to numerical code.','earthmover':'Avoid stating the same deadlock-search proof twice.','recycleye':'Use actual model evaluation/deployment experience to support an ML-evaluation offer.','sewerai':'Use actual model evaluation/deployment experience rather than an unexplained deadlock-to-vision jump.'}.get(r['account'],'No sentence-level repair required after full reread.'))
 if before!=r['body']:print(r['account']+'\n'+r['body']+'\n')
(root/'drafts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
