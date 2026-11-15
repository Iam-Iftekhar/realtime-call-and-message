// Project Spectra - REST API Client
const API_BASE = '/api/v1';

export class ApiClient {
  static get token() {
    return localStorage.getItem('spectra_access_token');
  }

  static set token(val) {
    if (val) localStorage.setItem('spectra_access_token', val);
    else localStorage.removeItem('spectra_access_token');
  }

  static get refreshToken() {
    return localStorage.getItem('spectra_refresh_token');
  }

  static set refreshToken(val) {
    if (val) localStorage.setItem('spectra_refresh_token', val);
    else localStorage.removeItem('spectra_refresh_token');
  }

  static async request(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    let response = await fetch(url, { ...options, headers });

    // Handle token expiry and auto-refresh
    if (response.status === 401 && this.refreshToken && !options._isRetry) {
      const refreshed = await this.refreshTokens();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.token}`;
        response = await fetch(url, { ...options, headers, _isRetry: true });
      }
    }

    if (!response.ok) {
      let errData = {};
      try {
        errData = await response.json();
      } catch (e) {
        errData = { detail: response.statusText };
      }
      const error = new Error(errData.detail || errData.title || 'Request failed');
      error.status = response.status;
      error.code = errData.code;
      throw error;
    }

    if (response.status === 204) return null;
    return response.json();
  }

  static async refreshTokens() {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (res.ok) {
        const data = await res.json();
        this.token = data.access_token;
        this.refreshToken = data.refresh_token;
        return true;
      }
    } catch (e) {
      console.warn('[API] Refresh failed:', e);
    }
    this.token = null;
    this.refreshToken = null;
    return false;
  }

  // Auth Endpoints
  static register(data) {
    return this.request('/auth/register', { method: 'POST', body: JSON.stringify(data) });
  }

  static login(data) {
    return this.request('/auth/login', { method: 'POST', body: JSON.stringify(data) });
  }

  static logout() {
    return this.request('/auth/logout', { method: 'POST' });
  }

  static getSessions() {
    return this.request('/auth/sessions');
  }

  // User Endpoints
  static getMe() {
    return this.request('/users/me');
  }

  static updateMe(data) {
    return this.request('/users/me', { method: 'PATCH', body: JSON.stringify(data) });
  }

  static searchUsers(query) {
    return this.request(`/users/search?q=${encodeURIComponent(query)}`);
  }

  // Device Endpoints
  static getDevices() {
    return this.request('/devices');
  }

  static registerDevice(data) {
    return this.request('/devices/register', { method: 'POST', body: JSON.stringify(data) });
  }

  // Cryptographic PreKey Endpoints
  static uploadPrekeys(data) {
    return this.request('/crypto/prekeys/upload', { method: 'POST', body: JSON.stringify(data) });
  }

  static getUserDevices(userId) {
    return this.request(`/crypto/prekeys/${userId}/devices`);
  }

  static fetchPrekeyBundles(deviceIds) {
    return this.request('/crypto/prekeys/bundle', {
      method: 'POST',
      body: JSON.stringify({ device_ids: deviceIds }),
    });
  }

  // Messaging Endpoints
  static getConversations() {
    return this.request('/conversations');
  }

  static createConversation(data) {
    return this.request('/conversations', { method: 'POST', body: JSON.stringify(data) });
  }

  static sendEnvelopes(data) {
    return this.request('/messages/send-batch', { method: 'POST', body: JSON.stringify(data) });
  }

  static syncEnvelopes(lastSeq = 0) {
    return this.request(`/messages/sync?last_seq=${lastSeq}`);
  }

  static ackEnvelopes(envelopeIds) {
    return this.request('/messages/ack', {
      method: 'POST',
      body: JSON.stringify({ envelope_ids: envelopeIds }),
    });
  }

  // WebRTC Calling Endpoints
  static getIceServers() {
    return this.request('/calling/ice-servers');
  }

  static initiateCall(data) {
    return this.request('/calling/initiate', { method: 'POST', body: JSON.stringify(data) });
  }

  static endCall(callId) {
    return this.request(`/calling/${callId}/end`, { method: 'POST' });
  }
}
