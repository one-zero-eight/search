#!/bin/bash

export SETTINGS_PATH="settings.test.yaml"

echo "Launching docker compose..."
if ! docker compose -f docker-compose.test.yaml up -d; then
  echo "Ahtung! docker compose failed to start"
  exit 1
fi

echo "All docker containers has been successfully launched"

echo "Running tests..."
if ! poetry run pytest -s --asyncio-mode=auto --cov-config=.coveragerc --cov=src/ tests/; then
  docker compose -f docker-compose.test.yaml down
  echo "Ahtung! some tests are failed"
  exit 1
fi

echo "Successfully run tests"

echo "Stopping docker compose..."
if ! docker compose -f docker-compose.test.yaml down; then
  echo "Something went wrong when stopping docker containers"
  exit 1
fi

echo "All docker containers stopped successfully"
echo "Testing is finished"
