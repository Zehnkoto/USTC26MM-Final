import { describe, expect, test } from 'vitest';
import { PRESET_PATHS, buildPresetList } from '../server/presets.js';

describe('preset PLY paths', () => {
  test('defaults to no committed local presets', () => {
    expect(PRESET_PATHS).toEqual([]);
    expect(buildPresetList(() => true)).toEqual([]);
  });
});
