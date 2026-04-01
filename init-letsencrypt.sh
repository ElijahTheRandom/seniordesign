#!/bin/bash
# -------------------------------------------------------------------
#  init-letsencrypt.sh
#  Bootstrap Let's Encrypt certificates for ps.elijahshannon.com
#
#  Run ONCE on the server before the first `docker compose up -d`.
#  After that the certbot container handles automatic renewal.
# -------------------------------------------------------------------
set -e

DOMAIN="ps.elijahshannon.com"
EMAIL="egs0025@uah.edu"          # change if needed
STAGING=0                                 # set to 1 to test against LE staging

DATA_PATH="./certbot"
NGINX_CONF="./nginx/conf.d/default.conf"

# --- 1. Download recommended TLS parameters if missing ----------------
if [ ! -e "$DATA_PATH/conf/options-ssl-nginx.conf" ] || [ ! -e "$DATA_PATH/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$DATA_PATH/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
    > "$DATA_PATH/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem \
    > "$DATA_PATH/conf/ssl-dhparams.pem"
  echo
fi

# --- 2. Create a dummy certificate so nginx can start -----------------
echo "### Creating dummy certificate for $DOMAIN ..."
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
docker compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
    -keyout '$CERT_PATH/privkey.pem' \
    -out    '$CERT_PATH/fullchain.pem' \
    -subj   '/CN=localhost'" certbot
echo

# --- 3. Start nginx with the dummy cert --------------------------------
echo "### Starting nginx ..."
docker compose up --force-recreate -d nginx
echo

# --- 4. Remove the dummy certificate -----------------------------------
echo "### Deleting dummy certificate for $DOMAIN ..."
docker compose run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/$DOMAIN && \
  rm -rf /etc/letsencrypt/archive/$DOMAIN && \
  rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot
echo

# --- 5. Request a real certificate from Let's Encrypt -------------------
echo "### Requesting Let's Encrypt certificate for $DOMAIN ..."

STAGING_ARG=""
if [ "$STAGING" != "0" ]; then
  STAGING_ARG="--staging"
fi

docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG \
    --email $EMAIL \
    -d $DOMAIN \
    --rsa-key-size 4096 \
    --agree-tos \
    --force-renewal" certbot
echo

# --- 6. Reload nginx with the real certificate --------------------------
echo "### Reloading nginx ..."
docker compose exec nginx nginx -s reload
echo

echo "### Done!  Certificate installed for $DOMAIN."
