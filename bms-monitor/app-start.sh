#!/usr/bin/env bash
set -euo pipefail

echo "[app-start] 準備執行資料庫遷移..."

# Export DATABASE_URL to alembic environment
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[app-start] 警告: DATABASE_URL 未設定，將由 alembic.ini 讀取"
fi

# Retry alembic upgrade until success (DB 可能尚未就緒)
max_retries=30
retry=0
until alembic -c /app/alembic.ini upgrade head; do
  retry=$((retry+1))
  if [ "$retry" -ge "$max_retries" ]; then
    echo "[app-start] 遷移失敗，已重試 $retry 次，放棄啟動。"
    exit 1
  fi
  echo "[app-start] 資料庫尚未就緒，3 秒後重試 ($retry/$max_retries)..."
  sleep 3
done

echo "[app-start] 遷移完成，啟動 FastAPI..."

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

