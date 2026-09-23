import { Switch, createTheme } from '@mantine/core';

// Mantine 8 and 9 changed defaults that would restyle the whole app: the
// corner radius went from sm (4px) to md (8px), and Switch gained an indicator
// in its thumb. Both are pinned to the look this UI was designed with; the
// light-colour change is handled on the provider in main.tsx.
export const theme = createTheme({
  primaryColor: 'indigo',
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans Thai", sans-serif',
  defaultRadius: 'sm',
  components: {
    Switch: Switch.extend({ defaultProps: { withThumbIndicator: false } }),
  },
});
