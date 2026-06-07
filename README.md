# RefugeeHealthChain

> Immutable Identity and Medical Records for Refugees and Displaced Persons
> Built on Polygon blockchain | Real UNHCR and WHO data | June 2026

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Blockchain: Polygon](https://img.shields.io/badge/Blockchain-Polygon-8247E5.svg)](https://polygon.technology/)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Data: UNHCR+WHO](https://img.shields.io/badge/Data-UNHCR%20%2B%20WHO-red.svg)](https://api.unhcr.org)

---

## The Problem

Over 117 million people are currently forcibly displaced worldwide (UNHCR 2026). When refugees flee conflict zones:

- Medical histories are lost or destroyed
- Identity documents do not cross borders
- Aid double-dipping and ghost beneficiaries drain humanitarian budgets
- Disease outbreaks like the 2026 DRC Ebola epidemic (1,262 cases, 349 deaths) cannot be cross-referenced with displaced population records in real time

RefugeeHealthChain solves this with blockchain-anchored, tamper-proof records that preserve privacy while enabling verification.

---

## Live Data Context (June 2026)

| Source | Data |
|--------|------|
| UNHCR API | 39.3M+ displaced in East and Central Africa |
| WHO DON API | 50 active outbreak alerts including 3 high priority |
| WHO PHEIC | Ebola DRC and Uganda declared 16 May 2026 |
| Focus Region | Kenya, Uganda, Ethiopia, DRC, Somalia, Sudan, South Sudan, Tanzania |

---

## Architecture---

## Project Structure---

## Smart Contracts

### RefugeeRegistry.sol

Registers refugee identities on-chain using SHA-256 hashes. Zero PII stored on the blockchain.

- Role-based access control (REGISTRAR and AUDITOR roles)
- Emergency pause functionality
- Country-level population counters
- Links to medical record hashes
- Full audit trail via events

### MedicalRecord.sol

Anchors medical record hashes on-chain for tamper-proof verification.

- Supports 8 record types including vaccination, diagnosis, and outbreak exposure
- Dual-signature verification requiring two health workers
- Outbreak exposure tracking with ICD-10 codes
- IPFS document link hashing
- Real context: tracks 2026 Ebola exposures (ICD-10 A98.4)

---

## Privacy Design

This system is privacy-preserving by design and compliant with UNHCR Data Protection Policy:

- No PII ever stored on-chain
- Only SHA-256 hashes of identity bundles go to the blockchain
- Actual documents stored encrypted in IPFS
- On-chain data provides proof of existence and integrity only
- Salted HMAC-SHA256 prevents rainbow table attacks
- Verification possible without revealing underlying data

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the repository### 2. Install dependencies### 2. Install dependencies### 3. Configure environment### 4. Start local blockchain - keep this terminal open### 5. Deploy contracts in a new terminal### 6. Run data pipeline### 7. Launch dashboardOpen http://localhost:8050 in your browser.

---

## Data Sources

| API | Purpose | Auth |
|-----|---------|------|
| UNHCR Refugee Statistics API | Global displacement data | None - free public API |
| WHO Disease Outbreak News API | Active outbreak alerts | None - free public API |

---

## Roadmap

- [x] Smart contract development (RefugeeRegistry and MedicalRecord)
- [x] Local blockchain deployment via Hardhat
- [x] Live UNHCR data pipeline
- [x] Live WHO outbreak alerts pipeline
- [x] Privacy-preserving SHA-256 hasher
- [x] Analytics dashboard
- [ ] web3.py on-chain anchoring
- [ ] Polygon Amoy testnet deployment
- [ ] PostgreSQL off-chain mirror
- [ ] IPFS document storage

---

## Author

Kevin Mbugua
Blockchain Data Engineer
Nairobi, Kenya
GitHub: https://github.com/mbuguakevvz

---

## License

MIT License - Open for humanitarian use and adaptation.
