import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { BufferAttribute, Color, Vector3 } from 'three';
import { FolderOpen, Loader2, Palette, RotateCcw } from 'lucide-react';
import { buildCloudStats, makeHeightColors } from './cloudStats.js';
import './styles.css';

const loader = new PLYLoader();
const backgrounds = {
  dark: '#090d12',
  light: '#eef1f4',
  black: '#000000'
};

function parsePly(buffer, name, source) {
  const geometry = loader.parse(buffer);
  geometry.computeBoundingBox();
  const positions = geometry.getAttribute('position')?.array || new Float32Array();
  const stats = buildCloudStats(positions);
  const colorAttribute = geometry.getAttribute('color');

  return {
    id: `${source}:${name}:${Date.now()}:${Math.random().toString(16).slice(2)}`,
    name,
    source,
    geometry,
    stats,
    hasVertexColors: Boolean(colorAttribute),
    originalColors: colorAttribute ? new Float32Array(colorAttribute.array) : null
  };
}

function Controls({ target, radius, resetToken }) {
  const { camera, gl } = useThree();
  const controlsRef = useRef();

  useEffect(() => {
    const controls = new OrbitControls(camera, gl.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controlsRef.current = controls;
    return () => controls.dispose();
  }, [camera, gl]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    camera.position.set(target.x + radius * 0.9, target.y - radius * 1.4, target.z + radius * 0.75);
    camera.near = Math.max(radius / 10000, 0.001);
    camera.far = Math.max(radius * 100, 1000);
    camera.updateProjectionMatrix();
    controls.target.set(target.x, target.y, target.z);
    controls.update();
  }, [camera, target, radius, resetToken]);

  useFrame(() => controlsRef.current?.update());
  return null;
}

function PointCloud({ cloud, pointSize, colorMode, monoColor }) {
  const materialRef = useRef();
  const renderedGeometry = useMemo(() => {
    const geometry = cloud.geometry.clone();
    const positions = geometry.getAttribute('position').array;

    if (colorMode === 'height') {
      geometry.setAttribute('color', new BufferAttribute(makeHeightColors(positions), 3));
    } else if (colorMode === 'original' && cloud.originalColors) {
      geometry.setAttribute('color', new BufferAttribute(new Float32Array(cloud.originalColors), 3));
    } else {
      geometry.deleteAttribute('color');
    }

    return geometry;
  }, [cloud, colorMode]);

  useEffect(() => () => renderedGeometry.dispose(), [renderedGeometry]);

  return (
    <points geometry={renderedGeometry}>
      <pointsMaterial
        ref={materialRef}
        size={pointSize}
        sizeAttenuation
        vertexColors={colorMode !== 'mono' && renderedGeometry.hasAttribute('color')}
        color={new Color(monoColor)}
      />
    </points>
  );
}

function Scene({ cloud, pointSize, colorMode, monoColor, resetToken }) {
  const target = useMemo(() => new Vector3(cloud.stats.center.x, cloud.stats.center.y, cloud.stats.center.z), [cloud]);
  return (
    <>
      <ambientLight intensity={1} />
      <PointCloud cloud={cloud} pointSize={pointSize} colorMode={colorMode} monoColor={monoColor} />
      <Controls target={target} radius={cloud.stats.radius} resetToken={resetToken} />
    </>
  );
}

function formatNumber(value) {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 }).format(value);
}

function BboxLine({ label, value }) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <code>{formatNumber(value.x)}, {formatNumber(value.y)}, {formatNumber(value.z)}</code>
    </div>
  );
}

function App() {
  const [clouds, setClouds] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [presets, setPresets] = useState([]);
  const [pointSize, setPointSize] = useState(0.015);
  const [colorMode, setColorMode] = useState('original');
  const [background, setBackground] = useState('dark');
  const [monoColor, setMonoColor] = useState('#f4d35e');
  const [status, setStatus] = useState('Choose local PLY files or load an available preset.');
  const [loading, setLoading] = useState(false);
  const [resetToken, setResetToken] = useState(0);

  const activeCloud = clouds.find((cloud) => cloud.id === activeId) || clouds[0] || null;

  useEffect(() => {
    fetch('/api/presets')
      .then((response) => response.json())
      .then(setPresets)
      .catch(() => setStatus('Preset API is unavailable. File picker loading still works.'));
  }, []);

  useEffect(() => {
    if (!activeId && clouds.length > 0) {
      setActiveId(clouds[0].id);
    }
  }, [activeId, clouds]);

  const addCloud = useCallback((cloud) => {
    setClouds((current) => [cloud, ...current]);
    setActiveId(cloud.id);
    setColorMode(cloud.hasVertexColors ? 'original' : 'height');
  }, []);

  const loadFiles = async (fileList) => {
    const files = Array.from(fileList || []).filter((file) => file.name.toLowerCase().endsWith('.ply'));
    if (files.length === 0) {
      setStatus('Select one or more .ply files.');
      return;
    }

    setLoading(true);
    try {
      for (const file of files) {
        const buffer = await file.arrayBuffer();
        addCloud(parsePly(buffer, file.name, 'local file'));
      }
      setStatus(`Loaded ${files.length} local PLY file${files.length === 1 ? '' : 's'}.`);
    } catch (error) {
      setStatus(`Failed to load PLY: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadPreset = async (preset) => {
    setLoading(true);
    setStatus(`Loading ${preset.label}...`);
    try {
      const response = await fetch(`/api/ply?path=${encodeURIComponent(preset.path)}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || response.statusText);
      }
      const buffer = await response.arrayBuffer();
      addCloud(parsePly(buffer, preset.label, preset.path));
      setStatus(`Loaded preset: ${preset.label}`);
    } catch (error) {
      setStatus(`Preset load failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <header>
          <h1>SfM/MVS PLY Viewer</h1>
          <p>{status}</p>
        </header>

        <label className="file-button">
          <FolderOpen size={18} />
          <span>Open PLY files</span>
          <input type="file" accept=".ply" multiple onChange={(event) => loadFiles(event.target.files)} />
        </label>

        <section>
          <h2>Presets</h2>
          <div className="stack">
            {presets.map((preset) => (
              <button key={preset.id} className="preset-button" disabled={!preset.exists || loading} onClick={() => loadPreset(preset)} title={preset.path}>
                <span>{preset.label}</span>
                <strong>{preset.exists ? 'Load' : 'Missing'}</strong>
              </button>
            ))}
          </div>
        </section>

        <section>
          <h2>Point Clouds</h2>
          <div className="stack">
            {clouds.length === 0 && <div className="empty">No PLY loaded yet.</div>}
            {clouds.map((cloud) => (
              <button key={cloud.id} className={`cloud-button ${activeCloud?.id === cloud.id ? 'active' : ''}`} onClick={() => setActiveId(cloud.id)}>
                <span>{cloud.name}</span>
                <strong>{formatNumber(cloud.stats.pointCount)} pts</strong>
              </button>
            ))}
          </div>
        </section>

        <section className="controls">
          <h2>View</h2>
          <label>
            <span>Point size</span>
            <input type="range" min="0.001" max="0.08" step="0.001" value={pointSize} onChange={(event) => setPointSize(Number(event.target.value))} />
          </label>
          <label>
            <span>Color</span>
            <select value={colorMode} onChange={(event) => setColorMode(event.target.value)}>
              <option value="original">PLY original</option>
              <option value="mono">Single color</option>
              <option value="height">Height color</option>
            </select>
          </label>
          {colorMode === 'mono' && (
            <label>
              <span>Single color</span>
              <input type="color" value={monoColor} onChange={(event) => setMonoColor(event.target.value)} />
            </label>
          )}
          <label>
            <span>Background</span>
            <select value={background} onChange={(event) => setBackground(event.target.value)}>
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="black">Black</option>
            </select>
          </label>
          <button className="icon-action" onClick={() => setResetToken((value) => value + 1)}>
            <RotateCcw size={17} />
            <span>Reset view</span>
          </button>
        </section>

        {activeCloud && (
          <section>
            <h2>Stats</h2>
            <div className="metrics">
              <div className="metric-row"><span>Points</span><code>{formatNumber(activeCloud.stats.pointCount)}</code></div>
              <BboxLine label="BBox min" value={activeCloud.stats.bbox.min} />
              <BboxLine label="BBox max" value={activeCloud.stats.bbox.max} />
              <BboxLine label="BBox size" value={activeCloud.stats.bbox.size} />
            </div>
          </section>
        )}
      </aside>

      <section className="viewport" style={{ background: backgrounds[background] }}>
        {loading && <div className="loading"><Loader2 size={18} /> Loading</div>}
        {!activeCloud && (
          <div className="welcome">
            <Palette size={36} />
            <h2>Load an SfM/MVS PLY point cloud</h2>
          </div>
        )}
        {activeCloud && (
          <Canvas camera={{ fov: 50 }} gl={{ antialias: true }}>
            <Suspense fallback={null}>
              <Scene cloud={activeCloud} pointSize={pointSize} colorMode={colorMode} monoColor={monoColor} resetToken={resetToken} />
            </Suspense>
          </Canvas>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
