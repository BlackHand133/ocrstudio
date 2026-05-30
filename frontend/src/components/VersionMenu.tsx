import { useState } from 'react';
import {
  ActionIcon,
  Button,
  Menu,
  Modal,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import { IconCheck, IconChevronDown, IconPlus, IconTrash } from '@tabler/icons-react';
import { api } from '../api/client';
import { queryClient } from '../api/queryClient';
import { useEditor } from '../store/editor';
import { reloadCurrentImage, saveCurrent, switchToVersion } from '../controller';
import { useT } from '../i18n';

export function VersionMenu({ workspaceId, current }: { workspaceId: string; current: string }) {
  const t = useT();
  const { data: versions } = useQuery({
    queryKey: ['versions', workspaceId],
    queryFn: () => api.listVersions(workspaceId),
  });
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['versions', workspaceId] });
    queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] });
    queryClient.invalidateQueries({ queryKey: ['images', workspaceId] });
  };

  const create = async () => {
    const n = name.trim();
    if (!n) return;
    setBusy(true);
    try {
      await saveCurrent().catch(() => undefined);
      await api.createVersion(workspaceId, n);
      invalidateAll();
      if (!useEditor.getState().dirty) await reloadCurrentImage();
      notifications.show({ color: 'green', message: t('ver.created', { n }) });
      setName('');
      close();
    } catch (e) {
      notifications.show({ color: 'red', title: t('wp.createFailed'), message: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (n: string) => {
    if (!window.confirm(t('confirm.delVersion', { n }))) return;
    try {
      await api.deleteVersion(workspaceId, n);
      invalidateAll();
      notifications.show({ message: t('ver.deleted', { n }) });
    } catch (e) {
      notifications.show({ color: 'red', message: (e as Error).message });
    }
  };

  const list = versions ?? [];

  return (
    <>
      <Modal opened={opened} onClose={close} title={t('ver.newTitle')} size="sm">
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            {t('ver.newDesc', { v: current })}
          </Text>
          <TextInput
            label={t('ver.name')}
            placeholder="e.g. v2"
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            onKeyDown={(e) => e.key === 'Enter' && create()}
          />
          <Button loading={busy} onClick={create}>
            {t('ver.create')}
          </Button>
        </Stack>
      </Modal>

      <Menu width={230} position="bottom-start" withinPortal>
        <Menu.Target>
          <Button size="xs" variant="light" rightSection={<IconChevronDown size={14} />}>
            {current}
          </Button>
        </Menu.Target>
        <Menu.Dropdown>
          <Menu.Label>{t('ver.versions')}</Menu.Label>
          {list.map((v) => (
            <Menu.Item
              key={v.name}
              leftSection={
                v.is_current ? <IconCheck size={14} /> : <span style={{ width: 14, display: 'inline-block' }} />
              }
              rightSection={
                !v.is_current && list.length > 1 ? (
                  <ActionIcon
                    component="div"
                    size="xs"
                    variant="subtle"
                    color="red"
                    onClick={(e) => {
                      e.stopPropagation();
                      remove(v.name);
                    }}
                  >
                    <IconTrash size={13} />
                  </ActionIcon>
                ) : null
              }
              onClick={() => {
                if (!v.is_current) switchToVersion(v.name);
              }}
            >
              {v.name}
            </Menu.Item>
          ))}
          <Menu.Divider />
          <Menu.Item leftSection={<IconPlus size={14} />} onClick={open}>
            {t('ver.new')}
          </Menu.Item>
        </Menu.Dropdown>
      </Menu>
    </>
  );
}
