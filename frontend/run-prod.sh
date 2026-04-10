#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
rm -rf .next
npm run build
exec npm run start
