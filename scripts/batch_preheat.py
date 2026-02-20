#!/usr/bin/env python3
"""
批量预热脚本 - 独立运行版本
用途：在后台批量导出所有场景的缓存（5城市 × 4模式 = 20个）
用法：
    python scripts/batch_preheat.py
    或
    python scripts/batch_preheat.py --path projects/aef-project-487710/assets/aef_demo
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import ee
except ImportError:
    print("❌ 错误：earthengine-api 未安装")
    print("请安装：pip install earthengine-api")
    sys.exit(1)

# 配置常量
EMBEDDING_COLLECTION = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
DEFAULT_BUFFER_METERS = 5000
DEFAULT_GEE_USER_PATH = "projects/aef-project-487710/assets/aef_demo"

# 所有城市配置
ALL_LOCATIONS = {
    "beijing": {"coords": [39.9042, 116.7000], "name": "北京·通州"},
    "xiongan": {"coords": [39.0500, 115.9800], "name": "河北·雄安"},
    "hangzhou": {"coords": [30.2450, 120.1400], "name": "杭州·西湖"},
    "shenzhen": {"coords": [22.5000, 113.9500], "name": "深圳·湾区"},
    "nyc": {"coords": [40.7580, -73.9855], "name": "美国·纽约"},
}

# 所有场景配置
MODE_CONFIG = {
    "地表 DNA": {
        "suffix": "dna",
        "date_start": "2024-01-01",
        "date_end": "2024-12-31",
    },
    "变化雷达": {
        "suffix": "change",
        "date_start_old": "2019-01-01",
        "date_end_old": "2019-12-31",
        "date_start_new": "2024-01-01",
        "date_end_new": "2024-12-31",
        "threshold": 0.06,
    },
    "建设强度": {
        "suffix": "intensity",
        "date_start": "2024-01-01",
        "date_end": "2024-12-31",
        "threshold": 0.15,
        "scale_min": -0.12,
        "scale_max": 0.12,
    },
    "生态韧性": {
        "suffix": "eco",
        "date_start": "2024-01-01",
        "date_end": "2024-12-31",
        "threshold": -0.15,
    },
}


def init_gee():
    """初始化 Google Earth Engine"""
    print("🔧 初始化 Google Earth Engine...")
    
    # 优先级1: 从环境文件加载配置（systemd 服务环境）
    env_file = "/etc/alphaearth/alphaearth.env"
    if os.path.exists(env_file):
        print(f"📂 检测到环境文件: {env_file}")
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        # 移除引号
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
            print("✅ 环境变量已从配置文件加载")
        except Exception as exc:
            print(f"⚠️ 环境文件读取失败: {exc}")
    
    # 优先级2: 尝试服务账号认证
    service_account = os.environ.get("EE_SERVICE_ACCOUNT")
    private_key_file = os.environ.get("EE_PRIVATE_KEY_FILE")
    
    if service_account and private_key_file:
        try:
            credentials = ee.ServiceAccountCredentials(service_account, private_key_file)
            ee.Initialize(credentials)
            print(f"✅ 使用服务账号认证: {service_account}")
            return True
        except Exception as exc:
            print(f"⚠️ 服务账号认证失败: {exc}")
            print("尝试使用用户凭证...")
    
    # 优先级3: 回退到用户凭证
    try:
        ee.Initialize()
        print("✅ 使用用户凭证认证成功")
        return True
    except Exception as exc:
        print(f"❌ Earth Engine 初始化失败: {exc}")
        print("\n请先认证：")
        print("  方式1（推荐）：配置服务账号（参考 app.py）")
        print("  方式2：运行 earthengine authenticate")
        return False


def get_flattened_image(col, date_start, date_end, bounds):
    """获取并展平 Embedding 图像"""
    filtered = col.filterBounds(bounds).filterDate(date_start, date_end)
    
    try:
        count = filtered.limit(1).size().getInfo()
    except:
        count = 0
    
    if int(count) == 0:
        # 回退到更大的时间范围
        filtered = col.filterBounds(bounds).filterDate("2019-01-01", "2025-12-31")
    
    raw_img = filtered.sort("system:time_start", False).mosaic()
    bands = raw_img.bandNames().slice(0, 64)
    # GEE 要求 Band ID 必须以字母开头，使用 b0, b1, b2...
    target = ee.List([f"b{i}" for i in range(64)])
    return raw_img.select(bands, target)


def compute_layer(mode_key, region):
    """计算指定场景的图层"""
    emb_col = ee.ImageCollection(EMBEDDING_COLLECTION)
    cfg = MODE_CONFIG[mode_key]
    
    if mode_key == "地表 DNA":
        img = get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        img = img.select(["b0", "b1", "b2"])
        
    elif mode_key == "变化雷达":
        img19 = get_flattened_image(emb_col, cfg["date_start_old"], cfg["date_end_old"], region)
        img24 = get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        diff = img19.subtract(img24)
        dist = diff.pow(2).reduce(ee.Reducer.sum()).sqrt()
        th = cfg["threshold"]
        img = dist.updateMask(dist.gt(th))
        
    elif mode_key == "建设强度":
        img_all = get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        val = img_all.select(["b0"])
        norm = val.unitScale(cfg["scale_min"], cfg["scale_max"]).clamp(0, 1)
        th = cfg["threshold"]
        img = norm.updateMask(norm.gt(th))
        
    else:  # 生态韧性
        img_all = get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        val = img_all.select(["b2"]).multiply(-1)
        th = cfg["threshold"]
        img = val.updateMask(val.gt(th))
    
    return img


def check_asset_exists(asset_id):
    """检查 Asset 是否已存在"""
    try:
        ee.data.getAsset(asset_id)
        return True
    except:
        return False


def export_to_asset(image, asset_id, region, description):
    """导出图像到 GEE Asset"""
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_id,
        region=region,
        scale=10,
        maxPixels=1e9,
    )
    task.start()
    return task.id


def batch_preheat(gee_user_path, skip_existing=True, dry_run=False):
    """批量预热所有场景"""
    if gee_user_path.startswith("/"):
        print("❌ 错误：本地路径不支持预热（需要 GEE Cloud Asset 路径）")
        return 0, 0
    
    print(f"\n📍 目标路径: {gee_user_path}")
    print(f"📊 总任务数: {len(ALL_LOCATIONS)} 城市 × {len(MODE_CONFIG)} 模式 = {len(ALL_LOCATIONS) * len(MODE_CONFIG)} 个\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    total_count = 0
    
    for loc_code, loc_data in ALL_LOCATIONS.items():
        lat, lon = loc_data["coords"]
        viewport = ee.Geometry.Point([lon, lat]).buffer(DEFAULT_BUFFER_METERS)
        
        print(f"\n🗺️  {loc_data['name']} ({loc_code})")
        
        for mode_key, mode_cfg in MODE_CONFIG.items():
            total_count += 1
            suffix = mode_cfg["suffix"]
            asset_id = f"{gee_user_path.rstrip('/')}/{loc_code}_{suffix}"
            
            # 检查是否已存在
            asset_exists = check_asset_exists(asset_id)
            
            if asset_exists and skip_existing:
                print(f"  ⏭️  {mode_key} - 已存在，跳过")
                skip_count += 1
                continue
            
            # 强制模式：删除已存在的 asset
            if asset_exists and not skip_existing:
                try:
                    ee.data.deleteAsset(asset_id)
                    print(f"  🗑️  {mode_key} - 删除旧缓存...", end=" ", flush=True)
                except Exception as exc:
                    print(f"⚠️ 删除失败: {exc}")
                    # 继续尝试导出
            
            try:
                # 计算图层
                print(f"  🧮 {mode_key} - 计算中...", end=" ", flush=True)
                img = compute_layer(mode_key, viewport)
                
                if dry_run:
                    print("✅ (演习模式)")
                    success_count += 1
                    continue
                
                # 提交导出任务
                description = f"Cache_{loc_code}_{suffix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                task_id = export_to_asset(img, asset_id, viewport, description)
                
                print(f"✅ 已提交")
                print(f"     Task ID: {task_id}")
                print(f"     Asset: {asset_id}")
                success_count += 1
                
            except Exception as exc:
                print(f"❌ 失败: {exc}")
                fail_count += 1
    
    return success_count, skip_count, fail_count, total_count


def main():
    parser = argparse.ArgumentParser(
        description="批量预热所有场景的 GEE Asset 缓存",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认路径
  python scripts/batch_preheat.py
  
  # 指定自定义路径
  python scripts/batch_preheat.py --path projects/my-project/assets/cache
  
  # 强制重新导出（覆盖已存在的）
  python scripts/batch_preheat.py --force
  
  # 演习模式（不实际提交）
  python scripts/batch_preheat.py --dry-run
        """
    )
    
    parser.add_argument(
        "--path",
        default=DEFAULT_GEE_USER_PATH,
        help=f"GEE Asset 根路径（默认: {DEFAULT_GEE_USER_PATH}）"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新导出，即使 Asset 已存在"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演习模式：仅检查，不实际提交任务"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 AlphaEarth 批量预热脚本")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  演习模式：不会实际提交任务")
    
    # 初始化 GEE
    if not init_gee():
        sys.exit(1)
    
    # 执行批量预热
    success, skip, fail, total = batch_preheat(
        args.path,
        skip_existing=not args.force,
        dry_run=args.dry_run
    )
    
    # 输出统计
    print("\n" + "=" * 60)
    print("📈 执行统计")
    print("=" * 60)
    print(f"✅ 成功提交: {success}/{total}")
    print(f"⏭️  已跳过: {skip}/{total}")
    print(f"❌ 失败: {fail}/{total}")
    
    if not args.dry_run and success > 0:
        print("\n💡 提示:")
        print("  任务已在后台运行，预计 10-15 分钟完成")
        print("  查看任务状态：")
        print("    https://code.earthengine.google.com/tasks")
    
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
