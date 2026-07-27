import { Checkbox, Group, NumberInput, Stack, Text } from '@mantine/core';
import { AUG_DEFS } from './augmentationDefs';
import type { TFunc } from '../../../i18n';

interface AugmentationPickerProps {
  /** Effect types currently enabled. */
  selected: string[];
  /** Per-effect parameter values, keyed by effect type then param key. */
  params: Record<string, Record<string, number>>;
  onToggle: (type: string, on: boolean) => void;
  onParamChange: (type: string, key: string, value: number) => void;
  t: TFunc;
}

/**
 * The augmentation catalogue: one row per effect, with its tunable parameters
 * revealed only while that effect is enabled.
 */
export function AugmentationPicker({
  selected,
  params,
  onToggle,
  onParamChange,
  t,
}: AugmentationPickerProps) {
  return (
    <Stack gap={6}>
      {AUG_DEFS.map((d) => {
        const on = selected.includes(d.type);
        return (
          <Group key={d.type} gap="sm" align="center" wrap="wrap">
            <Checkbox
              size="xs"
              label={d.label}
              checked={on}
              onChange={(e) => onToggle(d.type, e.currentTarget.checked)}
              styles={{ root: { minWidth: 120 }, label: { fontWeight: 500 } }}
            />
            {on &&
              d.params.map((p) => (
                <NumberInput
                  key={p.key}
                  size="xs"
                  w={118}
                  label={p.label}
                  min={p.min}
                  max={p.max}
                  step={p.step}
                  // Integer steps mean integer values; anything finer needs decimals.
                  decimalScale={Number.isInteger(p.step) ? 0 : 2}
                  value={params[d.type]?.[p.key] ?? p.def}
                  onChange={(v) => onParamChange(d.type, p.key, Number(v))}
                />
              ))}
            {on && d.params.length === 0 && (
              <Text size="xs" c="dimmed">
                {t('exp.noParams')}
              </Text>
            )}
          </Group>
        );
      })}
    </Stack>
  );
}
