import React from 'react';
import { createRoot } from 'react-dom/client';
import BasicSettings from './BasicSettings';

const rootEl = document.getElementById('root');
if (rootEl) {
  const root = createRoot(rootEl);
  root.render(<BasicSettings />);
}
