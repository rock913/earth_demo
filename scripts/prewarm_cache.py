#!/usr/bin/env python3
"""批量预热 AlphaEarth v5 缓存任务。

示例：
  python scripts/prewarm_cache.py --gee-user-path users/<username>/aef_demo
"""

from __future__ import annotations

import argparse
from datetime import datetime

import ee


LOCATIONS = {
    "shanghai": (31.2304, 121.5000),
    "beijing": (39.9042, 116.7000),
    "xiongan": (39.0500, 115.9800),
    "hangzhou": (30.2450, 120.1400),
    "shenzhen": (22.5000, 113.9500),
    "nyc": (40.7580, -73.9855),
}

MODES = {
    "dna": "地表 DNA",
    "change": "变化雷达",
    "intensity": "建设强度",
    "eco": "生态韧性",
}


def get_layer_logic(mode_key: str, region):
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")

    if mode_key == "dna":
        emb = emb_col.filterDate("2024-01-01", "2024-12-31").first()
        img = emb.select([0, 1, 2])
    elif mode_key == "change":
        emb19 = emb_col.filterDate("2019-01-01", "2019-12-31").first()
        emb24 = emb_col.filterDate("2024-01-01", "2024-12-31").first()
        img = emb19.subtract(emb24).pow(2).reduce(ee.Reducer.sum()).sqrt()
        img = img.updateMask(img.gt(0.18))
    elif mode_key == "intensity":
        emb = emb_col.filterDate("2024-01-01", "2024-12-31").first()
        img = emb.select([0]).unitScale(-0.12, 0.12).clamp(0, 1)
        img = img.updateMask(img.gt(0.4))
    else:
        emb = emb_col.filterDate("2024-01-01", "2024-12-31").first()
        img = emb.select([2]).multiply(-1)
        img = img.updateMask(img.gt(-0.05))

    return img.clip(region)


def submit_export(gee_user_path: str, loc_code: str, mode_key: str, dry_run: bool) -> None:
    lat, lon = LOCATIONS[loc_code]
    region = ee.Geometry.Point([lon, lat]).buffer(20000)
    image = get_layer_logic(mode_key, region)
    asset_id = f"{gee_user_path.rstrip('/')}/{loc_code}_{mode_key}"
    description = f"Cache_{loc_code}_{mode_key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if dry_run:
        print(f"[DRY-RUN] {description} -> {asset_id}")
        return

    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_id,
        region=region,
        scale=10,
        maxPixels=1e9,
    )
    task.start()
    print(f"[SUBMITTED] {description} | task_id={task.id} | asset={asset_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prewarm AlphaEarth cache assets")
    parser.add_argument("--gee-user-path", required=True, help="例如 users/<username>/aef_demo")
    parser.add_argument("--locations", nargs="*", default=list(LOCATIONS.keys()), help="默认全部城市")
    parser.add_argument("--modes", nargs="*", default=list(MODES.keys()), choices=list(MODES.keys()), help="默认全部模式")
    parser.add_argument("--dry-run", action="store_true", help="仅打印任务，不提交")
    args = parser.parse_args()

    ee.Initialize()

    for loc in args.locations:
        if loc not in LOCATIONS:
            print(f"[SKIP] 未知城市: {loc}")
            continue
        for mode in args.modes:
            submit_export(args.gee_user_path, loc, mode, args.dry_run)


if __name__ == "__main__":
    main()
