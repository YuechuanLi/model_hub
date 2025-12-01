"""Test script for Model Hub API - Sync and Download functionality."""

import asyncio

import httpx


async def test_model_hub_api():
    """Test the Model Hub API endpoints."""
    base_url = "http://localhost:8000/v1/hub"

    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("Testing Model Hub API - Sync and Download")
        print("=" * 60)

        # Test 1: Register a model
        print("\n1. Registering a model...")
        register_payload = {
            "vendor": "Wan-AI",
            "name": "Wan2.1-T2V-1.3B",
            "source_repo_id": "Wan-AI/Wan2.1-T2V-1.3B",
            "auto_sync": True,
        }

        try:
            response = await client.post(f"{base_url}/register", json=register_payload)
            if response.status_code == 200:
                model = response.json()
                print(f"✓ Model registered: {model['repo_id']}")
                print(f"  Status: {model['status']}")
                print(f"  ID: {model['id']}")
            elif response.status_code == 400:
                print("✓ Model already registered (expected if run multiple times)")
            else:
                print(f"✗ Failed to register model: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error registering model: {e}")

        # Test 2: List models
        print("\n2. Listing models...")
        try:
            response = await client.get(f"{base_url}/models")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Found {data['total_count']} model(s)")
                for model in data["models"]:
                    print(f"  - {model['repo_id']} ({model['status']})")
            else:
                print(f"✗ Failed to list models: {response.status_code}")
        except Exception as e:
            print(f"✗ Error listing models: {e}")

        # Test 3: Trigger sync manually
        print("\n3. Triggering metadata sync...")
        sync_payload = {"repo_id": "Wan-AI/Wan2.1-T2V-1.3B"}

        try:
            response = await client.post(f"{base_url}/sync", json=sync_payload)
            if response.status_code == 200:
                job = response.json()
                print(f"✓ Sync job queued: {job['job_id']}")
                print(f"  Status: {job['status']}")
                print(f"  Message: {job['message']}")

                # Wait a bit and check job status
                await asyncio.sleep(2)
                job_response = await client.get(f"{base_url}/jobs/{job['job_id']}")
                if job_response.status_code == 200:
                    job_status = job_response.json()
                    print(f"  Job status after 2s: {job_status['status']}")
                    if job_status.get("logs"):
                        print(f"  Logs: {job_status['logs']}")
            else:
                print(f"✗ Failed to trigger sync: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error triggering sync: {e}")

        # Test 4: List jobs
        print("\n4. Listing recent jobs...")
        try:
            response = await client.get(f"{base_url}/jobs")
            if response.status_code == 200:
                jobs = response.json()
                print(f"✓ Found {len(jobs)} job(s)")
                for job in jobs[:5]:  # Show first 5
                    print(
                        f"  - {job['type']}: {job['status']} (created: {job['created_at']})"
                    )
            else:
                print(f"✗ Failed to list jobs: {response.status_code}")
        except Exception as e:
            print(f"✗ Error listing jobs: {e}")

        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_model_hub_api())
