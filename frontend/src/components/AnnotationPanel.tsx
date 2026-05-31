import { useEffect, useRef, useState } from 'react';
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  ColorSwatch,
  Group,
  Menu,
  ScrollArea,
  SegmentedControl,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from '@mantine/core';
import {
  IconArrowsSort,
  IconChevronDown,
  IconCopy,
  IconEyeOff,
  IconForms,
  IconLock,
  IconLockOpen,
  IconRefresh,
  IconScan,
  IconTrash,
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useEditor } from '../store/editor';
import { api } from '../api/client';
import { copyFromPrevImage, runBatchDetect, runDetect } from '../controller';
import { isMask, MASK_COLORS } from '../lib/masks';
import { useT } from '../i18n';
import type { Tool } from '../types';

function Swatches({
  value,
  onPick,
  size = 16,
}: {
  value: string;
  onPick: (c: string) => void;
  size?: number;
}) {
  return (
    <Group gap={6} wrap="nowrap">
      {MASK_COLORS.map((c) => (
        <ColorSwatch
          key={c}
          color={c}
          size={size}
          withShadow
          style={{
            cursor: 'pointer',
            outline: value.toLowerCase() === c ? '2px solid var(--mantine-color-indigo-6)' : 'none',
            outlineOffset: 2,
          }}
          onClick={(e) => {
            e.stopPropagation();
            onPick(c);
          }}
        />
      ))}
    </Group>
  );
}

export function AnnotationPanel() {
  const t = useT();
  const imageKey = useEditor((s) => s.imageKey);
  const annotations = useEditor((s) => s.annotations);
  const selected = useEditor((s) => s.selected);
  const marked = useEditor((s) => s.marked);
  const editSeq = useEditor((s) => s.editSeq);
  const tool = useEditor((s) => s.tool);
  const setTool = useEditor((s) => s.setTool);
  const stickyTool = useEditor((s) => s.stickyTool);
  const toggleSticky = useEditor((s) => s.toggleSticky);
  const select = useEditor((s) => s.select);
  const toggleMark = useEditor((s) => s.toggleMark);
  const updateAnnotation = useEditor((s) => s.updateAnnotation);
  const setAnnotations = useEditor((s) => s.setAnnotations);
  const deleteSelected = useEditor((s) => s.deleteSelected);
  const sortByReadingOrder = useEditor((s) => s.sortByReadingOrder);
  const convertToMask = useEditor((s) => s.convertToMask);
  const convertToText = useEditor((s) => s.convertToText);
  const snapshot = useEditor((s) => s.snapshot);
  const maskColor = useEditor((s) => s.maskColor);
  const setMaskColor = useEditor((s) => s.setMaskColor);
  const maskMode = useEditor((s) => s.maskMode);
  const setMaskMode = useEditor((s) => s.setMaskMode);

  const taRefs = useRef<Record<number, HTMLTextAreaElement | null>>({});
  const cardRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const [reocrIdx, setReocrIdx] = useState<number | null>(null);

  // Scroll the selected card into view whenever the selection changes.
  useEffect(() => {
    if (selected === null) return;
    cardRefs.current[selected]?.scrollIntoView({ block: 'nearest' });
  }, [selected]);

  // Focus the selected box's transcription editor when requested (Tab / OCR).
  useEffect(() => {
    if (selected === null) return;
    cardRefs.current[selected]?.scrollIntoView({ block: 'nearest' });
    const ta = taRefs.current[selected];
    if (ta) {
      ta.focus();
      const len = ta.value.length;
      ta.setSelectionRange(len, len);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editSeq]);

  const modeData = [
    { label: t('mode.solid'), value: 'solid' },
    { label: t('mode.blur'), value: 'blur' },
    { label: t('mode.pixelate'), value: 'pixelate' },
  ];

  if (!imageKey) {
    return (
      <Box p="md">
        <Text c="dimmed" size="sm">
          {t('panel.selectImage')}
        </Text>
      </Box>
    );
  }

  const editText = (i: number, value: string) => {
    setAnnotations(
      annotations.map((a, idx) => (idx === i ? { ...a, transcription: value } : a)),
      false,
    );
  };

  const removeAt = (i: number) => {
    setAnnotations(annotations.filter((_, idx) => idx !== i));
    if (selected === i) select(null);
  };

  // Re-run OCR on a single box (e.g. after switching the model) and update its text.
  const reocr = async (i: number) => {
    const ws = useEditor.getState().workspaceId;
    const key = useEditor.getState().imageKey;
    const a = annotations[i];
    if (!ws || !key || !a) return;
    setReocrIdx(i);
    try {
      const res = await api.detectBox(ws, key, a.points);
      if (useEditor.getState().imageKey !== key) return; // navigated away during OCR
      updateAnnotation(i, { transcription: res.transcription, score: res.score });
      notifications.show(
        res.transcription
          ? { color: 'green', message: t('panel.reocrDone'), autoClose: 1500 }
          : { color: 'yellow', message: t('panel.reocrEmpty') },
      );
    } catch (e) {
      notifications.show({ color: 'red', title: t('panel.reocr'), message: (e as Error).message });
    } finally {
      setReocrIdx(null);
    }
  };

  const unionIdx = (): number[] => {
    const s = new Set<number>(marked);
    if (selected !== null) s.add(selected);
    return [...s].filter((i) => i >= 0 && i < annotations.length);
  };
  const selCount = unionIdx().length;

  const bulkDifficult = (val: boolean) => {
    const idx = new Set(unionIdx());
    setAnnotations(annotations.map((a, i) => (idx.has(i) ? { ...a, difficult: val } : a)));
  };

  return (
    <Stack gap="xs" h="100%">
      <Box p="sm" pb={0}>
        <Menu width="target" position="bottom-start">
          <Menu.Target>
            <Button
              fullWidth
              leftSection={<IconScan size={16} />}
              rightSection={<IconChevronDown size={14} />}
              variant="light"
              mb="xs"
            >
              {t('panel.runOcr')}
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item onClick={() => runDetect()}>{t('panel.ocrThis')}</Menu.Item>
            <Menu.Item onClick={() => runBatchDetect('empty')}>{t('panel.ocrEmpty')}</Menu.Item>
            <Menu.Item onClick={() => runBatchDetect('all', true)}>{t('panel.ocrAll')}</Menu.Item>
          </Menu.Dropdown>
        </Menu>

        <Group gap={6} wrap="nowrap" align="center">
          <SegmentedControl
            style={{ flex: 1 }}
            size="xs"
            value={tool}
            onChange={(v) => setTool(v as Tool)}
            data={[
              { label: t('tool.select'), value: 'select' },
              { label: t('tool.box'), value: 'quad' },
              { label: t('tool.polygon'), value: 'polygon' },
              { label: t('tool.mask'), value: 'mask' },
            ]}
          />
          <Tooltip label={t('panel.sticky')} withArrow>
            <ActionIcon
              variant={stickyTool ? 'filled' : 'default'}
              color={stickyTool ? 'indigo' : 'gray'}
              onClick={toggleSticky}
              aria-label={t('panel.sticky')}
            >
              {stickyTool ? <IconLock size={16} /> : <IconLockOpen size={16} />}
            </ActionIcon>
          </Tooltip>
        </Group>

        {tool === 'mask' && (
          <Stack gap={6} mt="xs">
            <SegmentedControl size="xs" fullWidth value={maskMode} onChange={setMaskMode} data={modeData} />
            {maskMode === 'solid' && (
              <Group gap="xs" align="center">
                <Text size="xs" c="dimmed">
                  {t('panel.color')}
                </Text>
                <Swatches value={maskColor} onPick={setMaskColor} size={18} />
              </Group>
            )}
          </Stack>
        )}

        <Group justify="space-between" mt="xs">
          <Text size="sm" fw={600}>
            {t('panel.annotations')}
          </Text>
          <Group gap={4} wrap="nowrap">
            <Tooltip label={t('panel.sortOrder')} withArrow>
              <ActionIcon
                variant="subtle"
                size="sm"
                onClick={sortByReadingOrder}
                disabled={annotations.length < 2}
                aria-label={t('panel.sortOrder')}
              >
                <IconArrowsSort size={15} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label={t('panel.copyPrev')} withArrow>
              <ActionIcon
                variant="subtle"
                size="sm"
                onClick={() => void copyFromPrevImage()}
                aria-label={t('panel.copyPrev')}
              >
                <IconCopy size={15} />
              </ActionIcon>
            </Tooltip>
            <Badge variant="light">{annotations.length}</Badge>
          </Group>
        </Group>
      </Box>

      {selCount > 1 && (
        <Group justify="space-between" px="sm">
          <Text size="xs" c="dimmed">
            {t('panel.selectedN', { n: selCount })}
          </Text>
          <Group gap={4} wrap="nowrap">
            <Button size="compact-xs" variant="light" onClick={() => bulkDifficult(true)}>
              {t('panel.setDifficult')}
            </Button>
            <Button size="compact-xs" variant="light" color="red" onClick={() => deleteSelected()}>
              {t('panel.deleteSel')}
            </Button>
          </Group>
        </Group>
      )}

      <ScrollArea style={{ flex: 1, minHeight: 0 }}>
        <Stack gap="xs" p="sm" pt={0}>
          {annotations.map((a, i) => {
            const active = i === selected || marked.has(i);
            const mask = isMask(a);
            const empty = !mask && !a.transcription.trim();
            return (
              <Card
                key={i}
                ref={(el) => {
                  cardRefs.current[i] = el;
                }}
                withBorder
                padding="xs"
                radius="md"
                onClick={(e) => (e.shiftKey ? toggleMark(i) : select(i))}
                style={{
                  cursor: 'pointer',
                  borderColor: active ? 'var(--mantine-color-indigo-6)' : undefined,
                  background: active ? 'var(--mantine-color-indigo-light)' : undefined,
                }}
              >
                <Group justify="space-between" mb={4} wrap="nowrap">
                  <Group gap={6}>
                    <Badge size="xs" variant="default">
                      #{i + 1}
                    </Badge>
                    <Badge size="xs" variant={mask ? 'filled' : 'light'} color={mask ? 'dark' : 'gray'}>
                      {mask ? t('panel.censor') : a.shape}
                    </Badge>
                    {!mask && typeof a.score === 'number' && (
                      <Badge size="xs" variant="light" color="blue">
                        {a.score.toFixed(2)}
                      </Badge>
                    )}
                    {empty && (
                      <Badge size="xs" variant="light" color="orange">
                        {t('panel.noText')}
                      </Badge>
                    )}
                  </Group>
                  <Group gap={2} wrap="nowrap">
                    {!mask && (
                      <Tooltip label={t('panel.reocr')} withArrow>
                        <ActionIcon
                          size="sm"
                          variant="subtle"
                          color="blue"
                          aria-label={t('panel.reocr')}
                          loading={reocrIdx === i}
                          onClick={(e) => {
                            e.stopPropagation();
                            void reocr(i);
                          }}
                        >
                          <IconRefresh size={15} />
                        </ActionIcon>
                      </Tooltip>
                    )}
                    <Tooltip label={mask ? t('panel.toText') : t('panel.toCensor')} withArrow>
                      <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="gray"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (mask) convertToText(i);
                          else convertToMask(i, maskColor, maskMode);
                        }}
                      >
                        {mask ? <IconForms size={15} /> : <IconEyeOff size={15} />}
                      </ActionIcon>
                    </Tooltip>
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      color="red"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeAt(i);
                      }}
                    >
                      <IconTrash size={15} />
                    </ActionIcon>
                  </Group>
                </Group>

                {mask ? (
                  <Stack gap={6} mt={4} onClick={(e) => e.stopPropagation()}>
                    <SegmentedControl
                      size="xs"
                      value={a.mask_mode || 'solid'}
                      onChange={(m) => updateAnnotation(i, { mask_mode: m })}
                      data={modeData}
                    />
                    {(a.mask_mode || 'solid') === 'solid' && (
                      <Swatches
                        value={a.mask_color || '#000000'}
                        onPick={(c) => updateAnnotation(i, { mask_color: c })}
                      />
                    )}
                    <Text size="xs" c="dimmed">
                      {t('panel.hiddenOnExport', { mode: a.mask_mode || 'solid' })}
                    </Text>
                  </Stack>
                ) : (
                  <>
                    <Textarea
                      ref={(el) => {
                        taRefs.current[i] = el;
                      }}
                      autosize
                      minRows={1}
                      maxRows={4}
                      placeholder={t('panel.transcriptionPh')}
                      value={a.transcription}
                      onFocus={() => snapshot()}
                      onChange={(e) => editText(i, e.currentTarget.value)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <Checkbox
                      mt={6}
                      size="xs"
                      label={t('panel.difficult')}
                      checked={a.difficult}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => updateAnnotation(i, { difficult: e.currentTarget.checked })}
                    />
                  </>
                )}
              </Card>
            );
          })}
          {annotations.length === 0 && (
            <Text c="dimmed" size="xs" ta="center" py="md">
              {t('panel.noAnns')}
            </Text>
          )}
        </Stack>
      </ScrollArea>
    </Stack>
  );
}
