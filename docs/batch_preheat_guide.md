# 批量预热脚本使用指南

## 📋 概述

批量预热脚本用于在后台一次性预热所有 20 个场景（5 城市 × 4 监测模式），避免用户首次访问时的长时间等待。

## 🚀 快速开始

### 演习模式（推荐先测试）

```bash
sudo bash scripts/batch_preheat_wrapper.sh --dry-run
```

这会**模拟运行**但不实际提交任务，用于验证配置是否正确。

### 正式预热

```bash
sudo bash scripts/batch_preheat_wrapper.sh
```

预计时间：**10-15 分钟**（后台运行）

### 强制重新预热（覆盖已存在的缓存）

```bash
sudo bash scripts/batch_preheat_wrapper.sh --force
```

## 📊 查看任务进度

访问 Google Earth Engine Tasks 页面：

```
https://code.earthengine.google.com/tasks
```

或在 Streamlit UI 侧边栏查看"🛰️ 缓存任务状态"面板。

## 🔧 高级用法

### 指定自定义 Asset 路径

```bash
sudo bash scripts/batch_preheat_wrapper.sh --path projects/my-project/assets/cache
```

### 组合参数

```bash
# 强制重新导出到自定义路径
sudo bash scripts/batch_preheat_wrapper.sh --force --path projects/custom/assets
```

## ⚙️ 技术说明

### 认证机制

脚本以 `alphaearth` 用户身份运行，继承 Streamlit 服务的 GEE 用户凭证：

- **用户凭证**：`/home/alphaearth/.config/earthengine/credentials`（当前）
- **服务账号**：未配置（可选，适合生产环境）

### 为什么需要 sudo？

- 脚本需要切换到 `alphaearth` 用户以访问 GEE 凭证
- 使用 `sudo -u alphaearth` 确保认证一致性

### 预热场景清单

| 城市 | 代码 | 地表 DNA | 变化雷达 | 建设强度 | 生态韧性 |
|------|------|----------|----------|----------|----------|
| 北京·通州 | beijing | ✓ | ✓ | ✓ | ✓ |
| 河北·雄安 | xiongan | ✓ | ✓ | ✓ | ✓ |
| 杭州·西湖 | hangzhou | ✓ | ✓ | ✓ | ✓ |
| 深圳·湾区 | shenzhen | ✓ | ✓ | ✓ | ✓ |
| 美国·纽约 | nyc | ✓ | ✓ | ✓ | ✓ |

**总计：20 个场景**

## 🐛 故障排查

### 错误：earthengine-api 未安装

**原因**：虚拟环境未激活或依赖缺失

**解决**：
```bash
cd /mnt/data/hyf/oneearth
source .venv/bin/activate
pip install earthengine-api
```

### 错误：Please authorize access to your Earth Engine account

**原因**：GEE 认证凭证不存在或已过期

**解决**：
```bash
# 以 alphaearth 用户重新认证
sudo -u alphaearth -H /opt/oneearth/.venv/bin/earthengine authenticate
```

### 错误：Permission denied: '/etc/alphaearth/alphaearth.env'

**原因**：正常警告，脚本会自动回退到用户凭证

**解决**：无需处理（或配置服务账号以消除警告）

### 任务提交后长时间 PENDING

**原因**：GEE 后台队列繁忙

**解决**：等待或降低并发量（分批提交）

## 📝 示例输出

```
🚀 AlphaEarth 批量预热脚本
============================================================
✅ 使用用户凭证认证成功

📍 目标路径: projects/aef-project-487710/assets/aef_demo
📊 总任务数: 5 城市 × 4 模式 = 20 个

🗺️  北京·通州 (beijing)
  🧮 地表 DNA - 计算中... ✅ 已提交
     Task ID: ABCD1234567890
     Asset: projects/aef-project-487710/assets/aef_demo/beijing_dna
  ⏭️  变化雷达 - 已存在，跳过
  ...

============================================================
📈 执行统计
============================================================
✅ 成功提交: 18/20
⏭️  已跳过: 2/20
❌ 失败: 0/20

💡 提示:
  任务已在后台运行，预计 10-15 分钟完成
  查看任务状态：
    https://code.earthengine.google.com/tasks
```

## 🔗 相关文档

- [Google Earth Engine Tasks 管理](https://code.earthengine.google.com/tasks)
- [AlphaEarth 部署手册](../docs/AlphaEarth_PoC_Development_Manual_v5.0.md)
- [GEE 认证指南](https://developers.google.com/earth-engine/guides/auth)

## ⏰ 建议执行时机

- **首次部署后**：立即预热所有场景
- **定期维护**：每月预热一次（数据更新）
- **性能优化**：用户反馈加载慢时
- **数据验证**：算法更新后验证结果

## 💡 最佳实践

1. **先演习后执行**：使用 `--dry-run` 验证配置
2. **避免重复提交**：默认会跳过已存在的缓存
3. **监控任务状态**：通过 GEE Tasks 页面查看进度
4. **错峰运行**：避免在高峰期（北京时间 9:00-18:00）提交大批量任务
5. **日志归档**：重要部署时保存输出日志

```bash
sudo bash scripts/batch_preheat_wrapper.sh --force 2>&1 | tee preheat_$(date +%Y%m%d_%H%M%S).log
```
