# Microservice Testing & CI Notes

## 1. Test Architecture Overview

### Test Types in This Project

This project uses **service-level integration tests (in-process)**
rather than pure unit tests or full infrastructure integration tests.

  Type                                           Used?   Notes
  ---------------------------------------------- ------- ------------------
  Unit Test (mock everything including DB)       ❌      Not purely unit
  Integration Test with real Postgres/Rabbit     ❌      Not required
  Service-level Integration (SQLite in-memory)   ✅      Current approach

------------------------------------------------------------------------

## 2. Database Strategy in Tests

Tests use:

``` python
sqlite+pysqlite:///:memory:
```

Key settings:

-   `StaticPool` (required for SQLite memory reuse)
-   `check_same_thread=False`
-   `SessionLocal` overridden via `monkeypatch`
-   FastAPI dependency `get_db` overridden

This ensures:

-   No dependency on Postgres container
-   No Docker required
-   Fast execution
-   Fully isolated test environment

------------------------------------------------------------------------

## 3. Dependency Overrides Used

### Database Override

``` python
main.app.dependency_overrides[main.get_db] = override_get_db
```

### Auth Override

``` python
main.app.dependency_overrides[main.require_user] = lambda: {...}
```

This removes:

-   JWT validation dependency
-   External Auth service requirement

------------------------------------------------------------------------

## 4. HTTP Calls Are Mocked

`httpx.AsyncClient` is replaced using `monkeypatch` and a fake client.

This ensures:

-   No real network calls
-   Deterministic behavior
-   True logic testing without external dependency

------------------------------------------------------------------------

## 5. CI Implications

Since tests use:

-   SQLite in-memory
-   Mocked HTTP
-   No real RabbitMQ

The service does **NOT require**:

-   Postgres container
-   RabbitMQ container
-   Docker Compose

CI can simply run:

``` bash
pytest -q
```

------------------------------------------------------------------------

## 6. Recommended CI Structure

### Fast Stage (Recommended)

Run without Docker:

``` bash
pytest -q
```

### Optional Integration Stage

Only required if real DB or broker testing is introduced later.

------------------------------------------------------------------------

## 7. Benefits of Current Approach

-   Fast execution
-   Deterministic results
-   No infra dependency
-   Clean isolation per test run
-   Suitable for microservice-level validation

------------------------------------------------------------------------

## 8. Future Improvement (Optional)

If needed later:

-   Add real Postgres integration tests
-   Add RabbitMQ integration tests
-   Separate test layers:
    -   Unit
    -   Service Integration (current)
    -   Infrastructure Integration
    -   End-to-End

------------------------------------------------------------------------

## Conclusion

The current testing design is:

-   Clean
-   Production-ready for CI
-   Optimized for speed
-   Infrastructure-independent

This is a strong pattern for microservice testing.
