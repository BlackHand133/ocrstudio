import { useState, type ReactNode } from 'react';
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Divider,
  Group,
  Image,
  Modal,
  NumberInput,
  Progress,
  Select,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Stepper,
  Switch,
  Text,
} from '@mantine/core';
import {
  IconArrowLeft,
  IconArrowRight,
  IconDownload,
  IconPhoto,
  IconRefresh,
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import {
  api,
  type AugPreview,
  type DatasetFormat,
  type ExportParams,
  type SplitMode,
  type SplitPreview,
} from '../../api/client';
import { useEditor } from '../../store/editor';
import { useImages } from '../../hooks/queries';
import { saveCurrent } from '../../controller';
import { useT } from '../../i18n';
import type { ExportResult } from '../../types';

const AUGS: { type: string; label: string; params: Record<string, unknown> }[] = [
  { type: 'blur', label: 'Blur', params: { kernel_size: 5 } },
  { type: 'noise', label: 'Noise', params: { noise_type: 'gaussian', intensity: 20 } },
  { type: 'brightness_contrast', label: 'Brightness', params: { brightness: 15, contrast: 1.2 } },
  { type: 'grayscale', label: 'Grayscale', params: {} },
  { type: 'sharpen', label: 'Sharpen', params: { strength: 1 } },
  { type: 'rotation', label: 'Rotate ±3°', params: { angle: 3 } },
  { type: 'perspective', label: 'Perspective', params: { strength: 0.08 } },
  { type: 'random_erasing', label: 'Random erase', params: { prob: 1, area_ratio: 0.06 } },
];

const FORMATS: { value: DatasetFormat; label: string }[] = [
  { value: 'paddleocr', label: 'PaddleOCR (det + rec)' },
  { value: 'icdar', label: 'ICDAR-2015 (det)' },
  { value: 'coco', label: 'COCO (det)' },
  { value: 'yolo', label: 'YOLO (det)' },
  { value: 'csv', label: 'CSV manifest' },
  { value: 'jsonl', label: 'JSONL manifest' },
];
const DET_ONLY: DatasetFormat[] = ['icdar', 'coco', 'yolo'];
const SPLIT_COLORS: Record<string, string> = { train: 'blue', valid: 'teal', test: 'orange' };

/** Roboflow-style horizontal train/valid/test bar from a split preview. */
function SplitBar({ splits, total }: { splits: Record<string, number>; total: number }) {
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

function Row({ label, value }: { label: string; value: ReactNode }) {
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

export function ExportModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const t = useT();
  const workspaceId = useEditor((s) => s.workspaceId);
  const excluded = useEditor((s) => s.excluded);
  const { data: images } = useImages(workspaceId);

  const [active, setActive] = useState(0);
  const [kind, setKind] = useState<'detection' | 'recognition'>('detection');
  const [datasetFormat, setDatasetFormat] = useState<DatasetFormat>('paddleocr');
  const [splitMode, setSplitMode] = useState<SplitMode>('percentage');
  const [train, setTrain] = useState<number>(80);
  const [valid, setValid] = useState<number>(10);
  const [test, setTest] = useState<number>(10);
  const [trainCount, setTrainCount] = useState<number>(0);
  const [validCount, setValidCount] = useState<number>(0);
  const [testCount, setTestCount] = useState<number>(0);
  const [nBins, setNBins] = useState<number>(3);
  const [groupByImage, setGroupByImage] = useState<boolean>(true);
  const [format, setFormat] = useState<'png' | 'jpg'>('png');
  const [crop, setCrop] = useState<'bbox' | 'rotated'>('bbox');
  const [autoOrient, setAutoOrient] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExportResult | null>(null);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [preview, setPreview] = useState<SplitPreview | null>(null);
  const [augment, setAugment] = useState(false);
  const [augMode, setAugMode] = useState<'combinatorial' | 'sequential'>('combinatorial');
  const [augCopies, setAugCopies] = useState<number>(1);
  const [selAugs, setSelAugs] = useState<string[]>(['blur', 'brightness_contrast']);
  const [augPreview, setAugPreview] = useState<AugPreview | null>(null);
  const [augBusy, setAugBusy] = useState(false);
  const [sampleIdx, setSampleIdx] = useState(0);

  const sum = train + valid + test;
  const splitInvalid = splitMode !== 'count' && (sum <= 0 || sum > 100);
  const countInvalid = splitMode === 'count' && trainCount + validCount + testCount <= 0;

  const buildParams = (): ExportParams => {
    const params: ExportParams = {
      kind,
      dataset_format: datasetFormat,
      split_mode: splitMode,
      train,
      valid,
      test,
      train_count: trainCount,
      valid_count: validCount,
      test_count: testCount,
      n_bins: nBins,
      group_by_image: groupByImage,
      image_format: format,
      crop_method: crop,
      auto_orient: autoOrient,
    };
    if (excluded.size && images?.length) {
      params.selected_keys = images.filter((i) => !excluded.has(i.key)).map((i) => i.key);
    }
    if (augment && selAugs.length) {
      params.augment = true;
      params.aug_mode = augMode;
      params.aug_copies = augCopies;
      params.augmentations = AUGS.filter((a) => selAugs.includes(a.type)).map((a) => ({
        type: a.type,
        params: a.params,
      }));
      params.aug_targets = ['train'];
    }
    return params;
  };

  const doPreview = async () => {
    if (!workspaceId) return;
    try {
      await saveCurrent();
      setPreview(await api.previewSplit(workspaceId, buildParams()));
    } catch (e) {
      notifications.show({ color: 'red', message: (e as Error).message });
    }
  };

  const doAugPreview = async (idx = 0) => {
    if (!workspaceId || !selAugs.length) return;
    setAugBusy(true);
    try {
      await saveCurrent();
      const ap = await api.previewAugment(workspaceId, buildParams(), idx);
      setAugPreview(ap);
      setSampleIdx(ap.sample_index);
    } catch (e) {
      notifications.show({ color: 'red', message: (e as Error).message });
    } finally {
      setAugBusy(false);
    }
  };

  // Navigate between wizard steps and lazily load the preview for the step we
  // land on (so each step shows fresh numbers without an extra click).
  const goStep = (nextRaw: number) => {
    const next = Math.max(0, Math.min(3, nextRaw));
    setActive(next);
    if (next === 1 && workspaceId && !preview) void doPreview();
    if (next === 2 && augment && selAugs.length && !augPreview) void doAugPreview(0);
    if (next === 3 && workspaceId) void doPreview();
  };

  const run = async () => {
    if (!workspaceId) return;
    setBusy(true);
    setResult(null);
    try {
      await saveCurrent();
      const { job_id } = await api.exportDataset(workspaceId, buildParams());
      let job = await api.getJob(job_id);
      while (job.status === 'running') {
        setProgress({ done: job.done, total: job.total });
        await new Promise((r) => setTimeout(r, 500));
        job = await api.getJob(job_id);
      }
      if (job.status === 'done') {
        setResult(job.result as unknown as ExportResult);
        notifications.show({
          color: 'green',
          message: t('exp.exported', { n: (job.result as { total?: number }).total ?? 0 }),
        });
      } else {
        notifications.show({ color: 'red', title: t('exp.failed'), message: job.error || 'error' });
      }
    } catch (e) {
      notifications.show({ color: 'red', title: t('exp.failed'), message: (e as Error).message });
    } finally {
      setBusy(false);
      setProgress(null);
    }
  };

  const close = () => {
    onClose();
    // reset so the next open starts clean
    setActive(0);
    setResult(null);
    setProgress(null);
  };

  // final (post-augmentation) counts for the review step
  const finalSplits = preview?.aug_splits ?? preview?.splits ?? null;
  const finalTotal = preview?.aug_total ?? preview?.total ?? 0;

  return (
    <Modal opened={opened} onClose={close} title={t('exp.title')} size="lg">
      <Stepper active={active} onStepClick={goStep} size="sm" mb="md">
        {/* ── Step 1: format & type ───────────────────────────── */}
        <Stepper.Step label={t('exp.step1')} description={t('exp.step1d')}>
          <Stack gap="sm" mt="md">
            <Select
              label={t('exp.format')}
              value={datasetFormat}
              onChange={(v) => {
                const f = (v as DatasetFormat) || 'paddleocr';
                setDatasetFormat(f);
                setPreview(null);
                if (DET_ONLY.includes(f)) setKind('detection');
              }}
              data={FORMATS}
              allowDeselect={false}
              comboboxProps={{ withinPortal: true }}
            />
            <div>
              <Text size="sm" fw={500} mb={4}>
                {t('exp.dsType')}
              </Text>
              <SegmentedControl
                fullWidth
                value={kind}
                onChange={(v) => {
                  setKind(v as 'detection' | 'recognition');
                  setPreview(null);
                }}
                data={[
                  { label: t('exp.detection'), value: 'detection' },
                  {
                    label: t('exp.recognition'),
                    value: 'recognition',
                    disabled: DET_ONLY.includes(datasetFormat),
                  },
                ]}
              />
              {DET_ONLY.includes(datasetFormat) && (
                <Text size="xs" c="dimmed" mt={4}>
                  {t('exp.formatDetOnly')}
                </Text>
              )}
            </div>
            <Group grow align="flex-start">
              <div>
                <Text size="sm" fw={500} mb={4}>
                  {t('exp.imageFormat')}
                </Text>
                <SegmentedControl
                  fullWidth
                  value={format}
                  onChange={(v) => setFormat(v as 'png' | 'jpg')}
                  data={['png', 'jpg']}
                />
              </div>
              {kind === 'recognition' && (
                <div>
                  <Text size="sm" fw={500} mb={4}>
                    {t('exp.cropMethod')}
                  </Text>
                  <SegmentedControl
                    fullWidth
                    value={crop}
                    onChange={(v) => setCrop(v as 'bbox' | 'rotated')}
                    data={[
                      { label: t('exp.bbox'), value: 'bbox' },
                      { label: t('exp.rotated'), value: 'rotated' },
                    ]}
                  />
                </div>
              )}
            </Group>
            {kind === 'recognition' && (
              <Switch
                label={t('exp.autoOrient')}
                checked={autoOrient}
                onChange={(e) => setAutoOrient(e.currentTarget.checked)}
              />
            )}
          </Stack>
        </Stepper.Step>

        {/* ── Step 2: split ───────────────────────────────────── */}
        <Stepper.Step label={t('exp.step2')} description={t('exp.step2d')}>
          <Stack gap="sm" mt="md">
            <SegmentedControl
              fullWidth
              size="xs"
              value={splitMode}
              onChange={(v) => {
                setSplitMode(v as SplitMode);
                setPreview(null);
              }}
              data={[
                { label: t('exp.byPct'), value: 'percentage' },
                { label: t('exp.byCount'), value: 'count' },
                { label: t('exp.byStrat'), value: 'stratified' },
              ]}
            />
            {splitMode === 'count' ? (
              <Group grow>
                <NumberInput label={t('exp.train')} min={0} value={trainCount} onChange={(v) => { setTrainCount(Number(v) || 0); setPreview(null); }} />
                <NumberInput label={t('exp.valid')} min={0} value={validCount} onChange={(v) => { setValidCount(Number(v) || 0); setPreview(null); }} />
                <NumberInput label={t('exp.test')} min={0} value={testCount} onChange={(v) => { setTestCount(Number(v) || 0); setPreview(null); }} />
              </Group>
            ) : (
              <>
                <Group grow>
                  <NumberInput label={t('exp.train')} min={0} max={100} value={train} onChange={(v) => { setTrain(Number(v) || 0); setPreview(null); }} />
                  <NumberInput label={t('exp.valid')} min={0} max={100} value={valid} onChange={(v) => { setValid(Number(v) || 0); setPreview(null); }} />
                  <NumberInput label={t('exp.test')} min={0} max={100} value={test} onChange={(v) => { setTest(Number(v) || 0); setPreview(null); }} />
                </Group>
                {sum !== 100 && (
                  <Text size="xs" c="orange">
                    {t('exp.splitSum', { s: sum })}
                  </Text>
                )}
              </>
            )}
            {splitMode === 'stratified' && (
              <Group align="flex-end" gap="sm">
                <NumberInput size="xs" w={140} label={t('exp.nbins')} min={2} max={10} value={nBins} onChange={(v) => { setNBins(Number(v) || 3); setPreview(null); }} />
                <Text size="xs" c="dimmed">
                  {t('exp.stratNote')}
                </Text>
              </Group>
            )}
            {kind === 'recognition' && (
              <Switch
                label={t('exp.groupByImage')}
                checked={groupByImage}
                onChange={(e) => {
                  setGroupByImage(e.currentTarget.checked);
                  setPreview(null);
                }}
              />
            )}
            <Group gap="xs">
              <Button size="compact-xs" variant="light" leftSection={<IconRefresh size={14} />} onClick={doPreview}>
                {t('exp.refreshPreview')}
              </Button>
            </Group>
            {preview && preview.total > 0 ? (
              <Stack gap={4}>
                <SplitBar splits={preview.splits} total={preview.total} />
                <Text size="xs" c="dimmed">
                  {preview.total} {preview.unit}
                </Text>
              </Stack>
            ) : (
              preview && (
                <Text size="sm" c="orange">
                  0 {preview.unit}
                </Text>
              )
            )}
          </Stack>
        </Stepper.Step>

        {/* ── Step 3: augmentation ────────────────────────────── */}
        <Stepper.Step label={t('exp.step3')} description={t('exp.step3d')}>
          <Stack gap="sm" mt="md">
            <Switch
              label={t('exp.augment')}
              checked={augment}
              onChange={(e) => {
                setAugment(e.currentTarget.checked);
                setAugPreview(null);
                setPreview(null);
              }}
            />
            {augment && (
              <>
                <Checkbox.Group
                  value={selAugs}
                  onChange={(v) => {
                    setSelAugs(v);
                    setAugPreview(null);
                    setPreview(null);
                  }}
                >
                  <Group gap="xs">
                    {AUGS.map((a) => (
                      <Checkbox key={a.type} value={a.type} label={a.label} size="xs" />
                    ))}
                  </Group>
                </Checkbox.Group>
                <Group gap="sm" align="flex-end">
                  <SegmentedControl
                    size="xs"
                    value={augMode}
                    onChange={(v) => {
                      setAugMode(v as 'combinatorial' | 'sequential');
                      setAugPreview(null);
                      setPreview(null);
                    }}
                    data={[
                      { label: t('exp.augSeparate'), value: 'combinatorial' },
                      { label: t('exp.augCombined'), value: 'sequential' },
                    ]}
                  />
                  <NumberInput
                    size="xs"
                    w={130}
                    label={t('exp.copies')}
                    min={1}
                    max={10}
                    value={augCopies}
                    onChange={(v) => {
                      setAugCopies(Number(v) || 1);
                      setPreview(null);
                    }}
                  />
                </Group>
                <Text size="xs" c="dimmed">
                  {t('exp.augNote')}
                </Text>
                <Group gap="xs" align="center">
                  <Button
                    size="compact-xs"
                    variant="light"
                    leftSection={<IconPhoto size={14} />}
                    onClick={() => doAugPreview(0)}
                    loading={augBusy}
                    disabled={!selAugs.length}
                  >
                    {t('exp.augPreview')}
                  </Button>
                  {augPreview && augPreview.eligible_count > 1 && (
                    <Button
                      size="compact-xs"
                      variant="subtle"
                      leftSection={<IconRefresh size={14} />}
                      onClick={() => doAugPreview(sampleIdx + 1)}
                      loading={augBusy}
                    >
                      {t('exp.otherSample')}
                    </Button>
                  )}
                  {augPreview && (
                    <Text size="xs" c="dimmed">
                      {t('exp.sampleIdx', {
                        i: augPreview.sample_index + 1,
                        n: augPreview.eligible_count,
                      })}{' '}
                      · {augPreview.sample_key} ({augPreview.box_count})
                    </Text>
                  )}
                </Group>
                {!selAugs.length && (
                  <Text size="xs" c="orange">
                    {t('exp.noAugSelected')}
                  </Text>
                )}
                {augPreview && (
                  <SimpleGrid cols={3} spacing="xs" verticalSpacing="xs">
                    {augPreview.samples.map((s, i) => (
                      <Stack key={`${s.label}-${i}`} gap={2} align="center">
                        <Image
                          src={s.image}
                          radius="sm"
                          fit="contain"
                          h={110}
                          style={{
                            border:
                              s.label === 'original'
                                ? '2px solid var(--mantine-color-blue-5)'
                                : '1px solid var(--mantine-color-gray-3)',
                          }}
                        />
                        <Text
                          size="xs"
                          c={s.label === 'original' ? 'blue' : 'dimmed'}
                          ta="center"
                          lineClamp={1}
                        >
                          {s.label}
                        </Text>
                      </Stack>
                    ))}
                  </SimpleGrid>
                )}
              </>
            )}
          </Stack>
        </Stepper.Step>

        {/* ── Step 4: review & export ─────────────────────────── */}
        <Stepper.Step label={t('exp.step4')} description={t('exp.step4d')}>
          <Stack gap="sm" mt="md">
            <Text fw={600} size="sm">
              {t('exp.reviewTitle')}
            </Text>
            <Stack gap={6}>
              <Row label={t('exp.format')} value={datasetFormat} />
              <Row
                label={t('exp.dsType')}
                value={kind === 'detection' ? t('exp.detection') : t('exp.recognition')}
              />
              <Row
                label={t('exp.splitMode')}
                value={
                  splitMode === 'count'
                    ? `${trainCount} / ${validCount} / ${testCount}`
                    : `${train}% / ${valid}% / ${test}%`
                }
              />
              <Row label={t('exp.imageFormat')} value={format} />
              <Row
                label={t('exp.augment')}
                value={
                  augment && selAugs.length ? (
                    <Group gap={4} justify="flex-end">
                      {selAugs.map((a) => (
                        <Badge key={a} size="xs" variant="light">
                          {a}
                        </Badge>
                      ))}
                      <Badge size="xs" color="teal" variant="filled">
                        ×{augCopies} · {augMode === 'sequential' ? t('exp.augCombined') : t('exp.augSeparate')}
                      </Badge>
                    </Group>
                  ) : (
                    <Text size="sm" c="dimmed">
                      {t('exp.augOff')}
                    </Text>
                  )
                }
              />
            </Stack>
            <Divider />
            <Group gap="xs">
              <Button size="compact-xs" variant="light" leftSection={<IconRefresh size={14} />} onClick={doPreview}>
                {t('exp.refreshPreview')}
              </Button>
            </Group>
            {finalSplits && finalTotal > 0 && (
              <Stack gap={4}>
                <SplitBar splits={finalSplits} total={finalTotal} />
                <Text size="sm" fw={500} c="teal.7">
                  {t('exp.willGenerate', { n: finalTotal, unit: preview?.unit ?? '' })}
                </Text>
              </Stack>
            )}

            {busy && progress && (
              <div>
                <Progress
                  value={progress.total ? (progress.done / progress.total) * 100 : 0}
                  striped
                  animated
                />
                <Text size="xs" c="dimmed" ta="center" mt={4}>
                  {progress.done} / {progress.total}
                </Text>
              </div>
            )}

            {result && (
              <Alert
                color="green"
                title={t('exp.exportedTitle', { n: result.total, kind: result.kind })}
              >
                <Stack gap="xs">
                  <Text size="sm">
                    {Object.entries(result.splits)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(' · ')}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {t('exp.savedTo', {
                      dir: `${result.kind === 'detection' ? 'output_det' : 'output_rec'}/${result.folder}`,
                    })}
                  </Text>
                  <Button
                    component="a"
                    href={result.download_url}
                    leftSection={<IconDownload size={16} />}
                    variant="light"
                    size="xs"
                  >
                    {t('exp.download')}
                  </Button>
                </Stack>
              </Alert>
            )}
          </Stack>
        </Stepper.Step>
      </Stepper>

      <Divider mb="sm" />
      <Group justify="space-between">
        <Button
          variant="default"
          leftSection={<IconArrowLeft size={16} />}
          disabled={active === 0}
          onClick={() => goStep(active - 1)}
        >
          {t('exp.back')}
        </Button>
        {active < 3 ? (
          <Button
            rightSection={<IconArrowRight size={16} />}
            onClick={() => goStep(active + 1)}
            disabled={active === 1 && (splitInvalid || countInvalid)}
          >
            {t('exp.next')}
          </Button>
        ) : (
          <Button
            leftSection={<IconDownload size={16} />}
            onClick={run}
            loading={busy}
            disabled={splitInvalid || countInvalid}
          >
            {t('exp.export')}
          </Button>
        )}
      </Group>
    </Modal>
  );
}
