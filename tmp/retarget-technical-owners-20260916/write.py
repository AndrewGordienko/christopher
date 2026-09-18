import json,sys,re
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import write_json
from readiness import fingerprint
root=Path('tmp/retarget-technical-owners-20260916');rows=json.load(open(root/'plans.json'))
intro=rows[0]['old']['queue_body'].split('\n\n')[1]
close='Happy to hop on a call if it sounds worth exploring, and happy to send over my resume as well.\n\nBest,\nAndrew'
changes={
'realtime-robotics':[
"I was reading about Realtime's multi-robot planning and got interested in what happens when one robot is delayed after the paths have been planned. The paths can still be collision-free, while the order in which the robots can move through a shared area has changed.",
"That's close to the failure and recovery work I do now, where individually valid actions can leave a system with no useful way to continue. I'd like to apply more of that work to physical automation where finding a different sequence lets the machines finish the job.",
"I wanted to ask whether there might be room for a small contract project around that. One idea would be to search an offline cell model for small timing changes that disrupt the sequence, then reduce them to cases the team can replay, but I'd rather shape the work around whichever planning problem would actually be useful."],
'orchard':[
"I was reading about FruitScope's repeated passes through an orchard and got interested in how you separate a change in the fruit from a change in what the cameras can see. The same trees can look quite different when fruit is hidden by the canopy on one pass and visible on the next.",
"That connects to the evaluation work I've done with models running on physical robots, where a change in the observation can affect the result. I'd like to use more of that work on agricultural systems that help people make decisions in the field.",
"I wanted to ask whether there might be room for a small contract project around that. One idea would be to compare paired passes against an agreed reference and test which visibility changes alter the count, but I'd rather start with whichever perception or evaluation problem the team actually needs help with."],
'gideon':[
"I was reading about Gideon's trailer loading and got interested in placements that work for the current pallet but leave less room for the next move. Once some of the trailer is already loaded, finding a way to continue is a different problem from planning the whole sequence from scratch.",
"That's close to what I work on in biotech automation: finding the conditions that leave a system stuck and searching for a recovery from the state it's already in. I'd like to do more of that planning work on machines operating in physical spaces with changing constraints.",
"That made me want to ask whether there might be room for a small contract project. One idea would be to search simulated loading sequences for those cases and compare ways to continue with less undoing of completed work, but I'd rather shape it around whichever autonomy or recovery problem would help your team."],
'carbonrobotics':[
"I was reading about Carbon's laser weeding and got interested in cases where a weed is partly hidden by a crop. The part I wondered about was whether the model's confidence changes as the view gets less informative, or whether it can stay confident after losing the detail it was relying on.",
"I've worked on evaluating a vision-language-action model and getting it running on physical hardware, so understanding what a model can reliably infer is something I'd like to spend more time on. Agricultural robotics is particularly appealing because those predictions lead to a concrete action in the field.",
"I wanted to ask whether there might be room for a small contract project around that. One idea would be to build an offline evaluation on an agreed image set and compare confidence with the result as crop and weed overlap changes, but I'd rather work on whichever perception-evaluation question would be useful to the team."]}
for r in rows:
 a=r['account'];first=r['owner']['name'].split()[0]
 if a in changes:
  r['body']='\n\n'.join(['Hi '+first+',',intro]+changes[a]+[close]);r['copy_change']='The later-wave draft still used the superseded exploratory formula. Restored the selected human progression while preserving its original technical question.'
 else:
  r['body']=re.sub(r'\AHi [^\n]+,','Hi '+first+',',r['old']['queue_body'],count=1);r['copy_change']='Greeting only; preserve the current approved company-specific thought and wording.'
 r['subject']=r['old']['queue_subject'];r['draft_hash']=fingerprint(r['subject'],r['body']);r['writer_completed_at']=datetime.now(timezone.utc).isoformat()
write_json(root/'written.json',rows)
print(json.dumps({'drafts':len(rows),'greeting_only':24,'later_wave_voice_corrections':list(changes),'queued':False}))
