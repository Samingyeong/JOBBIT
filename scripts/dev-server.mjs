import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
const root=resolve(process.cwd(),'web');
const types={'.html':'text/html;charset=utf-8','.js':'application/javascript;charset=utf-8','.json':'application/json;charset=utf-8','.css':'text/css;charset=utf-8'};
http.createServer(async(req,res)=>{const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);const file=resolve(root,'.'+(name==='/'?'/index.html':name));if(!(file===root||file.startsWith(root+sep))){res.writeHead(403).end();return;}try{const b=await readFile(file);res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(b);}catch{res.writeHead(404).end('Not found');}}).listen(1420,'127.0.0.1',()=>console.log('JOBBIT: http://localhost:1420'));
