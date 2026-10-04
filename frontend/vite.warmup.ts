// Entry files of every route, transformed when the dev server starts so the first page open does not pay for
// the module waterfall (https://vite.dev/guide/performance#warm-up-frequently-used-files).
export const warmupClientFiles = [
  './src/main.tsx', './src/App.tsx', './src/layout/AppShell.tsx', './src/layout/routes.tsx',
  './src/pages/Main.tsx', './src/pages/Review.tsx', './src/pages/Tasks.tsx', './src/pages/Observatory.tsx',
  './src/pages/JudgmentMap.tsx', './src/pages/Learning.tsx', './src/pages/Monitoring.tsx', './src/pages/Policy.tsx',
];
