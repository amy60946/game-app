#!/usr/bin/env bash
# CI: GitHub secret SUPABASE_PUBLISHABLE_KEY varsa oyunun sunucu ayarına (server.json) yazar.
# Yalnızca yayınlanabilir (anon/publishable) anahtar! Gizli anahtar (sb_secret_ / service_role) reddedilir;
# oyun da (ServerConfig.LooksSecret) böyle bir anahtarı yok sayar. Anahtar loga yazdırılmaz.
set -euo pipefail
f=Assets/_Pofi/Resources/Data/server.json
key="${SUPABASE_PUBLISHABLE_KEY:-}"
if [ -z "$key" ]; then
  echo "SUPABASE_PUBLISHABLE_KEY yok: oyun sahte arka uçla derlenir (deneme kodları)."
  exit 0
fi
case "$key" in
  sb_secret_*) echo "::error::SUPABASE_PUBLISHABLE_KEY gizli anahtar (sb_secret_). Publishable anahtarı yaz."; exit 1 ;;
  eyJ*)
    # eski tip JWT anahtar: yalnız "anon" rolü kabul (service_role derlemeye gömülmesin; güvenlik denetimi L1)
    payload=$(printf '%s' "$key" | cut -d. -f2 | tr '_-' '/+')
    while [ $(( ${#payload} % 4 )) -ne 0 ]; do payload="$payload="; done
    role=$(printf '%s' "$payload" | base64 -d 2>/dev/null | jq -r '.role // empty' 2>/dev/null || true)
    if [ "$role" != "anon" ]; then
      echo "::error::SUPABASE_PUBLISHABLE_KEY anon anahtarı değil (rol: ${role:-okunamadı}). Publishable/anon anahtarı yaz."; exit 1
    fi ;;
esac
jq --arg k "$key" '.publishableKey = $k' "$f" > "$f.tmp"
mv "$f.tmp" "$f"
echo "Gerçek sunucu açık: $(jq -r .url "$f") (deneme kodları sahte arka uçta kalır)."
