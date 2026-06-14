export function buildCloudStats(positions) {
  const pointCount = Math.floor(positions.length / 3);
  if (pointCount === 0) {
    return {
      pointCount: 0,
      bbox: {
        min: { x: 0, y: 0, z: 0 },
        max: { x: 0, y: 0, z: 0 },
        size: { x: 0, y: 0, z: 0 }
      },
      center: { x: 0, y: 0, z: 0 },
      radius: 1
    };
  }

  const min = { x: Infinity, y: Infinity, z: Infinity };
  const max = { x: -Infinity, y: -Infinity, z: -Infinity };

  for (let index = 0; index < positions.length; index += 3) {
    const x = positions[index];
    const y = positions[index + 1];
    const z = positions[index + 2];
    min.x = Math.min(min.x, x);
    min.y = Math.min(min.y, y);
    min.z = Math.min(min.z, z);
    max.x = Math.max(max.x, x);
    max.y = Math.max(max.y, y);
    max.z = Math.max(max.z, z);
  }

  const size = {
    x: max.x - min.x,
    y: max.y - min.y,
    z: max.z - min.z
  };
  const center = {
    x: (min.x + max.x) / 2,
    y: (min.y + max.y) / 2,
    z: (min.z + max.z) / 2
  };
  const radius = Math.max(size.x, size.y, size.z, 1);

  return { pointCount, bbox: { min, max, size }, center, radius };
}

export function makeHeightColors(positions) {
  const pointCount = Math.floor(positions.length / 3);
  const colors = new Float32Array(pointCount * 3);
  if (pointCount === 0) {
    return colors;
  }

  let minZ = Infinity;
  let maxZ = -Infinity;
  for (let index = 2; index < positions.length; index += 3) {
    minZ = Math.min(minZ, positions[index]);
    maxZ = Math.max(maxZ, positions[index]);
  }

  const range = maxZ - minZ || 1;
  for (let point = 0; point < pointCount; point += 1) {
    const z = positions[point * 3 + 2];
    const t = (z - minZ) / range;
    colors[point * 3] = roundColor(0.1 + t * 0.85);
    colors[point * 3 + 1] = roundColor(0.25 + Math.sin(t * Math.PI) * 0.45);
    colors[point * 3 + 2] = roundColor(0.95 - t * 0.85);
  }

  return colors;
}

function roundColor(value) {
  return Math.round(value * 1000) / 1000;
}
