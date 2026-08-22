#!/usr/bin/env python3
"""Associate & verify every external database referenced by NeuroOmics-AD.

Checks (1) reachability of the live APIs / portals the pipeline can talk to and
(2) presence & validity of the local data files (DrugBank XML, LINCS L1000 and
Connectivity Map signature CSVs) that the drug-repurposing adapters load.

Pure standard library — runs anywhere with Python 3.8+.

Usage:
    python scripts/verify_databases.py                # human-readable report
    python scripts/verify_databases.py --json         # machine-readable report
    python scripts/verify_databases.py --timeout 20   # longer per-request timeout

Exit codes: 0 = everything reachable/present, 1 = at least one check failed,
            2 = usage/configuration error.
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

# ---------------------------------------------------------------------------
# Registry of associated databases.
# kind: "live" (HTTP API) | "portal" (web portal) | "local" (data file)
# ---------------------------------------------------------------------------
CHECKS: list[dict] = [
    # ---- drug-target / repurposing live APIs ------------------------------
    {
        "key": "chembl",
        "name": "ChEMBL",
        "category": "Drug-target / mechanism",
        "kind": "live",
        "method": "GET",
        "url": "https://www.ebi.ac.uk/chembl/api/data/molecule/search.json?q=donepezil&limit=1",
        "gated_by": "DRUG_ENABLE_LIVE_API",
        "note": "Mechanism-of-action & target annotations per drug",
    },
    {
        "key": "open_targets",
        "name": "Open Targets Platform",
        "category": "Drug-target / mechanism",
        "kind": "live",
        "method": "POST",
        "url": "https://platform-api.opentargets.org/v4/graphql",
        "body": {"query": 'query { target(ensemblId: "ENSG00000130203") { approvedSymbol } }'},
        "gated_by": "DRUG_ENABLE_LIVE_API",
        "note": "Disease-target-drug associations (GraphQL)",
    },
    {
        "key": "dgidb",
        "name": "DGIdb",
        "category": "Drug-target / mechanism",
        "kind": "live",
        "method": "GET",
        "url": "https://dgidb.org/api/v2/interactions.json?genes=APOE",
        "gated_by": "DRUG_ENABLE_LIVE_API",
        "note": "Drug-gene interaction database (v2 REST)",
    },
    {
        "key": "drugbank",
        "name": "DrugBank (XML)",
        "category": "Drug-target / mechanism",
        "kind": "local",
        "paths": ["backend/data/drugbank/full_database.xml"],
        "gated_by": "DRUG_DATABANK_XML_PATH",
        "note": "Full drug database XML (licensed download -> data/drugbank/)",
    },
    {
        "key": "lincs",
        "name": "LINCS L1000 (signatures)",
        "category": "Drug-target / mechanism",
        "kind": "local",
        "paths": ["backend/data/lincs/compound_signatures.csv"],
        "gated_by": "LINCS_SIGNATURES_PATH",
        "note": "Gene->logFC signatures for pathway-reversal scoring",
        "csv_columns": ["perturbagen", "gene", "logfoldchange"],
    },
    {
        "key": "cmap",
        "name": "Connectivity Map (signatures)",
        "category": "Drug-target / mechanism",
        "kind": "local",
        "paths": ["backend/data/cmap/cmap_signatures.csv"],
        "gated_by": "CMAP_SIGNATURES_PATH",
        "note": "CMap-style signatures (same CSV schema as LINCS)",
        "csv_columns": ["perturbagen", "gene", "logfoldchange"],
    },
    # ---- pathway / gene-set enrichment ------------------------------------
    {
        "key": "enrichr",
        "name": "Enrichr (GO / KEGG / Reactome)",
        "category": "Pathway enrichment",
        "kind": "live",
        "method": "GET",
        "url": "https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName=GO_Biological_Process_2023",
        "gated_by": "always attempted (gseapy.enrichr)",
        "note": "Live gene-set enrichment; falls back to built-in library",
    },
    {
        "key": "kegg_rest",
        "name": "KEGG REST",
        "category": "Pathway enrichment",
        "kind": "live",
        "method": "GET",
        "url": "https://rest.kegg.jp/list/hsa05010",
        "gated_by": "optional (pathway metadata)",
        "note": "KEGG pathway definitions (hsa05010 = Alzheimer's disease)",
    },
    # ---- protein-protein interaction networks -----------------------------
    {
        "key": "string",
        "name": "STRING",
        "category": "PPI networks",
        "kind": "live",
        "method": "GET",
        "url": "https://string-db.org/api/tsv/network?identifiers=APP&species=9606",
        "gated_by": "optional (full PPI export)",
        "note": "PPI edges; platform ships a built-in AD skeleton by default",
    },
    {
        "key": "biogrid",
        "name": "BioGRID",
        "category": "PPI networks",
        "kind": "portal",
        "method": "GET",
        "url": "https://thebiogrid.org/",
        "gated_by": "optional (full PPI export)",
        "note": "Curated interaction repository (alternative PPI source)",
    },
    # ---- clinical trials ---------------------------------------------------
    {
        "key": "clinicaltrials",
        "name": "ClinicalTrials.gov API v2",
        "category": "Clinical evidence",
        "kind": "live",
        "method": "GET",
        "url": "https://clinicaltrials.gov/api/v2/studies?query.term=alzheimer&pageSize=1",
        "gated_by": "optional (CLINICALTRIALS_API_KEY)",
        "note": "Trial counts / status for clinical-evidence scoring",
    },
    # ---- AD genomics / cohort portals --------------------------------------
    {
        "key": "niagads",
        "name": "NIAGADS DSS",
        "category": "AD genomics cohorts",
        "kind": "portal",
        "method": "GET",
        "url": "https://dss.niagads.org/",
        "gated_by": "catalog metadata (Knight-ADRC, ADSP R4 accessions)",
        "note": "NG00083 / NG00102 / NG00108 / NG00113 / NG00114 / NG00067",
    },
    {
        "key": "adkp",
        "name": "AD Knowledge Portal",
        "category": "AD genomics cohorts",
        "kind": "portal",
        "method": "GET",
        "url": "https://adknowledgeportal.synapse.org/",
        "gated_by": "catalog metadata (AMP-AD)",
        "note": "AMP-AD multi-ethnic brain multi-omics",
    },
    {
        "key": "agora",
        "name": "AMP-AD Agora",
        "category": "AD genomics cohorts",
        "kind": "live",
        "method": "GET",
        "url": "https://agora.ampadportal.org/genes",
        "gated_by": "catalog metadata (AMP-AD)",
        "note": "Nomination of AD target genes from AMP-AD",
    },
    {
        "key": "datalens",
        "name": "Alzheimer DataLENS",
        "category": "AD genomics cohorts",
        "kind": "portal",
        "method": "GET",
        "url": "https://alzdatalens.partners.org/",
        "gated_by": "frontend deep-link (external annotations)",
        "note": "Query/visualization portal for harmonized AD omics",
    },
    {
        "key": "ontime",
        "name": "ONTIME QTL browser",
        "category": "AD genomics cohorts",
        "kind": "portal",
        "method": "GET",
        "url": "https://ontime.wustl.edu/",
        "gated_by": "frontend deep-link (external annotations)",
        "note": "PheWeb-based QTL browser (Knight-ADRC pQTL/mQTL)",
    },
]


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def check_live(item: dict, timeout: int) -> dict:
    """Probe a live API/portal endpoint."""
    url, method = item["url"], item["method"].upper()
    headers = {"User-Agent": "NeuroOmics-AD/1.0 (database verification)"}
    data = None
    if method == "POST" and item.get("body"):
        data = json.dumps(item["body"]).encode()
        headers["Content-Type"] = "application/json"
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            body = r.read(512)
            return {
                "status": "OK",
                "http": r.status,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "detail": f"HTTP {r.status} ({len(body)} bytes preview)",
            }
    except urllib.error.HTTPError as exc:
        return {"status": "FAIL", "http": exc.code, "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "detail": f"HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        text = str(reason)
        kind = "BLOCKED"
        if "Name or service not known" in text or "getaddrinfo" in text or "nodename nor servname" in text:
            kind = "DNS"
        elif "SSL" in text or "EOF" in text or "closed" in text:
            kind = "TLS/EGRESS"
        return {"status": "FAIL", "http": None, "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "detail": f"{kind}: {text[:120]}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "http": None, "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "detail": f"{type(exc).__name__}: {str(exc)[:120]}"}


def check_local(item: dict) -> dict:
    """Check local data files exist and (for CSVs) have the expected columns."""
    found = []
    for rel in item.get("paths", []):
        p = REPO_ROOT / rel
        if p.exists():
            found.append(str(p))
    if not found:
        return {"status": "MISSING", "http": None, "latency_ms": None,
                "detail": f"expected at {', '.join(item['paths'])}"}
    detail = f"found: {', '.join(found)}"
    # light validation for CSV signature files
    cols = item.get("csv_columns")
    if cols:
        try:
            import csv
            with open(found[0], newline="") as fh:
                reader = csv.reader(fh)
                header = next(reader, [])
                n_rows = sum(1 for _ in reader)
            missing = [c for c in cols if c not in header]
            detail += f" | {n_rows} rows | columns {header}"
            if missing:
                return {"status": "INVALID", "http": None, "latency_ms": None,
                        "detail": detail + f" | MISSING columns: {missing}"}
            return {"status": "OK", "http": None, "latency_ms": None, "detail": detail}
        except Exception as exc:  # noqa: BLE001
            return {"status": "INVALID", "http": None, "latency_ms": None,
                    "detail": detail + f" | parse error: {exc}"}
    return {"status": "OK", "http": None, "latency_ms": None, "detail": detail}


def load_env_overrides() -> dict:
    """Best-effort read of backend/.env so the report reflects live config."""
    env_file = BACKEND_DIR / ".env"
    overrides: dict = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            overrides[k.strip()] = v.strip()
    return overrides


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit JSON report")
    ap.add_argument("--timeout", type=int, default=10, help="per-request timeout (s)")
    ap.add_argument("--live-only", action="store_true", help="skip local-file checks")
    args = ap.parse_args()

    overrides = load_env_overrides()
    live_enabled = overrides.get("DRUG_ENABLE_LIVE_API", "false").lower() in {"1", "true", "yes", "on"}

    results = []
    for item in CHECKS:
        if item["kind"] == "local":
            if args.live_only:
                continue
            res = check_local(item)
        else:
            res = check_live(item, args.timeout)
        entry = {
            "key": item["key"],
            "name": item["name"],
            "category": item["category"],
            "kind": item["kind"],
            "url": item.get("url"),
            "gated_by": item["gated_by"],
            "note": item["note"],
            **res,
        }
        results.append(entry)

    if args.json:
        print(json.dumps({"drg_enable_live_api": live_enabled, "env_file": str(BACKEND_DIR / ".env"),
                          "env_file_exists": (BACKEND_DIR / ".env").exists(),
                          "results": results}, indent=2))
        return 0 if all(r["status"] == "OK" for r in results) else 1

    # human-readable report
    width = 100
    print("=" * width)
    print(" NeuroOmics-AD — external database association & verification report")
    print("=" * width)
    print(f" DRUG_ENABLE_LIVE_API : {live_enabled}")
    print(f" env file             : {BACKEND_DIR / '.env'} "
          f"({'exists' if (BACKEND_DIR / '.env').exists() else 'missing'})")
    print(f" per-request timeout  : {args.timeout}s")
    print("-" * width)
    print(f" {'DB':28s} {'KIND':8s} {'STATUS':9s} {'LAT':>7s}  DETAIL")
    print("-" * width)
    by_cat: dict = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    failed = 0
    for cat, rows in by_cat.items():
        print(f"\n [{cat}]")
        for r in rows:
            status = r["status"]
            marker = {"OK": "✅", "MISSING": "⚠️", "INVALID": "❌", "FAIL": "❌"}.get(status, "•")
            lat = f"{r['latency_ms']}ms" if r.get("latency_ms") is not None else "-"
            if status != "OK":
                failed += 1
            print(f"  {marker} {r['name'][:26]:26s} {r['kind']:8s} {status:9s} {lat:>7s}  {r['detail']}")
            print(f"      ↳ gated by: {r['gated_by']}")
            if r.get("url"):
                print(f"      ↳ {r['url']}")

    print("\n" + "-" * width)
    print(f" Summary: {len(results)} databases checked, "
          f"{sum(1 for r in results if r['status'] == 'OK')} OK, {failed} need attention.")
    if failed:
        print(" Note: 'TLS/EGRESS' or 'DNS' failures usually mean the runtime's network")
        print("       allowlist blocks the host (e.g. sandboxes), not that the database is down.")
    print("=" * width)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
