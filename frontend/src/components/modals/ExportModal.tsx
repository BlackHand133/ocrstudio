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
import {
  AUG_DEFS,
  DET_ONLY,
  FORMATS,
  defaultAugParams,
} from './export/augmentationDefs';
import { SplitBar, SummaryRow } from './export/parts';
import { AugmentationPicker } from './export/AugmentationPicker';

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
  const [augParams, setAugParams] = useState<Record<string, Record<string, number>>>(defaultAugParams);
  const [augPreview, setAugPreview] = useState<AugPreview | null>(null);
  const [augBusy, setAugBusy] = useState(false);
  const [sampleIdx, setSampleIdx] = useState(0);
  const [previewScope, setPreviewScope] = useState<'selected' | 'all'>('selected');
  const [zoom, setZoom] = useState<{ label: string; image: string } | null>(null);

  // editing an effect's params invalidates both previews so counts/gallery refresh
  const clearPreviews = () => {
    setAugPreview(null);
    setPreview(null);
  };
  const setParam = (type: string, key: string, val: number) => {
    setAugParams((prev) => ({ ...prev, [type]: { ...prev[type], [key]: val } }));
    clearPreviews();
  };
  const toggleAug = (type: string, on: boolean) => {
    setSelAugs((prev) => (on ? [...prev, type] : prev.filter((x) => x !== type)));
    clearPreviews();
  };
  const resetAugParams = () => {
    setAugParams(defaultAugParams());
    clearPreviews();
  };

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
      params.augmentations = AUG_DEFS.filter((d) => selAugs.includes(d.type)).map((d) => ({
        type: d.type,
        params: { ...(d.fixed ?? {}), ...augParams[d.type] },
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

  // Build the preview request: "selected" mirrors the export choices; "all"
  // shows every available effect (catalog view) so the user can compare them.
  const buildAugPreviewParams = (scope: 'selected' | 'all'): ExportParams => {
    const defs = scope === 'all' ? AUG_DEFS : AUG_DEFS.filter((d) => selAugs.includes(d.type));
    return {
      ...buildParams(),
      augment: true,
      aug_mode: scope === 'all' ? 'combinatorial' : augMode,
      augmentations: defs.map((d) => ({
        type: d.type,
        params: { ...(d.fixed ?? {}), ...augParams[d.type] },
      })),
      aug_targets: ['train'],
    };
  };

  const doAugPreview = async (idx = 0, scope: 'selected' | 'all' = previewScope) => {
    if (!workspaceId) return;
    if (scope === 'selected' && !selAugs.length) return;
    setAugBusy(true);
    try {
      await saveCurrent();
      const ap = await api.previewAugment(workspaceId, buildAugPreviewParams(scope), idx);
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
    if (next === 2 && augment && !augPreview && (previewScope === 'all' || selAugs.length))
      void doAugPreview(0);
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
    <Modal opened={opened} onClose={close} title={t('exp.title')} size="64rem">
      {/* full-size preview lightbox (click a sample to enlarge) */}
      <Modal
        opened={!!zoom}
        onClose={() => setZoom(null)}
        title={zoom?.label}
        size="auto"
        centered
        zIndex={400}
      >
        {zoom && (
          <Image src={zoom.image} alt={zoom.label} fit="contain" mah="78vh" maw="86vw" />
        )}
      </Modal>

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
                <AugmentationPicker
                  selected={selAugs}
                  params={augParams}
                  onToggle={toggleAug}
                  onParamChange={setParam}
                  t={t}
                />
                <Group gap="sm" align="flex-end">
                  <SegmentedControl
                    size="xs"
                    value={augMode}
                    onChange={(v) => {
                      setAugMode(v as 'combinatorial' | 'sequential');
                      clearPreviews();
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
                  <Button size="compact-xs" variant="subtle" color="gray" onClick={resetAugParams}>
                    {t('exp.resetParams')}
                  </Button>
                </Group>
                <Text size="xs" c="dimmed">
                  {t('exp.augNote')}
                </Text>
                <Divider label={t('exp.augPreview')} labelPosition="left" />
                <Group gap="xs" align="center">
                  <SegmentedControl
                    size="xs"
                    value={previewScope}
                    onChange={(v) => {
                      const sc = v as 'selected' | 'all';
                      setPreviewScope(sc);
                      void doAugPreview(0, sc);
                    }}
                    data={[
                      { label: t('exp.previewSelected'), value: 'selected' },
                      { label: t('exp.previewAll'), value: 'all' },
                    ]}
                  />
                  <Button
                    size="compact-xs"
                    variant="light"
                    leftSection={<IconPhoto size={14} />}
                    onClick={() => doAugPreview(0, previewScope)}
                    loading={augBusy}
                    disabled={previewScope === 'selected' && !selAugs.length}
                  >
                    {t('exp.augPreview')}
                  </Button>
                  {augPreview && augPreview.eligible_count > 1 && (
                    <Button
                      size="compact-xs"
                      variant="subtle"
                      leftSection={<IconRefresh size={14} />}
                      onClick={() => doAugPreview(sampleIdx + 1, previewScope)}
                      loading={augBusy}
                    >
                      {t('exp.otherSample')}
                    </Button>
                  )}
                </Group>
                {augPreview && (
                  <Text size="xs" c="dimmed">
                    {t('exp.sampleIdx', {
                      i: augPreview.sample_index + 1,
                      n: augPreview.eligible_count,
                    })}{' '}
                    · {augPreview.sample_key} ({augPreview.box_count}) · {t('exp.clickZoom')}
                  </Text>
                )}
                {previewScope === 'selected' && !selAugs.length && (
                  <Text size="xs" c="orange">
                    {t('exp.noAugSelected')}
                  </Text>
                )}
                {augPreview && (
                  <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="sm" verticalSpacing="sm">
                    {augPreview.samples.map((s, i) => (
                      <Stack key={`${s.label}-${i}`} gap={4} align="center">
                        <Image
                          src={s.image}
                          alt={s.label}
                          radius="sm"
                          fit="contain"
                          h={170}
                          onClick={() => setZoom(s)}
                          style={{
                            cursor: 'zoom-in',
                            background: 'var(--mantine-color-gray-1)',
                            border:
                              s.label === 'original'
                                ? '2px solid var(--mantine-color-blue-5)'
                                : '1px solid var(--mantine-color-gray-3)',
                          }}
                        />
                        <Text
                          size="sm"
                          fw={s.label === 'original' ? 600 : 400}
                          c={s.label === 'original' ? 'blue' : undefined}
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
              <SummaryRow label={t('exp.format')} value={datasetFormat} />
              <SummaryRow
                label={t('exp.dsType')}
                value={kind === 'detection' ? t('exp.detection') : t('exp.recognition')}
              />
              <SummaryRow
                label={t('exp.splitMode')}
                value={
                  splitMode === 'count'
                    ? `${trainCount} / ${validCount} / ${testCount}`
                    : `${train}% / ${valid}% / ${test}%`
                }
              />
              <SummaryRow label={t('exp.imageFormat')} value={format} />
              <SummaryRow
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
