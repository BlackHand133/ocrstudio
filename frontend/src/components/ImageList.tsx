import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Badge,
  Box,
  Button,
  Checkbox,
  Group,
  Image,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconAlertTriangle, IconSearch } from '@tabler/icons-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useEditor } from '../store/editor';
import { useImages, useMissing } from '../hooks/queries';
import { openImage } from '../controller';
import { api } from '../api/client';
import { RelinkModal } from './modals/RelinkModal';
import { useT } from '../i18n';
import type { ImageInfo } from '../types';

type Filter = 'all' | 'annotated' | 'empty';
const ROW = 52;

export function ImageList() {
  const t = useT();
  const workspaceId = useEditor((s) => s.workspaceId);
  const currentKey = useEditor((s) => s.imageKey);
  const excluded = useEditor((s) => s.excluded);
  const toggleExcluded = useEditor((s) => s.toggleExcluded);
  const setExcluded = useEditor((s) => s.setExcluded);
  const setImageKeys = useEditor((s) => s.setImageKeys);
  const { data: images } = useImages(workspaceId);
  const { data: missing } = useMissing(workspaceId);
  const [relinkOpened, { open: openRelink, close: closeRelink }] = useDisclosure(false);

  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<Filter>('all');

  const filtered = useMemo<ImageInfo[]>(() => {
    let items = images ?? [];
    if (filter === 'annotated') items = items.filter((i) => i.has_annotations);
    else if (filter === 'empty') items = items.filter((i) => !i.has_annotations);
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter((i) => i.key.toLowerCase().includes(q));
    }
    return items;
  }, [images, filter, search]);

  const includedCount = (images ?? []).filter((i) => !excluded.has(i.key)).length;

  const parentRef = useRef<HTMLDivElement>(null);
  const virt = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW,
    overscan: 10,
  });

  // Publish the (filtered) ordered keys so keyboard navigation in useShortcuts
  // follows exactly what the user sees.
  useEffect(() => {
    setImageKeys(filtered.map((i) => i.key));
  }, [filtered, setImageKeys]);

  // Keep the current image scrolled into view when navigating by keyboard.
  useEffect(() => {
    if (!currentKey) return;
    const idx = filtered.findIndex((i) => i.key === currentKey);
    if (idx >= 0) virt.scrollToIndex(idx, { align: 'auto' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentKey]);

  return (
    <Stack gap={0} h="100%">
      <Box p="xs">
        <TextInput
          size="xs"
          placeholder={t('list.search')}
          leftSection={<IconSearch size={14} />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          mb="xs"
        />
        <SegmentedControl
          size="xs"
          fullWidth
          value={filter}
          onChange={(v) => setFilter(v as Filter)}
          data={[
            { label: t('list.all'), value: 'all' },
            { label: t('list.labeled'), value: 'annotated' },
            { label: t('list.empty'), value: 'empty' },
          ]}
        />
        <Group justify="space-between" mt={6} gap={4}>
          <Text size="xs" c="dimmed">
            {t('list.forExport', { n: includedCount, m: (images ?? []).length })}
          </Text>
          <Group gap={2}>
            <Button size="compact-xs" variant="subtle" onClick={() => setExcluded([])}>
              {t('list.selAll')}
            </Button>
            <Button
              size="compact-xs"
              variant="subtle"
              onClick={() => setExcluded((images ?? []).map((i) => i.key))}
            >
              {t('list.selNone')}
            </Button>
          </Group>
        </Group>
      </Box>

      {workspaceId && missing && missing.missing_count > 0 && (
        <Box px="xs" pb={6}>
          <Button
            size="compact-xs"
            color="orange"
            variant="light"
            fullWidth
            leftSection={<IconAlertTriangle size={14} />}
            onClick={openRelink}
          >
            {t('list.missing', { n: missing.missing_count })}
          </Button>
        </Box>
      )}
      {workspaceId && (
        <RelinkModal
          workspaceId={workspaceId}
          missing={missing?.missing ?? []}
          opened={relinkOpened}
          onClose={closeRelink}
        />
      )}

      <div ref={parentRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        <div style={{ height: virt.getTotalSize(), position: 'relative', width: '100%' }}>
          {virt.getVirtualItems().map((row) => {
            const img = filtered[row.index];
            const active = img.key === currentKey;
            const included = !excluded.has(img.key);
            return (
              <div
                key={img.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: row.size,
                  transform: `translateY(${row.start}px)`,
                  padding: '2px 6px',
                }}
              >
                <Group
                  gap="xs"
                  wrap="nowrap"
                  h="100%"
                  px="xs"
                  onClick={() => openImage(img.key)}
                  style={{
                    cursor: 'pointer',
                    borderRadius: 6,
                    background: active
                      ? 'var(--mantine-color-indigo-light)'
                      : img.has_annotations
                        ? 'var(--mantine-color-green-light)'
                        : undefined,
                  }}
                >
                  <Checkbox
                    size="xs"
                    checked={included}
                    onClick={(e) => e.stopPropagation()}
                    onChange={() => toggleExcluded(img.key)}
                  />
                  {workspaceId && (
                    <Image
                      src={api.imageThumbUrl(workspaceId, img.key, 64)}
                      w={40}
                      h={40}
                      fit="contain"
                      radius="sm"
                      loading="lazy"
                      style={{ background: '#f1f3f5', flex: '0 0 auto' }}
                    />
                  )}
                  <Text size="sm" truncate="end" style={{ flex: 1, minWidth: 0 }} title={img.key}>
                    {img.key}
                  </Text>
                  {img.annotation_count > 0 && (
                    <Badge size="xs" variant="filled" color="green">
                      {img.annotation_count}
                    </Badge>
                  )}
                </Group>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <Text c="dimmed" size="xs" ta="center" py="md">
              {t('list.noImages')}
            </Text>
          )}
        </div>
      </div>
    </Stack>
  );
}
