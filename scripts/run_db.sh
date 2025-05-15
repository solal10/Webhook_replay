#!/usr/bin/env bash
set -e
case "$1" in
  up)
    docker compose up -d db
    echo "Postgres is starting…"
    ;;
  down)
    docker compose down
    ;;
  *)
    echo "Usage: $0 {up|down}"
    exit 1
esac
