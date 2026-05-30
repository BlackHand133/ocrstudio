import { useState } from 'react';
import { Button, Group, Modal, Stack, Text } from '@mantine/core';
import { Dropzone, IMAGE_MIME_TYPE } from '@mantine/dropzone';
import { IconPhoto } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { api } from '../../api/client';
import { queryClient } from '../../api/queryClient';
import { reloadCurrentImage } from '../../controller';
import { useT } from '../../i18n';

export function RelinkModal({
  workspaceId,
  missing,
  opened,
  onClose,
}: {
  workspaceId: string;
  missing: string[];
  opened: boolean;
  onClose: () => void;
}) {
  const t = useT();
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);

  const upload = async () => {
    if (!files.length) return;
    setBusy(true);
    try {
      const res = await api.uploadImages(workspaceId, files);
      await queryClient.invalidateQueries({ queryKey: ['images', workspaceId] });
      await queryClient.invalidateQueries({ queryKey: ['missing', workspaceId] });
      await queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] });
      await reloadCurrentImage().catch(() => undefined);
      notifications.show({ color: 'green', message: res.message || 'Uploaded' });
      setFiles([]);
      onClose();
    } catch (e) {
      notifications.show({ color: 'red', title: 'Upload failed', message: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={t('relink.title')} size="md">
      <Stack gap="sm">
        <Text size="sm">{t('relink.desc', { n: missing.length })}</Text>
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
        {missing.length > 0 && (
          <Text size="xs" c="dimmed">
            Missing: {missing.slice(0, 6).join(', ')}
            {missing.length > 6 ? ` +${missing.length - 6} more` : ''}
          </Text>
        )}
        <Button loading={busy} disabled={!files.length} onClick={upload}>
          {t('relink.upload')}
        </Button>
      </Stack>
    </Modal>
  );
}
