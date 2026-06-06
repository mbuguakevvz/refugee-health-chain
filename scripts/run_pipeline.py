import os
import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from data_pipeline.fetchers.unhcr_fetcher import UNHCRFetcher
from data_pipeline.fetchers.who_fetcher   import WHOFetcher
from data_pipeline.processors.record_hasher import RecordHasher

OUTPUT_DIR = Path("data_pipeline/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_pipeline():
    start_time = datetime.utcnow()
    print("\n" + "=" * 55)
    print("  RefugeeHealthChain - Data Pipeline")
    print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("  Author: Kevin Mbugua - github mbuguakevvz")
    print("=" * 55)

    results = {}

    # STEP 1 - UNHCR Data
    print("\n[1/3] Fetching UNHCR refugee statistics...")
    try:
        unhcr = UNHCRFetcher()
        pop_df = unhcr.fetch_population(year=2024)
        pop_df.to_csv(OUTPUT_DIR / "unhcr_population.csv", index=False)
        results["unhcr_records"] = len(pop_df)
        print(f"  OK - {len(pop_df):,} records saved")
    except Exception as e:
        print(f"  FAILED - {e}")
        results["unhcr_records"] = 0

    # STEP 2 - WHO Data
    print("\n[2/3] Fetching WHO outbreak alerts...")
    try:
        who = WHOFetcher()
        outbreak_df = who.fetch_outbreaks()
        outbreak_df.to_csv(OUTPUT_DIR / "who_outbreaks.csv", index=False)
        high = len(outbreak_df[outbreak_df.get("high_priority", False) == True]) if "high_priority" in outbreak_df.columns else 0
        results["who_outbreaks"]   = len(outbreak_df)
        results["who_high_priority"] = high
        print(f"  OK - {len(outbreak_df)} outbreaks | {high} HIGH PRIORITY")
        if high > 0:
            hp = outbreak_df[outbreak_df["high_priority"] == True]
            for _, row in hp.iterrows():
                print(f"       ALERT: {row['disease_type']} - {str(row['regions'])[:50]}")
    except Exception as e:
        print(f"  FAILED - {e}")
        results["who_outbreaks"] = 0

    # STEP 3 - Hash sample identities
    print("\n[3/3] Hashing sample refugee identities...")
    try:
        hasher = RecordHasher()
        identities = [
            ("Amina Hassan",             "1988-07-22", "SOM", "F", "KEN-2024-001"),
            ("Jean-Pierre Ndayishimiye", "1995-11-03", "BDI", "M", "UGA-2023-445"),
            ("Fatuma Osman",             "2001-02-14", "SOM", "F", "KEN-2022-882"),
            ("Emmanuel Nkurunziza",      "1978-09-30", "COD", "M", "UGA-2024-120"),
            ("Halima Warsame",           "1993-05-18", "SOM", "F", "ETH-2023-667"),
        ]
        hashed = []
        for name, dob, origin, gender, unhcr_id in identities:
            h = hasher.hash_identity(name, dob, origin, gender, unhcr_id)
            h["ready_for_chain"] = True
            hashed.append(h)
        hashed_df = pd.DataFrame(hashed)
        hashed_df.to_csv(OUTPUT_DIR / "hashed_identities.csv", index=False)
        results["hashed_identities"] = len(hashed)
        print(f"  OK - {len(hashed)} identities hashed and ready for chain")
    except Exception as e:
        print(f"  FAILED - {e}")
        results["hashed_identities"] = 0

    # Summary
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    results["last_run"]        = end_time.isoformat()
    results["duration_seconds"] = round(duration, 2)

    with open(OUTPUT_DIR / "pipeline_summary.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 55)
    print("  PIPELINE COMPLETE")
    print(f"  Duration:          {duration:.1f}s")
    print(f"  UNHCR records:     {results.get('unhcr_records', 0):,}")
    print(f"  WHO outbreaks:     {results.get('who_outbreaks', 0)}")
    print(f"  High priority:     {results.get('who_high_priority', 0)}")
    print(f"  Hashed identities: {results.get('hashed_identities', 0)}")
    print("=" * 55)
    print("\n  Next: python dashboard/app.py")
    return results

if __name__ == "__main__":
    run_pipeline()
