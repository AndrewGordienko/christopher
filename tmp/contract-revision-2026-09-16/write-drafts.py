import json
from pathlib import Path
from datetime import datetime,timezone

root=Path('tmp/contract-revision-2026-09-16');plans=json.load(open(root/'plans.json'))
# Writer pass uses the completed account packets and Andrew's supplied examples only.
failure="I'm a UofT student on co-op in London, UK, working on search and recovery for lab automation. I've built a system that finds deadlocks and searches for a way out of them."
planning="I'm a UofT student on co-op in London, UK, working on planning and simulation for lab automation. I've built a digital twin and a layout optimizer for reducing robot travel."
drafts={
'takadu':('Water-event replay tests',failure,"""TaKaDu's event detection caught my attention because the input history matters as much as any individual reading. A missing pressure reading is a useful case to test: does the surrounding data still produce the right event, and how late does it appear?

I'm looking for a small paid contract outside my co-op. If there are missing-data cases your team still checks manually, I could automate those replays against your existing detector and leave you with the input traces and regression tests.

Is that something on the R&D team's backlog? Happy to talk for 15 minutes if it is."""),
'dryad':('Silvanet message replay',failure,"""With Silvanet, I'd like to help on the software between a sensor reading and a fire alert. If delayed or missing messages are difficult to reproduce in your backend tests, I could build a replay tool that injects those gaps and records when the alert changes.

I'm looking for a small paid contract outside my co-op, and could own that through to runnable tests in your existing setup.

Does your team have any message-handling cases waiting for that kind of coverage? Happy to talk for 15 minutes if so."""),
'enode':('Charger recovery tests',failure,"""Enode's device-control work looks close to the recovery side of what I do. If a charger misses a command, the next plan has to account for the charge that never happened.

I'm looking for a small paid contract outside my co-op. I could build a simulated charger that misses commands or reconnects late, then turn the resulting recovery cases into tests for your existing scheduling code.

Are there device-control edge cases your team wants covered but hasn't had time to automate? Happy to talk for 15 minutes if so."""),
'searoutes':('AIS gap regression tests',planning,"""I was looking at the AIS data behind Searoutes' routing and emissions calculations. A gap in a vessel's track seems like a useful regression case: changing the reconstructed route can also change the emissions estimate.

I'm looking for a small paid contract outside my co-op. If your team has track-gap cases that still need manual checking, I could turn them into automated tests with reproducible inputs and a clear record of which results changed.

Is that a piece of the data-quality backlog someone could take on? Happy to talk for 15 minutes if it is."""),
'beebop':('Dispatch tests for asset dropouts',planning,"""For Beebop's virtual power plants, one concrete thing I could work on is testing dispatch when several assets drop out together. The useful result would be a repeatable case showing which commitments can still be met, rather than just a different dispatch score.

I'm looking for a small paid contract outside my co-op. I could build those scenarios around your existing dispatch code and hand over the simulator inputs and automated checks.

Do you have asset-availability cases waiting to be added to the test suite? Happy to talk for 15 minutes if so."""),
'bia':('Depot charging test cases',planning,"""Bia's fleet charging seems like a practical place to apply that experience. I could work on the case where a vehicle needs to leave early but the depot's available power is already allocated to other vehicles.

I'm looking for a small paid contract outside my co-op. If that is a scenario your team wants better coverage for, I could build an offline depot simulator that runs changed departure times through your charging logic and flags vehicles that would miss their required charge.

Is departure-readiness testing on the product backlog? Happy to talk for 15 minutes if it is."""),
'envelio':('Power-flow test scenarios',planning,"""I was reading about envelio's GPU power-flow work. One piece I could take on is generating difficult network scenarios for the solver, with each result reduced to an input case the team can rerun.

I'm looking for a small paid contract outside my co-op. Working within limits your engineers define, I could build the scenario search and automated checks around an existing solver interface, then leave the tests in your repository.

Does the solver team have a set of boundary cases it wants automated? Happy to talk for 15 minutes if so."""),
'quantstack':('Jupyter numerical test coverage',planning,"""Building the simulation has made me appreciate how much time goes into the tooling around a numerical workflow. With QuantStack's Jupyter work, I could take on a contained issue where the same calculation behaves differently in the browser and native Python.

I'm looking for a small paid contract outside my co-op. I could work from one reproducible case through the implementation and regression tests, so the result lives in the existing project.

Do you have a numerical or simulation-tooling issue like that waiting for an engineer? Happy to talk for 15 minutes if so."""),
'timefold':('Schedule disruption tests',planning,"""Timefold's constraint solving is close to the work I want to do more of. One useful piece I could own is testing what happens to a published schedule after a resource becomes unavailable, including how many unaffected assignments move.

I'm looking for a small paid contract outside my co-op. I could add those disruption cases to an existing benchmark and turn constraint violations or unexpected changes into small, reproducible tests.

Is there a schedule-repair testing task on the solver team's backlog? Happy to talk for 15 minutes if there is."""),
'axle':('Price-curve scheduling example',planning,"""I was reading Axle's price-curve documentation. A concrete piece I could build is a battery scheduling example that handles a revised price curve after part of the original plan has already run, keeping track of the charge actually left.

I'm looking for a small paid contract outside my co-op. I could take that from a working Python example through to tests for the energy limits and replanning cases, so it is useful to someone integrating the curves into their optimizer.

Is that kind of integration example on your backlog? Happy to talk for 15 minutes if it is."""),
'piclo':('Flexibility workflow tests',failure,"""Piclo's work across flexibility procurement, operation and settlement caught my attention. The piece I could help with is testing the transitions between those stages, particularly when an update arrives late or a commitment changes.

I'm looking for a small paid contract outside my co-op. If your team has integration cases that still need manual checking, I could automate the event sequences and leave behind tests that make a failed transition reproducible.

Is there a workflow-testing task like that on your product backlog? Happy to talk for 15 minutes if so."""),
'recycleye':('Sorting model regression cases',failure,"""For Recycleye's vision models, I could help with the tooling that turns difficult material classifications into repeatable evaluation cases. The useful output would be a clear view of which labelled items change classification between model versions, so they are easy to review.

I'm looking for a small paid contract outside my co-op. If that evaluation work needs an engineer, I could build the runner and results view around your existing detections and labels.

Is there a model-evaluation task like that waiting on the ML team's backlog? Happy to talk for 15 minutes if there is."""),
'earthmover':('Icechunk recovery test coverage',failure,"""I saw that Icechunk 2 already includes fault-injection testing against network failures. That is close to the work I do: searching for sequences of individually valid actions that leave a system stuck.

I'm looking for a small paid contract outside my co-op. If there are interrupted or overlapping-write cases you still want covered, I could extend the existing tests and reduce any failures to sequences the team can rerun.

Are there recovery cases on the backlog that someone could take ownership of? Happy to talk for 15 minutes if so."""),
'fero-labs':('Process simulator regression tests',failure,"""Fero's process simulator looks like a place where I could help with the engineering around model validation. If there are combinations of inputs your team still checks by hand, I could automate the sweeps and flag recommendations that fall outside bounds your engineers specify.

I'm looking for a small paid contract outside my co-op. The handover would be runnable tests and the exact inputs behind each flagged result, built around your existing simulator.

Do you have a simulator-testing task like that waiting for someone? Happy to talk for 15 minutes if you do."""),
'four-growers':('Harvest recovery test cases',failure,"""I was looking at the GR-100's collision-free motion planning. The part that overlaps with my work is what happens after an approach cannot finish: finding a way to continue without repeatedly attempting the same blocked move.

I'm looking for a small paid contract outside my co-op. If you have failed approaches that are difficult to reproduce, I could turn them into simulation tests and work through an agreed recovery change, leaving the code and regression cases with your team.

Is anything like that on the robotics backlog? Happy to talk for 15 minutes if so."""),
'rideco':('Dynamic driver-break tests',planning,"""I was reading about RideCo's dynamic driver breaks. A concrete piece I could help with is testing whether those breaks remain feasible as trips run late, then reducing a failed case to the few trips that trigger it.

I'm looking for a small paid contract outside my co-op. I could build that scenario runner around your scheduling code and hand over automated checks for the constraints your team already uses.

Does the algorithms team have break-scheduling cases waiting for regression coverage? Happy to talk for 15 minutes if it does."""),
'swiftly':('ETA completeness replay tests',failure,"""Swiftly's ETA Completeness Benchmark caught my attention because it includes the occasions when riders receive no prediction. I could help turn gaps in vehicle updates into repeatable input sequences, so it is clear exactly when an ETA disappears.

I'm looking for a small paid contract outside my co-op. If that replay work is still manual in places, I could automate it around your existing completeness checks and leave the cases in your test suite.

Is there a prediction-feed testing task on your team's backlog? Happy to talk for 15 minutes if there is."""),
'amperon':('Forecast backtesting tooling',planning,"""I was looking at Amperon's probabilistic wind and solar forecasts. One piece I could take on is the tooling for replaying historical forecasts against what actually happened, while keeping each run tied to the forecast available at that time.

I'm looking for a small paid contract outside my co-op. If there is manual work in that evaluation pipeline, I could automate a contained part of it and hand over a runner with tests and reproducible results.

Does your team have a backtesting task that needs an engineer? Happy to talk for 15 minutes if it does."""),
'earthsense':('TerraMax route recovery tests',failure,"""TerraMax's work under canopy looks close to the recovery side of what I do. One piece I could help with is reproducing a blocked route in simulation and checking whether the planner can still reach the remaining work.

I'm looking for a small paid contract outside my co-op. If your team has field cases waiting to become regression tests, I could own that process and reduce each one to a map and sequence the planner team can rerun.

Do you have blocked-route cases on the autonomy backlog? Happy to talk for 15 minutes if so."""),
'gridraven':('Line-rating sensitivity tests',planning,"""Gridraven's span-level weather modelling caught my attention. I could help automate tests that vary the weather inputs and show which span causes the line's rating to change, with each result tied back to the exact inputs.

I'm looking for a small paid contract outside my co-op. If your engineers still run parts of that analysis manually, I could build it around the existing model and the checks they specify, then leave you with a repeatable test runner.

Is there a sensitivity-testing task on the team's backlog? Happy to talk for 15 minutes if so."""),
'coiled':('Interrupted simulation workloads',planning,"""For Coiled's scientific Python workloads, I could help with a concrete interrupted-run example: a parameter sweep that checks which outputs were completed before a retry, and catches missing or duplicated results afterward.

I'm looking for a small paid contract outside my co-op. If there is a customer workload or documentation example waiting for this treatment, I could make it reproducible and add tests around the expected outputs.

Do you have a simulation-workload issue like that someone could take on? Happy to talk for 15 minutes if so."""),
'rugged':('Layout sequence recovery',failure,"""With Rugged's construction layout, the overlap I see is keeping work moving when part of the floor is temporarily blocked. I could work on reproducing those interruptions offline and checking whether the robot can finish the remaining marks without unnecessary return trips.

I'm looking for a small paid contract outside my co-op. If you have a layout-sequence issue waiting for attention, I could take it from a repeatable case through a bounded planning change and regression tests.

Is anything like that on the robotics team's backlog? Happy to talk for 15 minutes if so."""),
'agtonomy':('Multi-point turn test cases',failure,"""I was reading about Agtonomy's multi-point turns. Finding the small change in available space that stops a manoeuvre from completing looks close to the search work I do.

I'm looking for a small paid contract outside my co-op. If the autonomy team has turning cases it wants reproduced, I could build a simulation search around the existing planner, reduce the failures to small test cases and work on an agreed fix.

Is there a turning or recovery issue waiting for that work? Happy to talk for 15 minutes if there is."""),
'dusty-robotics':('FieldPrinter interruption tests',planning,"""Your FieldPrinter coordination guide mentions tracker line-of-sight interruptions. I could help turn those interruptions into repeatable software tests, checking what happens when printing pauses and which work is resumed afterward.

I'm looking for a small paid contract outside my co-op. If there are site cases your team wants covered, I could build an offline replay around an agreed layout and leave you with the scenarios and regression checks.

Does the robotics software team have pause-and-resume cases waiting to be automated? Happy to talk for 15 minutes if so."""),
'electric-era':('Battery dispatch regression tests',planning,"""Electric Era's battery-backed charging looks like a useful place to apply that experience. I could help test successive demand peaks, where serving the first group of vehicles changes how much the battery can contribute to the next.

I'm looking for a small paid contract outside my co-op. If you have dispatch scenarios waiting for coverage, I could build them around your existing control model and flag violations of the energy and site-power limits your team specifies.

Is there a dispatch-testing task the software team needs someone to own? Happy to talk for 15 minutes if so."""),
'open-ocean-robotics':('DataXplorer mission planning',planning,"""I'd like to apply that experience to ocean work. For DataXplorer, a concrete piece I could build is an offline planning tool that shows which survey sections remain feasible when the energy budget or weather window changes.

I'm looking for a small paid contract outside my co-op. If adapting survey plans is still manual in places, I could take on a contained part of it, using the vehicle limits and coverage priorities your team defines.

Is that on the mission-planning backlog? Happy to talk for 15 minutes if it is."""),
'sewerai':('AutoCode review-queue evaluation',failure,"""For AutoCode, I could help with the tooling for deciding which uncertain detections need a person's review. Using labelled inspection cases, the useful result would show both the review workload and the important defects a selection rule would miss.

I'm looking for a small paid contract outside my co-op. If that evaluation needs automation, I could build the runner and results view around your existing model outputs, so the team can rerun it after a change.

Is there a review-queue evaluation task on the engineering backlog? Happy to talk for 15 minutes if so."""),
'spare':('Paratransit replanning tests',planning,"""For Spare's paratransit routing, I could help turn a delayed pickup into a repeatable scheduling test: which later passengers are affected, and how much of the original plan changes during recovery.

I'm looking for a small paid contract outside my co-op. If your team has difficult schedules waiting for regression coverage, I could build the scenario runner and reduce failures to small cases, using the passenger-service constraints you already test against.

Is there a replanning evaluation task like that on your backlog? Happy to talk for 15 minutes if so."""),
'weavegrid':('Charging departure-change tests',planning,"""With DISCO's distribution-grid constraints, I could help test what happens when a driver needs the car earlier than planned. The useful distinction would be between a request that cannot be met within those limits and one where the scheduler could recover a workable plan.

I'm looking for a small paid contract outside my co-op. I could build those scenarios around existing charging logic and leave the team with reproducible inputs and regression checks.

Do you have departure-change cases waiting to be automated? Happy to talk for 15 minutes if so."""),
'inorbit':('Robot task-recovery tests',failure,"""InOrbit's coordination across different robots looks close to that work. I could help reproduce what happens when one robot stops with jobs still assigned to it, including cases where reassigning them creates a queue elsewhere.

I'm looking for a small paid contract outside my co-op. If there are orchestration cases your team wants covered, I could build the simulated task sequences around the existing logic and leave you with tests for the recovery behaviour you expect.

Is there a task-recovery issue on the engineering backlog? Happy to talk for 15 minutes if so."""),
}
at=datetime.now(timezone.utc).isoformat();out=[]
for p in plans:
 subject,intro,thought=drafts[p['account']];first=p['owner']['name'].split()[0]
 if p['account']=='electric-era':first='Sith'
 body='Hi '+first+',\n\n'+intro+'\n\n'+thought.strip()+'\n\nBest,\nAndrew'
 out.append({**p,'subject':subject,'body':body,'writer_completed_at':at,'phase':'written_pending_separate_critic'})
(root/'drafts.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(root/'drafts-for-review.md').write_text('\n\n---\n\n'.join('# '+r['account']+' — '+r['owner']['name']+'\n\nSubject: '+r['subject']+'\n\n'+r['body'] for r in out)+'\n')
print(json.dumps({'drafts':len(out),'words':{'min':min(len(r['body'].split()) for r in out),'max':max(len(r['body'].split()) for r in out)}}))
