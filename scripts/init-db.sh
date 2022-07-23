#!/usr/bin/env bash
set -euo pipefail

execDBStatement() {
  mysql \
  --host=$WRITE_DB_HOST \
  --port=$WRITE_DB_PORT \
  --user=$WRITE_DB_USER \
  --password=$WRITE_DB_PASS \
  --database=$WRITE_DB_NAME \
  --command="$1"
}

# TODO: will need to edit this when implementing unit tests
execDBStatement "CREATE DATABASE IF NOT EXISTS ${WRITE_DB_NAME};"
