/**
 * WebSocket Client for Real-time CRM Events
 * Handles connection, authentication, reconnection, and event streaming
 * Streams: /crm/ws/metrics (analytics), /crm/ws/steps (journey step logs)
 */

import React from 'react';

const WS_BASE = process.env.REACT_APP_WS_URL || 'wss://track.pureleven.com/api';
const WS_PREFIX = '/crm/ws';

class SocketClient {
  constructor(options = {}) {
    this.wsMetrics = null;
    this.wsSteps = null;
    this.token = options.token || localStorage.getItem('anu_admin_secret') || '';
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    this.reconnectDelay = options.reconnectDelay || 3000;
    this.handlers = {
      onMetricsUpdate: options.onMetricsUpdate || (() => {}),
      onStepLog: options.onStepLog || (() => {}),
      onError: options.onError || (() => {}),
      onConnect: options.onConnect || (() => {}),
      onDisconnect: options.onDisconnect || (() => {}),
    };
    this.isConnecting = false;
    this.shouldReconnect = true;
    this.reconnectTimer = null;
  }

  /**
   * Connect to WebSocket endpoints
   */
  async connect() {
    if (!this.token) {
      this.handlers.onDisconnect?.('auth');
      return;
    }
    if (this.isConnecting || this.isConnected()) return;
    this.isConnecting = true;

    try {
      // Connect to metrics stream
      await this.connectMetrics();
      // Connect to steps stream
      await this.connectSteps();
      this.reconnectAttempts = 0;
      this.clearReconnectTimer();
      this.handlers.onConnect?.();
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.handlers.onError?.(error);
      this.scheduleReconnect();
    } finally {
      this.isConnecting = false;
    }
  }

  /**
   * Connect to /ws/metrics endpoint
   */
  connectMetrics() {
    return new Promise((resolve, reject) => {
      let settled = false;
      let opened = false;
      try {
        const url = `${WS_BASE}${WS_PREFIX}/metrics?token=${this.token}`;
        this.wsMetrics = new WebSocket(url);

        this.wsMetrics.onopen = () => {
          opened = true;
          settled = true;
          console.log('✅ Connected to metrics stream');
          resolve();
        };

        this.wsMetrics.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handlers.onMetricsUpdate?.(data);
          } catch (err) {
            console.error('Failed to parse metrics message:', err);
          }
        };

        this.wsMetrics.onerror = (error) => {
          console.error('Metrics WebSocket error:', error);
          if (!opened && !settled) {
            settled = true;
            reject(error);
          }
        };

        this.wsMetrics.onclose = () => {
          console.log('❌ Disconnected from metrics stream');
          this.handlers.onDisconnect?.('metrics');
          if (!opened && !settled) {
            settled = true;
            reject(new Error('Metrics WebSocket closed before opening'));
            return;
          }
          this.scheduleReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Connect to /ws/steps endpoint
   */
  connectSteps() {
    return new Promise((resolve, reject) => {
      let settled = false;
      let opened = false;
      try {
        const url = `${WS_BASE}${WS_PREFIX}/steps?token=${this.token}`;
        this.wsSteps = new WebSocket(url);

        this.wsSteps.onopen = () => {
          opened = true;
          settled = true;
          console.log('✅ Connected to steps stream');
          resolve();
        };

        this.wsSteps.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handlers.onStepLog?.(data);
          } catch (err) {
            console.error('Failed to parse step message:', err);
          }
        };

        this.wsSteps.onerror = (error) => {
          console.error('Steps WebSocket error:', error);
          if (!opened && !settled) {
            settled = true;
            reject(error);
          }
        };

        this.wsSteps.onclose = () => {
          console.log('❌ Disconnected from steps stream');
          this.handlers.onDisconnect?.('steps');
          if (!opened && !settled) {
            settled = true;
            reject(new Error('Steps WebSocket closed before opening'));
            return;
          }
          this.scheduleReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Schedule automatic reconnection
   */
  scheduleReconnect() {
    if (!this.shouldReconnect) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(
        '❌ Max reconnection attempts reached. Giving up.'
      );
      return;
    }

    if (this.reconnectTimer) return;

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  clearReconnectTimer() {
    if (!this.reconnectTimer) return;
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }

  /**
   * Publish event to Redis channel (if supported by backend)
   */
  publish(channel, message) {
    const data = JSON.stringify({ channel, message });

    if (this.wsMetrics?.readyState === WebSocket.OPEN) {
      this.wsMetrics.send(data);
    }
    if (this.wsSteps?.readyState === WebSocket.OPEN) {
      this.wsSteps.send(data);
    }
  }

  /**
   * Subscribe to specific channel (backend implementation)
   */
  subscribe(channel) {
    this.publish('subscribe', { channel });
  }

  /**
   * Unsubscribe from channel
   */
  unsubscribe(channel) {
    this.publish('unsubscribe', { channel });
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    this.shouldReconnect = false;
    this.clearReconnectTimer();
    if (this.wsMetrics) {
      this.wsMetrics.close();
      this.wsMetrics = null;
    }
    if (this.wsSteps) {
      this.wsSteps.close();
      this.wsSteps = null;
    }
    this.reconnectAttempts = 0;
  }

  /**
   * Check connection status
   */
  isConnected() {
    return (
      this.wsMetrics?.readyState === WebSocket.OPEN &&
      this.wsSteps?.readyState === WebSocket.OPEN
    );
  }

  /**
   * Get connection status details
   */
  getStatus() {
    return {
      connected: this.isConnected(),
      metrics: {
        state: this.wsMetrics?.readyState || 'NOT_INITIALIZED',
        stateLabel: this.getStateLabel(this.wsMetrics?.readyState),
      },
      steps: {
        state: this.wsSteps?.readyState || 'NOT_INITIALIZED',
        stateLabel: this.getStateLabel(this.wsSteps?.readyState),
      },
      reconnectAttempts: this.reconnectAttempts,
    };
  }

  /**
   * Convert WebSocket state number to label
   */
  getStateLabel(state) {
    const states = {
      0: 'CONNECTING',
      1: 'OPEN',
      2: 'CLOSING',
      3: 'CLOSED',
    };
    return states[state] || 'UNKNOWN';
  }
}

/**
 * Singleton instance
 */
let socketInstance = null;

export const getSocketClient = (options) => {
  const nextToken = options?.token || localStorage.getItem('anu_admin_secret') || '';
  if (socketInstance && socketInstance.token !== nextToken) {
    socketInstance.disconnect();
    socketInstance = null;
  }

  if (!socketInstance) {
    socketInstance = new SocketClient(options);
  }
  return socketInstance;
};

const HTTP_HEALTH_URL = 'https://track.pureleven.com/api/health';

/**
 * React Hook for WebSocket integration with HTTP health polling fallback.
 * Shows "Live" if the health endpoint is reachable, even if WebSocket is unavailable.
 */
export const useSocket = (options = {}) => {
  const [connected, setConnected] = React.useState(false);
  const [metricsData, setMetricsData] = React.useState(null);
  const [stepLogs, setStepLogs] = React.useState([]);
  const [error, setError] = React.useState(null);
  const token = options.token || localStorage.getItem('anu_admin_secret') || '';

  // HTTP health polling — primary source of "Live" status
  React.useEffect(() => {
    let cancelled = false;
    const checkHealth = async () => {
      try {
        const res = await fetch(HTTP_HEALTH_URL, { method: 'GET' });
        if (!cancelled) {
          const alive = res.ok;
          setConnected(alive);
          if (alive) options.onConnect?.();
          else options.onDisconnect?.();
        }
      } catch {
        if (!cancelled) {
          setConnected(false);
          options.onDisconnect?.();
        }
      }
    };
    checkHealth();
    const poll = setInterval(checkHealth, 30000);
    return () => { cancelled = true; clearInterval(poll); };
  }, []);

  // WebSocket — best-effort real-time updates (does not affect Live/Offline indicator)
  React.useEffect(() => {
    const socket = getSocketClient({
      token,
      onConnect: () => { /* health poll drives the indicator */ },
      onDisconnect: () => { /* health poll drives the indicator */ },
      onMetricsUpdate: (data) => {
        setMetricsData(data);
        options.onMetricsUpdate?.(data);
      },
      onStepLog: (data) => {
        setStepLogs((prev) => [data, ...prev.slice(0, 99)]);
        options.onStepLog?.(data);
      },
      onError: (err) => {
        setError(err);
        options.onError?.(err);
      },
    });

    socket.connect();

    return () => {
      // Don't disconnect on unmount (keep stream alive)
    };
  }, [token]);

  return { connected, metricsData, stepLogs, error };
};

/**
 * Polling fallback (for environments without WebSocket support)
 */
export const startPollingFallback = (api, interval = 30000) => {
  const startPolling = async () => {
    try {
      const metrics = await api.getJourneyAnalytics();
      return metrics;
    } catch (err) {
      console.error('Polling failed:', err);
      return null;
    }
  };

  return setInterval(startPolling, interval);
};

/**
 * Connection monitor
 */
export const startConnectionMonitor = (socket, onStatusChange) => {
  const interval = setInterval(() => {
    const status = socket.getStatus();
    onStatusChange?.(status);
  }, 5000);

  return () => clearInterval(interval);
};

export default SocketClient;
