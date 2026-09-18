// Small adapter around pinned ats-jobs; preserves raw provider evidence as well as full descriptions.
import {fetchCompany} from '../third_party/ats-jobs/src/index.js';
const target=process.argv[2];
if(!target)throw Error('A researched company domain / careers URL is required');
const capture=[];const original=globalThis.fetch;
globalThis.fetch=async(...args)=>{const res=await original(...args);if(res.ok){const text=await res.clone().text();capture.push({url:res.url||String(args[0]),text,observed_at:new Date().toISOString()});}return res};
const result=await fetchCompany(target,{includeDescription:true,maxJobs:200,timeoutMs:12000});
console.log(JSON.stringify({target,observed_at:new Date().toISOString(),result,capture}));
