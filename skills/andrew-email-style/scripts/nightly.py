#!/usr/bin/env python3
"""23:00 Europe/London preparation job. Requires a running local Chrome/Codex session.
The model refreshes Gmail/research and drafts locally. This job never sends mail.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import argparse,fcntl,json,os,subprocess,shutil
from research import WORKSPACE,write_json
from state import connect,build_queue,projection,stamp
from operations import import_campaigns

PROMPT='''Read AGENTS.md and skills/andrew-email-style/SKILL.md, then references/nightly-workflow.md.
Prepare tomorrow's highest-value outbound actions, within daily capacity {capacity}, across existing active missions only.
Do not send, schedule in Gmail, create Gmail drafts, approve drafts, purchase anything, modify code/settings or enrich beyond remaining existing mission slots.
1. Read operations.py status and mission next tasks. Sync all known contacts using the current authenticated Chrome Gmail accounts; read complete current threads and all new replies, bounces, opt-outs and OOO. Capture original IDs/timestamps and classify from the actual messages. Use operations.py sync immediately for each update. A search miss does not erase a thread. If Gmail/browser unavailable, record the limitation in .runtime/nightly-limitations.json and leave stale contacts held. Do not claim a sync.
2. Run signals.py poll for existing watches. Read new/changed full JDs and pressure sources; classify problem/owner/freshness/fit using signals.py. Hiring is a ranking signal, not a job application or guaranteed external budget. Regulations require the actual legal obligation owner and sourced applicability. Unknowns stay unknown. Add public career/newsroom/status/regulator watches as research establishes their account relevance. For due follow-ups refresh current relevant company/person research; separate facts from hypotheses. Retrieve comparable Sent cadence/outcomes. Decide SEND / WAIT / COMPLETE with operations.py decide. SEND means prepare a local draft for review, never send. Preserve original subject, thread and sender. Only generate the due body now, with a real reason to reply and separate critic pass. No resending biography or generic following-up phrases. Current task drafts outrank generic Sent averages.
3. Fill remaining capacity from qualified first contacts in existing missions. Respect account rank, backup windows, account-wide replies and one account/email per queue day. Research unresolved slots only up to the mission's actual target; do not blindly create 30 new prospects. Use Apollo only for the final ranked people.
4. Persist sourced packets, context, retrieval, candidate/critic results and local drafts. Run operations.py import then operations.py queue --date {day} --capacity {capacity}. Run campaign_lint.py check for each affected campaign, compare the complete batch semantically, fix actual problems and save a fingerprint-bound campaign_lint.py review. Do not rewrite good emails to manufacture variation. Every active relationship needs a dated next action, a visible review task or an explicit hold/terminal disposition; report orphaned relationships.
5. Run gmail_labels.py pending. For existing managed threads only, refresh the complete thread, capture actual labels, run gmail_labels.py plan, apply the sourced diff in the correct Chrome Gmail account, then verify with gmail_labels.py confirm. Preserve unrelated labels. Never create company/person labels. If a previously scheduled Gmail message now requires cancellation, surface it urgently; do not pretend a local cancellation changed Gmail. This step changes labels only, never sends or schedules mail. Inaccessible mailboxes remain pending.
6. Report actual new/follow-up/held counts, label reconciliation receipts and any access limitations. Stop. Do not send anything.
'''


def run(scheduled=False,dry_run=False,capacity=30):
    runtime=WORKSPACE/'.runtime';runtime.mkdir(exist_ok=True)
    now=datetime.now(ZoneInfo('Europe/London'));day=(now+timedelta(days=1)).date().isoformat()
    with (runtime/'nightly.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'status':'already_running'}
        last=runtime/'nightly-last-date'
        if scheduled and (now.hour!=23 or (last.exists() and last.read_text()==now.date().isoformat())):return {'status':'outside_window_or_already_run'}
        if dry_run:
            with connect() as db:
                import_campaigns(db); result=build_queue(db,day,capacity)
            write_json(runtime/'nightly-dry-run.json',result);return result
        codex=shutil.which('codex')
        if not codex:raise ValueError('Codex CLI is unavailable')
        last.write_text(now.date().isoformat())
        with connect() as db:
            row=db.execute('INSERT INTO runs(started_at,status) VALUES(?,?)',(stamp(),'running')).lastrowid;db.commit()
        prompt=PROMPT.format(capacity=capacity,day=day)
        log=runtime/f'nightly-{now.date()}.log';result_file=runtime/f'nightly-{now.date()}-result.md'
        try:
            with log.open('w') as output:
                log.chmod(0o600)
                result=subprocess.run([codex,'exec','--skip-git-repo-check','--sandbox','workspace-write','-c','sandbox_workspace_write.network_access=true','-C',str(WORKSPACE),'-o',str(result_file),'-'],input=prompt,text=True,stdout=output,stderr=subprocess.STDOUT,timeout=2700)
            status='completed' if result.returncode==0 else 'failed'
        except subprocess.TimeoutExpired:status='timed_out'
        with connect() as db:
            db.execute('UPDATE runs SET status=?,finished_at=?,detail=? WHERE id=?',(status,stamp(),str(result_file),row));db.commit()
        return {'status':status,'result':str(result_file),'sending_enabled':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scheduled',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--capacity',type=int,default=30);a=p.parse_args()
    print(json.dumps(run(a.scheduled,a.dry_run,a.capacity)))
