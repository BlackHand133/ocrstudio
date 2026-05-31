import { ActionIcon, Divider, Group, Paper, Text } from '@mantine/core';
import {
  IconAspectRatio,
  IconEye,
  IconEyeOff,
  IconRotate,
  IconRotateClockwise,
  IconZoomIn,
  IconZoomOut,
  IconZoomScan,
} from '@tabler/icons-react';
import { useT } from '../../i18n';

interface Props {
  scale: number;
  maskPreview: boolean;
  loupe: boolean;
  onRotate: (dir: 1 | -1) => void;
  onZoom: (factor: number) => void;
  onFit: () => void;
  onToggleMaskPreview: () => void;
  onToggleLoupe: () => void;
}

/** Floating canvas controls: rotate, zoom, fit, censor-preview, magnifier, zoom%. */
export function CanvasToolbar({
  scale,
  maskPreview,
  loupe,
  onRotate,
  onZoom,
  onFit,
  onToggleMaskPreview,
  onToggleLoupe,
}: Props) {
  const t = useT();
  return (
    <Paper
      withBorder
      shadow="sm"
      radius="md"
      p={4}
      style={{ position: 'absolute', right: 12, bottom: 12, zIndex: 6 }}
    >
      <Group gap={4}>
        <ActionIcon variant="subtle" onClick={() => onRotate(-1)} title={t('canvas.rotateLeft')}>
          <IconRotate size={18} />
        </ActionIcon>
        <ActionIcon variant="subtle" onClick={() => onRotate(1)} title={t('canvas.rotateRight')}>
          <IconRotateClockwise size={18} />
        </ActionIcon>
        <Divider orientation="vertical" />
        <ActionIcon variant="subtle" onClick={() => onZoom(1.2)} title={t('canvas.zoomIn')}>
          <IconZoomIn size={18} />
        </ActionIcon>
        <ActionIcon variant="subtle" onClick={() => onZoom(1 / 1.2)} title={t('canvas.zoomOut')}>
          <IconZoomOut size={18} />
        </ActionIcon>
        <ActionIcon variant="subtle" onClick={onFit} title={t('canvas.fit')}>
          <IconAspectRatio size={18} />
        </ActionIcon>
        <Divider orientation="vertical" />
        <ActionIcon
          variant={maskPreview ? 'filled' : 'subtle'}
          color="dark"
          onClick={onToggleMaskPreview}
          title={t('canvas.previewCensor')}
        >
          {maskPreview ? <IconEyeOff size={18} /> : <IconEye size={18} />}
        </ActionIcon>
        <ActionIcon
          variant={loupe ? 'filled' : 'subtle'}
          color="indigo"
          onClick={onToggleLoupe}
          title={t('canvas.loupe')}
        >
          <IconZoomScan size={18} />
        </ActionIcon>
        <Text size="xs" c="dimmed" w={42} ta="center">
          {Math.round(scale * 100)}%
        </Text>
      </Group>
    </Paper>
  );
}
