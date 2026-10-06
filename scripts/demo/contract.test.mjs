import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read = name => fs.readFileSync(new URL(name, import.meta.url), 'utf8');
test('REC-2 uses isolated ports and tenant-restricted live worker', () => {
  assert.match(read('run.py'), /10291/);
  assert.match(read('vite.mjs'), /7591/);
  assert.match(read('run.py'), /'--tenant',env\['DEMO_TENANT'\]/);
  assert.match(read('run.py'), /AI_MODE='live'/);
});
test('REC-2 records all fifteen current scenes with motion and error accounting', () => {
  const script = read('record.mjs');
  assert.equal((script.match(/await scene\(/g) || []).length, 15);
  for (const text of ['분석 정지', '다시 분석', 'typing-bubble', 'radiogroup', 'consoleErrors', "reducedMotion:'no-preference'", "colorScheme:'dark'"]) assert.ok(script.includes(text), text);
});
