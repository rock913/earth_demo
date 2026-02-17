# AlphaEarth POC (ECS)

## 快速开始

### 方式 A：Conda（与手册一致，推荐 ECS）

```bash
conda create -n alpha_earth python=3.9 -y
conda activate alpha_earth
pip install -r requirements.txt

# 首次在 ECS 上需要做 Earth Engine 授权
# 无头 ECS 推荐 notebook 模式，避免 gcloud 依赖
earthengine authenticate --quiet --auth_mode=notebook

# 启动
./run.sh
```

### 方式 B：venv

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 首次在 ECS 上需要做 Earth Engine 授权
earthengine authenticate --quiet --auth_mode=notebook

# 启动
./run.sh
```

开发调试默认端口 `8501`。

- 本机访问：`http://127.0.0.1:8501`
- 公网访问（推荐）：通过 Nginx 反代：`http://<ECS公网IP>/`
- 公网直连（不推荐）：需将 Streamlit 监听改为 `0.0.0.0:8501` 并在安全组放行 `8501`（见下文）。

建议正式演示使用 Nginx + HTTPS（见下文），并将 Streamlit 仅绑定到 `127.0.0.1:8501`。

## 常见问题

- AEF 图层加载失败：通常是 GEE 未授权、数据集权限不可见、或网络受限。此时应用仍会展示 Sentinel-2 影像底图，并在页面给出报错提示。
- 无头服务器认证：按手册执行 `earthengine authenticate --quiet`，在本地浏览器打开 URL 并回填授权码。
- systemd 下仍提示“未认证”：务必确认你是用运行服务的同一用户（默认 `alphaearth`）做授权。推荐命令：
	- `sudo -u alphaearth -H /opt/oneearth/.venv/bin/earthengine authenticate --quiet --auth_mode=notebook --force`
	- 然后 `sudo systemctl restart alphaearth`

## systemd 运行的注意事项（重要）

- systemd 服务通常会启用硬化参数，导致 `/home/<user>` 在服务进程内不可访问。
- 本项目已在 [./.streamlit/config.toml](.streamlit/config.toml) 显式设置 `[secrets] files` 指向 `/opt/oneearth/.streamlit/secrets.toml`，避免 Streamlit 在 systemd 下尝试读取 `/home/.../.streamlit/secrets.toml`。
- Earth Engine 的交互式授权凭证默认写入 `~/.config/earthengine/credentials`（跟随 `HOME`/`XDG_CONFIG_HOME`）。因此 systemd 服务不应把 `HOME` 指向 `/opt/oneearth`，否则会“授权成功但服务仍找不到凭证”。

## 安全提示

不要在文档或仓库中保存真实 `refresh_token`/`credentials`。推荐只在服务器本地生成并用文件权限保护：`~/.config/earthengine/credentials`。

## 服务账号（可选）

### 如何获取服务账号以及其 JSON key

服务账号来自 Google Cloud (GCP)。总体流程是：创建/选择一个 Cloud Project → 启用 Earth Engine API → 创建 Service Account → 生成 JSON key → 将该 Service Account 授权给 Earth Engine → 在 ECS 上配置环境变量。

1) 创建/选择 Google Cloud Project

- 进入 Google Cloud Console，新建或选择一个项目（记下 `Project ID`）。
- 在该项目中启用 **Earth Engine API**（搜索 “Earth Engine API” → Enable）。

2) 创建 Service Account

- 进入：IAM & Admin → Service Accounts → Create Service Account
- 记录生成的服务账号邮箱（形如：`xxx@yyy.iam.gserviceaccount.com`）

3) 分配权限（最小可用建议）

- 给该 Service Account 赋予至少以下角色（在项目 IAM 中添加成员）：
	- Earth Engine Resource Viewer（通常为 `roles/earthengine.resourceViewer`）
	- Service Usage Consumer（通常为 `roles/serviceusage.serviceUsageConsumer`）

说明：不同组织策略/数据集权限可能需要额外角色；若仍报权限不足，再按报错逐步补齐。

4) 生成并下载 JSON key

- 打开该 Service Account → Keys → Add Key → Create New Key → JSON
- 下载得到的 JSON 文件就是 `EE_PRIVATE_KEY_FILE` 需要指向的 key。

安全提示：JSON key 等同于长期密钥，请勿上传仓库/群聊；建议只放服务器本地并 `chmod 600`。

5) 将 Service Account 授权给 Earth Engine（关键）

- 你的个人账号必须已开通 Earth Engine。
- 在 Earth Engine 的 Cloud Project / Service Account 管理页面中，将上面的 Service Account 邮箱加入到可访问该项目的列表（不同组织页面入口可能略有差异，核心是“把 SA 加入 Earth Engine 授权名单”）。

如果此步未完成，通常会出现 “Please authorize access … / Earth Engine account” 或权限相关错误。

如果不想做交互式授权，可用服务账号方式初始化 Earth Engine：

```bash
export EE_SERVICE_ACCOUNT="xxx@yyy.iam.gserviceaccount.com"
export EE_PRIVATE_KEY_FILE="/etc/alphaearth/service-account-key.json"
./run.sh
```

建议做法（systemd 常驻）：

1) 将服务账号 JSON key 放到服务器：`/etc/alphaearth/service-account-key.json`

2) 设置权限：

```bash
sudo chown alphaearth:alphaearth /etc/alphaearth/service-account-key.json
sudo chmod 600 /etc/alphaearth/service-account-key.json
```

3) 在 `/etc/alphaearth/alphaearth.env` 写入：

```bash
EE_SERVICE_ACCOUNT=xxx@yyy.iam.gserviceaccount.com
EE_PRIVATE_KEY_FILE=/etc/alphaearth/service-account-key.json
```

4) 重启服务：`sudo systemctl restart alphaearth`

## 测试（TDD / 快速定位问题）

本仓库提供了最小化 smoke tests，目标是：即使缺少 GEE/geemap 依赖，也能快速发现应用“启动即崩溃”的问题。

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 生产部署：systemd + Nginx + HTTPS

### 一键脚本（推荐）

在仓库根目录执行：

```bash
sudo bash deploy/bootstrap_ecs.sh -d your.domain.example --with-https --email you@example.com
```

说明：
- `-d` 这里建议填写域名（用于 Nginx 的 `server_name`）。
- 申请 HTTPS 证书（`--with-https`）时必须是域名，不能是纯 IP。

仅配置 HTTP（不申请证书）：

```bash
sudo bash deploy/bootstrap_ecs.sh -d 47.245.113.151
```

加速重跑（已装过系统包/依赖时）：

```bash
sudo bash deploy/bootstrap_ecs.sh -d 47.245.113.151 --skip-system --skip-python-deps --force-auth
```

提示：使用 IP 仅能 HTTP 访问；如需 HTTPS，请先准备域名并解析到该 ECS 公网 IP。

### 1) 安装依赖

说明：本节的“手动步骤”在 Debian/Ubuntu 上可直接照抄；在 Alibaba Cloud Linux（RHEL 系）请用 `dnf/yum`，并注意 Nginx 配置一般在 `/etc/nginx/conf.d/*.conf`。更推荐直接使用上面的“一键脚本”。

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

### 2) 交互式 Earth Engine 授权（一次性）

```bash
# 关键：交互式授权必须由运行服务的同一用户执行（这里是 alphaearth）
# 无头 ECS 推荐 notebook 模式，避免 gcloud 依赖
sudo -u alphaearth -H /opt/oneearth/.venv/bin/earthengine authenticate --quiet --auth_mode=notebook
```

### 3) 部署目录与日志目录

建议将代码放到：`/opt/oneearth`

```bash
sudo useradd -m -s /bin/bash alphaearth || true
sudo mkdir -p /opt/oneearth /var/log/alphaearth /etc/alphaearth
sudo chown -R alphaearth:alphaearth /opt/oneearth /var/log/alphaearth
sudo cp -r . /opt/oneearth/
sudo cp deploy/alphaearth.env.example /etc/alphaearth/alphaearth.env

# 建议在 /opt/oneearth 创建 venv（systemd 不依赖 conda）
sudo -u alphaearth -H bash -lc 'cd /opt/oneearth && python3 -m venv .venv'
sudo -u alphaearth -H bash -lc 'cd /opt/oneearth && ./.venv/bin/python -m pip install -U pip'
sudo -u alphaearth -H bash -lc 'cd /opt/oneearth && ./.venv/bin/python -m pip install -r requirements.txt'

# 关键：交互式授权必须由运行服务的同一用户执行（这里是 alphaearth）
sudo -u alphaearth -H /opt/oneearth/.venv/bin/earthengine authenticate --quiet --auth_mode=notebook
```

### 4) systemd 服务

```bash
sudo cp deploy/alphaearth.service /etc/systemd/system/alphaearth.service
sudo systemctl daemon-reload
sudo systemctl enable --now alphaearth

sudo systemctl status alphaearth --no-pager
sudo tail -n 200 /var/log/alphaearth/streamlit.log
```

### 5) Nginx 反向代理（HTTPS）

1) 先配置 HTTP 站点（用于后续申请证书）

```bash
sudo cp deploy/nginx-alphaearth.conf /etc/nginx/sites-available/alphaearth
sudo sed -i 's/YOUR_DOMAIN_NAME/your.domain.example/g' /etc/nginx/sites-available/alphaearth
sudo ln -sf /etc/nginx/sites-available/alphaearth /etc/nginx/sites-enabled/alphaearth
sudo nginx -t
sudo systemctl reload nginx
```

2) 申请 HTTPS 证书（Certbot）

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.example
```

完成后访问：`https://your.domain.example/`
```
# earth_demo
