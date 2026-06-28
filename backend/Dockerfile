FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend
WORKDIR /app/backend
ENV CRA_UPLOAD_DIR=/app/data/uploads
ENV CRA_DATABASE_URL=sqlite:////app/data/cra.db
RUN mkdir -p /app/data/uploads
EXPOSE 8000
# 首启动初始化种子（幂等），随后启动服务
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
