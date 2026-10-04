// Minimal Node typings for tokens.test.ts only (the project does not depend on @types/node).
declare module 'node:fs' { export function readFileSync(path: string, encoding: 'utf8'): string; }
