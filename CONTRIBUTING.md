# 协作与发布约定

## Git

- `main` 保持可构建，功能使用 `feat/<name>`，修复使用 `fix/<name>` 分支，通过 PR 合并。
- 提交建议使用 `feat:`、`fix:`、`build:`、`docs:` 等前缀，例如 `build: containerize frontend and backend`。
- 发布版本使用 `v1.0.0` 格式的 Git 标签，镜像对应 `1.0.0`；不要覆盖已发布版本。
- `.gitattributes` 统一 LF，`.editorconfig` 统一 UTF-8 和缩进。
- 提交前检查 `git diff --check` 和 `git diff --cached`。
- 不提交 `.env`、密钥、虚拟环境、Python 缓存、`node_modules`、`dist`、镜像导出文件。
- 提交前后端源码及依赖锁文件。后端使用 `requirements.txt` + `requirements.lock`；前端使用 `npm ci`。

本地仓库已设置 `core.autocrlf=false`、`core.safecrlf=warn`、`pull.ff=only`、`fetch.prune=true`、`push.default=simple`。
这些配置不随 Git 克隆传播；新机器可自行执行相应 `git config --local` 命令。
提交身份沿用你已有的 Git 配置。

## 检查

```powershell
./scripts/build.ps1
docker compose up -d --no-build --wait
python scripts/smoke_test.py
docker compose exec -T backend pip check
```

GitHub Actions 在 main 推送、PR、v 开头标签或手动触发时构建两个镜像，启动独立 MySQL/Redis，检查页面、SPA 路由和新闻接口。
CI 只构建和验证，不登录 Docker Hub、不推送镜像、不部署服务器。
数据库示例数据仅用于初次初始化；后续表结构变更应提交单独迁移脚本，不依靠重建数据卷。

## 手动发布到 Docker Hub

先检查并提交本次变更，创建发布标签：

```powershell
git add .
git diff --cached --check
git diff --cached --stat
git commit -m "build: containerize frontend and backend"
git tag -a v1.0.0 -m "Release 1.0.0"
```

使用你自己的 Docker Hub 用户名构建正式版本；脚本要求发布时工作区干净，并把 Git 提交和版本写入 OCI 标签。
默认按本机架构构建，本机为 linux/amd64。

```powershell
./scripts/build.ps1 -Version 1.0.0 -Namespace yourname
docker login --username yourname
docker push yourname/diggoldtitle-frontend:1.0.0
docker push yourname/diggoldtitle-backend:1.0.0
```

`yourname` 替换为实际 Docker Hub 用户名；令牌在 `docker login` 提示中输入，不写入 `.env` 或源码。
仅推送这两个应用镜像，MySQL/Redis 使用官方镜像。

部署机器获取项目的 `compose.yaml`、`sql/` 和自行配置的 `.env`，在 `.env` 中设置：

```dotenv
DOCKERHUB_NAMESPACE=yourname
IMAGE_TAG=1.0.0
```

然后执行：

```powershell
docker compose pull
docker compose up -d --no-build --wait
```

回退应用版本时，把 `IMAGE_TAG` 改回上一版本后执行同样命令；数据库结构变更需要单独兼容或回滚。
正式版本不要只依赖 `latest` 标签。需要更严格复现时，将基础镜像变量设置为 `镜像名@sha256:摘要`。
