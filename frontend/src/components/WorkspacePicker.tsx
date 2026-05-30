import { useState } from 'react';
import {
  ActionIcon,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
  TextInput,
  Title,
  Badge,
  Divider,
  Loader,
  Center,
  Tooltip,
} from '@mantine/core';
import { Dropzone, IMAGE_MIME_TYPE } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import { IconFolder, IconPhoto, IconPlus, IconTrash } from '@tabler/icons-react';
import { api } from '../api/client';
import { queryClient } from '../api/queryClient';
import { useWorkspaces } from '../hooks/queries';
import { openWorkspace } from '../controller';
import { useT } from '../i18n';

export function WorkspacePicker() {
  const t = useT();
  const { data: workspaces, isLoading } = useWorkspaces();
  const [name, setName] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    if (!name.trim()) {
      notifications.show({ color: 'red', message: t('wp.enterName') });
      return;
    }
    setBusy(true);
    try {
      const { id } = await api.createWorkspace(name.trim());
      if (files.length) await api.uploadImages(id, files);
      await queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      await openWorkspace(id);
    } catch (e) {
      notifications.show({ color: 'red', title: t('wp.createFailed'), message: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const deleteWs = async (id: string, wsName: string) => {
    if (!window.confirm(t('confirm.delWs', { n: wsName }))) return;
    try {
      await api.deleteWorkspace(id);
      await queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    } catch (e) {
      notifications.show({ color: 'red', message: (e as Error).message });
    }
  };

  return (
    <Container size="sm" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>OCR Studio</Title>
          <Text c="dimmed" size="sm">
            {t('wp.subtitle')}
          </Text>
        </div>

        <Card withBorder radius="md" padding="lg">
          <Stack gap="sm">
            <Text fw={600}>
              <Group gap={6}>
                <IconPlus size={18} /> {t('wp.newWs')}
              </Group>
            </Text>
            <TextInput
              label={t('wp.name')}
              placeholder="e.g. drug-bag-batch-1"
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
            />
            <Dropzone
              onDrop={(dropped) => setFiles((prev) => [...prev, ...dropped])}
              accept={IMAGE_MIME_TYPE}
              multiple
            >
              <Group justify="center" gap="sm" mih={90} style={{ pointerEvents: 'none' }}>
                <IconPhoto size={32} opacity={0.6} />
                <div>
                  <Text size="sm">{t('wp.drop')}</Text>
                  <Text size="xs" c="dimmed">
                    {files.length ? t('wp.selectedN', { n: files.length }) : t('wp.formats')}
                  </Text>
                </div>
              </Group>
            </Dropzone>
            <Button loading={busy} onClick={create}>
              {t('wp.create')}
            </Button>
          </Stack>
        </Card>

        <Divider label={t('wp.existing')} labelPosition="center" />

        {isLoading ? (
          <Center py="md">
            <Loader size="sm" />
          </Center>
        ) : workspaces && workspaces.length ? (
          <Stack gap="xs">
            {workspaces.map((w) => (
              <Card
                key={w.id}
                withBorder
                radius="md"
                padding="sm"
                style={{ cursor: 'pointer' }}
                onClick={() => openWorkspace(w.id)}
              >
                <Group justify="space-between">
                  <Group gap="sm">
                    <IconFolder size={20} />
                    <div>
                      <Text fw={500}>{w.name}</Text>
                      <Text size="xs" c="dimmed">
                        {w.id}
                      </Text>
                    </div>
                  </Group>
                  <Group gap="xs">
                    <Badge variant="light">{w.current_version}</Badge>
                    <Tooltip label={t('wp.delete')}>
                      <ActionIcon
                        component="div"
                        variant="subtle"
                        color="red"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteWs(w.id, w.name);
                        }}
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Group>
              </Card>
            ))}
          </Stack>
        ) : (
          <Text c="dimmed" size="sm" ta="center">
            {t('wp.none')}
          </Text>
        )}
      </Stack>
    </Container>
  );
}
