import { Quat, Vec3 } from 'playcanvas';

import { Splat } from './splat';
import { Events } from './events';
import { Scene } from './scene';
import { State } from './splat-state';

type ImportFile = {
    filename: string;
    url?: string;
    contents?: File;
    skipReorder?: boolean;
};

type PhysMotionAttribute = 'position' | 'rotation' | 'scale';

type PhysMotionManifest = {
    format?: 'phys-motion-v1';
    base?: string;
    binary: string;
    frameCount: number;
    frameRate?: number;
    numSplats: number;
    attributes?: PhysMotionAttribute[];
    frameStrideBytes?: number;
    indices?: string;
    updateBounds?: boolean;
    proxy?: {
        motion: string;
        skinning: string;
        groupCount: number;
        blendCount: number;
        motionStrideBytes?: number;
        skinningStrideBytes?: number;
    };
};

type PhysMotionTrack = {
    manifest: PhysMotionManifest;
    binary?: ArrayBuffer;
    binaryUrl?: string;
    indices?: Uint32Array;
    proxyMotion?: ArrayBuffer;
    proxyMotionUrl?: string;
    proxySkinning?: ArrayBuffer;
    proxyRestCenters?: Float32Array;
    proxyRestPositions?: Float32Array;
    proxyRestRotations?: Float32Array;
    proxyRestScales?: Float32Array;
    proxyPalette?: {
        paletteStart: number;
        groupCount: number;
        previousTransformIndices: Uint16Array;
        mode: 'exact' | 'hard';
        averageWeight: number;
        exactRatio: number;
    };
    target?: Splat;
    floatsPerSplat: number;
    frameStrideBytes: number;
    chunkFrameCount: number;
    frameCache: Map<number, Promise<ArrayBuffer>>;
    cacheBudgetBytes: number;
    requestedFrame: number;
    appliedFrame: number;
    droppedFrames: number;
};

const manifestNames = ['.physmotion.json', 'phys_motion.json'];
const proxyScratchQuat = new Quat();
const proxyBaseQuat = new Quat();
const proxyBlendQuat = new Quat();
const proxyPoint = new Vec3();
const proxyLocal = new Vec3();
const proxyRotated = new Vec3();
const proxyTmpVec = new Vec3();

const isPhysMotionManifest = (filename: string) => {
    const lower = filename.toLowerCase();
    return manifestNames.some(name => lower.endsWith(name));
};

const normalizeName = (name: string) => name.replace(/\\/g, '/').split('/').pop().toLowerCase();

const findFile = (files: ImportFile[], filename: string) => {
    const target = normalizeName(filename);
    return files.find(file => normalizeName(file.filename) === target);
};

const readArrayBuffer = async (file: ImportFile) => {
    if (file.contents) {
        return file.contents.arrayBuffer();
    }
    if (file.url) {
        return (await fetch(file.url)).arrayBuffer();
    }
    throw new Error(`motion package file '${file.filename}' has no contents or url`);
};

const readUrlRange = async (url: string, start: number, endExclusive: number) => {
    const response = await fetch(url, {
        headers: {
            Range: `bytes=${start}-${endExclusive - 1}`
        }
    });
    if (!response.ok && response.status !== 206) {
        throw new Error(`failed to read motion range ${start}-${endExclusive - 1}: ${response.status} ${response.statusText}`);
    }
    const buffer = await response.arrayBuffer();
    if (response.status === 206) {
        return buffer;
    }

    // Fallback for servers that ignore Range. This still works, but it costs one
    // full download; our FastAPI StaticFiles path supports 206 in the cloud.
    return buffer.slice(start, endExclusive);
};

const readText = async (file: ImportFile) => {
    if (file.contents) {
        return file.contents.text();
    }
    if (file.url) {
        return (await fetch(file.url)).text();
    }
    throw new Error(`motion package file '${file.filename}' has no contents or url`);
};

const floatsPerSplatFor = (attributes: PhysMotionAttribute[]) => {
    return attributes.reduce((sum, attribute) => {
        switch (attribute) {
            case 'position': return sum + 3;
            case 'rotation': return sum + 4;
            case 'scale': return sum + 3;
            default: return sum;
        }
    }, 0);
};

const normalizeQuatArray = (values: number[]) => {
    const length = Math.hypot(values[0], values[1], values[2], values[3]);
    if (length <= 1e-12) {
        values[0] = 1;
        values[1] = 0;
        values[2] = 0;
        values[3] = 0;
        return values;
    }
    values[0] /= length;
    values[1] /= length;
    values[2] /= length;
    values[3] /= length;
    return values;
};

const getSceneSplats = (events: Events) => (events.invoke('scene.splats') as Splat[]) ?? [];

const proxyPaletteMode = () => {
    const mode = new URLSearchParams(window.location.search).get('physProxyPalette')?.toLowerCase() ?? 'auto';
    if (mode === '0' || mode === 'off' || mode === 'false') return 'off';
    if (mode === 'exact') return 'exact';
    if (mode === 'hard' || mode === '1' || mode === 'true') return 'hard';
    return 'auto';
};

const chooseHardProxyGroups = (proxySkinning: ArrayBuffer, count: number, blendCount: number) => {
    const groupIds = new Uint32Array(proxySkinning, 0, count * blendCount);
    const weights = new Float32Array(proxySkinning, groupIds.byteLength, count * blendCount);
    const hardGroups = new Uint32Array(count);
    let exactCount = 0;
    let weightSum = 0;

    for (let i = 0; i < count; ++i) {
        let bestGroup = groupIds[i * blendCount];
        let bestWeight = weights[i * blendCount] ?? 0;
        for (let j = 1; j < blendCount; ++j) {
            const offset = i * blendCount + j;
            const weight = weights[offset] ?? 0;
            if (weight > bestWeight) {
                bestWeight = weight;
                bestGroup = groupIds[offset];
            }
        }
        hardGroups[i] = bestGroup;
        weightSum += bestWeight;
        if (bestWeight >= 0.999) {
            exactCount++;
        }
    }

    return {
        hardGroups,
        averageWeight: count > 0 ? weightSum / count : 0,
        exactRatio: count > 0 ? exactCount / count : 0
    };
};

const registerPhysMotionEvents = (events: Events, _scene: Scene) => {
    let activeTrack: PhysMotionTrack | null = null;
    let applying = false;
    let setFrameAgain = false;

    const restoreProxyPalette = (track: PhysMotionTrack | null) => {
        if (!track?.proxyPalette || !track.target || !track.indices) {
            return;
        }
        track.target.restoreMotionProxyPalette(track.indices, track.proxyPalette.previousTransformIndices);
        track.proxyPalette = null;
    };

    const resolveTarget = () => {
        const selected = events.invoke('selection') as Splat;
        if (selected?.visible) {
            return selected;
        }
        return getSceneSplats(events)[0] ?? null;
    };

    const importBaseIfNeeded = async (files: ImportFile[], manifest: PhysMotionManifest) => {
        const existing = getSceneSplats(events);
        if (existing.length > 0 || !manifest.base) {
            return existing[0] ?? null;
        }

        const baseFile = findFile(files, manifest.base);
        if (!baseFile) {
            throw new Error(`motion manifest references base '${manifest.base}', but it was not provided`);
        }

        const imported = await events.invoke('import', [{ ...baseFile, skipReorder: true }]) as Splat[];
        return imported?.[0] ?? null;
    };

    const ensureFrameChunk = (track: PhysMotionTrack, frame: number) => {
        if (track.binary) {
            return Promise.resolve(track.binary);
        }
        if (!track.binaryUrl) {
            throw new Error('Motion binary is not available');
        }

        const chunkIndex = Math.floor(frame / track.chunkFrameCount);
        const cached = track.frameCache.get(chunkIndex);
        if (cached) {
            return cached;
        }

        const startFrame = chunkIndex * track.chunkFrameCount;
        const frameCount = Math.min(track.chunkFrameCount, track.manifest.frameCount - startFrame);
        const startByte = startFrame * track.frameStrideBytes;
        const endByte = (startFrame + frameCount) * track.frameStrideBytes;
        const promise = readUrlRange(track.binaryUrl, startByte, endByte);
        track.frameCache.set(chunkIndex, promise);

        const maxCachedChunks = Math.max(2, Math.floor(track.cacheBudgetBytes / Math.max(track.frameStrideBytes * track.chunkFrameCount, 1)));
        while (track.frameCache.size > maxCachedChunks) {
            const firstKey = track.frameCache.keys().next().value;
            if (firstKey === chunkIndex) {
                break;
            }
            track.frameCache.delete(firstKey);
        }

        void promise.then(() => {
            const nextChunk = chunkIndex + 1;
            if (nextChunk * track.chunkFrameCount < track.manifest.frameCount && !track.frameCache.has(nextChunk)) {
                void ensureFrameChunk(track, nextChunk * track.chunkFrameCount);
            }
        }).catch((): null => null);

        return promise;
    };

    const decodeFrame = async (track: PhysMotionTrack, frame: number) => {
        const proxyFrame = decodeProxyFrame(track, frame);
        if (proxyFrame) {
            return proxyFrame;
        }

        const { manifest, indices, floatsPerSplat, frameStrideBytes } = track;
        const attributes = manifest.attributes ?? ['position'];
        const count = indices ? indices.length : manifest.numSplats;
        const binary = await ensureFrameChunk(track, frame);
        const chunkStartFrame = track.binary ? 0 : Math.floor(frame / track.chunkFrameCount) * track.chunkFrameCount;
        const byteOffset = (frame - chunkStartFrame) * frameStrideBytes;
        const floatOffset = byteOffset / Float32Array.BYTES_PER_ELEMENT;
        const floatsThisFrame = count * floatsPerSplat;
        const frameFloats = new Float32Array(binary, floatOffset * Float32Array.BYTES_PER_ELEMENT, floatsThisFrame);

        let cursor = 0;
        let positions: Float32Array = null;
        let rotations: Float32Array = null;
        let scales: Float32Array = null;

        for (const attribute of attributes) {
            const width = attribute === 'rotation' ? 4 : 3;
            const data = frameFloats.subarray(cursor, cursor + count * width);
            if (attribute === 'position') positions = data;
            if (attribute === 'rotation') rotations = data;
            if (attribute === 'scale') scales = data;
            cursor += count * width;
        }

        return {
            positions,
            rotations,
            scales,
            indices,
            updateBounds: manifest.updateBounds
        };
    };

    const decodeProxyFrame = (track: PhysMotionTrack, frame: number) => {
        const { manifest, indices, proxyMotion, proxySkinning } = track;
        const proxy = manifest.proxy;
        if (!proxy || !indices || (!proxyMotion && !track.proxyMotionUrl) || !proxySkinning || !track.target) {
            return null;
        }

        const groupCount = proxy.groupCount;
        const blendCount = proxy.blendCount;
        const count = indices.length;
        if (!proxyMotion) {
            return null;
        }
        const motionFloatsPerFrame = groupCount * 7;
        const proxyFloats = new Float32Array(proxyMotion, frame * motionFloatsPerFrame * Float32Array.BYTES_PER_ELEMENT, motionFloatsPerFrame);
        if (track.proxyPalette && track.proxyRestCenters) {
            return {
                proxyPalette: {
                    paletteStart: track.proxyPalette.paletteStart,
                    groupCount,
                    restCenters: track.proxyRestCenters,
                    frame: proxyFloats
                },
                updateBounds: false
            };
        }

        const groupIds = new Uint32Array(proxySkinning, 0, count * blendCount);
        const weights = new Float32Array(proxySkinning, count * blendCount * Uint32Array.BYTES_PER_ELEMENT, count * blendCount);
        const restCenters = track.proxyRestCenters ?? new Float32Array(proxyMotion, 0, groupCount * 3);
        const restPositions = track.proxyRestPositions;
        const restRotations = track.proxyRestRotations;
        const restScales = track.proxyRestScales;
        if (!restPositions || !restRotations || !restScales) {
            return null;
        }
        const positions = new Float32Array(count * 3);
        const rotations = new Float32Array(count * 4);
        const scales = new Float32Array(count * 3);

        for (let i = 0; i < count; ++i) {
            const id = indices[i];
            const src3 = i * 3;
            const src4 = i * 4;
            proxyPoint.set(restPositions[src3], restPositions[src3 + 1], restPositions[src3 + 2]);
            const quatAccum = [0, 0, 0, 0];
            proxyTmpVec.set(0, 0, 0);
            let totalWeight = 0;
            let referenceQuat: number[] = null;

            for (let j = 0; j < blendCount; ++j) {
                const skinIndex = i * blendCount + j;
                const weight = weights[skinIndex];
                if (weight <= 0) {
                    continue;
                }
                const groupId = groupIds[skinIndex];
                if (groupId >= groupCount) {
                    continue;
                }
                const centerOffset = groupId * 3;
                const rotationOffset = groupCount * 3 + groupId * 4;
                const cx = proxyFloats[centerOffset];
                const cy = proxyFloats[centerOffset + 1];
                const cz = proxyFloats[centerOffset + 2];
                const rx = restCenters[centerOffset];
                const ry = restCenters[centerOffset + 1];
                const rz = restCenters[centerOffset + 2];
                const qw = proxyFloats[rotationOffset];
                const qx = proxyFloats[rotationOffset + 1];
                const qy = proxyFloats[rotationOffset + 2];
                const qz = proxyFloats[rotationOffset + 3];
                proxyScratchQuat.set(qx, qy, qz, qw).normalize();
                proxyLocal.set(proxyPoint.x - rx, proxyPoint.y - ry, proxyPoint.z - rz);
                proxyScratchQuat.transformVector(proxyLocal, proxyRotated);
                proxyTmpVec.x += weight * (cx + proxyRotated.x);
                proxyTmpVec.y += weight * (cy + proxyRotated.y);
                proxyTmpVec.z += weight * (cz + proxyRotated.z);

                const quat = [qw, qx, qy, qz];
                if (!referenceQuat) {
                    referenceQuat = quat;
                }
                const sign = referenceQuat[0] * quat[0] + referenceQuat[1] * quat[1] + referenceQuat[2] * quat[2] + referenceQuat[3] * quat[3] < 0 ? -1 : 1;
                quatAccum[0] += sign * weight * quat[0];
                quatAccum[1] += sign * weight * quat[1];
                quatAccum[2] += sign * weight * quat[2];
                quatAccum[3] += sign * weight * quat[3];
                totalWeight += weight;
            }

            if (totalWeight <= 1e-8) {
                proxyTmpVec.copy(proxyPoint);
                quatAccum[0] = 1;
            } else if (Math.abs(totalWeight - 1) > 1e-5) {
                proxyTmpVec.mulScalar(1 / totalWeight);
            }
            normalizeQuatArray(quatAccum);

            positions[src3] = proxyTmpVec.x;
            positions[src3 + 1] = proxyTmpVec.y;
            positions[src3 + 2] = proxyTmpVec.z;
            proxyBlendQuat.set(quatAccum[1], quatAccum[2], quatAccum[3], quatAccum[0]).normalize();
            proxyBaseQuat.set(restRotations[src4 + 1], restRotations[src4 + 2], restRotations[src4 + 3], restRotations[src4]).normalize();
            proxyBlendQuat.mul(proxyBaseQuat);
            rotations[src4] = proxyBlendQuat.w;
            rotations[src4 + 1] = proxyBlendQuat.x;
            rotations[src4 + 2] = proxyBlendQuat.y;
            rotations[src4 + 3] = proxyBlendQuat.z;
            scales[src3] = restScales[src3];
            scales[src3 + 1] = restScales[src3 + 1];
            scales[src3 + 2] = restScales[src3 + 2];
        }

        return {
            positions,
            rotations,
            scales,
            indices,
            updateBounds: false
        };
    };

    const setFrame = async (frame: number) => {
        if (!activeTrack) {
            return;
        }

        const { manifest } = activeTrack;
        if (frame < 0 || frame >= manifest.frameCount) {
            return;
        }
        activeTrack.requestedFrame = frame;

        if (applying) {
            setFrameAgain = true;
            return;
        }

        applying = true;
        try {
            while (activeTrack) {
                setFrameAgain = false;
                const frameToApply = activeTrack.requestedFrame;
                const target = activeTrack.target?.visible ? activeTrack.target : resolveTarget();
                if (!target) {
                    return;
                }
                activeTrack.target = target;

                if (target.splatData.numSplats !== manifest.numSplats && !activeTrack.indices) {
                    throw new Error(`motion numSplats=${manifest.numSplats} does not match loaded splat numSplats=${target.splatData.numSplats}`);
                }

                await target.applyMotionFrame(await decodeFrame(activeTrack, frameToApply));
                if (frameToApply !== activeTrack.appliedFrame && activeTrack.appliedFrame !== -1) {
                    const skipped = Math.max(0, Math.abs(frameToApply - activeTrack.appliedFrame) - 1);
                    activeTrack.droppedFrames += skipped;
                }
                activeTrack.appliedFrame = frameToApply;

                if (!setFrameAgain || activeTrack.requestedFrame === frameToApply) {
                    break;
                }
            }
        } finally {
            applying = false;
        }
    };

    events.function('physmotion.loadPackage', async (files: ImportFile[]) => {
        const manifestFile = files.find(file => isPhysMotionManifest(file.filename));
        if (!manifestFile) {
            throw new Error('No .physmotion.json manifest found in motion package');
        }

        events.fire('startSpinner');
        try {
            const manifest = JSON.parse(await readText(manifestFile)) as PhysMotionManifest;
            const attributes = manifest.attributes ?? ['position'];

            if (!manifest.binary || !manifest.frameCount || !manifest.numSplats) {
                throw new Error('Motion manifest must define binary, frameCount, and numSplats');
            }
            restoreProxyPalette(activeTrack);

            const binaryFile = findFile(files, manifest.binary);
            if (!binaryFile) {
                throw new Error(`motion manifest references binary '${manifest.binary}', but it was not provided`);
            }

            const target = await importBaseIfNeeded(files, manifest);
            let streamBinary = !!binaryFile.url && !binaryFile.contents;
            let binary = streamBinary ? undefined : await readArrayBuffer(binaryFile);
            let indices: Uint32Array = null;
            if (manifest.indices) {
                const indexFile = findFile(files, manifest.indices);
                if (!indexFile) {
                    throw new Error(`motion manifest references indices '${manifest.indices}', but it was not provided`);
                }
                indices = new Uint32Array(await readArrayBuffer(indexFile));
            }
            let proxyMotion: ArrayBuffer = undefined;
            let proxyMotionUrl: string = undefined;
            let proxySkinning: ArrayBuffer = undefined;
            let proxyRestCenters: Float32Array = undefined;
            let proxyRestPositions: Float32Array = undefined;
            let proxyRestRotations: Float32Array = undefined;
            let proxyRestScales: Float32Array = undefined;
            let proxyPalette: PhysMotionTrack['proxyPalette'] = undefined;
            if (manifest.proxy) {
                const proxyMotionFile = findFile(files, manifest.proxy.motion);
                const proxySkinningFile = findFile(files, manifest.proxy.skinning);
                if (proxyMotionFile && proxySkinningFile && indices && target) {
                    proxySkinning = await readArrayBuffer(proxySkinningFile);
                    if (proxyMotionFile.url && !proxyMotionFile.contents) {
                        proxyMotionUrl = proxyMotionFile.url;
                        proxyMotion = await readArrayBuffer(proxyMotionFile);
                    } else {
                        proxyMotion = await readArrayBuffer(proxyMotionFile);
                    }
                    proxyRestCenters = new Float32Array(proxyMotion, 0, manifest.proxy.groupCount * 3);
                    const splatData = target.splatData;
                    const restX = splatData.getProp('x') as Float32Array;
                    const restY = splatData.getProp('y') as Float32Array;
                    const restZ = splatData.getProp('z') as Float32Array;
                    const restR0 = splatData.getProp('rot_0') as Float32Array;
                    const restR1 = splatData.getProp('rot_1') as Float32Array;
                    const restR2 = splatData.getProp('rot_2') as Float32Array;
                    const restR3 = splatData.getProp('rot_3') as Float32Array;
                    const restS0 = splatData.getProp('scale_0') as Float32Array;
                    const restS1 = splatData.getProp('scale_1') as Float32Array;
                    const restS2 = splatData.getProp('scale_2') as Float32Array;
                    proxyRestPositions = new Float32Array(indices.length * 3);
                    proxyRestRotations = new Float32Array(indices.length * 4);
                    proxyRestScales = new Float32Array(indices.length * 3);
                    for (let i = 0; i < indices.length; ++i) {
                        const id = indices[i];
                        const dst3 = i * 3;
                        const dst4 = i * 4;
                        proxyRestPositions[dst3] = restX[id];
                        proxyRestPositions[dst3 + 1] = restY[id];
                        proxyRestPositions[dst3 + 2] = restZ[id];
                        proxyRestRotations[dst4] = restR0[id];
                        proxyRestRotations[dst4 + 1] = restR1[id];
                        proxyRestRotations[dst4 + 2] = restR2[id];
                        proxyRestRotations[dst4 + 3] = restR3[id];
                        proxyRestScales[dst3] = restS0[id];
                        proxyRestScales[dst3 + 1] = restS1[id];
                        proxyRestScales[dst3 + 2] = restS2[id];
                    }
                    const mode = proxyPaletteMode();
                    const { hardGroups, averageWeight, exactRatio } = chooseHardProxyGroups(proxySkinning, indices.length, manifest.proxy.blendCount);
                    const useExact = exactRatio >= 0.999;
                    const useHard = mode === 'hard' || (mode === 'auto' && averageWeight >= 0.55);
                    if (mode !== 'off' && manifest.proxy.groupCount > 0 && (useExact || useHard)) {
                        const binding = target.setupMotionProxyPalette(indices, hardGroups, manifest.proxy.groupCount);
                        proxyPalette = {
                            ...binding,
                            mode: useExact ? 'exact' : 'hard',
                            averageWeight,
                            exactRatio
                        };
                    }
                    streamBinary = false;
                    binary = undefined;
                }
            }

            const floatsPerSplat = floatsPerSplatFor(attributes);
            const trackedSplats = indices ? indices.length : manifest.numSplats;
            const frameStrideBytes = manifest.frameStrideBytes ?? trackedSplats * floatsPerSplat * Float32Array.BYTES_PER_ELEMENT;
            if (frameStrideBytes % Float32Array.BYTES_PER_ELEMENT !== 0) {
                throw new Error('Motion frameStrideBytes must be divisible by 4');
            }
            if (binary && binary.byteLength < frameStrideBytes * manifest.frameCount) {
                throw new Error(`Motion binary is too small for ${manifest.frameCount} frames`);
            }

            const streamCacheBudgetBytes = 96 * 1024 * 1024;
            const chunkTargetBytes = 12 * 1024 * 1024;
            const chunkFrameCount = Math.max(1, Math.min(8, Math.floor(chunkTargetBytes / frameStrideBytes) || 1));
            activeTrack = {
                manifest: {
                    ...manifest,
                    attributes
                },
                binary,
                binaryUrl: streamBinary ? binaryFile.url : undefined,
                indices,
                proxyMotion,
                proxyMotionUrl,
                proxySkinning,
                proxyRestCenters,
                proxyRestPositions,
                proxyRestRotations,
                proxyRestScales,
                proxyPalette,
                target,
                floatsPerSplat,
                frameStrideBytes,
                chunkFrameCount,
                frameCache: new Map(),
                cacheBudgetBytes: streamCacheBudgetBytes,
                requestedFrame: 0,
                appliedFrame: -1,
                droppedFrames: 0
            };

            events.fire('timeline.setFrames', manifest.frameCount);
            const playbackFrameRate = streamBinary ? Math.min(manifest.frameRate ?? 30, 12) : manifest.frameRate;
            if (playbackFrameRate) {
                events.fire('timeline.setFrameRate', playbackFrameRate);
            }
            if (streamBinary) {
                const suffix = manifest.frameRate && playbackFrameRate !== manifest.frameRate
                    ? `；远程预览 ${playbackFrameRate} fps，原始动画 ${manifest.frameRate} fps`
                    : '';
                events.fire('physics.status', `动画包已启用按需加载：每块 ${chunkFrameCount} 帧，缓存预算约 ${Math.round(streamCacheBudgetBytes / 1024 / 1024)}MB${suffix}`);
            } else if (manifest.proxy && proxySkinning) {
                const proxyBytes = (proxyMotion?.byteLength ?? 0) + proxySkinning.byteLength;
                const suffix = proxyMotionUrl ? '；proxy motion 按需读取' : '';
                events.fire('physics.status', `Spark-style proxy 预览已启用：${manifest.proxy.groupCount} 组，轻量数据约 ${Math.max(1, Math.round(proxyBytes / 1024 / 1024))}MB${suffix}`);
            }
            await setFrame(0);
            events.fire('physmotion.loaded', activeTrack);

            return target;
        } finally {
            events.fire('stopSpinner');
        }
    });

    events.function('physmotion.clear', () => {
        restoreProxyPalette(activeTrack);
        activeTrack = null;
        setFrameAgain = false;
    });

    events.function('phys.selectionSummary', (includeIndices = false) => {
        const splat = resolveTarget();
        if (!splat) {
            return null;
        }

        const state = splat.splatData.getProp('state') as Uint8Array;
        const x = splat.splatData.getProp('x') as Float32Array;
        const y = splat.splatData.getProp('y') as Float32Array;
        const z = splat.splatData.getProp('z') as Float32Array;
        const worldTransform = splat.worldTransform;
        const point = new Vec3();
        const world = new Vec3();
        const localMin = new Vec3(Infinity, Infinity, Infinity);
        const localMax = new Vec3(-Infinity, -Infinity, -Infinity);
        const worldMin = new Vec3(Infinity, Infinity, Infinity);
        const worldMax = new Vec3(-Infinity, -Infinity, -Infinity);
        const indices: number[] = [];
        let count = 0;

        for (let i = 0; i < state.length; ++i) {
            if (state[i] !== State.selected) {
                continue;
            }

            point.set(x[i], y[i], z[i]);
            worldTransform.transformPoint(point, world);

            localMin.x = Math.min(localMin.x, point.x);
            localMin.y = Math.min(localMin.y, point.y);
            localMin.z = Math.min(localMin.z, point.z);
            localMax.x = Math.max(localMax.x, point.x);
            localMax.y = Math.max(localMax.y, point.y);
            localMax.z = Math.max(localMax.z, point.z);
            worldMin.x = Math.min(worldMin.x, world.x);
            worldMin.y = Math.min(worldMin.y, world.y);
            worldMin.z = Math.min(worldMin.z, world.z);
            worldMax.x = Math.max(worldMax.x, world.x);
            worldMax.y = Math.max(worldMax.y, world.y);
            worldMax.z = Math.max(worldMax.z, world.z);

            if (includeIndices) {
                indices.push(i);
            }
            count++;
        }

        if (count === 0) {
            return {
                splat: splat.name,
                count: 0,
                indices: includeIndices ? [] : undefined
            };
        }

        const pack = (v: Vec3) => [v.x, v.y, v.z];
        return {
            splat: splat.name,
            count,
            indices: includeIndices ? indices : undefined,
            aabbLocal: {
                min: pack(localMin),
                max: pack(localMax)
            },
            aabbWorld: {
                min: pack(worldMin),
                max: pack(worldMax)
            },
            physGaussianPreprocessDraft: {
                sim_area: [worldMin.x, worldMax.x, worldMin.y, worldMax.y, worldMin.z, worldMax.z],
                scale: 1.0,
                rotation_degree: [0],
                rotation_axis: [0]
            }
        };
    });

    events.function('physmotion.setFrameAsync', async (frame: number) => {
        await setFrame(frame);
        return activeTrack?.target ?? null;
    });

    events.on('timeline.frame', (frame: number) => {
        void setFrame(frame);
    });

    events.on('scene.clear', () => {
        restoreProxyPalette(activeTrack);
        activeTrack = null;
        setFrameAgain = false;
    });
};

export { registerPhysMotionEvents, isPhysMotionManifest, PhysMotionManifest };
