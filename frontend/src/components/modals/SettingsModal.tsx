import { useEffect, useState } from 'react';
import {
  Button,
  Divider,
  Modal,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { api } from '../../api/client';
import { useConfig } from '../../hooks/queries';
import { useT } from '../../i18n';

export function SettingsModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const t = useT();
  const { data: config } = useConfig();
  const [profile, setProfile] = useState<string | null>(null);
  const [mode, setMode] = useState<'official' | 'custom'>('official');
  const [lang, setLang] = useState('th');
  const [ocrVersion, setOcrVersion] = useState<string | null>(null);
  const [detDir, setDetDir] = useState('');
  const [recDir, setRecDir] = useState('');
  const [box, setBox] = useState(0.6);
  const [unclip, setUnclip] = useState(1.5);
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
        if (params.det_db_box_thresh != null) setBox(Number(params.det_db_box_thresh));
        if (params.det_db_unclip_ratio != null) setUnclip(Number(params.det_db_unclip_ratio));
        setOrient(Boolean(params.use_textline_orientation));
      })
      .catch(() => undefined);
  }, [opened, profile]);

  const save = async () => {
    if (!profile) return;
    setBusy(true);
    try {
      const common = {
        lang,
        det_db_box_thresh: box,
        det_db_unclip_ratio: unclip,
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
      notifications.show({ color: 'red', title: t('common.saveFailed'), message: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={t('set.title')} size="md">
      <Stack gap="sm">
        <Select
          label={t('set.profile')}
          data={config?.profiles ?? []}
          value={profile}
          onChange={setProfile}
          allowDeselect={false}
        />

        <div>
          <Text size="sm" fw={500} mb={4}>
            {t('set.modelSource')}
          </Text>
          <SegmentedControl
            fullWidth
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
              placeholder={t('set.versionPh')}
              data={['PP-OCRv5', 'PP-OCRv4', 'PP-OCRv3']}
              value={ocrVersion}
              onChange={setOcrVersion}
              clearable
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

        <Divider label={t('set.detTuning')} labelPosition="center" />
        <NumberInput
          label={t('set.boxThresh')}
          description="det_db_box_thresh (0–1)"
          min={0}
          max={1}
          step={0.05}
          decimalScale={2}
          value={box}
          onChange={(v) => setBox(Number(v) || 0)}
        />
        <NumberInput
          label={t('set.unclip')}
          description="det_db_unclip_ratio (1–5)"
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
