# agents/unreal_agent.py
import requests
import logging
import os

logging.basicConfig(level=logging.INFO)
UNREAL_ENDPOINT = os.environ.get("UNREAL_API_URL", "http://127.0.0.1:3000/unreal/ingest_spec")

def send_spec_to_unreal(spec: dict, timeout=8) -> bool:
    try:
        r = requests.post(UNREAL_ENDPOINT, json=spec, timeout=timeout)
        r.raise_for_status()
        logging.info("Spec delivered to Unreal: %s", r.status_code)
        return True
    except Exception as e:
        logging.error("Failed to send spec to Unreal: %s", e)
        return False
