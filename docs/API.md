# Project Spectra: API & Protocol Specification

> **Document Status**: Approved Baseline (Phase 0)  
> **Authors**: Principal Software Architect & Technical Lead  
> **Target Audience**: Backend Engineers, Frontend Engineers, Security Auditors

---

## 1. Protocol Architecture & Conventions

Spectra implements a dual transport architecture:
1. **REST API (`/api/v1/*`)**: Used for resource lifecycle, authentication, key bundle directory operations, session management, and encrypted blob uploads/downloads.
2. **WebSocket Gateway (`/ws/v1/connect`)**: Used for bidirectional real-time envelope dispatch, typing indicators, presence broadcasts, and WebRTC signaling.

### Standard Request & Response Rules
- **Base URI**: `https://api.spectra.internal/api/v1`
- **Content-Type**: `application/json` (except attachment file uploads: `multipart/form-data`)
- **Authentication**: HTTP Bearer JWT passed in `Authorization: Bearer <access_token>`.
- **Error Format (RFC 7807)**: All 4xx and 5xx responses return standard Problem Details:
  ```json
  {
    "type": "https://docs.spectra.chat/errors/invalid-credentials",
    "title": "Invalid Credentials",
    "status": 401,
    "detail": "The username or password provided was incorrect.",
    "instance": "/api/v1/auth/login",
    "code": "AUTH_INVALID_CREDENTIALS"
  }
  ```

---

## 2. Authentication & Session REST Endpoints

### 2.1 Register User
- **Method / Path**: `POST /api/v1/auth/register`
- **Access**: Public (Requires valid Invite Code)
- **Request Body**:
  ```json
  {
    "username": "alice",
    "password": "CorrectHorseBatteryStaple99!",
    "display_name": "Alice Cooper",
    "invite_code": "SPECTRA-INIT-2026-X7",
    "initial_device": {
      "device_identifier": "web-chrome-linux-8f92b",
      "device_name": "Alice ThinkPad (Chrome)",
      "client_platform": "web",
      "client_version": "1.0.0"
    }
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "user": {
      "id": "018f9e2b-1001-7000-8000-000000000001",
      "username": "alice",
      "display_name": "Alice Cooper",
      "created_at": "2026-11-15T23:30:00Z"
    },
    "device": {
      "id": "018f9e2b-2001-7000-8000-000000000001",
      "device_identifier": "web-chrome-linux-8f92b",
      "device_name": "Alice ThinkPad (Chrome)"
    },
    "tokens": {
      "access_token": "eyJhbGciOi...",
      "token_type": "Bearer",
      "expires_in": 900,
      "refresh_token": "rt_98ab710efc42..."
    }
  }
  ```

### 2.2 Login & Session Initiation
- **Method / Path**: `POST /api/v1/auth/login`
- **Request Body**:
  ```json
  {
    "username": "alice",
    "password": "CorrectHorseBatteryStaple99!",
    "device": {
      "device_identifier": "web-chrome-linux-8f92b",
      "device_name": "Alice ThinkPad (Chrome)",
      "client_platform": "web",
      "client_version": "1.0.0"
    }
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "user": { "id": "018f9e2b-1001-7000-8000-000000000001", "username": "alice" },
    "device": { "id": "018f9e2b-2001-7000-8000-000000000001" },
    "tokens": {
      "access_token": "eyJhbGciOi...",
      "token_type": "Bearer",
      "expires_in": 900,
      "refresh_token": "rt_c491a0b38e..."
    }
  }
  ```

### 2.3 Refresh Token Rotation
- **Method / Path**: `POST /api/v1/auth/refresh`
- **Request Body**:
  ```json
  {
    "refresh_token": "rt_c491a0b38e..."
  }
  ```
- **Response `200 OK`**: Returns a new access token and a **rotated** refresh token. (If an already-rotated token is reused, all tokens in the family are instantly revoked).

### 2.4 Active Sessions & Device Revocation
- `GET /api/v1/auth/sessions`: Returns list of all active sessions and bound devices.
- `DELETE /api/v1/auth/sessions/{session_id}`: Revokes target session and disconnects its active WebSockets.

---

## 3. Cryptographic Key Management (PreKey Directory)

### 3.1 Upload Pre-Key Bundle
Clients invoke this after registration or when one-time prekeys are low.
- **Method / Path**: `POST /api/v1/crypto/prekeys/upload`
- **Request Body**:
  ```json
  {
    "device_id": "018f9e2b-2001-7000-8000-000000000001",
    "identity_key": "MCowBQYDK2VuAyEA...",
    "signed_prekey": {
      "key_id": 1,
      "public_key": "MCowBQYDK2VuAyEA...",
      "signature": "MEYCIQDxK9..."
    },
    "one_time_prekeys": [
      { "key_id": 1001, "public_key": "MCowBQYDK2VuAyEA..." },
      { "key_id": 1002, "public_key": "MCowBQYDK2VuAyEA..." }
    ]
  }
  ```
- **Response `200 OK`**: `{ "status": "uploaded", "otk_count": 2 }`

### 3.2 Fetch Recipient Device List
Before sending a message, a sender discovers the active recipient devices.
- **Method / Path**: `GET /api/v1/crypto/prekeys/{user_id}/devices`
- **Response `200 OK`**:
  ```json
  {
    "user_id": "018f9e2b-1002-7000-8000-000000000002",
    "devices": [
      { "device_id": "018f9e2b-2002-7000-8000-000000000002", "device_name": "Bob Pixel 8", "is_active": true },
      { "device_id": "018f9e2b-2002-7000-8000-000000000003", "device_name": "Bob Mac Studio", "is_active": true }
    ]
  }
  ```

### 3.3 Fetch Pre-Key Bundles for Session Initiation (X3DH)
- **Method / Path**: `POST /api/v1/crypto/prekeys/bundle`
- **Request Body**:
  ```json
  {
    "device_ids": [
      "018f9e2b-2002-7000-8000-000000000002",
      "018f9e2b-2002-7000-8000-000000000003"
    ]
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "bundles": [
      {
        "device_id": "018f9e2b-2002-7000-8000-000000000002",
        "identity_key": "MCowBQYDK2VuAyEA...",
        "signed_prekey": {
          "key_id": 1,
          "public_key": "MCowBQYDK2VuAyEA...",
          "signature": "MEYCIQDxK9..."
        },
        "one_time_prekey": {
          "key_id": 1001,
          "public_key": "MCowBQYDK2VuAyEA..."
        }
      }
    ]
  }
  ```
*(Note: The server atomically flags `one_time_prekey` as consumed).*

---

## 4. Conversations & Group Management

- `GET /api/v1/conversations`: Returns list of conversations the authenticated user participates in.
- `POST /api/v1/conversations`:
  ```json
  {
    "type": "group",
    "title": "Spectra Core Architecture",
    "participant_user_ids": [
      "018f9e2b-1002-7000-8000-000000000002",
      "018f9e2b-1003-7000-8000-000000000003"
    ]
  }
  ```
- `POST /api/v1/conversations/{id}/members`: Adds members to a group. (Triggers Megolm Sender Key rotation).
- `DELETE /api/v1/conversations/{id}/members/{user_id}`: Removes a member. (Triggers immediate Sender Key invalidation).

---

## 5. Encrypted Attachments API

Files and media are encrypted **client-side** with a fresh ephemeral AES-256-GCM key prior to HTTP upload.

### 5.1 Upload Encrypted Blob
- **Method / Path**: `POST /api/v1/attachments/upload`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Opaque binary ciphertext
  - `sha256_checksum`: Checksum of the ciphertext blob
- **Response `201 Created`**:
  ```json
  {
    "attachment_id": "018f9e2b-5001-7000-8000-000000000001",
    "file_size_bytes": 1048576,
    "download_url": "/api/v1/attachments/018f9e2b-5001-7000-8000-000000000001"
  }
  ```

### 5.2 Download Encrypted Blob
- **Method / Path**: `GET /api/v1/attachments/{id}`
- **Response `200 OK`**: Returns raw binary stream `application/octet-stream`.

---

## 6. WebRTC Calling REST Endpoints

### 6.1 Obtain STUN/TURN ICE Servers
- **Method / Path**: `GET /api/v1/calling/ice-servers`
- **Response `200 OK`**:
  ```json
  {
    "ice_servers": [
      {
        "urls": "stun:turn.spectra.chat:3478"
      },
      {
        "urls": [
          "turn:turn.spectra.chat:3478?transport=udp",
          "turn:turn.spectra.chat:3478?transport=tcp",
          "turns:turn.spectra.chat:5349?transport=tcp"
        ],
        "username": "1718003600:018f9e2b-1001-7000-8000-000000000001",
        "credential": "Xj7b019v2+qL..."
      }
    ],
    "ttl": 3600
  }
  ```

---

## 7. WebSocket Protocol Specification

The WebSocket connection (`/ws/v1/connect`) multiplexes all real-time events.

### 7.1 WebSocket Frame Schema

Every frame transmitted across the WebSocket conforms to the unified JSON structure:
```json
{
  "version": "1.0",
  "id": "msg_018f9e2b-7001",
  "type": "FRAME_TYPE_STRING",
  "timestamp": 1718000000000,
  "payload": {}
}
```

### 7.2 Connection & Authentication Flow

#### Frame: `AUTH_INIT` (Client $\to$ Server)
```json
{
  "id": "f_01",
  "type": "AUTH_INIT",
  "timestamp": 1718000000100,
  "payload": {
    "token": "eyJhbGciOi...",
    "device_id": "018f9e2b-2001-7000-8000-000000000001"
  }
}
```

#### Frame: `AUTH_SUCCESS` (Server $\to$ Client)
```json
{
  "id": "f_02",
  "type": "AUTH_SUCCESS",
  "timestamp": 1718000000200,
  "payload": {
    "session_id": "sess_8819a",
    "user_id": "018f9e2b-1001-7000-8000-000000000001",
    "server_time": 1718000000200,
    "last_sequence_id": 4820
  }
}
```

---

### 7.3 Real-Time Envelope Transmission & Fan-Out

#### Frame: `ENVELOPE_SEND` (Client $\to$ Server)
Transmitted when a client dispatches an encrypted message to one or more recipient devices.
```json
{
  "id": "f_10",
  "type": "ENVELOPE_SEND",
  "timestamp": 1718000001000,
  "payload": {
    "conversation_id": "018f9e2b-3001-7000-8000-000000000001",
    "envelopes": [
      {
        "recipient_device_id": "018f9e2b-2002-7000-8000-000000000002",
        "envelope_type": "olm_msg",
        "ciphertext": "3k9La0vA...",
        "iv": "vB902ka..."
      },
      {
        "recipient_device_id": "018f9e2b-2002-7000-8000-000000000003",
        "envelope_type": "olm_msg",
        "ciphertext": "8Lm109z...",
        "iv": "99akL..."
      }
    ]
  }
}
```

#### Frame: `ENVELOPE_RECEIVE` (Server $\to$ Client)
Delivered down the WebSocket to the destination device.
```json
{
  "id": "f_11",
  "type": "ENVELOPE_RECEIVE",
  "timestamp": 1718000001050,
  "payload": {
    "envelope_id": "018f9e2b-4001-7000-8000-000000000001",
    "conversation_id": "018f9e2b-3001-7000-8000-000000000001",
    "sender_device_id": "018f9e2b-2001-7000-8000-000000000001",
    "sequence_id": 4821,
    "envelope_type": "olm_msg",
    "ciphertext": "3k9La0vA...",
    "iv": "vB902ka...",
    "created_at": "2026-11-15T23:30:01Z"
  }
}
```

#### Frame: `ENVELOPE_ACK` (Client $\to$ Server)
Sent by the client immediately after successfully decrypting and committing to local IndexedDB.
```json
{
  "id": "f_12",
  "type": "ENVELOPE_ACK",
  "timestamp": 1718000001120,
  "payload": {
    "envelope_ids": ["018f9e2b-4001-7000-8000-000000000001"],
    "last_sequence_id": 4821
  }
}
```

---

### 7.4 Presence & Typing Indicators

#### Frame: `TYPING_EVENT` (Bidirectional)
```json
{
  "id": "f_20",
  "type": "TYPING_EVENT",
  "timestamp": 1718000002000,
  "payload": {
    "conversation_id": "018f9e2b-3001-7000-8000-000000000001",
    "user_id": "018f9e2b-1001-7000-8000-000000000001",
    "is_typing": true
  }
}
```

#### Frame: `PRESENCE_UPDATE` (Server $\to$ Client)
```json
{
  "id": "f_21",
  "type": "PRESENCE_UPDATE",
  "timestamp": 1718000002500,
  "payload": {
    "user_id": "018f9e2b-1002-7000-8000-000000000002",
    "status": "online",
    "last_seen": 1718000002500
  }
}
```

---

### 7.5 WebRTC Calling Signaling Sub-Protocol

All WebRTC call setup messages are wrapped inside `CALL_SIGNAL` frames.

#### Action: `offer` (Caller $\to$ Server $\to$ Callee)
```json
{
  "id": "f_30",
  "type": "CALL_SIGNAL",
  "timestamp": 1718000005000,
  "payload": {
    "action": "offer",
    "call_id": "018f9e2b-6001-7000-8000-000000000001",
    "conversation_id": "018f9e2b-3001-7000-8000-000000000001",
    "caller_id": "018f9e2b-1001-7000-8000-000000000001",
    "caller_device_id": "018f9e2b-2001-7000-8000-000000000001",
    "callee_id": "018f9e2b-1002-7000-8000-000000000002",
    "call_type": "video",
    "sdp": "v=0\r\no=- 461173... IN IP4 0.0.0.0\r\ns=-\r\nt=0 0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111...\r\n"
  }
}
```

#### Action: `answer` (Callee $\to$ Server $\to$ Caller)
```json
{
  "id": "f_31",
  "type": "CALL_SIGNAL",
  "timestamp": 1718000006200,
  "payload": {
    "action": "answer",
    "call_id": "018f9e2b-6001-7000-8000-000000000001",
    "callee_device_id": "018f9e2b-2002-7000-8000-000000000002",
    "sdp": "v=0\r\no=- 891241... IN IP4 0.0.0.0\r\ns=-\r\n..."
  }
}
```

#### Action: `ice_candidate` (Bidirectional)
```json
{
  "id": "f_32",
  "type": "CALL_SIGNAL",
  "timestamp": 1718000006500,
  "payload": {
    "action": "ice_candidate",
    "call_id": "018f9e2b-6001-7000-8000-000000000001",
    "candidate": {
      "candidate": "candidate:842163049 1 udp 1677729535 192.168.1.150 54123 typ srflx raddr 10.0.0.1 rport 54123...",
      "sdpMid": "0",
      "sdpMLineIndex": 0
    }
  }
}
```

#### Action: `hangup` (Bidirectional)
```json
{
  "id": "f_33",
  "type": "CALL_SIGNAL",
  "timestamp": 1718000010000,
  "payload": {
    "action": "hangup",
    "call_id": "018f9e2b-6001-7000-8000-000000000001",
    "reason": "user_terminated"
  }
}
```

---

## 8. WebSocket Protocol Error Codes

| Code | Label | Meaning | Action Expected |
| :--- | :--- | :--- | :--- |
| `4001` | `AUTH_REQUIRED` | WebSocket frame sent before `AUTH_INIT` | Reconnect and authenticate |
| `4002` | `TOKEN_EXPIRED` | Access JWT expired | Refresh token via REST, reconnect |
| `4003` | `DEVICE_REVOKED` | Target device has been revoked | Clear local credentials, return to login |
| `4004` | `RATE_LIMITED` | Frame rate limit exceeded | Throttle transmission, back off |
| `4005` | `MALFORMED_FRAME` | JSON could not be parsed or failed schema | Fix frame formatting |
| `4009` | `INTERNAL_ERROR` | Server exception during frame dispatch | Exponential backoff reconnect |
