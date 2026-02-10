import json
import time

import requests

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "bhiv2024"


def get_auth_token():
    print("Getting authentication token...")

    auth_data = {"username": USERNAME, "password": PASSWORD}

    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login", data=auth_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if response.status_code == 200:
        token_data = response.json()
        print("Authentication successful")
        return token_data["access_token"]
    else:
        print(f"Authentication failed: {response.text}")
        return None


def test_bhiv_endpoint(token):
    print("\nTesting BHIV AI Assistant endpoint...")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    test_data = {
        "user_id": "admin",
        "prompt": "Design a modern 2BHK apartment with open kitchen and balcony",
        "city": "Mumbai",
        "project_id": f"proj_test_{int(time.time())}",
        "design_type": "residential",
        "budget": 1500000,
        "area_sqft": 800,
        "notify_prefect": True,
    }

    print("Sending request...")
    print(json.dumps(test_data, indent=2))

    start_time = time.time()
    response = requests.post(f"{BASE_URL}/bhiv/v1/prompt", json=test_data, headers=headers)
    end_time = time.time()

    print(f"\nResponse time: {(end_time - start_time):.2f} seconds")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 201:
        print("SUCCESS: BHIV endpoint test successful!")
        response_data = response.json()

        print("\nResponse Analysis:")
        print(f"  Request ID: {response_data.get('request_id', 'N/A')}")
        print(f"  Spec ID: {response_data.get('spec_id', 'N/A')}")
        print(f"  User ID: {response_data.get('user_id', 'N/A')}")
        print(f"  City: {response_data.get('city', 'N/A')}")
        print(f"  Status: {response_data.get('status', 'N/A')}")
        print(f"  Total Duration: {response_data.get('total_duration_ms', 'N/A')} ms")

        agents = response_data.get("agents", {})
        print(f"\nAgents Called ({len(agents)}):")
        for agent_name, agent_data in agents.items():
            status = "SUCCESS" if agent_data.get("success") else "FAILED"
            duration = agent_data.get("duration_ms", 0)
            print(f"  {status} {agent_name}: {duration}ms")
            if not agent_data.get("success"):
                print(f"    Error: {agent_data.get('error', 'Unknown')}")

        design_spec = response_data.get("design_spec", {})
        if design_spec:
            print(f"\nDesign Spec Generated:")
            print(f"  Objects: {len(design_spec.get('objects', []))}")
            print(f"  Rooms: {len(design_spec.get('rooms', []))}")
            if "estimated_cost" in design_spec:
                cost = design_spec["estimated_cost"]
                print(f"  Estimated Cost: {cost.get('total', 'N/A')} {cost.get('currency', 'INR')}")

        return response_data
    else:
        print("FAILED: BHIV endpoint test failed!")
        print(f"Error: {response.text}")
        return None


def main():
    print("BHIV AI Assistant Endpoint Test")
    print("=" * 50)

    token = get_auth_token()
    if not token:
        print("Cannot proceed without authentication")
        return

    response_data = test_bhiv_endpoint(token)

    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    main()
