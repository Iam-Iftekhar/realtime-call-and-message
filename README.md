# Project Spectra

> **A privacy-first, real-time communication platform combining the usability of Telegram, the cryptographic rigor of Signal, and a clean, futuristic web-first interface.**

---

## 1. Project Overview

Project Spectra is an open-source, self-hostable communication platform engineered for high-assurance confidentiality, modern usability, and web-native performance. It is designed to run in modern web browsers without requiring browser extensions or heavyweight desktop runtimes, while maintaining architectural extensibility for future native desktop (Tauri/Electron) and mobile clients.

### Core Tenets

1. **Zero-Knowledge by Default**: The server acts strictly as an untrusted blind relay and mailbox. All one-to-one messages, group messages, and media attachments are end-to-end encrypted (E2EE) on client devices prior to network dispatch. Plaintext payloads and cryptographic private keys are never stored on, inspected by, or accessible to the server.
2. **Standard-Conforming, Audited Cryptography**: No custom cryptographic algorithms. Spectra leverages proven protocols—specifically the Double Ratchet Algorithm, Extended Triple Diffie-Hellman (X3DH), and symmetric Sender Key ratchets (Megolm model)—compiled to WebAssembly (WASM) for memory safety and audited mathematical rigor.
3. **Telegram-Class Usability**: Privacy must not come at the cost of friction. Spectra features instant message delivery, fluid UI transitions, offline message queuing, multi-device synchronization, typing indicators, delivery/read receipts, rich media sharing, and high-fidelity WebRTC voice/video calling.
4. **Lean, Framework-Free Frontend**: The web client is built with modern Vanilla JavaScript (ES6+), standard Web Components, Tailwind CSS, and HTML5 Web APIs. It eliminates heavy frontend framework overhead, minimizes attack surface, and executes cryptographic primitives at native WASM speed.
5. **Self-Hostable Modular Monolith**: The backend is architected as an asynchronous, single-deployable modular monolith in Python and FastAPI, supported by PostgreSQL for durable persistence and Redis for ephemeral state, caching, and pub/sub signaling.

---

## 2. Technology Stack

| Layer | Technology | Version / Specification | Architectural Role |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python | 3.12+ | High-performance asynchronous backend application runtime |
| **Web Framework** | FastAPI | 0.111+ | Asynchronous REST API routing, Pydantic v2 validation, OpenAPI docs |
| **ASGI Server** | Uvicorn / Granian | Current Stable | Production ASGI event loop handling HTTP/1.1, HTTP/2, and WebSockets |
| **Database ORM** | SQLAlchemy | 2.0+ (Async) | Strict type-annotated asynchronous ORM and query builder |
| **DB Migrations** | Alembic | 1.13+ | Versioned database schema migrations |
| **Primary Database** | PostgreSQL | 16+ | ACID-compliant storage for users, devices, prekey bundles, and encrypted mailboxes |
| **Cache & Real-Time** | Redis | 7.2+ | Ephemeral state, presence tracking, rate limiting, and pub/sub message backplane |
| **WebRTC Gateway** | Coturn | 4.6+ | STUN/TURN server providing NAT traversal and relay with HMAC-SHA1 REST tokens |
| **Frontend Runtime** | Vanilla JavaScript | ES2022+ | Native browser JavaScript leveraging Web Components and Web Crypto API |
| **Client Crypto** | `@matrix-org/vodozemac` | WASM / Rust | Audited Rust implementation of Olm (Double Ratchet) and Megolm compiled to WASM |
| **Styling** | Tailwind CSS | 3.4+ / 4.x | Utility-first CSS pipeline for responsive, futuristic dark-first design |
| **Client Storage** | IndexedDB | Modern Browser API | Encrypted local storage for message histories, ratchet states, and key stores |
| **Containerization** | Docker & Compose | Compose v2 | Reproducible multi-service deployment for local dev and self-hosted production |

---

## 3. Project Architecture Summary

```
                       +-------------------------------------------------+
                       |              Client Web Browser                 |
                       |  (Vanilla JS + Web Components + Tailwind CSS)   |
                       |  +-------------------------------------------+  |
                       |  |  Client-Side Cryptographic Engine (WASM)  |  |
                       |  |  - Double Ratchet / Olm (1:1 Messaging)   |  |
                       |  |  - Sender Keys / Megolm (Group Ratchet)   |  |
                       |  |  - AES-256-GCM (Attachment Encryption)    |  |
                       |  |  - IndexedDB (Encrypted Local State)      |  |
                       |  +-------------------------------------------+  |
                       +---------+--------------------+------------------+
                                 |                    |            ^
                   HTTPS REST    |      WebSocket     |            | WebRTC P2P Media
                   (Prekeys, Auth|      (Signaling,   |            | (DTLS-SRTP Audio/Video)
                    Encrypted    |       Real-Time    |            |
                    Blobs)       |       Envelopes)   |            v
                                 v                    v    +---------------+
                       +----------------------------------+|  Remote Peer  |
                       |          Reverse Proxy           || (Direct Mesh) |
                       |          (Nginx / Caddy)         |+-------+-------+
                       +-----------------+----------------+        |
                                         |                         | Relayed Media
                                         v                         | (if Symmetric NAT)
                       +----------------------------------+        v
                       |      Project Spectra Backend     |  +-------------+
                       |    FastAPI Modular Monolith      |  |   Coturn    |
                       |  - auth         - messaging      |  |  STUN/TURN  |
                       |  - devices      - calling        |  |   Server    |
                       |  - encryption   - groups         |  +-------------+
                       |  - users        - notifications  |
                       +--------+----------------+--------+
                                |                |
                  Durable State |                | Ephemeral State / PubSub
                                v                v
                      +-------------------+    +-------------------+
                      |    PostgreSQL     |    |       Redis       |
                      |  - Users & Auth   |    | - Presence Engine |
                      |  - PreKey Bundles |    | - Pub/Sub Hub     |
                      |  - Encrypted Queue|    | - Ephemeral State |
                      |  - Group Metadata |    | - Rate Limiter    |
                      +-------------------+    +-------------------+
```

---

## 4. Phase 0 Documentation Index

This repository contains the complete architectural blueprint and engineering specification for Project Spectra. No application features will be implemented until this foundation is fully verified.

All technical documentation is organized within the `docs/` directory:

| Document | Description |
| :--- | :--- |
| **[System Architecture](file:///home/benimaru/Projects/docs/ARCHITECTURE.md)** | Complete modular monolith design, component interactions, WebSocket protocol, WebRTC signaling, and evolution roadmap. |
| **[Database Specification](file:///home/benimaru/Projects/docs/DATABASE.md)** | Relational PostgreSQL schema, index strategies, Redis ephemeral data structures, and data pruning policies. |
| **[API & Protocol Specification](file:///home/benimaru/Projects/docs/API.md)** | REST endpoints, WebSocket framing formats, WebRTC signaling payloads, error codes, and sequence flows. |
| **[Security & Cryptography](file:///home/benimaru/Projects/docs/SECURITY.md)** | Threat model, cryptographic protocol selection, prekey management, group ratchets, metadata analysis, and device revocation. |
| **[Development Roadmap](file:///home/benimaru/Projects/docs/ROADMAP.md)** | Staged development phases (0 through 5), dependency matrix, milestones, and Definition of Done (DoD). |
| **[Architectural Decisions (ADRs)](file:///home/benimaru/Projects/docs/DECISIONS.md)** | Formal Architectural Decision Records (ADRs 001–009) detailing rationale, trade-offs, and alternatives. |
| **[Testing Strategy](file:///home/benimaru/Projects/docs/TESTING.md)** | Testing pyramid, cryptographic vector verification, WebRTC mocking, integration tests, and CI/CD pipelines. |

---

## 5. Engineering Principles & Ground Rules

1. **Strict Separation of Concerns**: Domain logic is decoupled from transport layers (HTTP/WebSocket) and persistence mechanisms.
2. **Explicit Type Safety**: Strict type annotations across Python (Mypy/Pydantic v2) and ES6+ JavaScript modules.
3. **Zero Secret Hardcoding**: Secrets, private keys, API keys, and credentials must be injected solely via environment variables or secure keyrings.
4. **Log Sanitization**: PII, IP addresses, ciphertext bodies, tokens, and cryptographic keys are strictly excluded from server application logs.
5. **Defense in Depth**: Every API endpoint enforces server-side authorization regardless of client assertions.
6. **No "Fake" Encryption**: Ciphertexts stored on the server must never be decryptable by server-held keys. Encryption claims must reflect mathematically verifiable end-to-end security.

---

## 6. Repository Layout (Planned)

```
project-spectra/
├── .github/                      # CI/CD workflows and automated checks
├── docs/                         # Phase 0 Architecture Specifications
│   ├── ARCHITECTURE.md           # System Architecture & Component Interactions
│   ├── DATABASE.md               # Database Schema, Indexes, & Data Retention
│   ├── API.md                    # REST API & WebSocket Protocol Specs
│   ├── SECURITY.md               # Threat Model & Cryptographic Protocols
│   ├── ROADMAP.md                # Development Phases & Milestones
│   ├── DECISIONS.md              # Architectural Decision Records (ADRs)
│   └── TESTING.md                # Testing Strategy & Verification Plans
├── backend/                      # FastAPI Modular Monolith (Phase 1)
│   ├── alembic/                  # Database migration scripts
│   ├── app/
│   │   ├── core/                 # Config, security utils, database engine
│   │   ├── modules/              # Modular monolith domains
│   │   │   ├── auth/             # Authentication & session rotation
│   │   │   ├── users/            # User profile & contact directory
│   │   │   ├── devices/          # Multi-device registry & prekey directory
│   │   │   ├── messaging/        # Encrypted envelope mailbox & dispatch
│   │   │   ├── groups/           # Group membership & sender key dispatch
│   │   │   ├── calling/          # WebRTC signaling & Coturn credentials
│   │   │   └── notifications/    # Push tokens & presence alerts
│   │   └── main.py               # ASGI entrypoint
│   └── tests/                    # Backend unit & integration test suites
├── frontend/                     # Web-First Vanilla JS Client (Phase 2+)
│   ├── src/
│   │   ├── components/           # Custom HTML5 Web Components
│   │   ├── crypto/               # WASM Ratchet Engine & WebCrypto utils
│   │   ├── services/             # WebSocket, REST API, & WebRTC managers
│   │   ├── store/                # Reactive state store & IndexedDB sync
│   │   └── app.js                # Application entrypoint
│   ├── index.html                # Single-page shell
│   └── tailwind.config.js        # Futuristic dark-first theme tokens
├── docker/                       # Container infrastructure
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── coturn.conf
│   └── docker-compose.yml
└── README.md                     # Project overview and index
```
