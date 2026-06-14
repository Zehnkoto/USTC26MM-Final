import { describe, expect, test } from 'vitest';
import { buildCloudStats, makeHeightColors } from '../src/cloudStats.js';

describe('cloud statistics', () => {
  test('counts points and computes a bounding box from xyz triples', () => {
    const stats = buildCloudStats(new Float32Array([1, 2, 3, -4, 5, 6, 7, -8, 9]));

    expect(stats.pointCount).toBe(3);
    expect(stats.bbox.min).toEqual({ x: -4, y: -8, z: 3 });
    expect(stats.bbox.max).toEqual({ x: 7, y: 5, z: 9 });
    expect(stats.bbox.size).toEqual({ x: 11, y: 13, z: 6 });
    expect(stats.center).toEqual({ x: 1.5, y: -1.5, z: 6 });
  });

  test('returns empty stats for an empty point cloud', () => {
    const stats = buildCloudStats(new Float32Array());

    expect(stats.pointCount).toBe(0);
    expect(stats.bbox.min).toEqual({ x: 0, y: 0, z: 0 });
    expect(stats.bbox.max).toEqual({ x: 0, y: 0, z: 0 });
  });

  test('maps z height to blue through warm colors', () => {
    const colors = makeHeightColors(new Float32Array([0, 0, 0, 0, 0, 5, 0, 0, 10]));

    expect(colors).toHaveLength(9);
    expect(Array.from(colors.slice(0, 3))).toEqual([
      expect.closeTo(0.1),
      expect.closeTo(0.25),
      expect.closeTo(0.95)
    ]);
    expect(Array.from(colors.slice(6, 9))).toEqual([
      expect.closeTo(0.95),
      expect.closeTo(0.25),
      expect.closeTo(0.1)
    ]);
  });
});
