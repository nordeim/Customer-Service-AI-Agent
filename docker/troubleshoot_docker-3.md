Jeremiah — those Kafka logs tell the story:  
Kafka is starting, connecting to Zookeeper, establishing a session… and then Zookeeper closes the socket almost immediately. That’s why you see:

```
EndOfStreamException: Unable to read additional data from server sessionid ..., likely server has closed socket
```

This is a **Zookeeper-side disconnect** before Kafka can finish its startup handshake.

---

## Why this happens

In a Confluent Platform setup like yours (`cp-kafka` + `cp-zookeeper`), this pattern usually points to one of these:

| Cause | What happens | How to check/fix |
|-------|--------------|------------------|
| **Zookeeper not fully ready** | Kafka connects too early, ZK accepts the TCP connection but closes it before the session is usable | Add a healthcheck to Zookeeper and make Kafka `depends_on` that healthcheck |
| **Zookeeper data dir mismatch** | If you’ve upgraded Zookeeper or changed configs but kept the old `zookeeper_data` volume, the stored snapshot/log format may be incompatible | Stop stack, remove Zookeeper’s data volume, restart |
| **Low memory / container OOM** | Zookeeper starts but is killed or restarts due to memory limits, dropping Kafka’s connection | Check `docker logs ai-customer-service-zookeeper` for restarts or OOM errors; increase memory allocation |
| **Network name resolution issue** | Kafka can’t resolve `zookeeper` to the right container IP | `docker exec -it ai-customer-service-kafka ping zookeeper` should work |
| **SASL misconfig** | Not in your case — logs show “Will not attempt to authenticate using SASL” and you’re using PLAINTEXT |

---

## Step 1 — Check Zookeeper logs

Run:

```bash
docker logs ai-customer-service-zookeeper
```

If you see errors like `java.io.IOException: No snapshot found` or `File version mismatch`, it’s a data directory issue.

---

## Step 2 — If it’s a data mismatch, reset Zookeeper

Since you just reset Elasticsearch by removing its volume, you can do the same for Zookeeper (and Kafka, since Kafka stores metadata in Zookeeper):

```bash
docker-compose down
docker volume rm customer-service-ai-agent_kafka_data
docker volume rm customer-service-ai-agent_zookeeper_data   # if you have a named volume for ZK
docker-compose up -d zookeeper kafka
```

*(Replace volume names with the actual ones from `docker volume ls`.)*

---

## Step 3 — Add a Zookeeper healthcheck and startup ordering

In `docker-compose.yml`:

```yaml
  zookeeper:
    ...
    healthcheck:
      test: ["CMD", "zkServer.sh", "status"]
      interval: 10s
      timeout: 5s
      retries: 5

  kafka:
    ...
    depends_on:
      zookeeper:
        condition: service_healthy
```

This ensures Kafka only starts after Zookeeper is actually ready to accept long-lived sessions.

---

## Step 4 — Verify

After restarting:

```bash
docker ps
docker logs ai-customer-service-kafka
```

You should see Kafka’s startup complete with lines like:

```
[KafkaServer id=1] started (kafka.server.KafkaServer)
```

---

If you want, I can patch your `docker-compose.yml` so that:
- Zookeeper has a proper healthcheck
- Kafka waits for it
- Both have safe dev memory settings
- You can reset their volumes cleanly without touching other services

https://copilot.microsoft.com/shares/djY14dGfxr5WRUiKwXhSv
