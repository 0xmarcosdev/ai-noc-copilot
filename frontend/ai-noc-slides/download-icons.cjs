const fs = require('fs');
const https = require('https');
const path = require('path');

// Crea la carpeta si no existe
const dir = './public/assets/icons';
if (!fs.existsSync(dir)){
    fs.mkdirSync(dir, { recursive: true });
}

const icons = [
  { url: 'https://cdn.simpleicons.org/python/3776AB', name: 'python.svg' },
  { url: 'https://cdn.simpleicons.org/streamlit/FF4B4B', name: 'streamlit.svg' },
  { url: 'https://cdn.simpleicons.org/sqlite/003B57', name: 'sqlite.svg' },
  { url: 'https://cdn.simpleicons.org/github/ffffff', name: 'github.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/ollama.svg', name: 'ollama.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/qwen-color.svg', name: 'qwen.svg' },
  { url: 'https://cdn.simpleicons.org/gnubash/4EAA25', name: 'gnubash.svg' },
  { url: 'https://cdn.simpleicons.org/wolfram/DD1100', name: 'wolfram.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg', name: 'claude.svg' },
  { url: 'https://cdn.simpleicons.org/visualstudiocode/007ACC', name: 'vscode.svg' },
  { url: 'https://cdn.simpleicons.org/cursor/ffffff', name: 'cursor.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/opencode.svg', name: 'opencode.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/deepseek.svg', name: 'deepseek.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/deepseek-color.svg', name: 'deepseek-color.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/perplexity-color.svg', name: 'perplexity.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/grok.svg', name: 'grok.svg' },
  { url: 'https://unpkg.com/@lobehub/icons-static-svg@latest/icons/gemini-color.svg', name: 'gemini.svg' },
];

let completed = 0;
icons.forEach(icon => {
  const file = fs.createWriteStream(path.join(dir, icon.name));
  https.get(icon.url, (response) => {
    response.pipe(file);
    file.on('finish', () => {
      file.close();
      completed++;
      if (completed === icons.length) console.log('✅ ¡Todos los iconos se descargaron en /public/assets/icons/');
    });
  }).on('error', (err) => {
    console.error(`❌ Error descargando ${icon.name}:`, err.message);
  });
});