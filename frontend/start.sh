#!/bin/bash
cd "$(dirname "$0")"
npm install --silent
PORT=5000 npm run dev
