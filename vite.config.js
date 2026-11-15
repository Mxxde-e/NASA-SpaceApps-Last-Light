import { defineConfig } from 'vite';
import { copyFileSync,existsSync } from 'node:fs';
// Vite clears dist on build. Retain the user's saved presentation fallback.
export default defineConfig({server:{proxy:{'/api':'http://127.0.0.1:8000'}},plugins:[{
  name:'preserve-presentation-backup',
  closeBundle(){if(existsSync('docs/presentation-backup.html'))copyFileSync('docs/presentation-backup.html','dist/presentation-backup.html');},
}]});
