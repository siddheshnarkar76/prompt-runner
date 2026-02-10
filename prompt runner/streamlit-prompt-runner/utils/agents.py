#agents.py
from utils import mcpstore
import uuid

def parsing_agent(rule_json):
    case_id = str(uuid.uuid4())[:8]
    mcpstore.save_rule(city=rule_json.get("city", ""),
                       rule=rule_json,
                       meta={"authority": rule_json.get("authority", "")})
    return case_id

def calculator_agent(city):
    rules = mcpstore.get_rules(city)
    outputs = []
    for r in rules:
        outputs.append({
            "clause_no": r["rule"].get("clause_no"),
            "entitlement": "Allowed" if "height" in r["rule"].get("conditions", "").lower() else "Check"
        })
        mcpstore.log_geometry(r["id"], f"outputs/geometry/{r['id']}.glb")
    return outputs

def rl_agent(case_id, user_feedback):
    reward = mcpstore.save_feedback(case_id, user_feedback)
    return reward
