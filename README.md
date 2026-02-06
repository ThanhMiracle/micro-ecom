
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
