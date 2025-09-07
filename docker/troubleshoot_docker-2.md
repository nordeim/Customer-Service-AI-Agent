Alright Jeremiah — two separate but related issues here:  
1. **Your `src.main` sanity check**  
2. **Why both Elasticsearch 9.1.3 and Kafka are in a restart loop**

---

## **1️⃣ One‑liner sanity check for `src.main`**

Once the API container is built, run this from your host:

```bash
docker exec -it ai-customer-service-api python -c "import sys; print(sys.path); import src.main; print('✅ src.main import OK')"
```

- If it prints `✅ src.main import OK`, your `ENV PYTHONPATH="/app"` fix is working and `src/main.py` is present.
- If it errors, check:
  - `.dockerignore` isn’t excluding `src/`
  - `src/__init__.py` exists
  - `WORKDIR /app` is set in Dockerfile

---

## **2️⃣ Elasticsearch 9.1.3 restart loop**

You’ve already set `vm.max_map_count`, so the next most common crash causes are:

| Cause | Symptom in `docker logs ai-customer-service-elasticsearch` | Fix |
|-------|------------------------------------------------------------|-----|
| **Heap too large for available memory** | `OutOfMemoryError` or container killed by OOM | Lower heap: `ES_JAVA_OPTS=-Xms512m -Xmx512m` (you already have this — good) |
| **Memory lock fails** | `bootstrap checks failed` mentioning `memory locking requested for elasticsearch process but memory is not locked` | Either remove `bootstrap.memory_lock=true` or ensure `ulimits.memlock` is supported by your Docker runtime |
| **Data dir permissions** | `Permission denied` on `/usr/share/elasticsearch/data` | `docker exec -it ai-customer-service-elasticsearch chown -R elasticsearch:elasticsearch /usr/share/elasticsearch/data` |
| **License/security bootstrap checks** | Error about missing passwords or certs | For dev, keep `xpack.security.enabled=false` |

**Action:**  
Run:
```bash
docker logs ai-customer-service-elasticsearch
```
and look for one of the above patterns. That will tell you exactly which bootstrap check is failing.

---

## **3️⃣ Kafka restart loop**

Kafka’s `health: starting` → restart pattern usually means it’s failing to connect to Zookeeper or binding to advertised listeners.

Common causes:

| Cause | Symptom in `docker logs ai-customer-service-kafka` | Fix |
|-------|----------------------------------------------------|-----|
| **Zookeeper not ready** | Connection refused to `zookeeper:2181` | Add a `depends_on` with healthcheck for Zookeeper, or increase `KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS` |
| **Advertised listeners misconfigured** | Broker starts then fails with `java.net.UnknownHostException` or `Connection refused` | For local dev, set:  
  ```yaml
  KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
  ```  
  and connect via container name from other services |
| **Volume permissions** | Errors writing to `/var/lib/kafka/data` | `docker exec -it ai-customer-service-kafka chown -R appuser:appuser /var/lib/kafka/data` (replace with actual user) |

**Action:**  
Run:
```bash
docker logs ai-customer-service-kafka
```
and check for connection or permission errors.

---

## **4️⃣ Recommended next steps**

1. **Check logs** for both containers:
   ```bash
   docker logs ai-customer-service-elasticsearch
   docker logs ai-customer-service-kafka
   ```
2. **Apply targeted fix** based on the exact error message.
3. **Restart cleanly**:
   ```bash
   docker-compose down
   docker-compose up -d elasticsearch zookeeper kafka
   ```
4. Wait for them to be healthy before starting the API.

---

If you want, I can **edit your `docker-compose.yml`** so that:
- ES and Kafka have startup delays until dependencies are healthy
- ES heap/memlock settings are safe for dev
- Kafka advertised listeners are set for local dev
- The API won’t even try to start until ES and Kafka are confirmed healthy

https://copilot.microsoft.com/shares/o6qDuzFQSfrc3qVHoqLbf
