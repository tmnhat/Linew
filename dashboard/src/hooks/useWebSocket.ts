import { useEffect, useRef, useCallback, useState } from 'react';
import { useToastStore } from '../store/toast';

export interface WebSocketMessage {
  type: string;
  data?: unknown;
  timestamp?: string;
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttempts = useRef(0);
  const { addToast } = useToastStore();
  const [isConnected, setIsConnected] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  const connect = useCallback(() => {
    // Skip WebSocket if already connected or too many attempts
    if (reconnectAttempts.current > 10) {
      console.log('WebSocket: Max reconnection attempts reached, giving up');
      setIsInitialized(true);
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use window.location.host to get current host, include /dashboard/ws/ path
    const wsUrl = `${protocol}//${window.location.host}/dashboard/ws/events`;

    try {
      console.log('WebSocket: Connecting to', wsUrl);
      wsRef.current = new WebSocket(wsUrl);

      // Set timeout for connection
      const timeout = setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CONNECTING) {
          console.log('WebSocket: Connection timeout, closing');
          wsRef.current.close();
        }
      }, 10000); // Increased timeout to 10s

      wsRef.current.onopen = () => {
        clearTimeout(timeout);
        console.log('WebSocket: Connected');
        setIsConnected(true);
        setIsInitialized(true);
        reconnectAttempts.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (e) {
          // Silently ignore parse errors
        }
      };

      wsRef.current.onclose = (event) => {
        clearTimeout(timeout);
        console.log('WebSocket: Disconnected', event.code, event.reason);
        setIsConnected(false);
        setIsInitialized(true); // Mark as initialized even on disconnect

        // Don't block app if WebSocket fails - it's not critical
        if (reconnectAttempts.current >= 3) {
          console.log('WebSocket: Stopping reconnection attempts - non-critical');
          return;
        }

        // Reconnect after delay (exponential backoff)
        const delay = Math.min(3000 * Math.pow(1.5, reconnectAttempts.current), 30000);
        reconnectAttempts.current++;
        console.log(`WebSocket: Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      wsRef.current.onerror = (_error) => {
        // Mark as initialized so app doesn't wait forever
        setIsInitialized(true);
      };
    } catch (e) {
      console.log('WebSocket: Failed to create connection:', e);
      setIsInitialized(true); // Don't block app
    }
  }, []);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'article_state_change':
        addToast({
          type: 'info',
          title: 'Article Updated',
          message: `Article moved to ${(message.data as { state: string })?.state}`,
        });
        break;
      case 'article_published':
        addToast({
          type: 'success',
          title: 'Article Published',
          message: 'New article published to WordPress',
        });
        break;
      case 'signals_fetched':
        addToast({
          type: 'info',
          title: 'Signals Fetched',
          message: `${(message.data as { articles_created: number })?.articles_created} new articles`,
        });
        break;
      case 'connected':
        console.log('WebSocket: Server confirmed connection');
        break;
    }
  }, [addToast]);

  useEffect(() => {
    // Start WebSocket connection but don't block app loading
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connect]);

  return { isConnected, isInitialized, reconnect: connect };
}
