import hashlib
import hmac
import json
import os
from datetime import datetime
from loguru import logger

SALT = os.environ.get("HASH_SALT", "refugee_health_chain_dev_salt_2026")

class RecordHasher:

    def __init__(self):
        self.salt = SALT
        if self.salt == "refugee_health_chain_dev_salt_2026":
            logger.warning("Using dev salt - set HASH_SALT in .env for production")

    def _salted_hash(self, payload: str) -> str:
        return hmac.new(
            self.salt.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def to_bytes32(self, hex_str: str) -> str:
        clean = hex_str[:64].ljust(64, "0")
        return f"0x{clean}"

    def hash_identity(self, full_name: str, dob: str, origin_iso3: str, gender: str, unhcr_id: str = "") -> dict:
        payload = json.dumps({
            "name":     full_name.strip().lower(),
            "dob":      dob,
            "origin":   origin_iso3.upper(),
            "gender":   gender.upper(),
            "unhcr_id": unhcr_id or ""
        }, sort_keys=True)

        biometric_payload = json.dumps({
            "name": full_name.strip().lower(),
            "dob":  dob,
        }, sort_keys=True)

        identity_hash  = self._salted_hash(payload)
        biometric_hash = self._salted_hash(biometric_payload)

        result = {
            "identity_hash":  self.to_bytes32(identity_hash),
            "biometric_hash": self.to_bytes32(biometric_hash),
            "origin_iso3":    origin_iso3.upper(),
            "hashed_at":      datetime.utcnow().isoformat()
        }
        logger.debug(f"Hashed identity: {result['identity_hash'][:20]}... origin={origin_iso3}")
        return result

    def hash_medical_record(self, refugee_id_hash: str, record_type: str, disease_code: str,
                             treatment: str, facility_name: str, facility_iso3: str,
                             worker_id: str, record_date: str) -> dict:
        payload = json.dumps({
            "refugee_id":   refugee_id_hash,
            "type":         record_type,
            "disease_code": disease_code,
            "treatment":    treatment,
            "facility":     facility_name,
            "country":      facility_iso3,
            "worker_id":    worker_id,
            "date":         record_date,
        }, sort_keys=True)

        record_hash = self._salted_hash(payload)
        ipfs_hash   = self._salted_hash(f"ipfs_{record_hash}")

        result = {
            "record_hash":     self.to_bytes32(record_hash),
            "ipfs_cid_hash":   self.to_bytes32(ipfs_hash),
            "refugee_id_hash": refugee_id_hash,
            "record_type":     record_type,
            "disease_code":    disease_code,
            "facility_iso3":   facility_iso3,
            "hashed_at":       datetime.utcnow().isoformat()
        }
        logger.debug(f"Hashed medical record: {result['record_hash'][:20]}... type={record_type}")
        return result

    def verify_identity(self, full_name: str, dob: str, origin_iso3: str,
                        gender: str, stored_hash: str, unhcr_id: str = "") -> bool:
        recomputed = self.hash_identity(full_name, dob, origin_iso3, gender, unhcr_id)
        match = recomputed["identity_hash"].lower() == stored_hash.lower()
        logger.info(f"Identity verification: {'MATCH' if match else 'MISMATCH'}")
        return match

if __name__ == "__main__":
    hasher = RecordHasher()

    print("\n RefugeeHealthChain - Record Hasher Demo")
    print("=" * 55)
    print("NOTE: Synthetic data only - no real PII used")
    print("=" * 55)

    identities = [
        ("Amina Hassan",              "1988-07-22", "SOM", "F", "KEN-2024-001"),
        ("Jean-Pierre Ndayishimiye",  "1995-11-03", "BDI", "M", "UGA-2023-445"),
        ("Fatuma Osman",              "2001-02-14", "SOM", "F", "KEN-2022-882"),
        ("Emmanuel Nkurunziza",       "1978-09-30", "COD", "M", "UGA-2024-120"),
        ("Halima Warsame",            "1993-05-18", "SOM", "F", "ETH-2023-667"),
    ]

    hashed_ids = []
    for name, dob, origin, gender, unhcr_id in identities:
        h = hasher.hash_identity(name, dob, origin, gender, unhcr_id)
        hashed_ids.append(h)
        print(f"\n  Name:    {name}")
        print(f"  Origin:  {origin}")
        print(f"  Hash:    {h['identity_hash'][:30]}...")
        print(f"  Bio:     {h['biometric_hash'][:30]}...")

    print("\n\n  Medical Record Hash (Ebola exposure - 2026 DRC outbreak)")
    print("  " + "-" * 50)
    med = hasher.hash_medical_record(
        refugee_id_hash = hashed_ids[0]["identity_hash"],
        record_type     = "OUTBREAK_EXPOSURE",
        disease_code    = "A98.4",
        treatment       = "Quarantine observation - DRC Ebola 2026",
        facility_name   = "Bidi Bidi Health Center",
        facility_iso3   = "UGA",
        worker_id       = "HW-UGA-0088",
        record_date     = "2026-05-20"
    )
    print(f"  Record Hash:   {med['record_hash'][:30]}...")
    print(f"  IPFS Hash:     {med['ipfs_cid_hash'][:30]}...")
    print(f"  Disease Code:  {med['disease_code']} (ICD-10: Ebola)")
    print(f"  Facility:      {med['facility_iso3']}")

    print("\n  All PII stays off-chain. Only hashes go to blockchain.")
    print("=" * 55)
