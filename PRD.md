# PRD: JARVIS Azure Deployment with Redis Memory

## Introduction

Deploy the working JARVIS voice assistant with Redis-based long-term memory to Azure. The local setup (jarvis-voice on localhost:8000, Redis agent-memory-server on 10.69.3.72:8002) is confirmed working with semantic search. This PRD covers pushing jarvis-voice updates and replacing the broken Mem0/Qdrant setup in jarvis-cloud with Redis agent-memory-server.

## Current State

**Working locally:**
- jarvis-voice container with Redis memory_client.py
- Redis Stack + agent-memory-server on 10.69.3.72:8002
- Semantic search verified: "what is user name" finds "User name is James"

**Azure (outdated):**
- jarvis-voice: 17 commits behind + uncommitted Redis fix
- jarvis-cloud: Mem0 + Qdrant (substring matching only, broken)

## Goals

- Push jarvis-voice with Redis memory_client.py to GitHub
- Redeploy jarvis-voice to Azure Container Apps
- Replace jarvis-cloud Mem0+Qdrant with Redis Stack + agent-memory-server
- Verify semantic memory search works in production

## Definition of Done

1. Both repos pushed and current
2. Azure jarvis-voice using Redis memory endpoint
3. Manual test: Tell JARVIS a fact → Restart → Ask recall → Correct answer

---

## User Stories

### US-001: Commit and push jarvis-voice
**Description:** As a developer, I want to push all local changes to GitHub so the repo is current.

**Acceptance Criteria:**
- [ ] Stage modified files (memory_client.py, requirements.txt, etc.)
- [ ] Commit with message describing Redis integration
- [ ] Push all commits to origin/main
- [ ] GitHub repo shows latest commit

---

### US-002: Rebuild and push jarvis-voice Docker image
**Description:** As a developer, I want the updated Docker image in Azure Container Registry.

**Acceptance Criteria:**
- [ ] `az acr build` pushes new image to ACR
- [ ] Image tagged with commit SHA or version
- [ ] ACR shows new image

---

### US-003: Update jarvis-voice Container App
**Description:** As a developer, I want Azure Container App running the new image.

**Acceptance Criteria:**
- [ ] Container App updated to use new image
- [ ] MEMORY_SERVER_URL env var set (placeholder until US-007)
- [ ] Container healthy and responding on /health
- [ ] WebSocket connections work

---

### US-004: Create Redis Stack Azure YAML
**Description:** As a developer, I need Redis Stack container config for Azure.

**Reference:** 10.69.3.72 docker-compose.yml

**Acceptance Criteria:**
- [ ] Create azure/redis.yaml
- [ ] Image: redis/redis-stack:latest
- [ ] Internal ingress only (port 6379)
- [ ] 1Gi memory, 0.5 CPU
- [ ] Push to jarvis-cloud repo

---

### US-005: Create agent-memory-server Azure YAML
**Description:** As a developer, I need agent-memory-server container config for Azure.

**Reference:** 10.69.3.72 docker-compose.yml

**Acceptance Criteria:**
- [ ] Create azure/agent-memory-server.yaml
- [ ] Image from 10.69.3.72 setup (or redis/agent-memory-server)
- [ ] External ingress on port 8002
- [ ] REDIS_URL env var pointing to Redis container
- [ ] Push to jarvis-cloud repo

---

### US-006: Deploy Redis memory stack to Azure
**Description:** As a developer, I want Redis + agent-memory-server running in Azure.

**Acceptance Criteria:**
- [ ] Deploy Redis container (internal)
- [ ] Deploy agent-memory-server container (external)
- [ ] Verify health endpoints respond
- [ ] Get external memory API URL

---

### US-007: Connect jarvis-voice to Azure memory endpoint
**Description:** As a developer, I want jarvis-voice using the new Azure Redis endpoint.

**Acceptance Criteria:**
- [ ] Update MEMORY_SERVER_URL in jarvis-voice Container App
- [ ] Redeploy/restart container
- [ ] Container logs show connection to new endpoint

---

### US-008: Verify end-to-end memory flow
**Description:** As a user, I want to verify JARVIS remembers across sessions in production.

**Acceptance Criteria:**
- [ ] curl: Add memory to Azure endpoint → 200 OK
- [ ] curl: Search memory → Returns result
- [ ] Voice: Tell JARVIS a fact → "I'll remember that"
- [ ] Voice: Restart session → Ask recall → Correct answer

---

### US-009: Delete old Mem0 deployment
**Description:** As a developer, I want to clean up the broken Mem0 containers.

**Acceptance Criteria:**
- [ ] Delete mem0-api Container App
- [ ] Delete qdrant Container App
- [ ] Delete mem0-ui Container App (if exists)
- [ ] Verify no orphaned resources

---

## Non-Goals

- No changes to JARVIS voice/audio functionality
- No UI changes
- No multi-user support (hardcoded "sudo")
- No memory backup/restore

## Technical Reference

### 10.69.3.72 Setup (Blueprint)

```yaml
# docker-compose.yml on 10.69.3.72
redis:
  image: redis/redis-stack:latest
  ports:
    - "6379:6379"

agent-memory-server:
  image: redis/agent-memory-server:latest
  ports:
    - "8002:8000"
  environment:
    - REDIS_URL=redis://redis:6379
```

### Azure Container Apps URLs

- jarvis-voice: https://jarvis-voice.<env>.<region>.azurecontainerapps.io
- agent-memory-server: https://agent-memory-server.<env>.<region>.azurecontainerapps.io

### Required MCP Servers

| Task | MCP Server |
|------|------------|
| Redis agent-memory-server docs | Context7 |
| Azure Container Apps | Azure MCP |
| Azure CLI commands | Azure MCP |
| Deployment best practices | Microsoft Learn |
