import React from 'react';
const label=s=>String(s||'').replaceAll('_',' ');

export function OutageHubIntegration({account}){
 const p=account?.outagehub_integration,s=account?.outagehub_score;if(!p)return null;
 return <section className="finding"><h3>OutageHub integration</h3><p><strong>{p.relevant_product}</strong> · {p.product} · {label(p.use_case_cluster)}</p><p>{p.integration_sentence}</p><p><strong>Who benefits:</strong> {p.beneficiary}. {p.customer_benefit}</p><p><strong>Canada:</strong> {p.canadian_relevance}</p><p><strong>Buy versus build:</strong> {p.buy_vs_build}</p><p><strong>Next question:</strong> {p.next_question}</p><p className="muted">Current data gap: {label(p.gap_status)}. Benefits and willingness to buy remain hypotheses until confirmed.</p>{s&&<details><summary>{s.raw_total}/35 fit · {s.weighted_priority}/100 weighted priority</summary><p>Distribution reach carries the largest weight. {s.assessed_dimensions}/7 dimensions assessed.</p>{Object.entries(s.assessments).map(([k,v])=><p key={k}><strong>{label(k)}: {v.rating??'Unknown'}/5</strong><br/>{v.reason}</p>)}<p>{s.interpretation}</p></details>}</section>;
}

export function OutageHubMarket({campaigns=[]}){
 const rows=campaigns.filter(c=>c.engine==='outagehub_api'&&c.discovery_summary);if(!rows.length)return null;
 return <>{rows.map(c=><section className="finding" key={c.id}><h3>OutageHub market research</h3><p>{c.discovery_summary.screened} companies screened · {c.discovery_summary.qualified} qualified for a product conversation · {c.discovery_summary.held} held · {c.discovery_summary.rejected} rejected</p><p>{c.discovery_summary.recommendation}</p><div className="table-wrap"><table><thead><tr><th>Repeated workflow</th><th>Qualified companies</th></tr></thead><tbody>{c.outagehub_clusters.map(g=><tr key={g.use_case}><td>{label(g.use_case)}</td><td>{g.count}</td></tr>)}</tbody></table></div><p className="muted">These counts measure researched fit. Replies, evaluations and paid integrations will establish demand.</p>{c.outagehub_playbook&&<details><summary>{c.outagehub_playbook.title}</summary>{c.outagehub_playbook.principles.map(p=><p key={p.title}><strong>{p.title}.</strong> {p.detail}</p>)}<p>{c.outagehub_playbook.volume_note}</p><p><strong>Prepare for an evaluation:</strong> {c.outagehub_playbook.product_proof_needed.join('; ')}.</p></details>}</section>)}</>;
}
