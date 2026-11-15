// Project Spectra - Auto-Reconnecting WebSocket Client
import { store } from './store.js';

export class WebSocketClient extends EventTarget {
  constructor() {
    super();
    this.ws = null;
    this.reconnectTimer = null;
    this.pingInterval = null;
    this.isConnected = false;
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const token = localStorage.getItem('spectra_access_token');
    const device = store.device;
    if (!token || !device) {
      console.warn('[WS] Cannot connect: missing auth token or device');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/v1/connect`;

    console.log('[WS] Connecting to:', wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[WS] Socket connected. Sending AUTH_INIT...');
      this.isConnected = true;
      // Send AUTH_INIT
      this.send({
        type: 'AUTH_INIT',
        payload: {
          token,
          device_id: device.id,
        },
      });

      // Start Heartbeat PING every 25s
      clearInterval(this.pingInterval);
      this.pingInterval = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.send({ type: 'PING', payload: { ts: Date.now() } });
        }
      }, 25000);
    };

    this.ws.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data);
        this.handleFrame(frame);
      } catch (e) {
        console.error('[WS] Failed to parse incoming frame:', e, event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.warn(`[WS] Socket closed (code: ${event.code}). Scheduling reconnect...`);
      this.isConnected = false;
      clearInterval(this.pingInterval);
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (err) => {
      console.error('[WS] Socket error:', err);
    };
  }

  disconnect() {
    clearTimeout(this.reconnectTimer);
    clearInterval(this.pingInterval);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  send(frame) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        version: '1.0',
        id: `f_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        timestamp: Date.now(),
        ...frame,
      }));
    } else {
      console.warn('[WS] Cannot send frame, socket not open:', frame);
    }
  }

  handleFrame(frame) {
    const { type, payload } = frame;

    switch (type) {
      case 'AUTH_SUCCESS':
        console.log('[WS] Authenticated successfully with session:', payload.session_id);
        this.dispatchEvent(new CustomEvent('auth:success', { detail: payload }));
        break;

      case 'PONG':
        // Heartbeat acknowledged
        break;

      case 'ENVELOPE_RECEIVE':
        console.log('[WS] Received encrypted envelope:', payload.envelope_id);
        this.dispatchEvent(new CustomEvent('envelope:receive', { detail: payload }));
        // Automatically ACK delivered envelope
        this.send({
          type: 'ENVELOPE_ACK',
          payload: { envelope_ids: [payload.envelope_id] },
        });
        break;

      case 'TYPING_EVENT':
        store.setTyping(payload.conversation_id, payload.user_id, payload.is_typing);
        break;

      case 'CALL_SIGNAL':
        console.log('[WS] Received WebRTC Call Signal:', payload.action);
        this.dispatchEvent(new CustomEvent('call:signal', { detail: payload }));
        break;

      case 'ERROR':
        console.error('[WS] Server protocol error:', payload);
        break;

      default:
        console.log('[WS] Unhandled frame type:', type, payload);
    }
  }

  sendEnvelopeBatch(conversationId, envelopes) {
    this.send({
      type: 'ENVELOPE_SEND',
      payload: {
        conversation_id: conversationId,
        envelopes,
      },
    });
  }

  sendTyping(conversationId, isTyping) {
    this.send({
      type: 'TYPING_EVENT',
      payload: {
        conversation_id: conversationId,
        is_typing: isTyping,
      },
    });
  }

  sendCallSignal(signalPayload) {
    this.send({
      type: 'CALL_SIGNAL',
      payload: signalPayload,
    });
  }
}

export const wsClient = new WebSocketClient();
