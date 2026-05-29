## WhatsApp bridge install (mautrix-whatsapp)

Adds a WhatsApp bridge to the Synapse stack from `README.md`.

### Step 1. Prepare data directory

The bridge stores its config and state in `/data` inside the container.
The image runs as UID 1337, so the host dir must be owned by it.

```
mkdir -p /var/synapse/bridges/whatsapp/data
chown -R 1337:1337 /var/synapse/bridges/whatsapp/data
```

### Step 2. Add service to docker-compose.yml

Synapse needs to reach the bridge over the internal network; the bridge
needs its own appservice port. We use 29319 because 29318 is taken by
mautrix-telegram.

Add this block next to `mautrix-telegram`:

```yaml
  mautrix-whatsapp:
    container_name: mautrix-whatsapp
    image: dock.mau.dev/mautrix/whatsapp:latest
    restart: unless-stopped
    depends_on:
      - synapse
      - db
    volumes:
      - /var/synapse/bridges/whatsapp/data:/data
    networks:
      - synapse_network
    ports:
      - "29319:29319"
```

### Step 3. Generate default config.yaml

On first launch with an empty `/data` the bridge writes an example
`config.yaml` and exits. We use `run --rm` so it doesn't get caught by
the restart policy.

```
cd /etc/synapse
docker compose run --rm mautrix-whatsapp
ls /var/synapse/bridges/whatsapp/data
```

Expect to see `config.yaml` appear and the container exit with a message
saying the config needs editing.

### Step 4. Create whatsapp database in postgres

The bridge keeps its own state (linked devices, message map, portals) in
its own database, separate from Synapse's `synapse` DB.

```
docker exec -it synapse-db-1 psql -U synapse -c "CREATE DATABASE whatsapp OWNER synapse;"
```

### Step 5. Edit config.yaml

The generated config points at `example.com`. Replace these values so the
bridge knows how to reach Synapse, where to listen, which DB to use, and
who is allowed to use it.

Find and change in `/var/synapse/bridges/whatsapp/data/config.yaml`:

| Section          | Find                                                          | Replace with                                                  |
|------------------|---------------------------------------------------------------|---------------------------------------------------------------|
| `homeserver`     | `address: http://example.localhost:8008`                      | `address: http://synapse:8008`                                |
| `homeserver`     | `domain: example.com`                                         | `domain: atpmatrix.com`                                       |
| `appservice`     | `address: http://localhost:29318`                             | `address: http://mautrix-whatsapp:29319`                      |
| `appservice`     | `hostname: 127.0.0.1`                                         | `hostname: 0.0.0.0`                                           |
| `appservice`     | `port: 29318`                                                 | `port: 29319`                                                 |
| `database`       | `uri: postgres://user:password@host/database?sslmode=disable` | `uri: postgres://synapse:passwd@db/whatsapp?sslmode=disable`  |
| `bridge.permissions` | `"example.com": user`                                     | `"atpmatrix.com": user`                                       |
| `bridge.permissions` | `"@admin:example.com": admin`                             | `"@admin:atpmatrix.com": admin`                               |

Why:

* `synapse:8008` and `mautrix-whatsapp:29319` are the container DNS names
  on the `synapse_network` network — that's how the two services find
  each other.
* `0.0.0.0` is needed so the appservice listens on all interfaces inside
  the container, not just localhost.
* Port 29319 avoids the conflict with `mautrix-telegram` on 29318.
* The DB credentials match what's in `docker-compose.yml`. The `whatsapp`
  DB was created in step 4.
* Permissions: `atpmatrix.com: user` lets any local Matrix user start a
  WhatsApp session; `@admin:atpmatrix.com: admin` lets the admin run
  bridge-management commands.

Verify:

```
grep -nE "address:|domain:|hostname:|port:|uri:" /var/synapse/bridges/whatsapp/data/config.yaml
```

### Step 6. Generate registration.yaml

Run the bridge again. Now that the config is valid, it produces
`registration.yaml` with `as_token` / `hs_token` that Synapse needs.

```
docker compose run --rm mautrix-whatsapp
ls /var/synapse/bridges/whatsapp/data
```

`config.yaml` and `registration.yaml` should both be there.

### Step 7. Register the bridge in Synapse

Synapse only loads files that are inside its `/data` mount and listed in
`homeserver.yaml`. Copy the registration over (Telegram bridge uses the
same pattern), then add it to `app_service_config_files`.

```
cp /var/synapse/bridges/whatsapp/data/registration.yaml /var/synapse/data/whatsapp-registration.yaml
chmod 644 /var/synapse/data/whatsapp-registration.yaml
sed -i '/^- \/data\/registration.yaml$/a - /data/whatsapp-registration.yaml' /var/synapse/data/homeserver.yaml
```

Verify the block in `/var/synapse/data/homeserver.yaml`:

```
# Telegram
app_service_config_files:
- /data/registration.yaml
- /data/whatsapp-registration.yaml
```

Without this entry Synapse doesn't know about the bridge and rejects its
calls with 403.

### Step 8. Restart and verify

Restart so Synapse loads the new registration and the bridge connects.

```
systemctl restart synapse
docker logs --tail 30 mautrix-whatsapp
```

Look for `Bridge started` and successful `GET .../client/versions`
responses. Common failures:

* `password authentication failed for user "synapse"` — the password in
  `database.uri` doesn't match `POSTGRES_PASSWORD` in
  `docker-compose.yml`. The value `passwd` in the example is just a
  placeholder — use the real one from your stack.
* `connection refused` to `synapse:8008` — Synapse is restarting or
  failed to load the new registration; check `docker logs synapse-synapse-1`.

### Step 9. Login from Element

Start a direct chat with `@whatsappbot:atpmatrix.com` and send:

```
login qr
```

The bot replies with a QR code. On your phone open WhatsApp → Settings →
Linked Devices → Link a Device and scan it. After a few seconds your
existing chats appear as Matrix rooms.
