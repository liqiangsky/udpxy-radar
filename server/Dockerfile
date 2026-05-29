# ==========================================
# 阶段 1：依赖编译构建阶段（减小最终镜像体积）
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装底层编译所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖声明文件
COPY requirements.txt .

# 编译并生成 Python 依赖轮子（Wheels）
RUN pip install --no-cache-dir --user -r requirements.txt


# ==========================================
# 阶段 2：轻量化最终运行镜像阶段
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# 安装运行时系统环境：git（huggingfacehub备份必须）以及 sqlite3 基础工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 从编译阶段拷贝已安装的依赖库
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 预先创建数据库存储位置，并赋予 777 最高权限
# （Hugging Face 容器运行时会随机分配非 root 用户，必须保证其有写权限）
RUN mkdir -p /app/data && chmod -R 777 /app

# 智能声明环境变量
# 1. 强制 Python 将日志实时打印，防止在 Hugging Face 的 Logs 里面被缓存堵塞
ENV PYTHONUNBUFFERED=1
# 2. 将数据库路径重定向至具备可写权限的目录
ENV DB_PATH=/app/data/udpxy_radar.db
ENV CACHE_DB_PATH=/app/data/source_cache.db
ENV IPTV_DB_PATH=/app/data/iptv_list.db
# 3. 默认监听端口
ENV PORT=7860

# 拷贝全量解耦后的项目源码
COPY . .

# 暴露 Hugging Face 规定的默认 7860 端口
EXPOSE 7860

# 启动命令：使用 uvicorn 驱动，将单实例拉满，工作线程交由 fastapi 内部的 asyncio 异步矩阵打通
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
