// Project Spectra - Reactive State Store
export class Store extends EventTarget {
  constructor() {
    super();
    this.state = {
      user: null,
      device: null,
      conversations: [],
      activeConversationId: null,
      messages: {}, // convId -> array of messages
      presence: {}, // userId -> 'online' | 'offline'
      typing: {}, // convId -> { userId: boolean }
      activeCall: null, // { callId, conversationId, remoteUserId, callType, status, isCaller }
      iceServers: [],
    };
  }

  get user() { return this.state.user; }
  get device() { return this.state.device; }
  get conversations() { return this.state.conversations; }
  get activeConversation() {
    return this.state.conversations.find(c => c.id === this.state.activeConversationId) || null;
  }
  get activeMessages() {
    return this.state.messages[this.state.activeConversationId] || [];
  }
  get activeCall() { return this.state.activeCall; }

  setUserAndDevice(user, device) {
    this.state.user = user;
    this.state.device = device;
    localStorage.setItem('spectra_user', JSON.stringify(user));
    localStorage.setItem('spectra_device', JSON.stringify(device));
    this.emit('user:change', { user, device });
  }

  loadStoredUserAndDevice() {
    const u = localStorage.getItem('spectra_user');
    const d = localStorage.getItem('spectra_device');
    if (u && d) {
      try {
        this.state.user = JSON.parse(u);
        this.state.device = JSON.parse(d);
        this.emit('user:change', { user: this.state.user, device: this.state.device });
      } catch (e) {
        this.clearAuth();
      }
    }
  }

  clearAuth() {
    this.state.user = null;
    this.state.device = null;
    this.state.conversations = [];
    this.state.messages = {};
    this.state.activeConversationId = null;
    this.state.activeCall = null;
    localStorage.removeItem('spectra_user');
    localStorage.removeItem('spectra_device');
    localStorage.removeItem('spectra_access_token');
    localStorage.removeItem('spectra_refresh_token');
    this.emit('user:logout');
  }

  setConversations(convs) {
    this.state.conversations = convs;
    this.emit('conversations:change', convs);
  }

  addConversation(conv) {
    const idx = this.state.conversations.findIndex(c => c.id === conv.id);
    if (idx >= 0) {
      this.state.conversations[idx] = conv;
    } else {
      this.state.conversations.unshift(conv);
    }
    this.emit('conversations:change', this.state.conversations);
  }

  setActiveConversation(convId) {
    this.state.activeConversationId = convId;
    this.emit('conversation:active', this.activeConversation);
  }

  addMessage(convId, message) {
    if (!this.state.messages[convId]) {
      this.state.messages[convId] = [];
    }
    // Prevent duplicate messages
    if (!this.state.messages[convId].some(m => m.id === message.id)) {
      this.state.messages[convId].push(message);
      this.state.messages[convId].sort((a, b) => (a.sequence_id || 0) - (b.sequence_id || 0));
      this.emit('message:new', { convId, message });
    }
  }

  setTyping(convId, userId, isTyping) {
    if (!this.state.typing[convId]) {
      this.state.typing[convId] = {};
    }
    this.state.typing[convId][userId] = isTyping;
    this.emit('typing:change', { convId, userId, isTyping });
  }

  setPresence(userId, status) {
    this.state.presence[userId] = status;
    this.emit('presence:change', { userId, status });
  }

  setActiveCall(callObj) {
    this.state.activeCall = callObj;
    this.emit('call:change', callObj);
  }

  emit(eventName, detail = {}) {
    this.dispatchEvent(new CustomEvent(eventName, { detail }));
  }
}

export const store = new Store();
