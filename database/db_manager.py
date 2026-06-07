import os
import pandas as pd
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "dbname":   os.getenv("DB_NAME", "refugee_health_chain"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

class DatabaseManager:

    def __init__(self):
        logger.info("Connecting to PostgreSQL...")
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True
        logger.success("Connected to refugee_health_chain database")

    def load_unhcr_population(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        cur = self.conn.cursor()
        rows = []
        for _, row in df.iterrows():
            rows.append((
                row.get("year"),
                row.get("asylum_country", ""),
                row.get("asylum_iso3", ""),
                row.get("origin_country", ""),
                row.get("origin_iso3", ""),
                int(row.get("refugees", 0) or 0),
                int(row.get("asylum_seekers", 0) or 0),
                int(row.get("idps", 0) or 0),
                int(row.get("total_displaced", 0) or 0),
            ))
        execute_values(cur, """
            INSERT INTO unhcr_population
                (year, asylum_country, asylum_iso3, origin_country, origin_iso3,
                 refugees, asylum_seekers, idps, total_displaced)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, rows)
        count = cur.rowcount
        logger.success(f"Loaded {count} UNHCR population rows into PostgreSQL")
        return count

    def load_who_outbreaks(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        cur = self.conn.cursor()
        rows = []
        for _, row in df.iterrows():
            pub_date = None
            try:
                pub_date = datetime.strptime(str(row.get("publication_date", ""))[:10], "%Y-%m-%d").date()
            except Exception:
                pass
            rows.append((
                str(row.get("title", ""))[:500],
                str(row.get("disease_type", "Unknown")),
                str(row.get("regions", ""))[:300],
                pub_date,
                bool(row.get("who_pheic", False)),
                bool(row.get("high_priority", False)),
                row.get("confirmed_cases") if str(row.get("confirmed_cases", "")) not in ["None", "nan", ""] else None,
                row.get("deaths") if str(row.get("deaths", "")) not in ["None", "nan", ""] else None,
                bool(row.get("africa_relevant", False)),
            ))
        execute_values(cur, """
            INSERT INTO who_outbreaks
                (title, disease_type, regions, publication_date,
                 who_pheic, high_priority, confirmed_cases, deaths, africa_relevant)
            VALUES %s
        """, rows)
        count = cur.rowcount
        logger.success(f"Loaded {count} WHO outbreak rows into PostgreSQL")
        return count

    def load_chain_identities(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        cur = self.conn.cursor()
        rows = []
        for _, row in df.iterrows():
            on_chain_id = str(row.get("on_chain_id", ""))
            if on_chain_id in ["FAILED", "ALREADY_EXISTS", ""]:
                continue
            identity_hash = str(row.get("identity_hash", ""))[:66]
            rows.append((
                on_chain_id[:66],
                identity_hash,
                identity_hash,
                str(row.get("origin", ""))[:3],
                str(row.get("asylum", ""))[:3],
                str(row.get("camp", ""))[:200],
                "REFUGEE",
                "ACTIVE",
            ))
        if not rows:
            logger.warning("No valid chain identity rows to load")
            return 0
        execute_values(cur, """
            INSERT INTO chain_identities
                (on_chain_id, identity_hash, biometric_hash, origin_iso3, asylum_iso3,
                 camp_or_location, displacement_type, record_status)
            VALUES %s
            ON CONFLICT (on_chain_id) DO NOTHING
        """, rows)
        count = cur.rowcount
        logger.success(f"Loaded {count} chain identity rows into PostgreSQL")
        return count

    def log_pipeline_run(self, status: str, duration: float,
                          unhcr: int, who: int, hashed: int):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO pipeline_runs
                (status, duration_seconds, unhcr_records, who_outbreaks, hashed_records)
            VALUES (%s, %s, %s, %s, %s)
        """, (status, duration, unhcr, who, hashed))
        logger.success("Pipeline run logged to database")

    def get_summary(self) -> dict:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM unhcr_population")
        unhcr_rows = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM who_outbreaks")
        who_rows = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM who_outbreaks WHERE who_pheic = TRUE")
        pheic_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chain_identities")
        chain_count = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(total_displaced),0) FROM unhcr_population")
        total_displaced = cur.fetchone()[0]
        return {
            "unhcr_rows":       unhcr_rows,
            "who_outbreaks":    who_rows,
            "active_pheic":     pheic_count,
            "chain_identities": chain_count,
            "total_displaced":  total_displaced,
        }

    def close(self):
        self.conn.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from data_pipeline.fetchers.unhcr_fetcher import UNHCRFetcher
    from data_pipeline.fetchers.who_fetcher   import WHOFetcher

    print("\n" + "=" * 55)
    print("  RefugeeHealthChain - Database Loader")
    print("  Loading UNHCR + WHO + Chain data into PostgreSQL")
    print("=" * 55)

    db = DatabaseManager()

    print("\n[1/4] Loading UNHCR population data...")
    unhcr = UNHCRFetcher()
    pop_df = unhcr.fetch_population(year=2024)
    n1 = db.load_unhcr_population(pop_df)
    print(f"  OK - {n1} rows loaded")

    print("\n[2/4] Loading WHO outbreak data...")
    who = WHOFetcher()
    out_df = who.fetch_outbreaks()
    n2 = db.load_who_outbreaks(out_df)
    print(f"  OK - {n2} rows loaded")

    print("\n[3/4] Loading chain identities...")
    from pathlib import Path
    anchored_path = Path("data_pipeline/output/anchored_identities.csv")
    if anchored_path.exists():
        anchored_df = pd.read_csv(anchored_path)
        n3 = db.load_chain_identities(anchored_df)
        print(f"  OK - {n3} rows loaded")
    else:
        print("  SKIP - run chain_anchor.py first")
        n3 = 0

    print("\n[4/4] Database summary...")
    summary = db.get_summary()
    print("\n" + "=" * 55)
    print("  DATABASE LOADED SUCCESSFULLY")
    print(f"  UNHCR rows:        {summary['unhcr_rows']}")
    print(f"  WHO outbreaks:     {summary['who_outbreaks']}")
    print(f"  Active PHEICs:     {summary['active_pheic']}")
    print(f"  Chain identities:  {summary['chain_identities']}")
    print(f"  Total displaced:   {summary['total_displaced']:,}")
    print("=" * 55)

    db.log_pipeline_run("success", 0, n1, n2, n3)
    db.close()
