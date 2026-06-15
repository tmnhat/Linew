/* WordPress React Widget Entry Point */
/* This file is loaded when React build is used instead of vanilla JS */

import { createRoot } from 'react-dom/client';
import PredictionWidget from './PredictionWidget';

const initReactWidget = () => {
    // Find the homepage widget container that PHP renders
    const containers = document.querySelectorAll('.linew-homepage-widget');

    containers.forEach((container) => {
        // Check if already mounted
        if ((container as HTMLElement).dataset?.reactMounted) return;

        const root = createRoot(container);
        root.render(<PredictionWidget />);
        (container as HTMLElement).dataset.reactMounted = 'true';
    });
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReactWidget);
} else {
    initReactWidget();
}

// Also try to mount if script loads after DOMContentLoaded
initReactWidget();
