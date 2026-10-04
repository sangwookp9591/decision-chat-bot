// Minimal Node typings for the CSS/source-scanning tests only (the project does not depend on @types/node).
declare module 'node:fs' {
  export function readFileSync(path: string, encoding: 'utf8'): string;
  export function readdirSync(path: string): string[];
  export function statSync(path: string): { isDirectory(): boolean };
}
declare module 'node:path' { export function join(...parts: string[]): string; }
