#!/bin/sh
set -e

dirname=$(dirname "$0")
root=$(cd "$dirname/.." && pwd)
cd "$root"

docker compose build mcp-api
