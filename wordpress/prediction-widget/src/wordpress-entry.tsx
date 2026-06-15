/* WordPress React Widget Entry Point */
/* This file is the entry point for the WordPress plugin */

import { createRoot } from 'react-dom/client';
import App from './App';

// Global config from WordPress
declare global {
    interface Window {
        linewConfig?: {
            apiUrl: string;
            defaultSymbol: string;
            symbols: Array<{ symbol: string; name: string; type: string }>;
            nonce?: string;
        };
    }
}

function initWidget() {
    // Find ALL containers that PHP renders
    const containers = document.querySelectorAll('.linew-homepage-widget');

    if (containers.length === 0) {
        console.log('[LinewPrediction] No containers found');
        return;
    }

    console.log('[LinewPrediction] Found', containers.length, 'container(s)');

    containers.forEach((container, index) => {
        // Check if already mounted
        const el = container as HTMLElement;
        if (el.dataset.linewMounted) {
            console.log(`[LinewPrediction] Container ${index} already mounted`);
            return;
        }

        console.log(`[LinewPrediction] Mounting React to container ${index}`);

        try {
            const root = createRoot(el);
            root.render(<App />);
            el.dataset.linewMounted = 'true';
            console.log(`[LinewPrediction] Successfully mounted to container ${index}`);
        } catch (err) {
            console.error(`[LinewPrediction] Failed to mount container ${index}:`, err);
        }
    });
}

// Initialize when DOM is ready
function onDOMReady() {
    // Small delay to ensure WordPress has finished rendering
    setTimeout(initWidget, 100);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onDOMReady);
} else {
    onDOMReady();
}

// Re-check periodically in case containers are added late
let checkCount = 0;
const checkInterval = setInterval(() => {
    checkCount++;
    initWidget();
    if (checkCount >= 10) {
        clearInterval(checkInterval);
    }
}, 500);
