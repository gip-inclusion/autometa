# Caddy OAuth Setup for Matometa

**Goal:** Protect matometa.ljt.cc with Google OAuth authentication.

---

## Option A: caddy-security Plugin (Recommended)

The `caddy-security` plugin provides native OAuth2/OIDC support in Caddy.

### Step 1: Build Caddy with caddy-security

On the server, you need a custom Caddy build:

```bash
# Install xcaddy
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Build Caddy with security plugin
xcaddy build --with github.com/greenpau/caddy-security

# Replace system Caddy
sudo mv caddy /usr/bin/caddy
sudo systemctl restart caddy
```

### Step 2: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create or select a project
3. Click "Create Credentials" > "OAuth client ID"
4. Application type: **Web application**
5. Authorized redirect URIs:
   - `https://matometa.ljt.cc/auth/oauth2/google/callback`
6. Save the **Client ID** and **Client Secret**

### Step 3: Update Caddyfile

```caddyfile
{
    order authenticate before respond
    order authorize before respond

    security {
        oauth identity provider google {
            realm google
            driver google
            client_id {$GOOGLE_CLIENT_ID}
            client_secret {$GOOGLE_CLIENT_SECRET}
            scopes openid email profile
        }

        authentication portal myportal {
            crypto default token lifetime 3600
            cookie domain ljt.cc
            enable identity provider google

            # Optional: restrict to specific emails
            # transform user {
            #     match email suffix @yourcompany.com
            #     action add role authp/user
            # }
        }

        authorization policy mypolicy {
            set auth url https://matometa.ljt.cc/auth/
            allow roles authp/user authp/admin
        }
    }
}

matometa.ljt.cc {
    # Authentication portal routes
    route /auth/* {
        authenticate with myportal
    }

    # Protected app routes
    route /* {
        authorize with mypolicy
        reverse_proxy 127.0.0.1:5002
    }
}
```

### Step 4: Set Environment Variables

```bash
# On the server, add to /etc/caddy/environment or systemd override
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

For systemd:
```bash
sudo systemctl edit caddy
```

Add:
```ini
[Service]
Environment="GOOGLE_CLIENT_ID=your-client-id"
Environment="GOOGLE_CLIENT_SECRET=your-client-secret"
```

### Step 5: Reload Caddy

```bash
sudo systemctl daemon-reload
sudo systemctl restart caddy
```

---

## Option B: oauth2-proxy Sidecar (Simpler, No Custom Build)

If you can't rebuild Caddy, use `oauth2-proxy` as a sidecar.

### Step 1: Install oauth2-proxy

```bash
# Download latest release
wget https://github.com/oauth2-proxy/oauth2-proxy/releases/download/v7.6.0/oauth2-proxy-v7.6.0.linux-amd64.tar.gz
tar xzf oauth2-proxy-*.tar.gz
sudo mv oauth2-proxy-*/oauth2-proxy /usr/local/bin/
```

### Step 2: Create Config

```bash
sudo mkdir -p /etc/oauth2-proxy
sudo tee /etc/oauth2-proxy/oauth2-proxy.cfg << 'EOF'
provider = "google"
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
cookie_secret = "GENERATE_32_BYTE_SECRET"  # openssl rand -base64 32 | head -c 32
cookie_secure = true
cookie_domains = [".ljt.cc"]

email_domains = ["*"]  # Or restrict: ["yourcompany.com"]

upstreams = ["http://127.0.0.1:5002"]
http_address = "127.0.0.1:4180"
redirect_url = "https://matometa.ljt.cc/oauth2/callback"

skip_provider_button = true
EOF
```

### Step 3: Create Systemd Service

```bash
sudo tee /etc/systemd/system/oauth2-proxy.service << 'EOF'
[Unit]
Description=OAuth2 Proxy
After=network.target

[Service]
ExecStart=/usr/local/bin/oauth2-proxy --config=/etc/oauth2-proxy/oauth2-proxy.cfg
Restart=always
User=nobody

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable oauth2-proxy
sudo systemctl start oauth2-proxy
```

### Step 4: Update Caddyfile

```caddyfile
matometa.ljt.cc {
    reverse_proxy 127.0.0.1:4180
}
```

---

## Restricting Access to Specific Users

Both options support email whitelisting:

**caddy-security:**
```caddyfile
transform user {
    match email you@gmail.com
    action add role authp/admin
}
transform user {
    match email colleague@gmail.com
    action add role authp/user
}
```

**oauth2-proxy:**
```
authenticated_emails_file = "/etc/oauth2-proxy/allowed_emails.txt"
```

Where `allowed_emails.txt` contains one email per line.

---

## Verification

After setup:
1. Visit https://matometa.ljt.cc
2. Should redirect to Google login
3. After auth, should see the Matometa app
4. Check Caddy logs: `journalctl -u caddy -f`

---

## Security Notes

- The app still has no internal authentication - Caddy is the only gate
- Consider adding the authenticated user's email to request headers for audit logging
- Set `cookie_secure = true` (HTTPS only)
- Rotate cookie secrets periodically
