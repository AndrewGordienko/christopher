import http from 'node:http';
import { readFile, access } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
const localPython = fileURLToPath(new URL('./.venv/bin/python', import.meta.url));
let python = 'python3';
try { await access(localPython); python = localPython; } catch {}
const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/workspace.css', ['workspace.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
]);
const port = Number(process.env.PORT || 4173);
function operation(args, input) {
  return new Promise((resolve, reject) => {
    const child = spawn(python, ['skills/andrew-email-style/scripts/mission.py', ...args], {cwd:root, stdio:['pipe','pipe','pipe']});
    let output = ''; let bytes = 0;
    const timeout = setTimeout(() => { child.kill(); reject(new Error('Review operation timed out')); }, 20000);
    child.stdout.on('data', chunk => { bytes += chunk.length; if (bytes > 15e6) child.kill(); else output += chunk; });
    child.stderr.resume();
    child.on('error', error => { clearTimeout(timeout); reject(error); });
    child.on('close', code => {
      clearTimeout(timeout);
      try { const value=JSON.parse(output); if(code) reject(new Error(value.error || 'Review operation failed')); else resolve(value); }
      catch { reject(new Error('Review operation failed')); }
    });
    child.stdin.end(input ? JSON.stringify(input) : undefined);
  });
}
const server=http.createServer(async (req, res) => {
  const headers={
    'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer',
    'Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
  };
  function json(status,value) {res.writeHead(status,{...headers,'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));}
  if(![`localhost:${port}`,`127.0.0.1:${port}`].includes(req.headers.host)) return json(403,{error:'Local access only'});
  let pathname;
  try { pathname=new URL(req.url,'http://localhost').pathname; } catch {return json(400,{error:'Invalid URL'});}
  if(pathname==='/api/campaigns' && req.method==='GET') {
    try {return json(200,await operation(['review-catalog']));}
    catch(error){return json(500,{error:error.message});}
  }
  if(['/api/missions','/api/action','/api/calendar'].includes(pathname) && req.method==='POST') {
    if(![`http://localhost:${port}`,`http://127.0.0.1:${port}`].includes(req.headers.origin)) return json(403,{error:'Same-origin request required'});
    if(!req.headers['content-type']?.startsWith('application/json')) return json(415,{error:'JSON required'});
    try {let raw='';for await(const part of req){raw+=part;if(Buffer.byteLength(raw)>150000)return json(413,{error:'Request too large'});}
      return json(200,await operation([pathname==='/api/missions'?'create-mission':pathname==='/api/calendar'?'calendar-action':'review-action'],JSON.parse(raw)));
    } catch(error){return json(409,{error:error.message});}
  }
  const review=pathname.match(/^\/api\/review\/([a-z0-9-]+)\/([a-z0-9-]+)\/([a-z0-9-]+)$/);
  const markSent=pathname.match(/^\/api\/mark-sent\/([a-z0-9-]+)\/([a-z0-9-]+)\/([a-z0-9-]+)$/);
  if((review||markSent) && req.method==='POST') {
    if(![`http://localhost:${port}`,`http://127.0.0.1:${port}`].includes(req.headers.origin)) return json(403,{error:'Same-origin review required'});
    if(!req.headers['content-type']?.startsWith('application/json')) return json(415,{error:'JSON required'});
    try {
      let raw='';
      for await(const part of req){raw+=part;if(Buffer.byteLength(raw)>150000)return json(413,{error:'Review is too large'});}
      const change=JSON.parse(raw);
      return json(200,await operation([markSent?'mark-sent':'save-review',...(markSent||review).slice(1)],change));
    } catch(error){return json(409,{error:error.message});}
  }
  const file=files.get(pathname);
  if(!file || !['GET','HEAD'].includes(req.method)) return json(404,{error:'Not found'});
  try {const body=await readFile(new URL(`./public/${file[0]}`,import.meta.url));res.writeHead(200,{...headers,'Content-Type':file[1]});res.end(req.method==='HEAD'?undefined:body);}
  catch {json(500,{error:'Could not load page'});}
});
server.listen(port,'127.0.0.1',()=>console.log(`Outreach review: http://localhost:${port}`));
