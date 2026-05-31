import { Fragment, useEffect, useRef, useState } from 'react';
import { Stage, Layer, Image as KonvaImage, Line, Circle, Rect, Text as KonvaText } from 'react-konva';
import useImage from 'use-image';
import type Konva from 'konva';
import { Text, Center, Loader } from '@mantine/core';
import { useEditor } from '../store/editor';
import { api } from '../api/client';
import { saveCurrent } from '../controller';
import { isMask, hexToRgba } from '../lib/masks';
import { normRect, boxIntersectsRect } from '../lib/select';
import { Loupe } from './canvas/Loupe';
import { CanvasToolbar } from './canvas/CanvasToolbar';
import { useT } from '../i18n';

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

// Distance from point p to segment a→b (image coords).
function distToSeg(p: { x: number; y: number }, a: number[], b: number[]): number {
  const vx = b[0] - a[0];
  const vy = b[1] - a[1];
  const wx = p.x - a[0];
  const wy = p.y - a[1];
  const len2 = vx * vx + vy * vy;
  let tt = len2 > 0 ? (wx * vx + wy * vy) / len2 : 0;
  tt = Math.max(0, Math.min(1, tt));
  const cx = a[0] + tt * vx;
  const cy = a[1] + tt * vy;
  return Math.hypot(p.x - cx, p.y - cy);
}

function topLeft(points: number[][]): [number, number] {
  let mx = Infinity;
  let my = Infinity;
  for (const p of points) {
    if (p[0] < mx) mx = p[0];
    if (p[1] < my) my = p[1];
  }
  return [mx, my];
}

interface View {
  scale: number;
  x: number;
  y: number;
}

export function CanvasStage() {
  const t = useT();
  const workspaceId = useEditor((s) => s.workspaceId);
  const imageKey = useEditor((s) => s.imageKey);
  const tool = useEditor((s) => s.tool);
  const annotations = useEditor((s) => s.annotations);
  const selected = useEditor((s) => s.selected);
  const marked = useEditor((s) => s.marked);

  const select = useEditor((s) => s.select);
  const toggleMark = useEditor((s) => s.toggleMark);
  const selectMany = useEditor((s) => s.selectMany);
  const setTool = useEditor((s) => s.setTool);
  const stickyTool = useEditor((s) => s.stickyTool);
  const snapshot = useEditor((s) => s.snapshot);
  const resetHistory = useEditor((s) => s.resetHistory);
  const setAnnotations = useEditor((s) => s.setAnnotations);
  const addAnnotation = useEditor((s) => s.addAnnotation);
  const insertVertex = useEditor((s) => s.insertVertex);
  const deleteVertex = useEditor((s) => s.deleteVertex);
  const rotation = useEditor((s) => s.rotation);
  const setRotation = useEditor((s) => s.setRotation);
  const maskColor = useEditor((s) => s.maskColor);
  const maskMode = useEditor((s) => s.maskMode);
  const maskPreview = useEditor((s) => s.maskPreview);
  const toggleMaskPreview = useEditor((s) => s.toggleMaskPreview);

  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const [size, setSize] = useState({ width: 100, height: 100 });
  const [view, setView] = useState<View>({ scale: 1, x: 0, y: 0 });
  const [draft, setDraft] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(
    null,
  );
  const [polyPoints, setPolyPoints] = useState<number[][]>([]);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [marquee, setMarquee] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(
    null,
  );
  const [reloadToken, setReloadToken] = useState(0);
  const [loupe, setLoupe] = useState(true);

  const url =
    workspaceId && imageKey ? `${api.imageFileUrl(workspaceId, imageKey)}?t=${reloadToken}` : '';
  const [img, imgStatus] = useImage(url);

  // Keep the stage sized to its container.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setSize({ width: el.clientWidth, height: el.clientHeight });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    update();
    return () => ro.disconnect();
  }, []);

  const fit = () => {
    if (!img || !size.width) return;
    const s = Math.min(size.width / img.width, size.height / img.height) * 0.95;
    setView({ scale: s, x: (size.width - img.width * s) / 2, y: (size.height - img.height * s) / 2 });
  };

  // Re-fit when a new image loads or the container resizes.
  useEffect(fit, [img, size.width, size.height]);

  // Cancel any in-progress drawing when the tool or image changes.
  useEffect(() => {
    setDraft(null);
    setPolyPoints([]);
    setCursor(null);
    setMarquee(null);
  }, [tool, imageKey]);

  const finishPolygon = () => {
    // A double-click closes the polygon but also adds a duplicate final vertex
    // (two mousedowns at the same spot) — drop trailing duplicate(s).
    let pts = polyPoints;
    while (
      pts.length >= 2 &&
      pts[pts.length - 1][0] === pts[pts.length - 2][0] &&
      pts[pts.length - 1][1] === pts[pts.length - 2][1]
    ) {
      pts = pts.slice(0, -1);
    }
    if (pts.length >= 3) {
      addAnnotation({ points: pts, transcription: '', difficult: false, shape: 'Polygon' });
      if (!stickyTool) setTool('select');
    }
    setPolyPoints([]);
  };

  // Enter finishes a polygon in progress.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (tool === 'polygon' && e.key === 'Enter') {
        e.preventDefault();
        finishPolygon();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool, polyPoints, stickyTool]);

  // Zoom keyboard shortcuts (+/-/0/F) — local to the canvas view state.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tgt = e.target as HTMLElement | null;
      if (tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable))
        return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        zoomBy(1.2);
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        zoomBy(1 / 1.2);
      } else if (e.key === '0') {
        e.preventDefault();
        if (img) setView({ scale: 1, x: (size.width - img.width) / 2, y: (size.height - img.height) / 2 });
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        fit();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [img, size.width, size.height]);

  const relPointer = (): { x: number; y: number } | null => {
    const stage = stageRef.current;
    const p = stage?.getRelativePointerPosition();
    return p ? { x: p.x, y: p.y } : null;
  };

  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const stage = stageRef.current;
    const pointer = stage?.getPointerPosition();
    if (!pointer) return;
    const by = 1.08;
    const dir = e.evt.deltaY > 0 ? 1 / by : by;
    setView((v) => {
      const ns = clamp(v.scale * dir, 0.05, 30);
      const mx = (pointer.x - v.x) / v.scale;
      const my = (pointer.y - v.y) / v.scale;
      return { scale: ns, x: pointer.x - mx * ns, y: pointer.y - my * ns };
    });
  };

  const zoomBy = (factor: number) => {
    const cx = size.width / 2;
    const cy = size.height / 2;
    setView((v) => {
      const ns = clamp(v.scale * factor, 0.05, 30);
      const mx = (cx - v.x) / v.scale;
      const my = (cy - v.y) / v.scale;
      return { scale: ns, x: cx - mx * ns, y: cy - my * ns };
    });
  };

  // ---- drawing / selection ----
  const onMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    const stage = stageRef.current;
    const target = e.target;
    const isBg = target === stage || target.name() === 'bg';
    const p = relPointer();
    if (tool === 'quad' || tool === 'mask') {
      if (p) setDraft({ x0: p.x, y0: p.y, x1: p.x, y1: p.y });
    } else if (tool === 'polygon') {
      if (p) setPolyPoints((prev) => [...prev, [p.x, p.y]]);
    } else if (isBg) {
      // Shift+drag on the background = rubber-band select; plain click = deselect.
      if (e.evt.shiftKey && p) {
        stage?.draggable(false); // suppress pan during marquee
        setMarquee({ x0: p.x, y0: p.y, x1: p.x, y1: p.y });
      } else {
        select(null);
      }
    }
  };

  const onMouseMove = () => {
    const p = relPointer();
    if (p && tool !== 'select') setCursor(p);
    if (draft && p) setDraft({ ...draft, x1: p.x, y1: p.y });
    if (marquee && p) setMarquee({ ...marquee, x1: p.x, y1: p.y });
  };

  const onMouseUp = () => {
    if (marquee) {
      const r = normRect(marquee.x0, marquee.y0, marquee.x1, marquee.y1);
      const idxs = annotations
        .map((a, i) => (boxIntersectsRect(a.points, r) ? i : -1))
        .filter((i) => i >= 0);
      setMarquee(null);
      stageRef.current?.draggable(tool === 'select'); // restore pan
      if (idxs.length) selectMany(idxs);
      else select(null);
      return;
    }
    if (!draft) return;
    const x = Math.min(draft.x0, draft.x1);
    const y = Math.min(draft.y0, draft.y1);
    const w = Math.abs(draft.x1 - draft.x0);
    const h = Math.abs(draft.y1 - draft.y0);
    const makeMask = tool === 'mask';
    setDraft(null);
    if (w > 3 && h > 3) {
      const points = [
        [x, y],
        [x + w, y],
        [x + w, y + h],
        [x, y + h],
      ];
      addAnnotation(
        makeMask
          ? {
              points,
              transcription: '###',
              difficult: false,
              shape: 'Mask',
              mask_color: maskColor,
              mask_mode: maskMode,
            }
          : { points, transcription: '', difficult: false, shape: 'Quad' },
      );
      if (!stickyTool) setTool('select');
    }
  };

  const onDblClick = () => {
    if (tool === 'polygon') finishPolygon();
  };

  const onStageDragEnd = (e: Konva.KonvaEventObject<DragEvent>) => {
    if (e.target === stageRef.current) {
      setView({ ...view, x: e.target.x(), y: e.target.y() });
    }
  };

  const applyPoints = (i: number, pts: number[][]) => {
    setAnnotations(
      annotations.map((a, idx) => (idx === i ? { ...a, points: pts } : a)),
      false,
    );
  };

  // Double-click a selected polygon's edge to insert a vertex there.
  const onShapeDblClick = (i: number) => {
    if (tool !== 'select') return;
    const ann = annotations[i];
    if (!ann || ann.shape !== 'Polygon') return;
    const p = relPointer();
    if (!p) return;
    const pts = ann.points;
    let best = 0;
    let bestD = Infinity;
    for (let j = 0; j < pts.length; j++) {
      const d = distToSeg(p, pts[j], pts[(j + 1) % pts.length]);
      if (d < bestD) {
        bestD = d;
        best = j;
      }
    }
    select(i);
    insertVertex(i, best + 1, [p.x, p.y]);
  };

  // Rotate the image 90° and transform every annotation point into the new
  // frame, then persist so the backend serves the freshly-rotated image.
  const rotate = async (dir: 1 | -1) => {
    if (!img) return;
    const W = img.width;
    const H = img.height;
    const map =
      dir === 1
        ? (p: number[]) => [H - p[1], p[0]] // clockwise
        : (p: number[]) => [p[1], W - p[0]]; // counter-clockwise
    setAnnotations(
      annotations.map((a) => ({ ...a, points: a.points.map(map) })),
      false,
    );
    setRotation(rotation + dir * 90);
    // Old undo history is in the previous orientation's coordinate frame, so it
    // would misalign if replayed — drop it after a rotation.
    resetHistory();
    try {
      await saveCurrent();
    } catch {
      /* ignore */
    }
    setReloadToken((tk) => tk + 1);
  };

  const sw = (n: number) => n / view.scale;

  // NOTE: the container is rendered unconditionally so its ResizeObserver (set
  // up once on mount) always attaches — otherwise `size` would stay at its
  // initial 100x100 and fit() would shrink the image to a few percent.
  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        background: '#e9ecef',
        cursor: imageKey && tool !== 'select' ? 'crosshair' : 'default',
      }}
    >
      {!imageKey && (
        <Center style={{ position: 'absolute', inset: 0 }}>
          <Text c="dimmed">{t('canvas.selectStart')}</Text>
        </Center>
      )}

      {imageKey && (
      <>
      {imgStatus === 'loading' && (
        <Center style={{ position: 'absolute', inset: 0, zIndex: 5 }}>
          <Loader />
        </Center>
      )}

      <Stage
        ref={stageRef}
        width={size.width}
        height={size.height}
        scaleX={view.scale}
        scaleY={view.scale}
        x={view.x}
        y={view.y}
        draggable={tool === 'select'}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={() => {
          setCursor(null);
          if (marquee) {
            // mouse released outside the stage — cancel marquee + restore pan
            setMarquee(null);
            stageRef.current?.draggable(tool === 'select');
          }
        }}
        onDblClick={onDblClick}
        onDragEnd={onStageDragEnd}
      >
        <Layer>
          {img && <KonvaImage image={img} name="bg" />}

          {annotations.map((ann, i) => {
            const flat = ann.points.flatMap((p) => p);
            const isSel = i === selected;
            const isMarked = marked.has(i);
            const mask = isMask(ann);
            const mmode = ann.mask_mode || 'solid';
            const emptyText = !mask && !ann.transcription.trim();

            let stroke: string;
            if (mask) stroke = isSel || isMarked ? '#fa5252' : '#212529';
            else if (isSel) stroke = '#fa5252';
            else if (isMarked) stroke = '#f76707';
            else if (emptyText) stroke = '#f59f00';
            else stroke = '#4263eb';

            const fill = mask
              ? mmode === 'solid'
                ? hexToRgba(ann.mask_color || '#000000', maskPreview ? 1 : 0.5)
                : 'rgba(120,120,120,0.45)'
              : isSel || isMarked
                ? 'rgba(250,82,82,0.12)'
                : emptyText
                  ? 'rgba(245,159,0,0.08)'
                  : 'rgba(66,99,235,0.06)';

            const dash =
              mask && mmode !== 'solid'
                ? [sw(6), sw(4)]
                : emptyText
                  ? [sw(5), sw(4)]
                  : undefined;

            const [lx, ly] = topLeft(ann.points);

            return (
              <Fragment key={`grp${i}`}>
                <Line
                  key={`g${i}`}
                  points={flat}
                  closed
                  stroke={stroke}
                  strokeWidth={sw(2)}
                  fill={fill}
                  dash={dash}
                  hitStrokeWidth={Math.max(12, sw(12))}
                  draggable={tool === 'select'}
                  onMouseDown={(e) => {
                    if (tool === 'select') {
                      e.cancelBubble = true;
                      if (e.evt.shiftKey) toggleMark(i);
                      else select(i);
                    }
                  }}
                  onDblClick={(e) => {
                    e.cancelBubble = true;
                    onShapeDblClick(i);
                  }}
                  onDragStart={(e) => {
                    e.cancelBubble = true;
                    snapshot();
                  }}
                  onDragEnd={(e) => {
                    const node = e.target;
                    const dx = node.x();
                    const dy = node.y();
                    node.position({ x: 0, y: 0 });
                    applyPoints(
                      i,
                      ann.points.map(([px, py]) => [px + dx, py + dy]),
                    );
                  }}
                />
                <KonvaText
                  key={`n${i}`}
                  x={lx + sw(2)}
                  y={ly + sw(2)}
                  text={`${i + 1}`}
                  fontSize={sw(13)}
                  fontStyle="bold"
                  fill={stroke}
                  listening={false}
                />
              </Fragment>
            );
          })}

          {/* corner anchors for the primary selected shape (single selection only) */}
          {tool === 'select' &&
            selected !== null &&
            marked.size <= 1 &&
            annotations[selected]?.points?.map((p, pi) => (
              <Circle
                key={`a${pi}`}
                x={p[0]}
                y={p[1]}
                radius={sw(6)}
                fill="#fff"
                stroke="#fa5252"
                strokeWidth={sw(2)}
                draggable
                onMouseDown={(e) => {
                  e.cancelBubble = true;
                }}
                onContextMenu={(e) => {
                  e.evt.preventDefault();
                  e.cancelBubble = true;
                  if (annotations[selected]?.shape === 'Polygon') deleteVertex(selected, pi);
                }}
                onDragStart={(e) => {
                  e.cancelBubble = true;
                  snapshot();
                }}
                onDragMove={(e) => {
                  e.cancelBubble = true;
                  const pts = annotations[selected].points.map((q) => [...q]);
                  pts[pi] = [e.target.x(), e.target.y()];
                  applyPoints(selected, pts);
                }}
              />
            ))}

          {/* crosshair guides while drawing */}
          {cursor && tool !== 'select' && img && (
            <>
              <Line
                points={[cursor.x, 0, cursor.x, img.height]}
                stroke="rgba(250,82,82,0.6)"
                strokeWidth={sw(1)}
                dash={[sw(4), sw(4)]}
                listening={false}
              />
              <Line
                points={[0, cursor.y, img.width, cursor.y]}
                stroke="rgba(250,82,82,0.6)"
                strokeWidth={sw(1)}
                dash={[sw(4), sw(4)]}
                listening={false}
              />
            </>
          )}

          {/* polygon in progress */}
          {polyPoints.length > 0 && (
            <>
              <Line
                points={polyPoints.flatMap((p) => p)}
                stroke="#4263eb"
                strokeWidth={sw(2)}
                dash={[sw(6), sw(4)]}
              />
              {polyPoints.map((p, i) => (
                <Circle key={`pp${i}`} x={p[0]} y={p[1]} radius={sw(4)} fill="#4263eb" />
              ))}
            </>
          )}

          {draft && (
            <Rect
              x={Math.min(draft.x0, draft.x1)}
              y={Math.min(draft.y0, draft.y1)}
              width={Math.abs(draft.x1 - draft.x0)}
              height={Math.abs(draft.y1 - draft.y0)}
              stroke="#4263eb"
              dash={[sw(6), sw(4)]}
              strokeWidth={sw(2)}
              fill="rgba(66,99,235,0.08)"
            />
          )}

          {marquee && (
            <Rect
              x={Math.min(marquee.x0, marquee.x1)}
              y={Math.min(marquee.y0, marquee.y1)}
              width={Math.abs(marquee.x1 - marquee.x0)}
              height={Math.abs(marquee.y1 - marquee.y0)}
              stroke="#7048e8"
              dash={[sw(4), sw(4)]}
              strokeWidth={sw(1)}
              fill="rgba(112,72,232,0.08)"
              listening={false}
            />
          )}
        </Layer>
      </Stage>

      {/* overlay controls */}
      <CanvasToolbar
        scale={view.scale}
        maskPreview={maskPreview}
        loupe={loupe}
        onRotate={rotate}
        onZoom={zoomBy}
        onFit={fit}
        onToggleMaskPreview={toggleMaskPreview}
        onToggleLoupe={() => setLoupe((v) => !v)}
      />

      {img && (
        <Text
          size="xs"
          c="dimmed"
          style={{ position: 'absolute', left: 12, bottom: 14, zIndex: 6 }}
        >
          {t('canvas.status', { w: img.width, h: img.height, r: rotation, n: annotations.length })}
        </Text>
      )}

      {/* magnifier loupe — follows the cursor while a draw tool is active */}
      {loupe && cursor && tool !== 'select' && img && <Loupe img={img} cursor={cursor} />}
      </>
      )}
    </div>
  );
}
