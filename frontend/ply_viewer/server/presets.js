import fs from 'node:fs';
import path from 'node:path';

const configPath = process.env.PLY_VIEWER_PRESETS || path.join(process.cwd(), 'presets.local.json');

function loadPresets() {
  if (!fs.existsSync(configPath)) return [];
  const data = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  if (!Array.isArray(data)) {
    throw new Error(`${configPath} must contain an array of { label, path } presets`);
  }
  return data.map((preset) => ({
    label: preset.label || path.basename(preset.path || ''),
    path: preset.path
  })).filter((preset) => preset.path);
}

export const PRESETS = loadPresets();
export const PRESET_PATHS = PRESETS.map((preset) => preset.path);

export function buildPresetList(existsSync) {
  return PRESETS.map((preset, index) => ({
    id: `preset-${index}`,
    label: preset.label || path.basename(preset.path),
    path: preset.path,
    exists: existsSync(preset.path)
  }));
}
