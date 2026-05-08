#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -x /opt/homebrew/opt/node@22/bin/node ]; then
  export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
fi
export NODE_OPTIONS="${NODE_OPTIONS:-} --no-experimental-webstorage"
rm -rf .next
npm run build
exec npm run start
