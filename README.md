
# 🍭 MicroShop (Candy Edition)

Full-stack microservices demo:
- FastAPI microservices
- React + Vite frontend (candy / colorful UI)
- PostgreSQL
- RabbitMQ (emails)
- Docker Compose

## Run
- docker compose up --build
- Frontend: http://localhost:3000

----------------------------------------
# Health Check 
Short answer: **no, it’s not strictly necessary**.
But it *does* change how Docker / Compose / orchestration behaves, so here’s the practical breakdown without fluff.

---

## If you **DON’T** have a healthcheck

Nothing breaks by itself.

What happens:

* Docker considers the container **“running” as soon as the process starts**
* Even if:

  * the app hasn’t finished startup
  * DB/RabbitMQ is unreachable
  * background consumers crashed
* `depends_on` **cannot** wait for “ready”, only “started”
* Other services may start calling it too early

This is exactly why earlier you saw:

* notify starts → RabbitMQ not ready → consumer crashes → container still “Up”
* emails **sometimes** work, sometimes not

Docker thinks everything is fine because the process is alive.

---

## If you **DO** have a healthcheck

Docker gets a real signal: *“is this service usable?”*

What changes:

* Container has states: `starting` → `healthy` / `unhealthy`
* `depends_on: condition: service_healthy` **actually means something**
* You can:

  * delay dependent services
  * restart unhealthy containers
  * detect broken-but-running services

For example:

```bash
docker ps
# STATUS
Up 2 minutes (healthy)
```

vs

```bash
Up 2 minutes (unhealthy)
```

---

## In your specific project (microservices + RabbitMQ)

### Healthcheck is **strongly recommended** for:

* `notify` (RabbitMQ consumer)
* `auth` / `order` (DB + RabbitMQ)
* `product` (DB)

Because:

* Your services **depend on external systems**
* They can be “up” but **functionally dead**
* Without healthcheck, failures are silent

Mail not sending is the perfect example.

---

## What happens if you skip it (real consequences)

* Race conditions at startup (you already hit this)
* No automatic recovery
* Harder debugging
* Orchestrators (Compose / Swarm / K8s) make worse decisions

In Kubernetes, a missing readiness probe causes *the same class of bugs*.

---

## When healthcheck is NOT worth it

You can skip it if:

* Single container app
* No dependencies
* No background workers
* You don’t care about startup order

That’s not your case.

---

## Minimal, low-cost healthcheck (recommended)

This is enough and cheap:

```dockerfile
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"
```

And in FastAPI:

```py
@app.get("/health")
def health():
    return {"ok": True}
```

No DB calls, no RabbitMQ calls — just “is the web server alive”.

---

## Important clarification

Healthcheck **does NOT replace retry logic**.

You still must:

* retry RabbitMQ connections
* handle DB reconnects

Healthcheck just tells the platform the truth.

---

### Bottom line

* ❌ Not required
* ✅ Very useful
* 🚨 In your system: **you already felt the pain of not having it**

If you want, I can tell you:

* which services need **readiness** vs **liveness**
* or how this maps cleanly to Kubernetes probes later

Just say the word.


# FIX DNS docker 
That error is not your compose file — it’s your machine/container runtime **can’t complete TLS to Docker Hub** (`registry-1.docker.io`). Typical causes: flaky network, DNS, IPv6 path issues, corporate proxy, or Docker daemon DNS.

Here are fixes that usually work (do in order).

---

## 1) Quick retry + increase client timeouts

```bash
export DOCKER_CLIENT_TIMEOUT=300
export COMPOSE_HTTP_TIMEOUT=300
docker compose -f docker-compose.yml pull
docker compose -f docker-compose.yml up -d --build
```

---

## 2) Check basic connectivity to Docker Hub

```bash
curl -I https://registry-1.docker.io/v2/
```

* If this also times out → it’s network/DNS/proxy issue on your host.

---

## 3) Fix Docker DNS (very common)

Create/edit `/etc/docker/daemon.json`:

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "dns": ["1.1.1.1", "8.8.8.8"]
}
JSON
```

Restart Docker:

```bash
sudo systemctl restart docker
```

Then try:

```bash
docker compose pull
```

---

## 4) Disable IPv6 for Docker (often fixes TLS handshake timeout)

Edit `/etc/docker/daemon.json` to:

```json
{
  "ipv6": false,
  "dns": ["1.1.1.1", "8.8.8.8"]
}
```

Restart Docker again:

```bash
sudo systemctl restart docker
```

---

## 5) If you’re behind a proxy / VPN

Docker daemon needs proxy config too.

Check if you have proxy env vars:

```bash
env | grep -i proxy
```

If you do, you must configure Docker service proxy:

```bash
sudo systemctl edit docker
```

Add:

```
[Service]
Environment="HTTP_PROXY=http://YOUR_PROXY:PORT"
Environment="HTTPS_PROXY=http://YOUR_PROXY:PORT"
Environment="NO_PROXY=localhost,127.0.0.1,.local,::1"
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

## 6) Workaround: pull with a mirror / different registry route

Sometimes Docker Hub rate/route issues. If you have images hosted elsewhere (GHCR), switch.

Or temporarily change network:

```bash
docker pull hello-world
```

If `hello-world` fails too → definitely connectivity to hub.

---

## 7) If you just want to start without pulling

If you already have images locally, do:

```bash
docker compose up -d --build --pull never
```

(But yours is failing while pulling, so this only helps if images already exist.)

---

### Tell me these 3 outputs and I’ll point to the exact fix:

```bash
curl -I https://registry-1.docker.io/v2/
docker info | sed -n '1,80p'
cat /etc/docker/daemon.json 2>/dev/null || echo "no daemon.json"
```

Most likely fix is **Docker DNS** + restart.




docker run -d \
  --name jenkins-blueocean \
  --restart unless-stopped \
  --user root \
  --dns 10.16.32.53 --dns 10.133.93.53 --dns 10.98.112.53 \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins-data:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  myjenkins-blueocean:2.541.2-2


  docker compose -p microshop-ci-36 \
  -f docker-compose.yml \
  -f docker-compose.ci.yml \
  build --progress=plain