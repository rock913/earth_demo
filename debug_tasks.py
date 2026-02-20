import ee

try:
    ee.Initialize()
except Exception as e:
    print(f"Auth failed: {e}")
    exit(1)

print("Listing recent tasks...")
tasks = ee.batch.Task.list()
for i, task in enumerate(tasks[:5]):
    status = task.status()
    print(f"Task {i}: {status['description']} ({status['state']})")
    print(f"  Start: {status.get('start_timestamp_ms')}")
    print(f"  Update: {status.get('update_timestamp_ms')}")

print("\nDone.")
