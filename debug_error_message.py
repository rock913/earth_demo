import ee

try:
    ee.Initialize()
except Exception as e:
    print(f"Init failed: {e}")
    exit(1)

path = "projects/aef-project-487710/assets/aef_demo/shanghai_dna"

print(f"Checking asset: {path}")

try:
    ee.data.getAsset(path)
    print("Found.")
except Exception as exc:
    msg = str(exc)
    print(f"Exception type: {type(exc)}")
    print(f"Exception str: '{msg}'")
    print(f"Exception repr: {repr(exc)}")
    
    classification = "unknown"
    lower_msg = msg.lower()
    
    if any(k in lower_msg for k in ["not found", "asset not found", "cannot find", "does not exist"]):
        classification = "not_found"
    elif any(k in lower_msg for k in ["permission", "forbidden", "not authorized", "access denied", "insufficient"]):
        classification = "permission"

    print(f"Classification: {classification}")
