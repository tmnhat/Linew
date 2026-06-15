import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

console.log('[Linew] Starting app...');

// Global error handler for uncaught errors
window.addEventListener('error', (event) => {
  console.error('[Linew] Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('[Linew] Unhandled rejection:', event.reason);
});

const rootEl = document.getElementById('root');
if (!rootEl) {
  console.error('[Linew] FATAL: #root element not found!');
} else {
  console.log('[Linew] #root found, creating React root...');
  const root = createRoot(rootEl);
  console.log('[Linew] Root created, rendering App...');
  root.render(<App />);
  console.log('[Linew] App render called');
}
