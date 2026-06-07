import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_pipeline.processors.record_hasher import RecordHasher

# ── Config ────────────────────────────────────────────────
RPC_URL          = os.getenv("LOCAL_RPC_URL", "http://127.0.0.1:8545")
REGISTRY_ADDRESS = os.getenv("REFUGEE_REGISTRY_ADDRESS", "")
MEDICAL_ADDRESS  = os.getenv("MEDICAL_RECORD_ADDRESS", "")
OUTPUT_DIR       = Path("data_pipeline/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Hardhat default account #0 private key (local only - never use on mainnet)
LOCAL_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# ── Load ABIs from compiled artifacts ─────────────────────
def load_abi(contract_name: str) -> list:
    path = Path(f"artifacts/blockchain/contracts/{contract_name}.sol/{contract_name}.json")
    if not path.exists():
        raise FileNotFoundError(f"ABI not found: {path}. Run: npx hardhat compile")
    with open(path) as f:
        return json.load(f)["abi"]

# ── Chain Anchor Class ────────────────────────────────────
class ChainAnchor:

    def __init__(self):
        logger.info(f"Connecting to blockchain at {RPC_URL}...")
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to blockchain at {RPC_URL}. Is hardhat node running?")

        logger.success(f"Connected - Chain ID: {self.w3.eth.chain_id} | Block: {self.w3.eth.block_number}")

        self.account = self.w3.eth.account.from_key(LOCAL_PRIVATE_KEY)
        logger.info(f"Deployer account: {self.account.address}")

        registry_abi = load_abi("RefugeeRegistry")
        medical_abi  = load_abi("MedicalRecord")

        self.registry = self.w3.eth.contract(
            address=Web3.to_checksum_address(REGISTRY_ADDRESS),
            abi=registry_abi
        )
        self.medical = self.w3.eth.contract(
            address=Web3.to_checksum_address(MEDICAL_ADDRESS),
            abi=medical_abi
        )
        logger.success("Contracts loaded successfully")

    def _send_tx(self, fn, description: str) -> dict:
        nonce    = self.w3.eth.get_transaction_count(self.account.address)
        gas_est  = fn.estimate_gas({"from": self.account.address})
        tx       = fn.build_transaction({
            "from":     self.account.address,
            "nonce":    nonce,
            "gas":      int(gas_est * 1.2),
            "gasPrice": self.w3.eth.gas_price,
        })
        signed   = self.w3.eth.account.sign_transaction(tx, LOCAL_PRIVATE_KEY)
        tx_hash  = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt  = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        status   = "SUCCESS" if receipt.status == 1 else "FAILED"
        logger.info(f"  {status} | {description} | tx: {tx_hash.hex()[:20]}... | gas: {receipt.gasUsed}")
        return receipt

    def anchor_identity(self, identity_hash: str, biometric_hash: str,
                        origin_iso3: str, asylum_iso3: str, camp: str,
                        displacement_type: int = 0) -> str:
        id_bytes  = bytes.fromhex(identity_hash.replace("0x", ""))
        bio_bytes = bytes.fromhex(biometric_hash.replace("0x", ""))

        try:
            already = self.registry.functions.verifyIdentity(id_bytes).call()
            if already:
                logger.warning(f"Identity already registered: {identity_hash[:20]}...")
                return "ALREADY_EXISTS"
        except Exception:
            pass

        fn      = self.registry.functions.registerRefugee(
            id_bytes, bio_bytes, origin_iso3, asylum_iso3, camp, displacement_type
        )
        receipt = self._send_tx(fn, f"Register {origin_iso3}->{asylum_iso3}")

        if receipt.status == 1:
            logs = self.registry.events.RefugeeRegistered().process_receipt(receipt)
            if logs:
                refugee_id = logs[0]["args"]["refugeeId"].hex()
                logger.success(f"  On-chain ID: 0x{refugee_id[:20]}...")
                return f"0x{refugee_id}"
        return "FAILED"

    def anchor_medical_record(self, refugee_on_chain_id: str, record_hash: str,
                               ipfs_cid_hash: str, record_type: int,
                               facility_iso3: str, facility_name: str,
                               disease_code: str) -> str:
        rid_bytes  = bytes.fromhex(refugee_on_chain_id.replace("0x", ""))
        rec_bytes  = bytes.fromhex(record_hash.replace("0x", ""))
        ipfs_bytes = bytes.fromhex(ipfs_cid_hash.replace("0x", ""))

        fn      = self.medical.functions.anchorRecord(
            rid_bytes, rec_bytes, ipfs_bytes,
            record_type, facility_iso3, facility_name, disease_code
        )
        receipt = self._send_tx(fn, f"Anchor {facility_iso3} {disease_code}")

        if receipt.status == 1:
            logs = self.medical.events.MedicalRecordAnchored().process_receipt(receipt)
            if logs:
                entry_id = logs[0]["args"]["entryId"].hex()
                logger.success(f"  Entry ID: 0x{entry_id[:20]}...")
                return f"0x{entry_id}"
        return "FAILED"

    def get_stats(self) -> dict:
        total = self.registry.functions.totalRegistered().call()
        kenya = self.registry.functions.getCountByCountry("KEN").call()
        uganda= self.registry.functions.getCountByCountry("UGA").call()
        ethiopia=self.registry.functions.getCountByCountry("ETH").call()
        med_total = self.medical.functions.totalRecordsAnchored().call()
        return {
            "total_registered": total,
            "kenya":            kenya,
            "uganda":           uganda,
            "ethiopia":         ethiopia,
            "medical_records":  med_total,
        }

def run_anchoring():
    print("\n" + "=" * 60)
    print("  RefugeeHealthChain - Chain Anchoring")
    print("  Writing hashed records to Polygon blockchain")
    print("  Author: Kevin Mbugua - github mbuguakevvz")
    print("=" * 60)

    anchor = ChainAnchor()
    hasher = RecordHasher()

    # Sample refugee identities to anchor
    identities = [
        ("Amina Hassan",             "1988-07-22", "SOM", "KEN", "Kakuma Camp",     0),
        ("Jean-Pierre Ndayishimiye", "1995-11-03", "BDI", "UGA", "Bidi Bidi",       0),
        ("Fatuma Osman",             "2001-02-14", "SOM", "KEN", "Dadaab Camp",      0),
        ("Emmanuel Nkurunziza",      "1978-09-30", "COD", "UGA", "Nakivale Camp",    0),
        ("Halima Warsame",           "1993-05-18", "SOM", "ETH", "Dollo Ado Camp",  0),
    ]

    print(f"\n[1/3] Anchoring {len(identities)} refugee identities on-chain...")
    anchored = []
    for name, dob, origin, asylum, camp, dtype in identities:
        print(f"\n  Processing: {name} ({origin} -> {asylum})")
        h = hasher.hash_identity(name, dob, origin, "F" if name.split()[0] in ["Amina","Fatuma","Halima"] else "M", "")
        on_chain_id = anchor.anchor_identity(
            h["identity_hash"], h["biometric_hash"],
            origin, asylum, camp, dtype
        )
        anchored.append({
            "name":           name,
            "origin":         origin,
            "asylum":         asylum,
            "camp":           camp,
            "identity_hash":  h["identity_hash"],
            "on_chain_id":    on_chain_id,
            "anchored_at":    datetime.utcnow().isoformat()
        })

    anchored_df = pd.DataFrame(anchored)
    anchored_df.to_csv(OUTPUT_DIR / "anchored_identities.csv", index=False)
    print(f"\n  Saved to data_pipeline/output/anchored_identities.csv")

    # Anchor a medical record for Ebola exposure (2026 outbreak context)
    print(f"\n[2/3] Anchoring Ebola exposure medical record (2026 DRC outbreak)...")
    first_refugee = anchored[0]
    if first_refugee["on_chain_id"] not in ["FAILED", "ALREADY_EXISTS"]:
        med = hasher.hash_medical_record(
            refugee_id_hash = first_refugee["identity_hash"],
            record_type     = "OUTBREAK_EXPOSURE",
            disease_code    = "A98.4",
            treatment       = "Quarantine observation DRC Ebola 2026",
            facility_name   = "Kakuma Health Center",
            facility_iso3   = "KEN",
            worker_id       = "HW-KEN-0042",
            record_date     = "2026-05-20"
        )
        entry_id = anchor.anchor_medical_record(
            refugee_on_chain_id = first_refugee["on_chain_id"],
            record_hash         = med["record_hash"],
            ipfs_cid_hash       = med["ipfs_cid_hash"],
            record_type         = 4,
            facility_iso3       = "KEN",
            facility_name       = "Kakuma Health Center",
            disease_code        = "A98.4"
        )
        print(f"  Medical record anchored: {entry_id[:25] if entry_id else 'FAILED'}...")

    # Print final stats
    print(f"\n[3/3] Reading on-chain stats...")
    stats = anchor.get_stats()
    print("\n" + "=" * 60)
    print("  CHAIN ANCHORING COMPLETE")
    print(f"  Total registered on-chain: {stats['total_registered']}")
    print(f"  Kenya (KEN):               {stats['kenya']}")
    print(f"  Uganda (UGA):              {stats['uganda']}")
    print(f"  Ethiopia (ETH):            {stats['ethiopia']}")
    print(f"  Medical records anchored:  {stats['medical_records']}")
    print("=" * 60)
    print("\n  These records are now immutable on the blockchain.")
    print("  Tamper-proof. Permanent. Verifiable without PII.")

if __name__ == "__main__":
    run_anchoring()
