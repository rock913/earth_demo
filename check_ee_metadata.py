import ee
import json

DATASETS = [
    "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
    "GOOGLE/RESEARCH/SATELLITE_EMBEDDING/V1/ANNUAL"
]

def check_dataset(dataset_id):
    print(f"\nChecking dataset: {dataset_id}")
    try:
        # Check if it's an ImageCollection or Image
        # Try both, usually these are collections
        try:
            collection = ee.ImageCollection(dataset_id)
            # Basic info
            count = collection.size().getInfo()
            if count == 0:
                print(f"Dataset {dataset_id} exists but is empty (0 images).")
                return
            
            print(f"Dataset exists. Image count: {count}")
            
            # Get first image to inspect bands
            first_image = collection.first()
            bands = first_image.bandNames().getInfo()
            print(f"Bands: {bands}")
            
            # Get time range from collection
            # Sort by system:time_start
            sorted_collection = collection.sort('system:time_start')
            first_date = ee.Date(sorted_collection.first().get('system:time_start')).format('YYYY-MM-dd').getInfo()
            last_date = ee.Date(sorted_collection.sort('system:time_start', False).first().get('system:time_start')).format('YYYY-MM-dd').getInfo()
            print(f"Time Range: {first_date} to {last_date}")
            
            # Check properties for access info? (hard to check programmatically unless explicit)
            # Usually if we can read it, it's accessible to us.
            print("Access: Public/Accessible (since we can read metadata)")

        except ee.EEException as e:
            # Maybe it's an Image?
            try:
                image = ee.Image(dataset_id)
                bands = image.bandNames().getInfo()
                print(f"Dataset exists as single Image. Bands: {bands}")
            except Exception as e_inner:
                print(f"Error accessing as Collection or Image: {e}")
                
    except Exception as e:
        print(f"Unexpected error for {dataset_id}: {e}")

if __name__ == "__main__":
    try:
        ee.Initialize()
        print("Earth Engine initialized successfully.")
    except Exception as e:
        print(f"earthengine initialization failed: {e}")
        print("Dataset accessibility cannot be verified without authentication.")
        exit(1)

    for ds in DATASETS:
        check_dataset(ds)
