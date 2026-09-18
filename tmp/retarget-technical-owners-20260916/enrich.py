import json,sys,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from apollo import request,receipt
from research import write_json
root=Path('tmp/retarget-technical-owners-20260916')
rows={r['account']:r for r in json.load(open(root/'discovery.json'))}
ids={
'axle':['60335ea0d4026e000137e2b1'],
'agtonomy':['651796e1f9cfb50001790901'],
'bonsai-robotics':['615d1de316b81200012a97e6'],
'bearing-ai':['5f5cf4d562b17000016f199c','623160d19eb3930001891c26'],
'spoor':['54c236197468697af7242c85','60f98ce057693200014140a8'],
'glacier':['54c17a0f7468697af7c4d814'],
'terraclear':['57e142cca6da987dc46cd39b'],
'timefold':['62c5a62e20272f00012894d3'],
'toffeex-marco':['64f394263947c70001684b6b','6114217e5f381d0001a38f32'],
'ev-energy-steve':['57e0358da6da985eec176185'],
'flash-forest':['5e76824105cbab000196310b'],
'treefera':['6861ecbdcce6ba000131e2ca'],
'chloris':['54a417ef7468692abf1e9c2b'],
'rugged':['5653b7e8a6da984c66011f96'],
'civ-robotics':['67996316b12b8f0001aa0575'],
'foxglove':['5ffb5bb8dd5c51000166dbee'],
'vsp-aaike':['5f8424b5dd27130001295bc7'],
'assaia':['667411496bbd320001cc8b4c'],
'neural-concept':['6195b2a9fafc120001ed208e'],
'augmentus':['612a3a97bb3aac0001706593','54a2d2a77468693a7e63bd3f'],
'duality':['5648f881a6da980db5057368'],
'albert':['55710e3273696475ced30800'],
'realtime-robotics':['5e83c2d086ebd700010da725','5f0a8877f77a8600018de827'],
'orchard':['6215cf39d130eb0001a3318c','60c59eda60f57e0001c90499'],
'gideon':['5f5357193cb023000142c9fb','600b8d21cb66840001737f40'],
'carbonrobotics':['6083d9652406d10001e14d8b'],
'waabi':['67125925f4a93700018b8e19','6312252c6de58a00017ee40f'],
'kepler':['60e77992cf4ba00001953a6c'],
'ecobee':['60f5e0e3a7ba870001d5d26f'],
'peak-power':['67ef6c03e877fe00013de4cc'],
'rbc-borealis':['602f8df3f068da0001a63050']}
jobs=[(a,{'id':i}) for a,ii in ids.items() for i in ii]+[('coiled',{'name':'Florian Jetter'}),('atmo',{'name':'Johan Mathe'})]
def call(j):
 a,p=j;p={**p,'domain':rows[a]['domain'],'reveal_personal_emails':False,'reveal_phone_number':False,'run_waterfall_email':False,'run_waterfall_phone':False}
 try:return p,request('people/match',p)
 except Exception as e:return p,{'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(call,jobs))
out=[]
for (a,_),(p,v) in zip(jobs,results):
 r=rows[a];sid,at=receipt(Path('campaigns')/r['campaign'],'people/match',p,v);person=v.get('person') or {}
 out.append({'account':a,'campaign':r['campaign'],'domain':r['domain'],'source_id':sid,'observed_at':at,'person':person,'error':v.get('error')})
 org=person.get('organization') or {}
 print(a,person.get('name'),person.get('title'),org.get('primary_domain'),person.get('email_status'),person.get('email'),person.get('city'),v.get('error'))
write_json(root/'enriched.json',out)
