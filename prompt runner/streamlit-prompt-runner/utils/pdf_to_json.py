# pdf_to_json.py
# ...existing code...
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# optional extractors
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

# HTTP fallback
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Folders ---
DOWNLOADS_DIR = r"C:\Users\sid\Desktop\prompt runner\streamlit-prompt-runner\downloads"
JSON_OUTPUT_DIR = os.path.join(DOWNLOADS_DIR, "json_rules")
os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

# Default API fallback (used if direct Mongo utils not available)
MCP_API_SAVE_RULE = os.environ.get("MCP_API_SAVE_RULE", "http://127.0.0.1:5001/api/mcp/save_rule")


def _extract_text(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        logger.error("PDF not found: %s", pdf_path)
        return ""

    text_parts: List[str] = []

    # PyMuPDF preferred
    if fitz:
        try:
            doc = fitz.open(pdf_path)
            for i in range(len(doc)):
                page = doc.load_page(i)
                txt = page.get_text("text") or ""
                if txt.strip():
                    text_parts.append(txt)
            if text_parts:
                logger.info("Extracted text via PyMuPDF")
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.debug("PyMuPDF extraction failed: %s", e)

    # pdfplumber fallback
    if pdfplumber:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for p in pdf.pages:
                    txt = p.extract_text() or ""
                    if txt.strip():
                        text_parts.append(txt)
            if text_parts:
                logger.info("Extracted text via pdfplumber")
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.debug("pdfplumber extraction failed: %s", e)

    # plain text fallback
    try:
        with open(pdf_path, "r", encoding="utf-8") as f:
            raw = f.read()
            if raw.strip():
                logger.info("Read file as plain text fallback")
                return raw
    except Exception:
        pass

    logger.warning("No text extracted from PDF (may be scanned).")
    return ""


def _find_clauses(text: str) -> List[Dict[str, Any]]:
    import re

    if not text:
        return []

    t = text.replace("\r\n", "\n")

    clause_pattern = re.compile(
        r"(?:Clause|Section)\s*([0-9]+(?:\.[0-9]+)*)\s*[:.-]?\s*(.*?)\n(?=(?:Clause|Section|\d+\.)|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    clauses = []
    for m in clause_pattern.finditer(t):
        clause_no = m.group(1).strip()
        clause_text = m.group(2).strip()
        clauses.append({"clause_no": clause_no, "text": clause_text})

    if not clauses:
        heading_pattern = re.compile(r"(^\d+(?:\.\d+)*\s*[).:-]\s*(.+))", re.MULTILINE)
        for m in heading_pattern.finditer(t):
            parts = re.split(r"\s*[).:-]\s*", m.group(1), maxsplit=1)
            if len(parts) == 2:
                clauses.append({"clause_no": parts[0].strip(), "text": parts[1].strip()})

    if not clauses:
        paras = [p.strip() for p in t.split("\n\n") if p.strip()]
        for p in paras:
            if len(p) > 50:
                clauses.append({"clause_no": None, "text": p})

    return clauses


def parse_pdf_to_json(city: str, pdf_path: str) -> Dict[str, Any]:
    logger.info("📄 Converting PDF: %s", pdf_path)
    text = _extract_text(pdf_path)
    if not text:
        logger.warning("⚠️ No text extracted from PDF.")
        return {"city": city, "rules": [], "error": "no_text"}

    clauses = _find_clauses(text)
    parsed = {
        "city": city,
        "source_file": os.path.basename(pdf_path),
        "parsed_at": datetime.utcnow().isoformat() + "Z",
        "rule_count": len(clauses),
        "rules": [],
    }

    for idx, c in enumerate(clauses, start=1):
        parsed_rule = {
            "id": f"{city.lower()}_r_{idx}",
            "clause_no": c.get("clause_no"),
            "summary": (c.get("text")[:300] + "...") if c.get("text") and len(c.get("text")) > 300 else c.get("text"),
            "full_text": c.get("text"),
            "page": None,
            "notes": "",
        }
        parsed["rules"].append(parsed_rule)

    # Save JSON locally
    safe = os.path.splitext(os.path.basename(pdf_path))[0]
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(JSON_OUTPUT_DIR, f"{safe}_{ts}.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        logger.info("Saved JSON -> %s", out_path)
    except Exception as e:
        logger.error("Failed to save JSON locally: %s", e)

    # Try to push to MCP (prefer direct mongo utils)
    push_result = {"pushed": False, "reason": None}
    try:
        from utils.mongo import get_collection  # type: ignore

        docs = get_collection("documents")
        rules_col = get_collection("rules")

        doc_record = {
            "filename": parsed["source_file"],
            "city": parsed["city"],
            "parsed_at": parsed["parsed_at"],
            "rule_count": parsed["rule_count"],
            "raw": parsed,
        }
        dres = docs.insert_one(doc_record)
        doc_id = str(dres.inserted_id)

        inserted = []
        for r in parsed["rules"]:
            rr = {
                "city": parsed["city"],
                "clause_no": r.get("clause_no"),
                "summary": r.get("summary"),
                "full_text": r.get("full_text"),
                "source_doc_id": doc_id,
                "inserted_at": datetime.utcnow().isoformat() + "Z",
            }
            ir = rules_col.insert_one(rr)
            inserted.append(str(ir.inserted_id))

        push_result["pushed"] = True
        push_result["inserted_rules"] = inserted
        push_result["document_id"] = doc_id
        logger.info("Pushed parsed document and rules to MCP (direct).")
    except Exception as e:
        push_result["reason"] = str(e)
        logger.debug("Direct MCP push failed: %s", e)
        # HTTP fallback: post to MCP API
        try:
            resp = requests.post(MCP_API_SAVE_RULE, json=parsed, timeout=10)
            if resp.ok:
                push_result["pushed"] = True
                push_result["api_resp"] = resp.json()
                logger.info("Pushed parsed JSON to MCP API (HTTP).")
            else:
                push_result["reason"] = f"API {resp.status_code}: {resp.text}"
                logger.error("MCP API push failed %s", push_result["reason"])
        except Exception as e2:
            push_result["reason"] = f"http_error: {e2}"
            logger.error("HTTP fallback failed: %s", e2)

    parsed["push_result"] = push_result
    return parsed


# CLI convenience
if __name__ == "__main__":
    samples = []
    for k, v in {
        "Mumbai": r"C:\Users\sid\Documents\Mumbai_DCPR_Fake.pdf",
        "Ahmedabad": r"C:\Users\sid\Documents\Ahmedabad_DCR_Fake.pdf",
    }.items():
        if os.path.exists(v):
            samples.append((k, v))
    if not samples:
        logger.info("No sample PDFs found in hardcoded paths. Edit file or pass to parse_pdf_to_json().")
    for city, path in samples:
        out = parse_pdf_to_json(city, path)
        logger.info("Parse result: city=%s rules=%d pushed=%s", city, out.get("rule_count", 0), out.get("push_result", {}).get("pushed"))
# ...existing code...