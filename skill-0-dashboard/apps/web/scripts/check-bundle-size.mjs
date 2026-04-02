import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const assetsDir = path.resolve(__dirname, '../dist/assets');
const maxJsChunkBytes = Number(process.env.SKILL0_MAX_JS_CHUNK_BYTES ?? 350 * 1024);

function formatKiB(bytes) {
  return `${(bytes / 1024).toFixed(2)} KiB`;
}

async function main() {
  const entries = await readdir(assetsDir);
  const jsFiles = entries.filter((entry) => entry.endsWith('.js'));

  if (jsFiles.length === 0) {
    throw new Error(`No JavaScript assets found under ${assetsDir}`);
  }

  const chunks = await Promise.all(
    jsFiles.map(async (file) => {
      const fullPath = path.join(assetsDir, file);
      const { size } = await stat(fullPath);
      return { file, size };
    })
  );

  chunks.sort((a, b) => b.size - a.size);

  console.log(`Bundle size check (${formatKiB(maxJsChunkBytes)} max per JS chunk):`);
  for (const chunk of chunks.slice(0, 5)) {
    console.log(`- ${chunk.file}: ${formatKiB(chunk.size)}`);
  }

  const oversized = chunks.filter((chunk) => chunk.size > maxJsChunkBytes);
  if (oversized.length > 0) {
    const details = oversized
      .map((chunk) => `${chunk.file} (${formatKiB(chunk.size)})`)
      .join(', ');
    throw new Error(`Bundle size budget exceeded: ${details}`);
  }

  console.log('Bundle size check passed.');
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
