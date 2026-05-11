#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
conda run -n UAX python -m dashboard.html.build
(sleep 1.5 && open http://127.0.0.1:8001) &
exec conda run -n UAX python dashboard/html/server.py --port 8001