import { createServer } from '../../frontend/node_modules/vite/dist/node/index.js';
const server = await createServer({root: new URL('../../frontend', import.meta.url).pathname, server:{host:'127.0.0.1', port:6491, strictPort:true, proxy:{'/api':'http://127.0.0.1:9191'}}});
await server.listen();
