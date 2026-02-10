#prompt_to_spec.py
def prompt_to_spec(prompt):
    """
    Converts a user prompt into a JSON spec (dummy examples)
    """
    if "control room" in prompt.lower():
        return {
            "scene": "Sci-Fi Control Room",
            "elements": ["holographic displays", "sliding doors"],
            "lighting": "neon blue",
            "theme": "futuristic industrial"
        }
    elif "kitchen" in prompt.lower():
        return {
            "scene": "Modern Kitchen",
            "elements": ["island", "stainless steel appliances"],
            "lighting": "warm white",
            "theme": "contemporary"
        }
    else:
        return {
            "scene": "Generic Scene",
            "elements": [],
            "lighting": "default",
            "theme": "neutral"
        }
