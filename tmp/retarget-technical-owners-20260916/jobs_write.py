import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
root=Path('campaigns/toronto-january-2027-jobs')
texts={
'waabi':('January placement in simulation and planning',"""Hi Sean,

I'm a UofT student currently on co-op at Automata in London, working on search, planning and simulation for biotech automation. I'm looking for a four-month role in Toronto from January to April 2027.

I saw that your CVPR tutorial session covered world models for closed-loop simulation, and came across Waabi's research co-op opening. The simulation and evaluation work caught my attention because a lot of what I do now is finding conditions that make a plan fail, then searching for a recovery before trying it on the physical system.

At Automata I've built a lab digital twin, a search-based layout optimizer and a deterministic gate that checks recovery plans before execution. I've also worked on RL and MCTS, and distilled a robot policy that I then deployed on hardware.

I'd like to keep working on systems where the simulation has to tell you something useful about what the machine will actually do. Would your team consider a four-month placement in Toronto for January? I've attached my resume and would be happy to talk if the background looks relevant.

Best,
Andrew"""),
'rbc-borealis':('January ML software placement in Toronto',"""Hi Hanieh,

I'm a UofT student on co-op at Automata in London, working on search and planning for biotech robotics. I came across RBC Borealis's winter ML software engineering opening and wanted to reach out about the four-month option in Toronto.

The part about taking a project from an ML idea through to an implementation caught my attention. In a recent robotics project I distilled a 450M-parameter policy to 292M, checked its performance against the teacher on held-out evaluations, then deployed it on physical hardware. I've also built an AlphaZero-style training system with batched neural evaluation and self-play, scaling it from Apple MPS to H200 GPUs.

I've enjoyed the work between getting a model to behave in an experiment and making it useful in a working system, and I'd like to do more of that from January to April 2027.

Is the Toronto team considering four-month students with that kind of background? I've attached my resume and would be glad to talk, or follow up with the relevant person if another team owns the opening.

Best,
Andrew"""),
'kepler':('January software internship in Toronto',"""Hi Sarah,

I'm a UofT student currently on co-op at Automata in London, working on planning and recovery for medical-lab robotics. I saw Kepler's January 2027 software internship at the Ward Street office, and the four-month timing fits what I'm looking for in Toronto.

The testing and hardware side caught my attention. At Automata I've built a deterministic gate that verifies search-generated recovery plans before they run on the robots. In a separate project I deployed a distilled robot policy on physical hardware and debugged the simulation-to-hardware pipeline.

My background is in robotics, planning and software verification. I've liked having to account for what happens when the code reaches a real machine, which is what drew me to the satellite and ground-system work in the posting.

Would that background be useful to your team for the January placement? I've attached my resume and would be happy to talk about where I could contribute.

Best,
Andrew"""),
'ecobee':('Four months of software work in Toronto this January',"""Hi Alan,

I'm a UofT student on co-op at Automata in London, working on search, planning and simulation for biotech robotics. I'm looking for a four-month role in Toronto from January to April 2027.

I've been looking at ecobee because I'd like to work on software that has a direct effect on energy use and on devices people rely on. At Automata, I've built a digital twin and layout optimizer, along with a gate that verifies recovery plans before they run on physical robots. Outside that work, I built OutageHub, a Rust platform that turns Canadian utility outage data into a national map and API.

The combination of device behaviour and the software behind it is what interests me about ecobee. I wanted to ask whether any of your Toronto engineering teams might have room for someone with that background for four months, even if it doesn't sit under a formal internship opening.

I've attached my resume. Happy to talk if there could be a fit, or hear who would be closest to that kind of work.

Best,
Andrew"""),
'peak-power':('January software and data work at Peak Power',"""Hi Meysam,

I'm a UofT student currently on co-op at Automata in London, working on search, planning and simulation for biotech automation. I'm looking for a four-month role in Toronto from January to April 2027.

I was reading about Peak Power's work on forecasting grid peaks and deciding when to dispatch batteries. That connection between predicting what will happen and deciding what to do caught my attention. My current work involves finding where a plan can fail, searching for a recovery and checking it before it reaches the physical system.

I've also built a search-based lab layout optimizer and OutageHub, a Rust platform that aggregates Canadian utility outage data into a national map and API. I'd like to apply more of that software and planning work to energy systems, where the decisions have a practical consequence.

Do you think there could be room for someone with that background on the Toronto software or data team for four months? I've attached my resume and would be happy to talk if it sounds relevant.

Best,
Andrew""")}
plans=json.load(open(root/'job-plans.json'));now=datetime.now(timezone.utc).isoformat()
for p in plans:
 subject,body=texts[p['id']];d=root/'accounts'/p['id'];resume=json.load(open(d/'resume-tailoring.json'))
 attachment=resume.get('output') or str(Path('/Users/andrewgordienko/Downloads/A. Gordienko F2026.pdf'))
 assert Path(attachment).is_file()
 draft={'subject':subject,'body':body,'recipient':p['contact']['email'],'recipient_name':p['person'],'sender':'gordienko.adg@gmail.com','attachments':[attachment],'status':'local_draft_unreviewed','send_authorized':False,'created_at':now,'research_completed_at':p['research_completed_at'],'research_sha256':hashlib.sha256((d/'job-research.json').read_bytes()).hexdigest()}
 draft['draft_hash']=hashlib.sha256((subject+'\n'+body).encode()).hexdigest()
 (d/'draft.json').write_text(json.dumps(draft,indent=2)+'\n')
 (d/'draft.md').write_text(f"To: {p['person']} <{p['contact']['email']}>\nFrom: gordienko.adg@gmail.com\nSubject: {subject}\nAttachment: {attachment}\n\n{body}\n")
 (d/'writer-packet.json').write_text(json.dumps({'research':p,'draft_hash':draft['draft_hash'],'relationship':'First-touch inquiry; no relationship asserted','voice':'Current supplied human-progression examples and contract Sent retrieval; adapted to full-time four-month employment, not side-contract sales','research_before_writer':True,'review_pending':True},indent=2)+'\n')
print('Wrote five local job drafts with real attachment paths; independent reread pending.')
