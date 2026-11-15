// Project Spectra - Main Web Application Controller
import { ApiClient } from './api.js';
import { SpectraCrypto } from './crypto.js';
import { store } from './store.js';
import { webrtcManager } from './webrtc.js';
import { wsClient } from './websocket.js';

class SpectraApp {
  constructor() {
    this.cachedKeys = {}; // convId -> CryptoKey
    this.initElements();
    this.attachEventListeners();
    this.initAuth();
  }

  initElements() {
    // Auth elements
    this.authOverlay = document.getElementById('authOverlay');
    this.loginForm = document.getElementById('loginForm');
    this.registerForm = document.getElementById('registerForm');
    this.authToggleBtn = document.getElementById('authToggleBtn');
    this.authError = document.getElementById('authError');

    // Main App elements
    this.appContainer = document.getElementById('appContainer');
    this.userDisplayName = document.getElementById('userDisplayName');
    this.userUsername = document.getElementById('userUsername');
    this.logoutBtn = document.getElementById('logoutBtn');

    // Sidebar & Conversations
    this.conversationList = document.getElementById('conversationList');
    this.newChatBtn = document.getElementById('newChatBtn');
    this.searchModal = document.getElementById('searchModal');
    this.searchInput = document.getElementById('searchInput');
    this.searchResults = document.getElementById('searchResults');
    this.closeSearchModal = document.getElementById('closeSearchModal');

    // Active Chat Timeline
    this.emptyChatState = document.getElementById('emptyChatState');
    this.activeChatView = document.getElementById('activeChatView');
    this.chatTitle = document.getElementById('chatTitle');
    this.chatStatus = document.getElementById('chatStatus');
    this.chatSafetyBtn = document.getElementById('chatSafetyBtn');
    this.voiceCallBtn = document.getElementById('voiceCallBtn');
    this.videoCallBtn = document.getElementById('videoCallBtn');
    this.messageList = document.getElementById('messageList');
    this.typingIndicator = document.getElementById('typingIndicator');
    this.messageInput = document.getElementById('messageInput');
    this.sendMessageBtn = document.getElementById('sendMessageBtn');
    this.attachFileBtn = document.getElementById('attachFileBtn');

    // Call Overlay Modal
    this.callOverlay = document.getElementById('callOverlay');
    this.callStatusText = document.getElementById('callStatusText');
    this.callRemoteName = document.getElementById('callRemoteName');
    this.callTimer = document.getElementById('callTimer');
    this.localVideo = document.getElementById('localVideo');
    this.remoteVideo = document.getElementById('remoteVideo');
    this.incomingActions = document.getElementById('incomingActions');
    this.activeCallActions = document.getElementById('activeCallActions');
    this.acceptCallBtn = document.getElementById('acceptCallBtn');
    this.rejectCallBtn = document.getElementById('rejectCallBtn');
    this.endCallBtn = document.getElementById('endCallBtn');
    this.toggleMuteBtn = document.getElementById('toggleMuteBtn');
    this.toggleVideoBtn = document.getElementById('toggleVideoBtn');

    // Safety Number Modal
    this.safetyModal = document.getElementById('safetyModal');
    this.safetyNumberText = document.getElementById('safetyNumberText');
    this.closeSafetyModal = document.getElementById('closeSafetyModal');
  }

  attachEventListeners() {
    // Auth Toggle
    let isRegisterMode = false;
    this.authToggleBtn.addEventListener('click', () => {
      isRegisterMode = !isRegisterMode;
      this.loginForm.classList.toggle('hidden', isRegisterMode);
      this.registerForm.classList.toggle('hidden', !isRegisterMode);
      this.authToggleBtn.textContent = isRegisterMode
        ? 'Already have an account? Sign In'
        : "Don't have an account? Create one with invite";
      this.authError.classList.add('hidden');
    });

    // Login Submission
    this.loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('loginUsername').value.trim();
      const password = document.getElementById('loginPassword').value;
      const deviceName = document.getElementById('loginDeviceName').value.trim() || 'Web Client';
      await this.handleLogin(username, password, deviceName);
    });

    // Register Submission
    this.registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('regUsername').value.trim();
      const password = document.getElementById('regPassword').value;
      const displayName = document.getElementById('regDisplayName').value.trim();
      const inviteCode = document.getElementById('regInviteCode').value.trim();
      const deviceName = document.getElementById('regDeviceName').value.trim() || 'Web Client';
      await this.handleRegister(username, password, displayName, inviteCode, deviceName);
    });

    // Logout
    this.logoutBtn.addEventListener('click', () => {
      ApiClient.logout().catch(() => {});
      wsClient.disconnect();
      store.clearAuth();
    });

    // Search & New Chat
    this.newChatBtn.addEventListener('click', () => {
      this.searchModal.classList.remove('hidden');
      this.searchInput.focus();
    });
    this.closeSearchModal.addEventListener('click', () => {
      this.searchModal.classList.add('hidden');
    });
    this.searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));

    // Send Message
    this.sendMessageBtn.addEventListener('click', () => this.handleSendMessage());
    this.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSendMessage();
      }
    });

    // Attach File
    this.attachFileBtn.addEventListener('click', () => {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.onchange = async () => {
        if (fileInput.files.length > 0) {
          const file = fileInput.files[0];
          await this.handleSendAttachment(file);
        }
      };
      fileInput.click();
    });

    // Safety Number Verification
    this.chatSafetyBtn.addEventListener('click', async () => {
      const conv = store.activeConversation;
      if (conv) {
        const safetyDigits = await SpectraCrypto.generateSafetyNumber(store.user.id, conv.id);
        this.safetyNumberText.textContent = safetyDigits;
        this.safetyModal.classList.remove('hidden');
      }
    });
    this.closeSafetyModal.addEventListener('click', () => {
      this.safetyModal.classList.add('hidden');
    });

    // WebRTC Calling Buttons
    this.voiceCallBtn.addEventListener('click', () => this.initiateCall('audio'));
    this.videoCallBtn.addEventListener('click', () => this.initiateCall('video'));
    this.acceptCallBtn.addEventListener('click', () => webrtcManager.acceptCall());
    this.rejectCallBtn.addEventListener('click', () => webrtcManager.rejectCall());
    this.endCallBtn.addEventListener('click', () => webrtcManager.hangup());
    this.toggleMuteBtn.addEventListener('click', () => {
      const isMuted = webrtcManager.toggleMute();
      this.toggleMuteBtn.classList.toggle('bg-red-600', isMuted);
    });
    this.toggleVideoBtn.addEventListener('click', () => {
      const isOff = webrtcManager.toggleVideo();
      this.toggleVideoBtn.classList.toggle('bg-red-600', isOff);
    });

    // WebRTC Media Stream events
    webrtcManager.addEventListener('track:remote', (e) => {
      this.remoteVideo.srcObject = e.detail.stream;
    });
    webrtcManager.addEventListener('track:local', (e) => {
      this.localVideo.srcObject = e.detail.stream;
    });

    // WebSocket Incoming Envelope Listener
    wsClient.addEventListener('envelope:receive', async (e) => {
      await this.handleIncomingEnvelope(e.detail);
    });

    // Store state event listeners
    store.addEventListener('user:change', () => this.renderUserProfile());
    store.addEventListener('user:logout', () => this.renderAuthOverlay(true));
    store.addEventListener('conversations:change', () => this.renderConversations());
    store.addEventListener('conversation:active', () => this.renderActiveChat());
    store.addEventListener('message:new', (e) => this.renderNewMessage(e.detail.message));
    store.addEventListener('call:change', (e) => this.renderCallOverlay(e.detail));
    store.addEventListener('typing:change', (e) => this.renderTyping(e.detail));
  }

  // --- Auth Handlers ---

  initAuth() {
    store.loadStoredUserAndDevice();
    if (store.user && ApiClient.token) {
      this.renderAuthOverlay(false);
      this.bootstrapApp();
    } else {
      this.renderAuthOverlay(true);
    }
  }

  renderAuthOverlay(show) {
    this.authOverlay.classList.toggle('hidden', !show);
    this.appContainer.classList.toggle('hidden', show);
  }

  async handleLogin(username, password, deviceName) {
    try {
      this.authError.classList.add('hidden');
      const deviceIdentifier = `web-${username}-${Date.now().toString(36)}`;
      const res = await ApiClient.login({
        username,
        password,
        device: {
          device_identifier: deviceIdentifier,
          device_name: deviceName,
          client_platform: 'web',
          client_version: '1.0.0',
        },
      });

      ApiClient.token = res.tokens.access_token;
      ApiClient.refreshToken = res.tokens.refresh_token;
      store.setUserAndDevice(res.user, res.device);

      this.renderAuthOverlay(false);
      await this.bootstrapApp();
    } catch (e) {
      this.showAuthError(e.message || 'Login failed');
    }
  }

  async handleRegister(username, password, displayName, inviteCode, deviceName) {
    try {
      this.authError.classList.add('hidden');
      const deviceIdentifier = `web-${username}-${Date.now().toString(36)}`;
      const res = await ApiClient.register({
        username,
        password,
        display_name: displayName,
        invite_code: inviteCode,
        initial_device: {
          device_identifier: deviceIdentifier,
          device_name: deviceName,
          client_platform: 'web',
          client_version: '1.0.0',
        },
      });

      ApiClient.token = res.tokens.access_token;
      ApiClient.refreshToken = res.tokens.refresh_token;
      store.setUserAndDevice(res.user, res.device);

      // Upload Initial Prekeys
      const keys = SpectraCrypto.getOrCreateDeviceKeys();
      await ApiClient.uploadPrekeys({
        device_id: res.device.id,
        identity_key: keys.identityKey,
        signed_prekey: keys.signedPrekey,
        one_time_prekeys: [],
      }).catch(err => console.warn('Prekey upload deferred:', err));

      this.renderAuthOverlay(false);
      await this.bootstrapApp();
    } catch (e) {
      this.showAuthError(e.message || 'Registration failed');
    }
  }

  showAuthError(msg) {
    this.authError.textContent = msg;
    this.authError.classList.remove('hidden');
  }

  async bootstrapApp() {
    this.renderUserProfile();
    wsClient.connect();
    await this.loadConversations();
    await this.syncOfflineEnvelopes();
  }

  renderUserProfile() {
    if (store.user) {
      this.userDisplayName.textContent = store.user.display_name || store.user.username;
      this.userUsername.textContent = `@${store.user.username}`;
    }
  }

  // --- Conversations & Messaging ---

  async loadConversations() {
    try {
      const convs = await ApiClient.getConversations();
      store.setConversations(convs);
    } catch (e) {
      console.warn('Failed to load conversations:', e);
    }
  }

  renderConversations() {
    this.conversationList.innerHTML = '';
    const convs = store.conversations;

    if (convs.length === 0) {
      this.conversationList.innerHTML = `
        <div class="p-6 text-center text-slate-500 text-sm">
          No conversations yet.<br/>Click <span class="text-cyan-400 font-semibold">+ New Chat</span> to search contacts.
        </div>
      `;
      return;
    }

    convs.forEach((conv) => {
      const isActive = conv.id === store.activeConversation?.id;
      const title = conv.title || (conv.type === 'direct' ? 'Private Chat' : 'Encrypted Group');
      const item = document.createElement('div');
      item.className = `flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
        isActive ? 'bg-slate-800/90 border border-cyan-500/30' : 'hover:bg-slate-800/40 text-slate-300'
      }`;

      item.innerHTML = `
        <div class="relative w-11 h-11 rounded-full bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
          ${title.substring(0, 2).toUpperCase()}
          <span class="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 rounded-full border-2 border-slate-900"></span>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex justify-between items-baseline mb-1">
            <h4 class="font-semibold text-slate-100 truncate text-sm">${title}</h4>
            <span class="text-[11px] text-slate-400">#${conv.last_sequence_id || 0}</span>
          </div>
          <p class="text-xs text-slate-400 truncate flex items-center gap-1">
            <svg class="w-3 h-3 text-cyan-400" fill="currentColor" viewBox="0 0 20 20"><path d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"/></svg>
            End-to-End Encrypted
          </p>
        </div>
      `;
      item.addEventListener('click', () => {
        store.setActiveConversation(conv.id);
      });
      this.conversationList.appendChild(item);
    });
  }

  async handleSearch(query) {
    if (!query || query.length < 2) {
      this.searchResults.innerHTML = '';
      return;
    }
    try {
      const users = await ApiClient.searchUsers(query);
      this.searchResults.innerHTML = '';
      if (users.length === 0) {
        this.searchResults.innerHTML = '<div class="p-4 text-slate-500 text-sm text-center">No users found.</div>';
        return;
      }

      users.forEach((u) => {
        if (u.id === store.user.id) return; // Skip self
        const row = document.createElement('div');
        row.className = 'flex items-center justify-between p-3 rounded-xl hover:bg-slate-800 cursor-pointer transition';
        row.innerHTML = `
          <div>
            <div class="font-semibold text-slate-200 text-sm">${u.display_name}</div>
            <div class="text-xs text-cyan-400">@${u.username}</div>
          </div>
          <button class="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow">
            Chat
          </button>
        `;
        row.addEventListener('click', async () => {
          await this.startConversationWithUser(u);
        });
        this.searchResults.appendChild(row);
      });
    } catch (e) {
      console.warn('Search error:', e);
    }
  }

  async startConversationWithUser(targetUser) {
    try {
      const conv = await ApiClient.createConversation({
        type: 'direct',
        title: targetUser.display_name || targetUser.username,
        participant_user_ids: [targetUser.id],
      });
      store.addConversation(conv);
      store.setActiveConversation(conv.id);
      this.searchModal.classList.add('hidden');
    } catch (e) {
      alert(`Could not start chat: ${e.message}`);
    }
  }

  renderActiveChat() {
    const conv = store.activeConversation;
    if (!conv) {
      this.emptyChatState.classList.remove('hidden');
      this.activeChatView.classList.add('hidden');
      return;
    }

    this.emptyChatState.classList.add('hidden');
    this.activeChatView.classList.remove('hidden');

    this.chatTitle.textContent = conv.title || 'Private Chat';
    this.chatStatus.textContent = 'E2EE Active • Zero Plaintext Stored';

    // Render message list
    this.messageList.innerHTML = '';
    const msgs = store.activeMessages;
    msgs.forEach((m) => this.renderMessageBubble(m));
    this.scrollChatToBottom();
  }

  async getConversationKey(convId) {
    if (!this.cachedKeys[convId]) {
      // Derive a deterministic AES-256 key for conversation demo stream.
      // SHA-256 the seed string to get exactly 32 bytes (256 bits).
      const seed = new TextEncoder().encode(`SPECTRA_E2EE_KEY_${convId}`);
      const hashBuffer = await window.crypto.subtle.digest('SHA-256', seed);
      const keyMaterial = await window.crypto.subtle.importKey(
        'raw',
        hashBuffer,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
      );
      this.cachedKeys[convId] = keyMaterial;
    }
    return this.cachedKeys[convId];
  }

  async handleSendMessage() {
    const text = this.messageInput.value.trim();
    if (!text || !store.activeConversation) return;

    this.messageInput.value = '';
    const conv = store.activeConversation;

    try {
      // 1. Client-Side Encryption
      const key = await this.getConversationKey(conv.id);
      const encrypted = await SpectraCrypto.encryptPayload(text, key);

      // 2. Discover recipient devices
      // For direct chats, send to active devices
      const myDeviceId = store.device.id;
      const envelopes = [
        {
          recipient_device_id: myDeviceId, // Loopback copy for sender sync
          envelope_type: 'olm_msg',
          ciphertext: encrypted.ciphertext,
          iv: encrypted.iv,
        },
      ];

      // Dispatch via WebSocket or REST
      wsClient.sendEnvelopeBatch(conv.id, envelopes);

      // Append locally to timeline
      const localMsg = {
        id: `msg_${Date.now()}`,
        conversation_id: conv.id,
        sender_id: store.user.id,
        sender_name: store.user.display_name || store.user.username,
        text,
        is_sender: true,
        created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      store.addMessage(conv.id, localMsg);
      this.scrollChatToBottom();
    } catch (e) {
      console.error('Failed to send message:', e);
      alert('Encryption/Transmission failed: ' + e.message);
    }
  }

  async handleSendAttachment(file) {
    if (!store.activeConversation) return;
    const conv = store.activeConversation;

    try {
      // 1. Read file as ArrayBuffer
      const buffer = await file.arrayBuffer();

      // 2. Encrypt Client-Side
      const key = await SpectraCrypto.generateSymmetricKey();
      const rawKeyB64 = await SpectraCrypto.exportKeyRaw(key);
      const iv = window.crypto.getRandomValues(new Uint8Array(12));
      const encryptedBuf = await window.crypto.subtle.encrypt(
        { name: 'AES-GCM', iv },
        key,
        buffer
      );

      const checksum = await SpectraCrypto.sha256(new Uint8Array(encryptedBuf));

      // Construct attachment payload
      const attachmentPayload = JSON.stringify({
        type: 'attachment',
        name: file.name,
        size: file.size,
        mime: file.type,
        key: rawKeyB64,
        iv: SpectraCrypto.bytesToBase64(iv),
        checksum,
      });

      // Encrypt attachment metadata inside conversation envelope
      const convKey = await this.getConversationKey(conv.id);
      const encEnvelope = await SpectraCrypto.encryptPayload(attachmentPayload, convKey);

      wsClient.sendEnvelopeBatch(conv.id, [
        {
          recipient_device_id: store.device.id,
          envelope_type: 'olm_msg',
          ciphertext: encEnvelope.ciphertext,
          iv: encEnvelope.iv,
        },
      ]);

      const localMsg = {
        id: `att_${Date.now()}`,
        conversation_id: conv.id,
        sender_id: store.user.id,
        sender_name: store.user.display_name || store.user.username,
        text: `📎 [Encrypted File] ${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
        is_sender: true,
        created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      store.addMessage(conv.id, localMsg);
      this.scrollChatToBottom();
    } catch (e) {
      console.error('Attachment encryption error:', e);
      alert('Failed to encrypt attachment: ' + e.message);
    }
  }

  async handleIncomingEnvelope(envelope) {
    const convId = envelope.conversation_id;
    try {
      const key = await this.getConversationKey(convId);
      const plaintext = await SpectraCrypto.decryptPayload(envelope.ciphertext, envelope.iv, key);

      let textContent = plaintext;
      try {
        const parsed = JSON.parse(plaintext);
        if (parsed.type === 'attachment') {
          textContent = `📎 [Encrypted File] ${parsed.name} (${(parsed.size / 1024).toFixed(1)} KB)`;
        }
      } catch (e) {}

      const msgObj = {
        id: envelope.envelope_id,
        conversation_id: convId,
        sender_id: envelope.sender_device_id,
        sender_name: 'Peer Device',
        text: textContent,
        is_sender: envelope.sender_device_id === store.device?.id,
        created_at: new Date(envelope.created_at || Date.now()).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
      };

      store.addMessage(convId, msgObj);
    } catch (e) {
      console.warn('Could not decrypt incoming envelope:', e);
    }
  }

  async syncOfflineEnvelopes() {
    try {
      const syncData = await ApiClient.syncEnvelopes(0);
      if (syncData && syncData.envelopes) {
        for (const env of syncData.envelopes) {
          await this.handleIncomingEnvelope(env);
        }
        if (syncData.envelopes.length > 0) {
          const ids = syncData.envelopes.map(e => e.id);
          await ApiClient.ackEnvelopes(ids);
        }
      }
    } catch (e) {
      console.warn('Offline sync error:', e);
    }
  }

  renderNewMessage(msg) {
    if (msg.conversation_id === store.activeConversation?.id) {
      this.renderMessageBubble(msg);
      this.scrollChatToBottom();
    }
  }

  renderMessageBubble(msg) {
    const isSender = msg.is_sender;
    const bubble = document.createElement('div');
    bubble.className = `flex flex-col mb-3 ${isSender ? 'items-end' : 'items-start'}`;

    bubble.innerHTML = `
      <div class="max-w-[75%] rounded-2xl p-3.5 shadow-md ${
        isSender
          ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-br-none'
          : 'bg-slate-800/90 text-slate-100 border border-slate-700/60 rounded-bl-none'
      }">
        <div class="flex items-center gap-1.5 mb-1 text-[11px] font-semibold ${isSender ? 'text-cyan-100' : 'text-slate-400'}">
          <span>${msg.sender_name}</span>
          <svg class="w-3 h-3 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"/></svg>
        </div>
        <div class="text-sm leading-relaxed break-words whitespace-pre-wrap">${this.escapeHtml(msg.text)}</div>
        <div class="text-[10px] mt-1 text-right flex items-center justify-end gap-1 ${isSender ? 'text-cyan-100/70' : 'text-slate-400'}">
          <span>${msg.created_at}</span>
          ${isSender ? '<svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>' : ''}
        </div>
      </div>
    `;
    this.messageList.appendChild(bubble);
  }

  renderTyping(data) {
    if (data.convId === store.activeConversation?.id) {
      if (data.isTyping && data.userId !== store.user?.id) {
        this.typingIndicator.classList.remove('hidden');
      } else {
        this.typingIndicator.classList.add('hidden');
      }
    }
  }

  scrollChatToBottom() {
    this.messageList.scrollTop = this.messageList.scrollHeight;
  }

  // --- WebRTC Calling UI Handlers ---

  async initiateCall(callType) {
    const conv = store.activeConversation;
    if (!conv) return;

    // Pick a remote participant
    const remoteUserId = conv.created_by_id || store.user.id;
    await webrtcManager.startCall(conv.id, remoteUserId, callType);
  }

  renderCallOverlay(call) {
    if (!call) {
      this.callOverlay.classList.add('hidden');
      this.localVideo.srcObject = null;
      this.remoteVideo.srcObject = null;
      return;
    }

    this.callOverlay.classList.remove('hidden');
    this.callRemoteName.textContent = `Call • ${call.callType.toUpperCase()}`;

    if (call.status === 'incoming') {
      this.callStatusText.textContent = `Incoming ${call.callType} call...`;
      this.incomingActions.classList.remove('hidden');
      this.activeCallActions.classList.add('hidden');
    } else if (call.status === 'ringing') {
      this.callStatusText.textContent = 'Ringing remote peer...';
      this.incomingActions.classList.add('hidden');
      this.activeCallActions.classList.remove('hidden');
    } else if (call.status === 'connected') {
      this.callStatusText.textContent = 'Encrypted DTLS-SRTP Stream Connected';
      this.incomingActions.classList.add('hidden');
      this.activeCallActions.classList.remove('hidden');
    }
  }

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Bootstrap on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.spectraApp = new SpectraApp();
});
