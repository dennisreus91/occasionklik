#!/bin/bash

echo "📦 Start build: Installing Playwright and dependencies"
pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps
