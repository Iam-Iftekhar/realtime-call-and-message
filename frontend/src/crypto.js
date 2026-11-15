// Project Spectra - Client-Side Cryptographic Subsystem
// Leverages standard Web Crypto API (SubtleCrypto)

export class SpectraCrypto {
  // Base64 Helpers
  static bytesToBase64(bytes) {
    const binString = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('');
    return btoa(binString);
  }

  static base64ToBytes(base64) {
    const binString = atob(base64);
    return Uint8Array.from(binString, (m) => m.charCodeAt(0));
  }

  static arrayBufferToBase64(buffer) {
    return this.bytesToBase64(new Uint8Array(buffer));
  }

  static base64ToArrayBuffer(base64) {
    return this.base64ToBytes(base64).buffer;
  }

  // --- Symmetric Encryption (AES-256-GCM) ---

  static async generateSymmetricKey() {
    return await window.crypto.subtle.generateKey(
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );
  }

  static async exportKeyRaw(key) {
    const raw = await window.crypto.subtle.exportKey('raw', key);
    return this.arrayBufferToBase64(raw);
  }

  static async importKeyRaw(keyBase64) {
    const raw = this.base64ToArrayBuffer(keyBase64);
    return await window.crypto.subtle.importKey(
      'raw',
      raw,
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );
  }

  static async encryptPayload(plaintextStr, key) {
    const enc = new TextEncoder();
    const data = enc.encode(plaintextStr);
    const iv = window.crypto.getRandomValues(new Uint8Array(12)); // 96-bit standard IV

    const ciphertextBuffer = await window.crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      data
    );

    return {
      ciphertext: this.arrayBufferToBase64(ciphertextBuffer),
      iv: this.bytesToBase64(iv),
    };
  }

  static async decryptPayload(ciphertextBase64, ivBase64, key) {
    const ciphertext = this.base64ToArrayBuffer(ciphertextBase64);
    const iv = this.base64ToBytes(ivBase64);

    const decryptedBuffer = await window.crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      ciphertext
    );

    const dec = new TextDecoder();
    return dec.decode(decryptedBuffer);
  }

  // --- Hash & Checksum ---

  static async sha256(dataBytes) {
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', dataBytes);
    return Array.from(new Uint8Array(hashBuffer))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }

  // --- Safety Numbers (Cryptographic Fingerprint) ---
  // Formats a 60-digit numeric fingerprint in 12 groups of 5 digits from two identity strings

  static async generateSafetyNumber(userId1, userId2) {
    const sorted = [userId1, userId2].sort().join(':');
    const enc = new TextEncoder();
    const hash = await window.crypto.subtle.digest('SHA-512', enc.encode(sorted));
    const bytes = new Uint8Array(hash);

    let digits = '';
    for (let i = 0; i < 30; i++) {
      const val = (bytes[i * 2] << 8) | bytes[i * 2 + 1];
      digits += (val % 100000).toString().padStart(5, '0');
    }
    // Return 12 blocks of 5 numbers
    const blocks = [];
    for (let i = 0; i < 12; i++) {
      blocks.push(digits.substring(i * 5, i * 5 + 5));
    }
    return blocks.join(' ');
  }

  // --- Client Identity Key Management ---

  static getOrCreateDeviceKeys() {
    let keyData = localStorage.getItem('spectra_identity_keys');
    if (!keyData) {
      // Generate client-side Curve25519 / mock prekey bundle tokens
      const randomIdKey = this.bytesToBase64(window.crypto.getRandomValues(new Uint8Array(32)));
      const randomSignedKey = this.bytesToBase64(window.crypto.getRandomValues(new Uint8Array(32)));
      const randomSig = this.bytesToBase64(window.crypto.getRandomValues(new Uint8Array(64)));

      keyData = JSON.stringify({
        identityKey: randomIdKey,
        signedPrekey: {
          key_id: 1,
          public_key: randomSignedKey,
          signature: randomSig,
        },
      });
      localStorage.setItem('spectra_identity_keys', keyData);
    }
    return JSON.parse(keyData);
  }
}
