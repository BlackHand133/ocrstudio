import { useEffect } from 'react';
import { AppShell } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useEditor } from './store/editor';
import { useShortcuts } from './hooks/useShortcuts';
import { useAutosave } from './hooks/useAutosave';
import { WorkspacePicker } from './components/WorkspacePicker';
import { Header } from './components/Header';
import { ImageList } from './components/ImageList';
import { CanvasStage } from './components/CanvasStage';
import { AnnotationPanel } from './components/AnnotationPanel';

export default function App() {
  const workspaceId = useEditor((s) => s.workspaceId);
  // The image list and annotation panel are 660px of chrome combined. On a
  // narrow screen they have to collapse behind toggles or the canvas — the
  // actual work surface — is left with nothing.
  const [navOpened, { toggle: toggleNav, close: closeNav }] = useDisclosure(false);
  const [asideOpened, { toggle: toggleAside }] = useDisclosure(false);
  const imageKey = useEditor((s) => s.imageKey);
  useShortcuts();
  useAutosave();

  // On mobile the list is an overlay sitting on top of the canvas. Close it once
  // an image is actually chosen — but only then, so ticking export checkboxes
  // does not dismiss the list out from under the user.
  useEffect(() => {
    if (imageKey) closeNav();
  }, [imageKey, closeNav]);

  if (!workspaceId) {
    return <WorkspacePicker />;
  }

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 300, breakpoint: 'sm', collapsed: { mobile: !navOpened } }}
      aside={{ width: 360, breakpoint: 'md', collapsed: { mobile: !asideOpened } }}
      padding={0}
    >
      <AppShell.Header>
        <Header
          navOpened={navOpened}
          asideOpened={asideOpened}
          onToggleNav={toggleNav}
          onToggleAside={toggleAside}
        />
      </AppShell.Header>
      <AppShell.Navbar>
        <ImageList />
      </AppShell.Navbar>
      <AppShell.Main style={{ height: '100dvh' }}>
        <CanvasStage />
      </AppShell.Main>
      <AppShell.Aside>
        <AnnotationPanel />
      </AppShell.Aside>
    </AppShell>
  );
}
