#!/bin/bash
echo "📦 Start build: Installing Playwright and dependencies"

pip install playwright
playwright install --with-deps
