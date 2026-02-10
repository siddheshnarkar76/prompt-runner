"""
Parsing Agent (production-ready)
--------------------------------
- Extracts text from PDFs using fitz/pdfplumber
- Detects clauses, classifies rules, and extracts numeric info
- Pushes data to MongoDB Atlas (MCP)
- Saves parsed JSON locally

Environment variables:
- MONGO_URI : MongoDB Atlas connection string (required)
- MONGO_DB  : MongoDB database name (default: mcp_database)
- PARSED_OUTPUT_DIR : optional local folder to save json outputs (default: data/parsed)

Usage (CLI):
python agents/parsing_agent.py "path/to/file.pdf" "Mumbai"
"""
#parsing_agent.py
import os
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv

# ---------------- ENV LOADING ----------------
# Load from project root
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

# Debug prints
print(f"🔍 Loading .env from: {env_path}")
print("✅ .env exists:", os.path.exists(env_path))

# ---------------- CONFIG ----------------
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "mcp_database")
PARSED_OUTPUT_DIR = os.getenv("PARSED_OUTPUT_DIR", "data/parsed")
os.makedirs(PARSED_OUTPUT_DIR, exist_ok=True)

if not MONGO_URI:
    raise EnvironmentError("❌ MONGO_URI environment variable must be set to your MongoDB Atlas URI.")

# ---------------- IMPORTS ----------------
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    import pdfplumber
except Exception:
    pdfplumber = None

from pymongo import MongoClient
import certifi

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ParsingAgent")

# ---------------- MONGO CONNECTION ----------------
try:
    _client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=15000)
    _client.server_info()  # test connection
    _db = _client[MONGO_DB]
    _docs_col = _db.get_collection("documents")
    _rules_col = _db.get_collection("rules")
    logger.info(f"✅ Connected to MongoDB database: {MONGO_DB}")
except Exception as e:
    raise ConnectionError(f"❌ Failed to connect to MongoDB Atlas: {e}")

# ---------------- TEXT EXTRACTION ----------------
def extract_text_from_pdf(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    text_parts: List[str] = []

    if fitz:
        try:
            doc = fitz.open(pdf_path)
            for pno in range(len(doc)):
                page = doc.load_page(pno)
                txt = page.get_text("text") or ""
                if txt.strip():
                    text_parts.append(f"--- PAGE {pno+1} ---\n" + txt)
            if text_parts:
                logger.info("Extracted text using PyMuPDF (fitz).")
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.warning("fitz extraction failed: %s", e)

    if pdfplumber:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for idx, p in enumerate(pdf.pages):
                    txt = p.extract_text() or ""
                    if txt.strip():
                        text_parts.append(f"--- PAGE {idx+1} ---\n" + txt)
            if text_parts:
                logger.info("Extracted text using pdfplumber.")
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.warning("pdfplumber extraction failed: %s", e)

    logger.warning("⚠️ No text extracted — possibly scanned PDF (image only).")
    return ""

# ---------------- CLAUSE DETECTION ----------------
CLAUSE_RE = re.compile(
    r"(?:Clause|Section)\s*([0-9]+(?:\.[0-9]+)*)\s*[:.\-]?\s*(.*?)\n(?=(?:Clause|Section|\d+\.)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
HEADING_RE = re.compile(r"(^\d+(?:\.\d+)*\s*[).:-]\s*(.+))", re.MULTILINE)

def find_clauses(text: str) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    if not text:
        return rules
    t = text.replace("\r\n", "\n")

    for m in CLAUSE_RE.finditer(t):
        clause_no = m.group(1).strip()
        clause_text = m.group(2).strip()
        if clause_text:
            rules.append({"clause_no": clause_no, "text": clause_text})

    if not rules:
        for m in HEADING_RE.finditer(t):
            raw = m.group(1).strip()
            parts = re.split(r"\s*[).:-]\s*", raw, maxsplit=1)
            if len(parts) == 2:
                rules.append({"clause_no": parts[0].strip(), "text": parts[1].strip()})

    if not rules:
        paras = [p.strip() for p in t.split("\n\n") if p.strip()]
        for p in paras:
            if len(p) > 60:
                rules.append({"clause_no": None, "text": p})

    return rules

# ---------------- CLASSIFICATION ----------------
METER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:m|meter|metre|meters|metres)\b", re.IGNORECASE)
FSI_RE = re.compile(r"(?:FSI|F\.S\.I|floor space index)\s*(?:[:=]|\s)?\s*([\d\.]+)", re.IGNORECASE)
SETBACK_RE = re.compile(r"setback[s]?\s*(?:[:=]|\s)?\s*(\d+(?:\.\d+)?)\s*(?:m|meter|metre)?", re.IGNORECASE)
FLOOR_RE = re.compile(r"(\d+)\s*(?:floors|storeys|stories|storey|floor)\b", re.IGNORECASE)
ENTITLEMENT_RE = re.compile(r"(?:entitle(?:ment|d)?|allow(?:ed)?|permitted|permit)\b.*", re.IGNORECASE)

def classify_rule_text(text: str) -> Tuple[str, Dict[str, Any]]:
    lc = text.lower()
    fsi_m = FSI_RE.search(text)
    if fsi_m:
        try:
            val = float(fsi_m.group(1))
            return "fsi", {"fsi": val}
        except:
            return "fsi", {}

    if "height" in lc:
        m = METER_RE.search(text)
        if m:
            return "height", {"height_m": float(m.group(1))}
    if "setback" in lc:
        m = SETBACK_RE.search(text)
        if m:
            return "setback", {"setback_m": float(m.group(1))}
    if FLOOR_RE.search(text):
        return "floors", {"floors": int(FLOOR_RE.search(text).group(1))}
    if any(w in lc for w in ["allowed", "permitted", "entitlement", "may be permitted", "shall be permitted"]):
        return "entitlement", {"note": text[:200]}
    return "other", {}

# ---------------- MONGO PUSH ----------------
def push_parsed_document_to_mcp(parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
    doc_record = {
        "filename": parsed_doc.get("source_file"),
        "city": parsed_doc.get("city"),
        "parsed_at": parsed_doc.get("parsed_at"),
        "rule_count": len(parsed_doc.get("rules", [])),
        "raw": parsed_doc,
    }
    dres = _docs_col.insert_one(doc_record)
    doc_id = str(dres.inserted_id)
    inserted_rule_ids = []
    for r in parsed_doc.get("rules", []):
        rr = {
            "city": parsed_doc.get("city"),
            "clause_no": r.get("clause_no"),
            "text": r.get("text"),
            "parsed_fields": r.get("parsed_fields"),
            "rule_type": r.get("rule_type"),
            "source_doc_id": doc_id,
            "inserted_at": datetime.utcnow().isoformat() + "Z",
        }
        ins = _rules_col.insert_one(rr)
        inserted_rule_ids.append(str(ins.inserted_id))
    return {"document_id": doc_id, "inserted_rules": inserted_rule_ids}

# ---------------- MAIN PARSER ----------------
def parse_pdf_to_json(pdf_path: str, city: str) -> Dict[str, Any]:
    logger.info("Parsing PDF: %s for city=%s", pdf_path, city)
    text = extract_text_from_pdf(pdf_path)
    clauses = find_clauses(text)
    parsed = {
        "city": city,
        "source_file": os.path.basename(pdf_path),
        "parsed_at": datetime.utcnow().isoformat() + "Z",
        "rule_count": len(clauses),
        "rules": [],
    }

    for idx, c in enumerate(clauses, start=1):
        rtype, fields = classify_rule_text(c.get("text", ""))
        parsed["rules"].append({
            "id": f"{city.lower()}_r_{idx}",
            "clause_no": c.get("clause_no"),
            "text": c.get("text"),
            "parsed_fields": fields,
            "rule_type": rtype,
        })

    out_name = f"{Path(pdf_path).stem}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = os.path.join(PARSED_OUTPUT_DIR, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ Saved parsed JSON locally: {out_path}")

    push_info = push_parsed_document_to_mcp(parsed)
    parsed["push_result"] = push_info
    logger.info(f"✅ Uploaded {len(parsed['rules'])} rules to MongoDB.")
    return parsed

# ---------------- CLI ENTRY ----------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python agents/parsing_agent.py <pdf_path> <city>")
        sys.exit(1)
    path = sys.argv[1]
    city = sys.argv[2]
    result = parse_pdf_to_json(path, city)
    print(json.dumps({
        "file": result.get("source_file"),
        "rules": result.get("rule_count"),
        "mongo_push": result.get("push_result")
    }, indent=2))
