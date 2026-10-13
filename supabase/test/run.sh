#!/usr/bin/env bash
# Önerilen oyun şemasını yerel PostgreSQL'de ebeveyn uygulamasının şemasıyla birlikte dener.
# Gerekenler: psql, çalışan bir sunucu (PGHOST/PGPORT), parent-app deposu (PARENT_APP, varsayılan ../../parent-app).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
parent="${PARENT_APP:-$here/../../../parent-app}"
db=pofi_test
psql -q -v ON_ERROR_STOP=1 -d postgres -c "drop database if exists $db" -c "create database $db"
run() { psql -q -t -o /dev/null -v ON_ERROR_STOP=1 -d "$db" -f "$1"; }
run "$here/supabase_stub.sql"
for f in "$parent"/supabase/migrations/*.sql; do run "$f"; done
for f in "$here"/../proposed/*.sql; do run "$f"; run "$f"; done   # iki kez: tekrar çalıştırmak zarar vermemeli
run "$here/test_game.sql"
echo "TAMAM: tüm testler geçti"
