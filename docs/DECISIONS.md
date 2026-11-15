# Project Spectra: Architectural Decision Records (ADRs)

> **Document Status**: Approved Baseline (Phase 0)  
> **Authors**: Principal Software Architect & Technical Lead  
> **Target Audience**: Core Engineering Team, Architects, Security Auditors

---

## Index of Architectural Decision Records

- [ADR-001: Modular Monolith Architecture over Microservices](#adr-001-modular-monolith-architecture-over-microservices)
- [ADR-002: Cryptographic Engine Selection (`@matrix-org/vodozemac`)](#adr-002-cryptographic-engine-selection-matrix-orgvodozemac)
- [ADR-003: Vanilla JavaScript (ES6+) & Web Components over Frontend Frameworks](#adr-003-vanilla-javascript-es6--web-components-over-frontend-frameworks)
- [ADR-004: Group Messaging Protocol: Megolm Sender Keys over Pairwise Mesh](#adr-004-group-messaging-protocol-megolm-sender-keys-over-pairwise-mesh)
- [ADR-005: Untrusted Store-and-Forward Mailbox with Immediate ACK Pruning](#adr-005-untrusted-store-and-forward-mailbox-with-immediate-ack-pruning)
- [ADR-006: WebRTC Signaling Multiplexed over Primary WebSocket Gateway](#adr-006-webrtc-signaling-multiplexed-over-primary-websocket-gateway)
- [ADR-007: Coturn with REST API Ephemeral Credentials for TURN Relay](#adr-007-coturn-with-rest-api-ephemeral-credentials-for-turn-relay)
- [ADR-008: Multi-Device Cryptography: Device-Bound Keys & Client-Side Fan-Out](#adr-008-multi-device-cryptography-device-bound-keys--client-side-fan-out)
- [ADR-009: Sealed Sender & Metadata Minimization Strategy](#adr-009-sealed-sender--metadata-minimization-strategy)

---

### ADR-001: Modular Monolith Architecture over Microservices

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  Spectra is a new real-time communication platform requiring high developmental velocity, strict transactional integrity, and low operational friction for self-hosters. A microservices architecture introduces network latency, distributed state synchronization, distributed transactions, and substantial deployment complexity (Kubernetes, service meshes).
- **Decision**:  
  We will construct the backend as a single deployable **Modular Monolith** using Python, FastAPI, and SQLAlchemy 2.0. Internal domains (`auth`, `users`, `devices`, `messaging`, `groups`, `calling`, `encryption`, `notifications`) are partitioned into independent Python packages. Modules communicate via direct in-memory service calls and database transactions. Cross-module direct table joins are strictly forbidden.
- **Consequences**:
  - *Positive*: Simple single-container Docker deployment; sub-millisecond in-process communication; atomic database transactions; straightforward local development.
  - *Negative*: Shared CPU/memory resources; failure in one module can potentially crash the process (mitigated by isolated error handling and ASGI worker isolation).
  - *Evolution*: Any module can be extracted into an independent microservice in future phases without rewriting business logic.

---

### ADR-002: Cryptographic Engine Selection (`@matrix-org/vodozemac`)

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  End-to-end encryption in the browser requires a robust, memory-safe, audited cryptographic library supporting the Double Ratchet (1:1 messaging) and symmetric group ratchets. The two industry candidates are Signal's `@signalapp/libsignal-client` and Matrix's `@matrix-org/vodozemac`.
- **Decision**:  
  Adopt **`@matrix-org/vodozemac`** compiled to WebAssembly (WASM) for client-side cryptographic operations, supplemented by the native browser **Web Crypto API** (`crypto.subtle`) for symmetric attachment encryption (AES-256-GCM).
- **Rationale**:
  1. *Licensing*: `libsignal-client` is licensed under **AGPLv3** (strong copyleft), which imposes viral open-source requirements on the entire platform infrastructure and limits self-hosting flexibility. In contrast, `vodozemac` is licensed under the permissive **Apache-2.0** license.
  2. *Security & Safety*: `vodozemac` is written in 100% pure Rust, eliminating memory corruption vulnerabilities, and was formally audited by Least Authority in 2022.
  3. *Group Efficiency*: `vodozemac` provides native implementations of both Olm (Double Ratchet) and Megolm (ratcheted group sessions), which are essential for scaling group conversations.
- **Consequences**:
  - *Positive*: Permissive licensing; memory-safe WASM execution; proven interoperability with standard WebAssembly runtimes.
  - *Negative*: Requires asynchronous loading and initialization of the `.wasm` binary during client bootstrap.

---

### ADR-003: Vanilla JavaScript (ES6+) & Web Components over Frontend Frameworks

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  Modern frontend frameworks (React, Vue, Angular) introduce extensive dependency trees (thousands of transitive npm packages), virtual DOM reconciliation overhead, large JavaScript bundle sizes, and increased software supply-chain vulnerabilities. Spectra demands a web-first, lightweight, highly responsive interface with zero bloat.
- **Decision**:  
  Build the web client using **Vanilla JavaScript (ES6+)**, native browser **Web Components (`HTMLElement`, Shadow DOM, Custom Elements)**, and **Tailwind CSS**. State management is handled via a native `EventTarget` reactive store.
- **Consequences**:
  - *Positive*: Near-instant initial page loads; zero framework runtime overhead; immune to framework-specific supply-chain exploits; native browser lifecycle hooks; minimal memory footprint.
  - *Negative*: Reusable UI components and state bindings must be constructed using native browser APIs rather than declarative JSX. Virtualized scrolling lists must be explicitly managed.

---

### ADR-004: Group Messaging Protocol: Megolm Sender Keys over Pairwise Mesh

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  In a group of $N$ participants, direct pairwise Double Ratchet encryption requires the sending device to encrypt each message $N-1$ times and upload $N-1$ ciphertexts over the network. For a group of 500 members on a mobile or browser connection, this results in unacceptable CPU burn, battery drain, and network congestion ($O(N)$ client complexity).
- **Decision**:  
  Adopt the **Megolm Sender Keys** ratchet architecture:
  1. Each device maintains an Outbound Group Session (symmetric HKDF ratchet).
  2. The session key is distributed to other group members via their 1:1 pairwise Olm sessions.
  3. When sending to the group, the client encrypts the payload **once** using the current Megolm message key, and the server broadcasts the *identical* ciphertext to all group members ($O(1)$ client complexity).
  4. When a member leaves or is removed, all remaining members immediately invalidate their outbound sessions and establish new keys shared only with remaining members.
- **Consequences**:
  - *Positive*: Extremely efficient bandwidth usage ($O(1)$ client upload); supports groups of hundreds of users effortlessly; maintains backward secrecy and post-removal forward secrecy.
  - *Negative*: Does not provide per-message Diffie-Hellman break-in recovery within an existing group session; forward secrecy within a group session relies on symmetric ratchet advancement.

---

### ADR-005: Untrusted Store-and-Forward Mailbox with Immediate ACK Pruning

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  Spectra's server must deliver messages to offline devices without having access to plaintext contents, while strictly minimizing stored metadata to prevent long-term data exposure during server seizure or breach.
- **Decision**:  
  Implement an **Untrusted Store-and-Forward Mailbox** in PostgreSQL:
  1. Messages are uploaded as opaque ciphertext envelopes addressed to target `recipient_device_id`s.
  2. The server queues envelopes until the target device connects and issues a `SYNC_REQUEST`.
  3. Upon receiving and decrypting an envelope into local IndexedDB, the recipient device sends a `MESSAGE_ACK`.
  4. The server **immediately hard-deletes** the acknowledged envelope from PostgreSQL (`DELETE FROM message_envelopes WHERE id = ...`).
  5. Uncollected envelopes are purged automatically after a 30-day retention TTL.
- **Consequences**:
  - *Positive*: Server-side database remains virtually empty during normal operation; drastically reduces exposure surface; enforces absolute zero-knowledge storage.
  - *Negative*: Historical message retrieval on a new device requires peer-to-peer sync or zero-knowledge encrypted backups, as historical plaintexts cannot be re-fetched from the server.

---

### ADR-006: WebRTC Signaling Multiplexed over Primary WebSocket Gateway

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  WebRTC requires an out-of-band signaling mechanism to exchange SDP offers, SDP answers, and ICE candidates. We evaluated deploying a dedicated signaling server (e.g., Janus, Pion) versus routing signaling frames over the existing real-time WebSocket connection.
- **Decision**:  
  Multiplex WebRTC call signaling directly over the platform's primary authenticated WebSocket gateway (`/ws/v1/connect`) via dedicated `CALL_SIGNAL` JSON frames.
- **Consequences**:
  - *Positive*: Eliminates the need to maintain, authenticate, and monitor a separate signaling service; reuses established authentication, presence tracking, and Redis pub/sub backplanes; eliminates dual-connection overhead on mobile/browser clients.
  - *Negative*: Signaling messages share bandwidth with chat envelopes (mitigated by prioritizing call signal frames in the client/server dispatch queue).

---

### ADR-007: Coturn with REST API Ephemeral Credentials for TURN Relay

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  Direct peer-to-peer WebRTC connections fail when participants are behind symmetric NATs or corporate firewalls. A TURN relay server is mandatory. However, public or static TURN credentials are prone to bandwidth theft and unauthorized abuse.
- **Decision**:  
  Deploy **Coturn** integrated with the standard **TURN REST API (RFC 7635)**:
  1. The FastAPI backend shares a static HMAC-SHA1 secret key with Coturn.
  2. When a call is negotiated, clients request ephemeral credentials via `GET /api/v1/calling/ice-servers`.
  3. The backend generates a temporary username (`<timestamp>:<user_id>`) and HMAC-SHA1 password with a 1-hour expiration window.
- **Consequences**:
  - *Positive*: Prevents unauthorized relay abuse; standards-compliant across all modern WebRTC browser implementations; enables reliable voice/video calling across strict firewalls.
  - *Negative*: Coturn server must be deployed on an address with unrestricted UDP/TCP ports and configured with public IP addresses.

---

### ADR-008: Multi-Device Cryptography: Device-Bound Keys & Client-Side Fan-Out

- **Status**: Accepted
- **Date**: 2026-11-15
- **Context**:  
  Users expect seamless multi-device messaging (e.g., laptop and mobile phone simultaneously active). In end-to-end encrypted systems, keys can either be shared across devices (requiring risky private key replication) or each device can maintain independent cryptographic identities.
- **Decision**:  
  Bind cryptographic identities strictly to **individual devices**:
  1. Each device generates and holds its own independent `IdentityKeyPair` and prekey bundles.
  2. When sending a message, the sending client queries the prekey directory for all active devices of the recipient **and** all other active devices of the sender.
  3. The sender performs **client-side fan-out**, generating distinct encrypted envelopes under each target device's pairwise Double Ratchet.
  4. The sender uploads this batch in one atomic request, allowing all of the user's personal devices to maintain synchronized chat histories without ever sharing private keys.
- **Consequences**:
  - *Positive*: Cryptographically robust; private keys never leave the hardware device; compromise of one device does not compromise keys of another; seamless multi-device history sync.
  - *Negative*: Encryption computation and upload payload size scale with the number of devices owned by conversation participants ($O(D_{\text{total}})$).

---

### ADR-009: Sealed Sender & Metadata Minimization Strategy

- **Status**: Accepted (Phased Implementation)
- **Date**: 2026-11-15
- **Context**:  
  In standard store-and-forward architectures, the server must read the `sender_device_id` on the outer envelope to authenticate the sender and apply rate limits. This leaks the communication graph (who is talking to whom) to the server.
- **Decision**:  
  Adopt a phased metadata minimization strategy:
  - *Phase 1–4*: Explicit sender routing on outer envelopes for baseline simplicity, combined with aggressive padding (PKCS#7 to nearest 256 bytes) and zero server log retention.
  - *Phase 5 (Hardening)*: Implement **Sealed Sender**:
    1. The client acquires a short-lived Sender Certificate signed by the server during authentication.
    2. The outer envelope contains only the `recipient_device_id` and an encrypted inner envelope.
    3. The inner envelope contains the actual sender identity and payload, encrypted with the recipient's public key.
    4. The server delivers the message to the recipient without knowing the identity of the sender.
- **Consequences**:
  - *Positive*: Shields the social graph from server-side observers; state-of-the-art privacy protection.
  - *Negative*: Complicates server-side spam prevention and abuse mitigation (requires cryptographic delivery tokens).
