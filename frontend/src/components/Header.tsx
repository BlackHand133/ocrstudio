import {
  ActionIcon,
  Box,
  Burger,
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

interface HeaderProps {
  /** Image-list drawer state — only rendered below the navbar breakpoint. */
  navOpened: boolean;
  /** Annotation-panel drawer state — only rendered below the aside breakpoint. */
  asideOpened: boolean;
  onToggleNav: () => void;
  onToggleAside: () => void;
}

export function Header({ navOpened, asideOpened, onToggleNav, onToggleAside }: HeaderProps) {
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
      {/* gap keeps the two sides from touching: space-between alone lets the
          truncated workspace name butt right up against the first action. */}
      <Group h="100%" px="md" gap="sm" justify="space-between" wrap="nowrap">
        {/* flex:1 + minWidth:0 so this side absorbs the leftover width and
            truncates inside it; the action group opposite must not shrink or it
            starts overlapping this one. overflow:hidden is the backstop — a
            nowrap child otherwise renders past this box and lands on top of
            the buttons. */}
        <Group gap="sm" wrap="nowrap" style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
          <Burger
            opened={navOpened}
            onClick={onToggleNav}
            hiddenFrom="sm"
            size="sm"
            aria-label={t('hdr.toggleList')}
          />
          {/* The product name is the first thing to go when space is tight —
              the workspace name is what tells the user where they are. Held
              back to md: at tablet width it wraps to two lines and squeezes the
              workspace name, and nowrap alone just moves the squeeze. */}
          <Text fw={700} visibleFrom="md" style={{ whiteSpace: 'nowrap' }}>
            OCR Studio
          </Text>
          {ws && (
            <>
              <Text visibleFrom="md">·</Text>
              {/* miw, not just minWidth:0 — the nowrap action group on the right
                  wins the flex negotiation and squeezes this to 0px on a phone,
                  leaving a version chip with nothing to attach it to. A floor
                  makes it truncate instead of vanishing. */}
              <Text fw={500} truncate="end" miw={64} style={{ flexShrink: 1 }}>
                {ws.name}
              </Text>
              {/* No room for it beside the name at phone widths, and a clipped
                  dropdown reads as broken. Version switching is a desktop task. */}
              <Box visibleFrom="sm">
                <VersionMenu workspaceId={workspaceId!} current={ws.current_version} />
              </Box>
              <Text size="xs" c="dimmed" visibleFrom="md">
                {t('hdr.annotated', { a: ws.annotated_count, b: ws.image_count })}
              </Text>
            </>
          )}
        </Group>

        <Group gap="xs" wrap="nowrap" style={{ flexShrink: 0 }}>
          <SegmentedControl
            size="xs"
            aria-label={t('hdr.uiLanguage')}
            visibleFrom="sm"
            value={lang}
            onChange={(v) => setLang(v as 'en' | 'th')}
            data={[
              { label: 'EN', value: 'en' },
              { label: 'ไทย', value: 'th' },
            ]}
          />
          {/* The two-option control does not fit on a phone, but hiding it
              outright strands someone who opens the app on one — this is a
              Thai-first tool and the default is English. Toggle instead,
              labelled with the language it switches to. */}
          <Tooltip label={t('hdr.uiLanguage')}>
            <ActionIcon
              variant="default"
              hiddenFrom="sm"
              aria-label={t('hdr.uiLanguage')}
              onClick={() => setLang(lang === 'en' ? 'th' : 'en')}
            >
              <Text size="xs" fw={700}>
                {lang === 'en' ? 'ไทย' : 'EN'}
              </Text>
            </ActionIcon>
          </Tooltip>
          {/* Tooltips are hover-only affordances — icon-only buttons still need
              an aria-label or they are announced as just "button". */}
          <Tooltip label={t('hdr.theme')}>
            <ActionIcon
              variant="default"
              aria-label={t('hdr.theme')}
              onClick={() => setColorScheme(computed === 'dark' ? 'light' : 'dark')}
            >
              {computed === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
          </Tooltip>

          {/* Dropped below sm: nine actions plus two burgers leave the workspace
              name no room at 390px, and it overflows into them. Undo/redo are
              the most mouse-bound of the set — this is not a phone annotation
              tool — so they are what gives way. */}
          <Tooltip label={t('hdr.undo')}>
            <ActionIcon
              variant="default"
              visibleFrom="sm"
              aria-label={t('hdr.undo')}
              disabled={!canUndo}
              onClick={undo}
            >
              <IconArrowBackUp size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label={t('hdr.redo')}>
            <ActionIcon
              variant="default"
              visibleFrom="sm"
              aria-label={t('hdr.redo')}
              disabled={!canRedo}
              onClick={redo}
            >
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

          {/* Below sm the labelled buttons become icon-only so the row still
              fits; the aria-label carries the meaning either way. */}
          <Button
            size="xs"
            variant="default"
            leftSection={<IconFileExport size={16} />}
            onClick={openExport}
            visibleFrom="sm"
          >
            {t('hdr.export')}
          </Button>
          <Tooltip label={t('hdr.export')}>
            <ActionIcon
              variant="default"
              aria-label={t('hdr.export')}
              onClick={openExport}
              hiddenFrom="sm"
            >
              <IconFileExport size={18} />
            </ActionIcon>
          </Tooltip>

          <Button
            size="xs"
            leftSection={<IconDeviceFloppy size={16} />}
            variant={dirty ? 'filled' : 'default'}
            onClick={onSave}
            visibleFrom="sm"
          >
            {dirty ? t('hdr.saveDirty') : t('hdr.saved')}
          </Button>
          <Tooltip label={dirty ? t('hdr.saveDirty') : t('hdr.saved')}>
            <ActionIcon
              variant={dirty ? 'filled' : 'default'}
              aria-label={dirty ? t('hdr.saveDirty') : t('hdr.saved')}
              onClick={onSave}
              hiddenFrom="sm"
            >
              <IconDeviceFloppy size={18} />
            </ActionIcon>
          </Tooltip>

          <Tooltip label={t('hdr.settings')}>
            <ActionIcon variant="default" aria-label={t('hdr.settings')} onClick={openSettings}>
              <IconSettings size={18} />
            </ActionIcon>
          </Tooltip>

          <Tooltip label={t('hdr.switch')}>
            <ActionIcon variant="default" aria-label={t('hdr.switch')} onClick={onSwitch}>
              <IconLogout size={18} />
            </ActionIcon>
          </Tooltip>

          <Burger
            opened={asideOpened}
            onClick={onToggleAside}
            hiddenFrom="md"
            size="sm"
            aria-label={t('hdr.togglePanel')}
          />
        </Group>
      </Group>
    </>
  );
}
