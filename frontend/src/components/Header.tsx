import {
  ActionIcon,
  Button,
  Group,
  SegmentedControl,
  Select,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useDisclosure } from '@mantine/hooks';
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconDeviceFloppy,
  IconFileExport,
  IconLogout,
  IconMoon,
  IconSettings,
  IconSun,
} from '@tabler/icons-react';
import { useEditor } from '../store/editor';
import { ExportModal } from './modals/ExportModal';
import { SettingsModal } from './modals/SettingsModal';
import { VersionMenu } from './VersionMenu';
import { useConfig, useWorkspace } from '../hooks/queries';
import { api } from '../api/client';
import { queryClient } from '../api/queryClient';
import { saveCurrent } from '../controller';
import { useI18n, useT } from '../i18n';

export function Header() {
  const t = useT();
  const lang = useI18n((s) => s.lang);
  const setLang = useI18n((s) => s.setLang);
  const { setColorScheme } = useMantineColorScheme();
  const computed = useComputedColorScheme('light', { getInitialValueInEffect: true });

  const workspaceId = useEditor((s) => s.workspaceId);
  const dirty = useEditor((s) => s.dirty);
  const canUndo = useEditor((s) => s.past.length > 0);
  const canRedo = useEditor((s) => s.future.length > 0);
  const undo = useEditor((s) => s.undo);
  const redo = useEditor((s) => s.redo);
  const setWorkspace = useEditor((s) => s.setWorkspace);

  const { data: ws } = useWorkspace(workspaceId);
  const { data: config } = useConfig();
  const [exportOpened, { open: openExport, close: closeExport }] = useDisclosure(false);
  const [settingsOpened, { open: openSettings, close: closeSettings }] = useDisclosure(false);

  const onSave = async () => {
    try {
      await saveCurrent();
      notifications.show({ color: 'green', message: t('common.saved'), autoClose: 1200 });
    } catch (e) {
      notifications.show({ color: 'red', title: t('common.saveFailed'), message: (e as Error).message });
    }
  };

  const onSwitch = async () => {
    try {
      await saveCurrent();
    } catch {
      /* ignore */
    }
    setWorkspace(null);
  };

  const onProfile = async (value: string | null) => {
    if (!value) return;
    try {
      await api.setProfile(value);
      queryClient.invalidateQueries({ queryKey: ['config'] });
    } catch (e) {
      notifications.show({ color: 'red', message: (e as Error).message });
    }
  };

  return (
    <>
      <ExportModal opened={exportOpened} onClose={closeExport} />
      <SettingsModal opened={settingsOpened} onClose={closeSettings} />
      <Group h="100%" px="md" justify="space-between" wrap="nowrap">
        <Group gap="sm" wrap="nowrap">
          <Text fw={700}>OCR Studio</Text>
          {ws && (
            <>
              <Text>·</Text>
              <Text fw={500}>{ws.name}</Text>
              <VersionMenu workspaceId={workspaceId!} current={ws.current_version} />
              <Text size="xs" c="dimmed" visibleFrom="sm">
                {t('hdr.annotated', { a: ws.annotated_count, b: ws.image_count })}
              </Text>
            </>
          )}
        </Group>

        <Group gap="xs" wrap="nowrap">
          <SegmentedControl
            size="xs"
            value={lang}
            onChange={(v) => setLang(v as 'en' | 'th')}
            data={[
              { label: 'EN', value: 'en' },
              { label: 'ไทย', value: 'th' },
            ]}
          />
          <Tooltip label={t('hdr.theme')}>
            <ActionIcon
              variant="default"
              onClick={() => setColorScheme(computed === 'dark' ? 'light' : 'dark')}
            >
              {computed === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
          </Tooltip>

          <Tooltip label={t('hdr.undo')}>
            <ActionIcon variant="default" disabled={!canUndo} onClick={undo}>
              <IconArrowBackUp size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label={t('hdr.redo')}>
            <ActionIcon variant="default" disabled={!canRedo} onClick={redo}>
              <IconArrowForwardUp size={18} />
            </ActionIcon>
          </Tooltip>

          {config && (
            <Select
              size="xs"
              w={100}
              data={config.profiles}
              value={config.current_profile}
              onChange={onProfile}
              allowDeselect={false}
              aria-label="OCR profile"
              visibleFrom="sm"
            />
          )}

          <Button
            size="xs"
            variant="default"
            leftSection={<IconFileExport size={16} />}
            onClick={openExport}
          >
            {t('hdr.export')}
          </Button>

          <Button
            size="xs"
            leftSection={<IconDeviceFloppy size={16} />}
            variant={dirty ? 'filled' : 'default'}
            onClick={onSave}
          >
            {dirty ? t('hdr.saveDirty') : t('hdr.saved')}
          </Button>

          <Tooltip label={t('hdr.settings')}>
            <ActionIcon variant="default" onClick={openSettings}>
              <IconSettings size={18} />
            </ActionIcon>
          </Tooltip>

          <Tooltip label={t('hdr.switch')}>
            <ActionIcon variant="default" onClick={onSwitch}>
              <IconLogout size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>
    </>
  );
}
