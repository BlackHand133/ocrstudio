import type { ReactNode } from 'react';
import { Group, Progress, Text } from '@mantine/core';
import { SPLIT_COLORS } from './augmentationDefs';

/** Roboflow-style horizontal train/valid/test bar from a split preview. */
export function SplitBar({ splits, total }: { splits: Record<string, number>; total: number }) {
  const denom = total || 1;
  return (
    <Progress.Root size={26} radius="sm">
      {Object.entries(splits).map(
        ([k, v]) =>
          v > 0 && (
            <Progress.Section key={k} value={(v / denom) * 100} color={SPLIT_COLORS[k] || 'gray'}>
              <Progress.Label>{`${k} ${v}`}</Progress.Label>
            </Progress.Section>
          ),
      )}
    </Progress.Root>
  );
}

/** One label/value line in the export summary. */
export function SummaryRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Group justify="space-between" gap="sm" wrap="nowrap">
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={500} ta="right">
        {value}
      </Text>
    </Group>
  );
}
