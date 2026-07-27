import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Modal,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { IconAlertTriangle, IconWand } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { api } from '../../api/client';
import { useConfig, useEngineStatus } from '../../hooks/queries';
import { useT } from '../../i18n';
import {
  buildVersionOptions,
  versionSupportsLang,
  versionsForLang,
} from '../../lib/ocrVersions';

/**
 * Detection settings tuned for scripts that stack marks above and below the
 * base glyph. Thai tone marks are 1-2px thick, so the two things that lose them
 * are a box that hugs the consonant body and a downscale before detection.
 */
const THAI_PRESET = {
  text_det_unclip_ratio: 2.2,
  text_det_box_thresh: 0.5,
  max_image_size: 0,
} as const;

const DEFAULT_TUNING = {
  text_det_unclip_ratio: 1.5,
  text_det_box_thresh: 0.7,
  max_image_size: 2500,
} as const;

export function SettingsModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const t = useT();
  const { data: config } = useConfig();
  const { data: engine } = useEngineStatus(opened);
  const [profile, setProfile] = useState<string | null>(null);
  const [mode, setMode] = useState<'official' | 'custom'>('official');
  const [lang, setLang] = useState('th');
  const [ocrVersion, setOcrVersion] = useState<string | null>(null);
  const [detDir, setDetDir] = useState('');
  const [recDir, setRecDir] = useState('');
  const [box, setBox] = useState<number>(DEFAULT_TUNING.text_det_box_thresh);
  const [unclip, setUnclip] = useState<number>(DEFAULT_TUNING.text_det_unclip_ratio);
  const [maxImageSize, setMaxImageSize] = useState<number>(DEFAULT_TUNING.max_image_size);
  const [orient, setOrient] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (config && !profile) setProfile(config.current_profile);
  }, [config, profile]);

  useEffect(() => {
    if (!opened || !profile) return;
    api
      .getProfileParams(profile)
      .then(({ params }) => {
        const det = (params.text_detection_model_dir as string) || '';
        const rec = (params.text_recognition_model_dir as string) || '';
        setLang(params.lang ? String(params.lang) : 'th');
        setOcrVersion(params.ocr_version ? String(params.ocr_version) : null);
        setDetDir(det);
        setRecDir(rec);
        setMode(det || rec ? 'custom' : 'official');
        if (params.text_det_box_thresh != null) setBox(Number(params.text_det_box_thresh));
        if (params.text_det_unclip_ratio != null) setUnclip(Number(params.text_det_unclip_ratio));
        setMaxImageSize(
          params.max_image_size != null
            ? Number(params.max_image_size)
            : DEFAULT_TUNING.max_image_size,
        );
        setOrient(Boolean(params.use_textline_orientation));
      })
      .catch(() => undefined);
  }, [opened, profile]);

  const versionLanguages = config?.version_languages;
  const versions = useMemo(() => config?.ocr_versions ?? [], [config?.ocr_versions]);

  const versionOptions = useMemo(
    () =>
      buildVersionOptions(versionLanguages, versions, lang, (version, code) =>
        t('set.versionUnsupported', { version, lang: code }),
      ),
    [versionLanguages, versions, lang, t],
  );

  const firstSupportedVersion = useMemo(
    () => versionsForLang(versionLanguages, versions, lang)[0],
    [versionLanguages, versions, lang],
  );

  // Changing the language can strip the model out from under the chosen
  // version. Drop back to "engine default" rather than saving a dead pair.
  useEffect(() => {
    if (ocrVersion && !versionSupportsLang(versionLanguages, ocrVersion, lang)) {
      setOcrVersion(null);
    }
  }, [lang, versionLanguages, ocrVersion]);

  const applyPreset = (preset: typeof THAI_PRESET | typeof DEFAULT_TUNING) => {
    setUnclip(preset.text_det_unclip_ratio);
    setBox(preset.text_det_box_thresh);
    setMaxImageSize(preset.max_image_size);
    notifications.show({ color: 'blue', message: t('set.presetApplied') });
  };

  const save = async () => {
    if (!profile) return;
    setBusy(true);
    try {
      const common = {
        lang,
        text_det_box_thresh: box,
        text_det_unclip_ratio: unclip,
        max_image_size: maxImageSize,
        use_textline_orientation: orient,
      };
      const payload =
        mode === 'official'
          ? {
              ...common,
              ocr_version: ocrVersion || null,
              text_detection_model_dir: null,
              text_recognition_model_dir: null,
              text_detection_model_name: null,
              text_recognition_model_name: null,
            }
          : {
              ...common,
              ocr_version: null,
              text_detection_model_dir: detDir || null,
              text_recognition_model_dir: recDir || null,
            };
      await api.updateProfileParams(profile, payload);
      notifications.show({ color: 'green', message: t('set.savedToast') });
      onClose();
    } catch (e) {
      notifications.show({
        color: 'red',
        title: t('common.saveFailed'),
        message: (e as Error).message,
      });
    } finally {
      setBusy(false);
    }
  };

  const engineWarnings = engine?.warnings ?? [];
  const shrinksImages = maxImageSize > 0 && maxImageSize < 1600;

  return (
    <Modal opened={opened} onClose={onClose} title={t('set.title')} size="md">
      <Stack gap="sm">
        {engine && (
          <Group gap="xs" wrap="wrap" aria-live="polite">
            <Text size="sm" fw={500}>
              {t('set.engine')}
            </Text>
            <Badge color={engine.loaded ? 'green' : 'gray'} variant="light">
              {engine.loaded ? t('set.engineLoaded') : t('set.engineIdle')}
            </Badge>
            <Text size="xs" c="dimmed">
              {engine.engine} {engine.engine_version}
              {engine.loaded && engine.ocr_version ? ` · ${engine.ocr_version}` : ''}
              {engine.loaded && engine.device ? ` · ${engine.device}` : ''}
            </Text>
            {!engine.loaded && (
              <Text size="xs" c="dimmed">
                {t('set.engineIdleHint')}
              </Text>
            )}
          </Group>
        )}

        {engineWarnings.length > 0 && (
          <Alert
            variant="light"
            color="yellow"
            icon={<IconAlertTriangle size={16} />}
            title={t('set.engineWarnings')}
          >
            <Stack gap={2}>
              {engineWarnings.map((w) => (
                <Text key={w} size="xs">
                  {w}
                </Text>
              ))}
            </Stack>
          </Alert>
        )}

        <Select
          label={t('set.profile')}
          data={config?.profiles ?? []}
          value={profile}
          onChange={setProfile}
          allowDeselect={false}
        />

        <div>
          <Text size="sm" fw={500} mb={4} id="model-source-label">
            {t('set.modelSource')}
          </Text>
          <SegmentedControl
            fullWidth
            aria-labelledby="model-source-label"
            value={mode}
            onChange={(v) => setMode(v as 'official' | 'custom')}
            data={[
              { label: t('set.official'), value: 'official' },
              { label: t('set.custom'), value: 'custom' },
            ]}
          />
        </div>

        {mode === 'official' ? (
          <>
            <Select
              label={t('set.language')}
              data={config?.languages ?? []}
              value={lang}
              onChange={(v) => v && setLang(v)}
              searchable
            />
            <Select
              label={t('set.version')}
              placeholder={t('set.versionAuto')}
              data={versionOptions}
              value={ocrVersion}
              onChange={setOcrVersion}
              clearable
              description={
                firstSupportedVersion && ocrVersion == null
                  ? t('set.versionRecommended', { version: firstSupportedVersion, lang })
                  : undefined
              }
            />
          </>
        ) : (
          <>
            <TextInput
              label={t('set.detDir')}
              placeholder="models/det/my_det"
              value={detDir}
              onChange={(e) => setDetDir(e.currentTarget.value)}
            />
            <TextInput
              label={t('set.recDir')}
              placeholder="models/rec/my_rec"
              value={recDir}
              onChange={(e) => setRecDir(e.currentTarget.value)}
            />
            <Select
              label={t('set.recLang')}
              data={config?.languages ?? []}
              value={lang}
              onChange={(v) => v && setLang(v)}
              searchable
            />
            <Text size="xs" c="dimmed">
              {t('set.customNote')}
            </Text>
          </>
        )}

        <Divider label={t('set.presets')} labelPosition="center" />
        <Group gap="xs">
          <Button
            size="xs"
            variant="light"
            leftSection={<IconWand size={14} />}
            onClick={() => applyPreset(THAI_PRESET)}
          >
            {t('set.presetThai')}
          </Button>
          <Button size="xs" variant="subtle" onClick={() => applyPreset(DEFAULT_TUNING)}>
            {t('set.presetDefaults')}
          </Button>
        </Group>
        <Text size="xs" c="dimmed">
          {t('set.presetThaiDesc')}
        </Text>

        <Divider label={t('set.detTuning')} labelPosition="center" />
        <NumberInput
          label={t('set.boxThresh')}
          description="text_det_box_thresh (0–1)"
          min={0}
          max={1}
          step={0.05}
          decimalScale={2}
          value={box}
          onChange={(v) => setBox(Number(v) || 0)}
        />
        <NumberInput
          label={t('set.unclip')}
          description="text_det_unclip_ratio (1–5)"
          min={1}
          max={5}
          step={0.1}
          decimalScale={2}
          value={unclip}
          onChange={(v) => setUnclip(Number(v) || 1)}
        />
        <Switch
          label={t('set.textline')}
          checked={orient}
          onChange={(e) => setOrient(e.currentTarget.checked)}
        />

        <Divider label={t('set.preprocess')} labelPosition="center" />
        <NumberInput
          label={t('set.maxImageSize')}
          description={t('set.maxImageSizeDesc')}
          min={0}
          max={10000}
          step={100}
          value={maxImageSize}
          onChange={(v) => setMaxImageSize(Math.max(0, Number(v) || 0))}
          error={shrinksImages ? t('set.maxImageSizeWarn') : undefined}
        />

        <Button loading={busy} onClick={save}>
          {t('set.save')}
        </Button>
        <Text size="xs" c="dimmed">
          {t('set.applyNote')}
        </Text>
      </Stack>
    </Modal>
  );
}
