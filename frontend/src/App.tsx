import { AppShell } from '@mantine/core';
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
  useShortcuts();
  useAutosave();

  if (!workspaceId) {
    return <WorkspacePicker />;
  }

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 300, breakpoint: 'sm' }}
      aside={{ width: 360, breakpoint: 'md' }}
      padding={0}
    >
      <AppShell.Header>
        <Header />
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
