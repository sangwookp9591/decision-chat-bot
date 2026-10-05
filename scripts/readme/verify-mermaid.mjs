import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {JSDOM}=require('jsdom');
const dom=new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window=dom.window; globalThis.document=dom.window.document;
const {default:mermaid}=await import(pathToFileURL(process.argv[2]).href);
mermaid.initialize({startOnLoad:false});
const source=fs.readFileSync(new URL('../../README.md',import.meta.url),'utf8');
const diagrams=[...source.matchAll(/```mermaid\n([\s\S]*?)```/g)];
if(diagrams.length!==2) throw Error('Expected two Mermaid diagrams');
for(const [i,match] of diagrams.entries()) { await mermaid.parse(match[1]); console.log(`Mermaid ${i+1}: PASS`); }
