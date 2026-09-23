import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider, v8CssVariablesResolver } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClientProvider } from '@tanstack/react-query';

import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import '@mantine/dropzone/styles.css';
import './index.css';

import App from './App';
import { theme } from './theme';
import { queryClient } from './api/queryClient';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    {/* Mantine 9 made the "light" colours solid. The image-list and card
        highlights (--mantine-color-*-light) were tuned against the earlier
        translucent ones, so keep those. */}
    <MantineProvider
      theme={theme}
      defaultColorScheme="auto"
      cssVariablesResolver={v8CssVariablesResolver}
    >
      <QueryClientProvider client={queryClient}>
        <Notifications position="top-right" />
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
