# upload_rules.py
"""
Upload rules from mcp_data/rules.json to MCP MongoDB database
"""
import json
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_API_URL = "http://127.0.0.1:5001/api/mcp/save_rule"
RULES_FILE = "data/mcp/rules/rules.json"


def upload_rules_to_mcp():
    """Upload all rules from local JSON to MCP database"""
    
    # Load rules from file
    try:
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            all_rules = json.load(f)
        logger.info(f"Loaded rules from {RULES_FILE}")
    except FileNotFoundError:
        logger.error(f"Rules file not found: {RULES_FILE}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in rules file: {e}")
        return
    
    # Statistics
    total_uploaded = 0
    total_failed = 0
    
    # Upload city by city
    for city, rules in all_rules.items():
        logger.info(f"\n📍 Uploading rules for {city}...")
        
        for rule_entry in rules:
            try:
                # Prepare payload for MCP API
                payload = {
                    "city": city,
                    "authority": rule_entry.get("meta", {}).get("authority", ""),
                    "clause_no": rule_entry.get("rule", {}).get("clause_no", ""),
                    "page": rule_entry.get("rule", {}).get("page", 0),
                    "rule_type": rule_entry.get("rule", {}).get("rule_type", ""),
                    "conditions": rule_entry.get("rule", {}).get("conditions", ""),
                    "entitlements": rule_entry.get("rule", {}).get("entitlements", ""),
                    "notes": rule_entry.get("rule", {}).get("notes", ""),
                    "parsed_fields": rule_entry.get("rule", {}).get("parsed_fields", {}),
                }
                
                # Send to MCP API
                response = requests.post(MCP_API_URL, json=payload, timeout=10)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    if result.get("success"):
                        logger.info(f"  ✅ {payload['clause_no']} - {payload['rule_type']}")
                        total_uploaded += 1
                    else:
                        logger.error(f"  ❌ Failed: {result.get('error')}")
                        total_failed += 1
                else:
                    logger.error(f"  ❌ HTTP {response.status_code}: {response.text}")
                    total_failed += 1
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"  ❌ Connection error: {e}")
                total_failed += 1
            except Exception as e:
                logger.error(f"  ❌ Unexpected error: {e}")
                total_failed += 1
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"📊 Upload Summary:")
    logger.info(f"  ✅ Successfully uploaded: {total_uploaded}")
    logger.info(f"  ❌ Failed: {total_failed}")
    logger.info(f"  📦 Total: {total_uploaded + total_failed}")
    logger.info(f"{'='*50}\n")
    
    return total_uploaded, total_failed


def verify_upload():
    """Verify rules were uploaded by querying MCP API"""
    try:
        response = requests.get("http://127.0.0.1:5001/api/mcp/list_rules?limit=1000", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                rules = result.get("rules", [])
                logger.info(f"\n✅ Verification: Found {len(rules)} rules in MCP database")
                
                # Count by city
                cities = {}
                for rule in rules:
                    city = rule.get("city", "Unknown")
                    cities[city] = cities.get(city, 0) + 1
                
                logger.info("\n📊 Rules by City:")
                for city, count in sorted(cities.items()):
                    logger.info(f"  {city}: {count} rules")
                
                return True
        logger.error(f"Verification failed: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False


def main():
    """Main execution"""
    logger.info("🚀 Starting MCP Rules Upload...\n")
    
    # Check if MCP server is running
    try:
        response = requests.get("http://127.0.0.1:5001/", timeout=5)
        logger.info("✅ MCP Server is running\n")
    except requests.exceptions.RequestException:
        logger.error("❌ MCP Server is not running!")
        logger.error("   Please start it with: python mcp_server.py")
        return
    
    # Upload rules
    uploaded, failed = upload_rules_to_mcp()
    
    # Verify
    if uploaded > 0:
        logger.info("\n🔍 Verifying upload...")
        verify_upload()
    
    logger.info("\n✨ Done!")


if __name__ == "__main__":
    main()
