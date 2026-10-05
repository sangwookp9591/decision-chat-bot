import {defineConfig} from '../../../../frontend/node_modules/vite/dist/node/index.js';
import react from '../../../../frontend/node_modules/@vitejs/plugin-react/dist/index.js';
export default defineConfig({plugins:[react()],server:{host:'127.0.0.1',port:8691,strictPort:true,proxy:{'/api':'http://127.0.0.1:11291'}}});
