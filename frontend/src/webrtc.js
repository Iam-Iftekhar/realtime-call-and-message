// Project Spectra - WebRTC Real-Time Calling Engine
import { ApiClient } from './api.js';
import { store } from './store.js';
import { wsClient } from './websocket.js';

export class WebRTCManager extends EventTarget {
  constructor() {
    super();
    this.peerConnection = null;
    this.localStream = null;
    this.remoteStream = null;
    this.currentCallId = null;
    this.iceServers = [];
    this.isMuted = false;
    this.isVideoOff = false;
    this.audioContext = null;
    this.ringtoneOscillator = null;

    // Listen for WebSocket signaling frames
    wsClient.addEventListener('call:signal', (e) => this.handleSignal(e.detail));
  }

  async initIceServers() {
    try {
      const data = await ApiClient.getIceServers();
      this.iceServers = data.ice_servers || [];
      console.log('[WebRTC] Loaded ICE Servers:', this.iceServers);
    } catch (e) {
      console.warn('[WebRTC] Failed to fetch ICE servers, using default STUN:', e);
      this.iceServers = [{ urls: 'stun:stun.l.google.com:19302' }];
    }
  }

  createPeerConnection() {
    if (this.peerConnection) {
      this.peerConnection.close();
    }

    const config = {
      iceServers: this.iceServers.length > 0 ? this.iceServers : [
        { urls: 'stun:stun.l.google.com:19302' }
      ],
    };

    this.peerConnection = new RTCPeerConnection(config);

    // ICE Candidate Callback
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        wsClient.sendCallSignal({
          action: 'ice_candidate',
          call_id: this.currentCallId,
          target_user_id: store.activeCall?.remoteUserId,
          candidate: event.candidate.toJSON(),
        });
      }
    };

    // Remote Track Callback
    this.remoteStream = new MediaStream();
    this.peerConnection.ontrack = (event) => {
      console.log('[WebRTC] Received remote track:', event.track.kind);
      this.remoteStream.addTrack(event.track);
      this.dispatchEvent(new CustomEvent('track:remote', { detail: { stream: this.remoteStream } }));
    };

    this.peerConnection.onconnectionstatechange = () => {
      console.log('[WebRTC] Connection state:', this.peerConnection.connectionState);
      this.dispatchEvent(new CustomEvent('connection:state', { detail: this.peerConnection.connectionState }));
      if (['failed', 'disconnected', 'closed'].includes(this.peerConnection.connectionState)) {
        this.stopRingtone();
      }
    };
  }

  async startCall(conversationId, calleeId, callType = 'audio') {
    await this.initIceServers();
    this.currentCallId = `call_${Date.now()}`;
    this.createPeerConnection();

    store.setActiveCall({
      callId: this.currentCallId,
      conversationId,
      remoteUserId: calleeId,
      callType,
      status: 'ringing',
      isCaller: true,
    });

    this.startRingtone(false); // Play outgoing ringing chime

    // Capture Local Audio/Video
    try {
      this.localStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: callType === 'video',
      });
      this.localStream.getTracks().forEach((track) => {
        this.peerConnection.addTrack(track, this.localStream);
      });
      this.dispatchEvent(new CustomEvent('track:local', { detail: { stream: this.localStream } }));
    } catch (e) {
      console.error('[WebRTC] Could not capture media:', e);
      alert('Camera/Microphone access was denied or not found.');
      this.hangup();
      return;
    }

    // Create SDP Offer
    const offer = await this.peerConnection.createOffer();
    await this.peerConnection.setLocalDescription(offer);

    wsClient.sendCallSignal({
      action: 'offer',
      call_id: this.currentCallId,
      callee_id: calleeId,
      conversation_id: conversationId,
      call_type: callType,
      sdp: offer.sdp,
    });
  }

  async acceptCall() {
    this.stopRingtone();
    const call = store.activeCall;
    if (!call || !call.pendingOfferSdp) return;

    await this.initIceServers();
    this.createPeerConnection();

    // Capture Local Media
    try {
      this.localStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: call.callType === 'video',
      });
      this.localStream.getTracks().forEach((track) => {
        this.peerConnection.addTrack(track, this.localStream);
      });
      this.dispatchEvent(new CustomEvent('track:local', { detail: { stream: this.localStream } }));
    } catch (e) {
      console.error('[WebRTC] Failed to capture local media on accept:', e);
      this.rejectCall();
      return;
    }

    // Set Remote Description (Offer)
    await this.peerConnection.setRemoteDescription(new RTCSessionDescription({
      type: 'offer',
      sdp: call.pendingOfferSdp,
    }));

    // Create SDP Answer
    const answer = await this.peerConnection.createAnswer();
    await this.peerConnection.setLocalDescription(answer);

    store.setActiveCall({
      ...call,
      status: 'connected',
    });

    wsClient.sendCallSignal({
      action: 'answer',
      call_id: call.callId,
      caller_id: call.remoteUserId,
      sdp: answer.sdp,
    });
  }

  rejectCall() {
    this.stopRingtone();
    const call = store.activeCall;
    if (call) {
      wsClient.sendCallSignal({
        action: 'reject',
        call_id: call.callId,
        caller_id: call.remoteUserId,
      });
      store.setActiveCall(null);
    }
  }

  hangup() {
    this.stopRingtone();
    const call = store.activeCall;
    if (call) {
      wsClient.sendCallSignal({
        action: 'hangup',
        call_id: call.callId,
        target_user_id: call.remoteUserId,
      });
    }

    if (this.localStream) {
      this.localStream.getTracks().forEach((t) => t.stop());
      this.localStream = null;
    }
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    store.setActiveCall(null);
    this.currentCallId = null;
  }

  toggleMute() {
    if (this.localStream) {
      const audioTrack = this.localStream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        this.isMuted = !audioTrack.enabled;
        return this.isMuted;
      }
    }
    return false;
  }

  toggleVideo() {
    if (this.localStream) {
      const videoTrack = this.localStream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        this.isVideoOff = !videoTrack.enabled;
        return this.isVideoOff;
      }
    }
    return false;
  }

  async handleSignal(payload) {
    const { action, sdp, candidate, from_user_id, call_id, call_type, conversation_id } = payload;

    switch (action) {
      case 'offer':
        this.currentCallId = call_id;
        this.startRingtone(true); // Incoming ringtone
        store.setActiveCall({
          callId: call_id,
          conversationId: conversation_id,
          remoteUserId: from_user_id,
          callType: call_type || 'audio',
          status: 'incoming',
          isCaller: false,
          pendingOfferSdp: sdp,
        });
        break;

      case 'answer':
        this.stopRingtone();
        if (this.peerConnection) {
          await this.peerConnection.setRemoteDescription(new RTCSessionDescription({
            type: 'answer',
            sdp,
          }));
          const call = store.activeCall;
          if (call) {
            store.setActiveCall({ ...call, status: 'connected' });
          }
        }
        break;

      case 'ice_candidate':
        if (this.peerConnection && candidate) {
          try {
            await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
          } catch (e) {
            console.warn('[WebRTC] Error adding ICE candidate:', e);
          }
        }
        break;

      case 'reject':
      case 'hangup':
      case 'offline':
        this.stopRingtone();
        if (this.localStream) {
          this.localStream.getTracks().forEach((t) => t.stop());
          this.localStream = null;
        }
        if (this.peerConnection) {
          this.peerConnection.close();
          this.peerConnection = null;
        }
        store.setActiveCall(null);
        alert(action === 'offline' ? 'User is currently offline.' : 'Call ended.');
        break;
    }
  }

  // --- Synthesized Ringtone using Web Audio API ---
  startRingtone(isIncoming = false) {
    try {
      this.stopRingtone();
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      this.audioContext = new AudioCtx();

      const osc = this.audioContext.createOscillator();
      const gain = this.audioContext.createGain();

      osc.type = isIncoming ? 'triangle' : 'sine';
      osc.frequency.setValueAtTime(isIncoming ? 440 : 400, this.audioContext.currentTime);

      // Simple periodic pulse
      gain.gain.setValueAtTime(0.1, this.audioContext.currentTime);

      osc.connect(gain);
      gain.connect(this.audioContext.destination);
      osc.start();
      this.ringtoneOscillator = osc;
    } catch (e) {
      console.warn('AudioContext not allowed without user gesture:', e);
    }
  }

  stopRingtone() {
    if (this.ringtoneOscillator) {
      try {
        this.ringtoneOscillator.stop();
        this.ringtoneOscillator.disconnect();
      } catch (e) {}
      this.ringtoneOscillator = null;
    }
    if (this.audioContext) {
      try {
        this.audioContext.close();
      } catch (e) {}
      this.audioContext = null;
    }
  }
}

export const webrtcManager = new WebRTCManager();
