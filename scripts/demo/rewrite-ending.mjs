/** Replace only the presentation card after an invalid timing instrument is discovered.
 * Never changes recorded application scenes. Usage: node scripts/demo/rewrite-ending.mjs DIR
 */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {chromium}=require('@playwright/test');
const out=path.resolve(process.argv[2]);
const manifest=JSON.parse(fs.readFileSync(path.join(out,'manifest.json')));
manifest.timing.shared_summary_region_ms=manifest.timing.final;
manifest.timing.final=null;
manifest.timing.final_measurement_note='최초 측정 선택자가 잠정·최종 공용 영역을 감지했으므로 최종 표시 실측은 폐기함. provisional-badge 측정은 유효.';
const browser=await chromium.launch();
const context=await browser.newContext({viewport:{width:1440,height:900},recordVideo:{dir:path.join(out,'raw'),size:{width:1440,height:900}}});
const page=await context.newPage();
await page.setContent(`<html lang="ko"><body style="margin:0;background:#0b162b;color:#f5f8ff;font-family:'Apple SD Gothic Neo',sans-serif;display:flex;align-items:center;justify-content:center;height:900px"><div style="width:1100px"><p style="color:#65d6b6;font-size:23px;letter-spacing:5px">13 · JEV TRIAGE · LIVE WALKTHROUGH</p><h1 style="font-size:48px;line-height:1.4">요청에서 실행·학습·통제까지</h1><p style="font-size:27px;line-height:1.8;color:#b9c9e2">접수와 근거 → 사람의 결정 → 실제 업무 → 규칙 학습<br>정책·평가·운영 관찰·접근 통제로 연결됩니다.</p><p style="font-size:24px;line-height:1.8;color:#b9c9e2">이번 녹화: 클릭 → 잠정 카드 최초 표시 ${(manifest.timing.preliminary/1000).toFixed(2)}초<br>최종 표시 시간은 측정 선택자 오류로 제외했습니다.<br>문서 예시: 잠정 0.5–0.7초 · 최종 1.3–1.6초<br><span style="font-size:19px">출처: docs/architecture/ARCHITECTURE_OVERVIEW.html · 이번 녹화 실측값 아님</span></p></div></body></html>`);
await page.waitForTimeout(15000);
await page.screenshot({path:path.join(out,'scene-13.png')});
const v=page.video();await context.close();const raw=await v.path();await browser.close();
execFileSync('ffmpeg',['-y','-loglevel','error','-i',raw,'-vf','fps=30,scale=1440:900','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-an',path.join(out,'raw/scene-13.mp4')]);
// Trim only the idle tail after the rule has already stopped (all actions finish before 30s).
const trimmed=path.join(out,'raw/scene-8-trimmed.mp4');
execFileSync('ffmpeg',['-y','-loglevel','error','-i',path.join(out,'raw/scene-8.mp4'),'-t','40','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-an',trimmed]);
fs.renameSync(trimmed,path.join(out,'raw/scene-8.mp4'));
execFileSync('ffmpeg',['-y','-loglevel','error','-f','concat','-safe','0','-i',path.join(out,'raw/concat.txt'),'-c','copy','-movflags','+faststart',path.join(out,'walkthrough.mp4')]);
const probe=JSON.parse(execFileSync('ffprobe',['-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,r_frame_rate','-of','json',path.join(out,'walkthrough.mp4')],{encoding:'utf8'}));
manifest.probe=probe;for(const scene of manifest.scenes){if(scene.limitations.some(x=>x.includes('실패→Trace')))scene.status='partial';}manifest.scenes.find(s=>s.n===13).duration=Number(probe.format.duration)-manifest.scenes.find(s=>s.n===13).start;
fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2));
let readme=fs.readFileSync(path.join(out,'README.md'),'utf8');readme=readme.replace(/```json\n[\s\S]*?\n```/,'```json\n'+JSON.stringify(probe,null,2)+'\n```');readme=readme.replace(/## 화면 측정과 문서 인용\n\n[^\n]+/, '## 화면 측정과 문서 인용\n\n'+JSON.stringify(manifest.timing));
readme+='\n## 측정 정정\n\n잠정·최종이 공유하는 summary 영역을 최종 완료로 잘못 감지하여 최종 표시 시각은 폐기했습니다. 잠정 배지 표시 '+(manifest.timing.preliminary/1000).toFixed(2)+'초는 클릭 이벤트부터 DOM 출현까지의 값입니다. 최종 영상 엔딩을 이 사실에 맞게 재촬영했으며 실제 제품 화면 장면 1–12는 바꾸지 않았습니다. 재실행 스크립트의 최종 표시 측정은 LIVE 배지 존재로 수정했습니다.\n';
fs.writeFileSync(path.join(out,'README.md'),readme);
let offset=0;const chapters=['# Jev Triage 화면 녹화 챕터',''];for(const scene of manifest.scenes){scene.start=offset;scene.duration=Number(execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',path.join(out,`raw/scene-${scene.n}.mp4`)],{encoding:'utf8'}));chapters.push(`${String(Math.floor(offset/60)).padStart(2,'0')}:${String(Math.floor(offset%60)).padStart(2,'0')} — ${scene.n}. ${scene.title}${scene.status==='partial'?' (실패→Trace 이동 미시연)':''}`);offset+=scene.duration;}fs.writeFileSync(path.join(out,'chapters.md'),chapters.join('\n\n')+'\n');fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2));
console.log(JSON.stringify(probe));
