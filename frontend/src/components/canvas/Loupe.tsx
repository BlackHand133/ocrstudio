import { Stage, Layer, Image as KonvaImage, Line } from 'react-konva';

const SIZE = 150;
const ZOOM = 5;

/** Magnifier inset that shows the area under the cursor at ZOOM×, with a crosshair. */
export function Loupe({ img, cursor }: { img: HTMLImageElement; cursor: { x: number; y: number } }) {
  const c = SIZE / 2;
  return (
    <div
      style={{
        position: 'absolute',
        right: 12,
        top: 12,
        zIndex: 6,
        width: SIZE,
        height: SIZE,
        borderRadius: 8,
        overflow: 'hidden',
        border: '2px solid #adb5bd',
        boxShadow: '0 1px 6px rgba(0,0,0,0.25)',
        background: '#fff',
        pointerEvents: 'none',
      }}
    >
      <Stage width={SIZE} height={SIZE}>
        <Layer>
          <KonvaImage
            image={img}
            scaleX={ZOOM}
            scaleY={ZOOM}
            x={c - cursor.x * ZOOM}
            y={c - cursor.y * ZOOM}
          />
          <Line points={[c - 8, c, c + 8, c]} stroke="#fa5252" strokeWidth={1} listening={false} />
          <Line points={[c, c - 8, c, c + 8]} stroke="#fa5252" strokeWidth={1} listening={false} />
        </Layer>
      </Stage>
    </div>
  );
}
