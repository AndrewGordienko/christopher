from pathlib import Path
import json, hashlib
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

root=Path('campaigns/toronto-january-2027-jobs')
out=Path('output/pdf');out.mkdir(parents=True,exist_ok=True)
fontroot=Path('/System/Library/Fonts/Supplemental')
for name,file in [('Resume','Times New Roman.ttf'),('Resume-Bold','Times New Roman Bold.ttf'),('Resume-Italic','Times New Roman Italic.ttf'),('Resume-BoldItalic','Times New Roman Bold Italic.ttf')]:
 pdfmetrics.registerFont(TTFont(name,str(fontroot/file)))
pdfmetrics.registerFontFamily('Resume',normal='Resume',bold='Resume-Bold',italic='Resume-Italic',boldItalic='Resume-BoldItalic')
W,H=A4; width=W-90
styles={
 'body':ParagraphStyle('body',fontName='Resume',fontSize=10.35,leading=12.0,spaceAfter=1.4),
 'bullet':ParagraphStyle('bullet',fontName='Resume',fontSize=10.35,leading=12.0,leftIndent=11,firstLineIndent=-8,spaceAfter=1.1),
 'small':ParagraphStyle('small',fontName='Resume',fontSize=9.5,leading=11.0,spaceAfter=1.0),
 'entry':ParagraphStyle('entry',fontName='Resume',fontSize=10.6,leading=12.2,spaceAfter=0),
 'right':ParagraphStyle('right',fontName='Resume',fontSize=10.25,leading=12.2,alignment=2),
 'section':ParagraphStyle('section',fontName='Resume-Bold',fontSize=12,leading=13.3,spaceBefore=6.3,spaceAfter=1.0),
 'name':ParagraphStyle('name',fontName='Resume-Bold',fontSize=19,leading=21.5,spaceAfter=2.0),
 'headline':ParagraphStyle('headline',fontName='Resume',fontSize=10.3,leading=12.0,spaceAfter=2.0),
}

# Each bullet retains a traceable fact from the purple master. Selection/order
# changes are recorded beside each role; missing job requirements stay absent.
automata={
 'search':'Developed a deadlock search and recovery system using CP-SAT and breadth-first search to identify unsafe workflow states and generate valid recovery paths for medical-laboratory robotics.',
 'gate':'Built a deterministic safety gate that verifies search-generated plans before execution, taking the system from simulation to deployment on physical robotic hardware.',
 'twin':'Built a 3D digital twin to generate and validate laboratory configurations, then extended it into a search-based layout optimizer minimizing robot travel and other workflow costs.'}
tiny={
 'model':'Distilled a 450M-parameter SmolVLA policy to 292M parameters for local deployment, reducing bf16 footprint from 749 MB to 557 MB while achieving performance comparable to the teacher on held-out evaluations.',
 'hardware':'Deployed the distilled policy onto physical robotic hardware and debugged the simulation-to-hardware pipeline for closed-loop manipulation.'}
hudson={
 'search':'Built an AlphaZero-style chess engine combining a learned policy-value network with Monte Carlo Tree Search, reaching approximately 1800 Elo.',
 'training':'Implemented PUCT search, network-guided priors, exploration, batched neural evaluation, self-play, replay buffers and arena-based model promotion.',
 'scale':'Scaled training from Apple MPS to NVIDIA H200 GPUs, building high-throughput infrastructure for self-play generation and policy-value training.'}
utm=['Led the creation of a Karl Sims-inspired genetic algorithm to generate MuJoCo robot morphologies and trained shared PPO locomotion policies across evolved bodies to play 2v2 soccer.','Developed multi-agent planning experiments using Transformer-generated spatial heatmaps and Monte Carlo Tree Search for action selection.']
configs={
 'waabi':{'label':'Waabi','headline':'Planning & Search | Robotics Simulation | Reinforcement Learning','auto':['twin','search','gate'],'tiny':['model','hardware'],'hudson':['search','training','scale'],'projects':['tiny','utm','hudson'],'skill_order':['ml','languages','tools'],'changes':['Moved education and technical skills nearer the top for student-role screening.','Led Automata with the digital twin and search-based layout optimizer, retaining recovery and verification details.','Placed MuJoCo/PPO and multi-agent planning ahead of chess infrastructure.','Shortened low-relevance commercial/instruction bullets without changing employers, titles or dates.']},
 'rbc-borealis':{'label':'RBC-Borealis','headline':'Machine Learning | Model Evaluation & Deployment | Software Engineering','auto':['gate','search','twin'],'tiny':['model','hardware'],'hudson':['scale','training','search'],'projects':['tiny','hudson','utm'],'skill_order':['languages','ml','tools'],'changes':['Moved education and technical skills nearer the top.','Emphasized model compression, held-out evaluation, implementation and H200 training infrastructure.','Kept the Rust outage-data API as concrete software experience.','Did not add Bash, Spark, Hadoop, databases or a Computer Science degree.']},
 'kepler':{'label':'Kepler','headline':'Software Verification | Planning Algorithms | Robotics & Hardware Deployment','auto':['gate','search','twin'],'tiny':['hardware','model'],'hudson':['search','training','scale'],'projects':['tiny','hudson','utm'],'skill_order':['languages','tools','ml'],'changes':['Led with deterministic plan verification and physical-hardware deployment.','Moved TinyVLA hardware debugging ahead of model compression.','Made C++, Python, Git and Linux easy to find without tying them to undocumented projects.','Did not claim embedded Linux, firmware/drivers, Yocto, OpenEmbedded, FreeRTOS or electrical instrumentation.']}
}
skills={
 'languages':'<b>Languages:</b> Python, C++, Rust, JavaScript',
 'ml':'<b>ML &amp; Robotics:</b> PyTorch, MuJoCo, CUDA, NumPy, Gymnasium, Transformers, LeRobot',
 'tools':'<b>Tooling:</b> Git, Linux, pytest, Flask, multi-GPU training (H200), Apple MPS'}
def P(t,style='body'):return Paragraph(t,styles[style])
def section(story,title):
 story.extend([P(title,'section'),HRFlowable(width='100%',thickness=.4,spaceAfter=4)])
def row(left,right):
 t=Table([[P(left,'entry'),P(right,'right')]],colWidths=[width*.77,width*.23])
 t.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('VALIGN',(0,0),(-1,-1),'TOP')]))
 return t
def entry(story,name,date,role,location,bullets):
 block=[row('<b>'+escape(name)+'</b>',escape(date)),row('<i>'+escape(role)+'</i>',escape(location))]
 if bullets:block.append(P('- '+escape(bullets[0]),'bullet'))
 story.append(KeepTogether(block))
 story.extend(P('- '+escape(b),'bullet') for b in bullets[1:]);story.append(Spacer(1,3.1))

outputs=[]
for key,c in configs.items():
 path=out/f"Andrew-Gordienko-{c['label']}-January-2027.pdf"
 story=[P('Andrew Gordienko','name'),P('<link href="mailto:gordienko.adg@gmail.com">gordienko.adg@gmail.com</link> | <link href="https://github.com/AndrewGordienko">github.com/AndrewGordienko</link> | <link href="https://www.linkedin.com/in/andrewgordienko">LinkedIn: Andrew Gordienko</link>','small'),P(escape(c['headline']),'headline'),P('Seeking a Toronto role | January-April 2027 (4 months)','small')]
 section(story,'Education')
 story.extend([row('<b>University of Toronto</b>','Expected June 2028'),row('B.A., Computational Cognitive Science; Computer Science coursework','Toronto, Canada')])
 section(story,'Technical Skills')
 for sk in c['skill_order']:story.append(P(skills[sk]))
 section(story,'Work Experience')
 entry(story,'Automata Technologies','May 2026 - Present','Research Intern, Robotics and Planning','London, UK',[automata[k] for k in c['auto']])
 entry(story,'OutageHub (OutageHub.ca)','Nov 2024 - Present','Founder','Hybrid',['Built a Rust-based platform aggregating Canadian utility outage data into a real-time national map and API.','Lead partnerships and business development with organizations including the Government of Canada and Canadian Red Cross around outage intelligence and API access.'])
 section(story,'Research and Projects')
 for project in c['projects']:
  if project=='tiny':entry(story,'TinyVLA','2026','Vision-Language-Action Model Distillation for Robotics','',[tiny[k] for k in c['tiny']])
  if project=='hudson':entry(story,'Hudson64','2025','AlphaZero-Style Reinforcement Learning and Search','',[hudson[k] for k in c['hudson']])
  if project=='utm':entry(story,'UTMIST Virtual Creatures','Sep 2023 - Apr 2024','Lead Researcher, Reinforcement Learning and Multi-Agent Planning','',utm)
 section(story,'Additional Experience')
 entry(story,'G&K Software LLC','Nov 2025 - Present','Head of Growth','Remote',['Lead sales and business development for a software and AI consultancy, translating customer problems into scoped technical engagements.'])
 entry(story,'CODE-IT Hacks','Jun 2022 - Sep 2022','Artificial Intelligence Instructor','Toronto, Canada',['Taught AI, machine learning and programming to middle and high school students through hands-on coding projects.'])
 doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=39,leftMargin=39,topMargin=29,bottomMargin=28,title='Andrew Gordienko - January 2027',author='Andrew Gordienko',subject=c['headline'])
 doc.build(story)
 reader=PdfReader(path);assert len(reader.pages)==1,(key,len(reader.pages))
 text=reader.pages[0].extract_text();assert all(x in text for x in ['292M','749 MB','557 MB','1800 Elo','Expected June 2028','Computational Cognitive Science'])
 assert not any(x in text for x in ['FreeRTOS','Yocto','OpenEmbedded','Spark','Hadoop'])
 uris=[a.get_object().get('/A',{}).get('/URI') for a in reader.pages[0].get('/Annots',[])]
 assert set(uris)=={'mailto:gordienko.adg@gmail.com','https://github.com/AndrewGordienko','https://www.linkedin.com/in/andrewgordienko'}
 (Path('tmp/pdfs')/(key+'-resume.txt')).write_text(text)
 target=root/'accounts'/key/'resume-tailoring.json';meta=json.load(open(target));meta.update(status='Authored; text and links checked; visual review pending',output=str(path.resolve()),changes=c['changes'],headline=c['headline'],preserved=['actual degree','employers and job titles','dates','model metrics','ownership level','original three contact links'],master_unchanged=True,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 target.write_text(json.dumps(meta,indent=2)+'\n');outputs.append({'company':key,'pdf':str(path),'pages':1,'links':len(uris)})
print(json.dumps(outputs,indent=2))
