# Infrastructure Security for RAG Systems

## Overview

Infrastructure security covers deployment, hosting, and operational security for RAG systems. This includes container security, secrets management, network security, database hardening, and secure configuration of the underlying infrastructure components. RAG systems typically run on containerized platforms (Docker) with multiple data stores (ChromaDB for vectors, Neo4j for knowledge graphs, SQLite for application data), making infrastructure security critical to overall system security.

Unlike application-layer security which focuses on code and APIs, infrastructure security addresses the environment in which the application runs. A secure application running on compromised infrastructure is still vulnerable. This document provides practical guidance for hardening Docker containers, securing databases, managing secrets, and implementing network security controls.

The `multi_agent_rag_local_v4` system uses Docker for containerization, ChromaDB for vector storage, Neo4j for graph data, and SQLite for application state. Each component requires specific security configurations to prevent unauthorized access, data breaches, and privilege escalation attacks.

## Fundamentals

### Container Security Principles

**Principle 1: Minimal Base Images**
Use minimal base images (alpine, slim, distroless) to reduce attack surface. Fewer packages mean fewer vulnerabilities.

**Principle 2: Non-Root Execution**
Never run containers as root. Create dedicated users with minimal privileges.

**Principle 3: Immutable Infrastructure**
Containers should be immutable. Configuration changes require rebuilding images, not modifying running containers.

**Principle 4: Resource Limits**
Set CPU and memory limits to prevent resource exhaustion attacks.

**Principle 5: Network Isolation**
Use Docker networks to isolate containers. Only expose necessary ports.

### Secrets Management

**Never hardcode secrets** in code, Dockerfiles, or environment variables visible in `docker inspect`.

**Use secret management tools:**
- Docker Secrets (Swarm mode)
- Kubernetes Secrets
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault

**Encrypt secrets at rest** using tools like `cryptography.fernet` or `age`.

**Rotate secrets regularly** - API keys, database passwords, encryption keys should be rotated on a schedule.

### Network Security

**Defense in Depth:**
1. **Firewall**: Block all ports except those explicitly needed
2. **TLS/HTTPS**: Encrypt all network traffic
3. **Network Segmentation**: Isolate frontend, backend, and data layers
4. **VPN/Bastion**: Restrict administrative access

**Zero Trust Networking**: Assume breach. Verify every connection, even internal ones.

### Database Security

**Authentication**: Require strong passwords or certificate-based authentication.

**Authorization**: Grant minimum necessary privileges. Application users should not have admin rights.

**Encryption**: Encrypt data at rest and in transit.

**Audit Logging**: Log all database access for forensic analysis.

**Backup Security**: Encrypt backups and store them securely.

## Threat Landscape

### Container Escape Vulnerabilities

**Container escape** allows an attacker to break out of container isolation and access the host system.

**Common causes:**
- Running containers as root
- Mounting sensitive host paths (`/`, `/var/run/docker.sock`)
- Using privileged mode (`--privileged`)
- Kernel vulnerabilities (CVE-2019-5736, CVE-2022-0847 "Dirty Pipe")

**Impact**: Full host compromise, access to all containers, data exfiltration.

### Exposed Secrets in Environment Variables

**Problem**: Secrets in environment variables are visible in:
- `docker inspect` output
- Process listings (`ps aux`)
- Container logs
- Crash dumps

**Example vulnerable configuration:**
```dockerfile
# VULNERABLE: Secret in environment variable
ENV DATABASE_PASSWORD=supersecret123
```

**Attack scenario**: Attacker gains read access to container, runs `docker inspect`, extracts all secrets.

### Unencrypted Database Connections

**Problem**: Database traffic transmitted in plaintext can be intercepted.

**Vulnerable configuration:**
```python
# VULNERABLE: No TLS
neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))
```

**Attack scenario**: Network sniffing reveals credentials and query data.

### Missing TLS/HTTPS

**Problem**: HTTP traffic is unencrypted and vulnerable to:
- Man-in-the-middle (MITM) attacks
- Session hijacking
- Credential theft
- Data tampering

**Impact**: Attackers can intercept authentication tokens, modify responses, inject malicious content.

### Insecure Docker Daemon Exposure

**Problem**: Docker daemon exposed on TCP without authentication.

**Vulnerable configuration:**
```bash
# VULNERABLE: Docker daemon exposed without TLS
dockerd -H tcp://0.0.0.0:2375
```

**Attack scenario**: Remote attacker connects to Docker daemon, creates privileged container, escapes to host.

### Weak Database Authentication

**Problem**: Default credentials, weak passwords, or no authentication.

**Common defaults:**
- Neo4j: `neo4j/neo4j` (must be changed on first login)
- ChromaDB: No authentication by default
- PostgreSQL: `postgres/postgres`

**Attack scenario**: Attacker scans for exposed databases, tries default credentials, gains full access.

## Defense Strategies

### Container Hardening

**1. Use Minimal Base Images**

```dockerfile
# GOOD: Use slim Python image
FROM python:3.11-slim

# BETTER: Use alpine for even smaller size
FROM python:3.11-alpine

# BEST: Use distroless for minimal attack surface
FROM gcr.io/distroless/python3-debian11
```

**2. Run as Non-Root User**

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser
WORKDIR /app

# Install dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

CMD ["python", "app/api/main.py"]
```

**3. Set Resource Limits**

```yaml
# docker-compose.yml
services:
  backend:
    image: rag-backend:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

**4. Use Read-Only Filesystem**

```yaml
services:
  backend:
    image: rag-backend:latest
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

**5. Drop Unnecessary Capabilities**

```yaml
services:
  backend:
    image: rag-backend:latest
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if binding to port < 1024
    security_opt:
      - no-new-privileges:true
```

**6. Scan Images for Vulnerabilities**

```bash
# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Scan Docker image
trivy image rag-backend:latest

# Fail build on HIGH/CRITICAL vulnerabilities
trivy image --exit-code 1 --severity HIGH,CRITICAL rag-backend:latest
```

### Secrets Management Implementation

**1. Environment-Based Secrets (Basic)**

```python
# Load secrets from environment variables (better than hardcoding)
import os
from pathlib import Path

def load_secret(key: str, default: str = "") -> str:
    """Load secret from environment variable."""
    value = os.getenv(key, default).strip()
    if not value:
        raise ValueError(f"Secret {key} not configured")
    return value

# Usage
DATABASE_PASSWORD = load_secret("DATABASE_PASSWORD")
API_KEY = load_secret("OPENAI_API_KEY")
```

**2. File-Based Secrets (Docker Secrets)**

```python
# Load secrets from files (Docker Secrets pattern)
from pathlib import Path

def load_secret_from_file(secret_name: str) -> str:
    """Load secret from /run/secrets/ (Docker Secrets)."""
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        return secret_path.read_text().strip()
    # Fallback to environment variable
    return os.getenv(secret_name.upper(), "")

# Usage
DATABASE_PASSWORD = load_secret_from_file("database_password")
```

**3. Encrypted Secrets (Advanced)**

```python
# Encrypt secrets at rest using Fernet
import os
from cryptography.fernet import Fernet
from pathlib import Path

class SecretManager:
    def __init__(self, key_path: str = ".secrets.key"):
        self.key_path = Path(key_path)
        self.cipher = self._load_or_create_key()
    
    def _load_or_create_key(self) -> Fernet:
        """Load encryption key or create new one."""
        if self.key_path.exists():
            key = self.key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)
            self.key_path.chmod(0o600)  # Owner read/write only
        return Fernet(key)
    
    def encrypt_secret(self, plaintext: str) -> str:
        """Encrypt a secret."""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt_secret(self, ciphertext: str) -> str:
        """Decrypt a secret."""
        return self.cipher.decrypt(ciphertext.encode()).decode()
    
    def get_secret(self, key: str) -> str:
        """Get decrypted secret from environment."""
        encrypted = os.getenv(key)
        if not encrypted:
            raise ValueError(f"Secret {key} not found")
        return self.decrypt_secret(encrypted)

# Usage
secret_manager = SecretManager()
DATABASE_PASSWORD = secret_manager.get_secret("DATABASE_PASSWORD_ENCRYPTED")
```

**4. Docker Compose with Secrets**

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    image: rag-backend:latest
    secrets:
      - database_password
      - openai_api_key
    environment:
      DATABASE_PASSWORD_FILE: /run/secrets/database_password
      OPENAI_API_KEY_FILE: /run/secrets/openai_api_key

secrets:
  database_password:
    file: ./secrets/database_password.txt
  openai_api_key:
    file: ./secrets/openai_api_key.txt
```

### Database Security Configuration

**1. Neo4j Security Hardening**

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5.13
    environment:
      # Authentication
      NEO4J_AUTH: neo4j/strong_random_password_here
      
      # Disable default database (force explicit database selection)
      NEO4J_dbms_default__database: neo4j
      
      # Enable audit logging
      NEO4J_dbms_logs_security_level: INFO
      
      # Restrict network binding
      NEO4J_dbms_connector_bolt_listen__address: 127.0.0.1:7687
      NEO4J_dbms_connector_http_listen__address: 127.0.0.1:7474
      
      # Enable TLS (requires certificates)
      # NEO4J_dbms_connector_bolt_tls__level: REQUIRED
      # NEO4J_dbms_ssl_policy_bolt_enabled: true
    
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    
    # Network isolation
    networks:
      - backend
    
    # No port exposure to host (only accessible via Docker network)
    # ports:
    #   - "7474:7474"
    #   - "7687:7687"

volumes:
  neo4j_data:
  neo4j_logs:

networks:
  backend:
    driver: bridge
```

**2. Neo4j Connection with TLS (Python)**

```python
from neo4j import GraphDatabase

# Secure connection with TLS
driver = GraphDatabase.driver(
    "neo4j+s://neo4j:7687",  # +s enables TLS
    auth=("neo4j", os.getenv("NEO4J_PASSWORD")),
    encrypted=True,
    trust=TRUST_SYSTEM_CA_SIGNED_CERTIFICATES,
    max_connection_lifetime=3600,
    max_connection_pool_size=50,
    connection_timeout=30,
)

# Verify connection
with driver.session() as session:
    result = session.run("RETURN 1 AS num")
    assert result.single()["num"] == 1
```

**3. ChromaDB Security Configuration**

```python
# ChromaDB with authentication (requires Chroma 0.4.0+)
import chromadb
from chromadb.config import Settings

# Create client with authentication
client = chromadb.HttpClient(
    host="localhost",
    port=8000,
    settings=Settings(
        chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
        chroma_client_auth_credentials=os.getenv("CHROMA_TOKEN"),
    )
)

# For local persistent storage (no network exposure)
client = chromadb.PersistentClient(
    path="./data/chroma",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=False,  # Prevent accidental data deletion
    )
)
```

**4. SQLite Security Best Practices**

```python
import sqlite3
from pathlib import Path

def create_secure_connection(db_path: str) -> sqlite3.Connection:
    """Create secure SQLite connection."""
    db_file = Path(db_path)
    
    # Set restrictive file permissions (owner read/write only)
    if db_file.exists():
        db_file.chmod(0o600)
    
    # Create connection with security settings
    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
        isolation_level="DEFERRED",
        timeout=30.0,
    )
    
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Enable Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA journal_mode = WAL")
    
    # Secure delete (overwrite deleted data)
    conn.execute("PRAGMA secure_delete = ON")
    
    return conn

# Usage
conn = create_secure_connection("data/app.db")
```

### Network Security Implementation

**1. TLS/HTTPS Configuration (FastAPI + Uvicorn)**

```python
# Production HTTPS configuration
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8443,
        ssl_keyfile="/etc/ssl/private/server.key",
        ssl_certfile="/etc/ssl/certs/server.crt",
        ssl_ca_certs="/etc/ssl/certs/ca-bundle.crt",
        ssl_cert_reqs=2,  # Require client certificates (mutual TLS)
        workers=4,
        log_level="info",
    )
```

**2. Nginx Reverse Proxy with TLS**

```nginx
# /etc/nginx/sites-available/rag-system
server {
    listen 443 ssl http2;
    server_name rag.example.com;
    
    # TLS configuration
    ssl_certificate /etc/ssl/certs/rag.example.com.crt;
    ssl_certificate_key /etc/ssl/private/rag.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to backend
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name rag.example.com;
    return 301 https://$server_name$request_uri;
}
```

**3. Docker Network Isolation**

```yaml
# docker-compose.yml with network segmentation
version: '3.8'

services:
  frontend:
    image: rag-frontend:latest
    networks:
      - frontend
    ports:
      - "3000:3000"
  
  backend:
    image: rag-backend:latest
    networks:
      - frontend
      - backend
    # No direct port exposure
  
  neo4j:
    image: neo4j:5.13
    networks:
      - backend
    # Only accessible from backend network
  
  chromadb:
    image: chromadb/chroma:latest
    networks:
      - backend
    # Only accessible from backend network

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

## Implementation Guide

### Step 1: Docker Hardening Checklist

**Base Image Security:**
- [ ] Use official images from trusted registries
- [ ] Use specific version tags (not `latest`)
- [ ] Use minimal base images (slim, alpine, distroless)
- [ ] Scan images for vulnerabilities with Trivy

**Runtime Security:**
- [ ] Run containers as non-root user
- [ ] Use read-only filesystem where possible
- [ ] Drop all capabilities, add only necessary ones
- [ ] Set resource limits (CPU, memory)
- [ ] Enable `no-new-privileges` security option

**Network Security:**
- [ ] Use Docker networks for isolation
- [ ] Don't expose unnecessary ports
- [ ] Use TLS for all network communication
- [ ] Implement network policies

### Step 2: Neo4j Security Configuration

```bash
# Generate strong password
NEO4J_PASSWORD=$(openssl rand -base64 32)

# Store in secrets file
echo "$NEO4J_PASSWORD" > secrets/neo4j_password.txt
chmod 600 secrets/neo4j_password.txt

# Update docker-compose.yml to use secret
# See "Database Security Configuration" section above
```

### Step 3: ChromaDB Access Control

```python
# For production, use ChromaDB server with authentication
# docker-compose.yml
services:
  chromadb:
    image: chromadb/chroma:latest
    environment:
      CHROMA_SERVER_AUTH_PROVIDER: chromadb.auth.token.TokenAuthServerProvider
      CHROMA_SERVER_AUTH_CREDENTIALS_FILE: /chroma/auth/tokens.txt
    volumes:
      - ./secrets/chroma_tokens.txt:/chroma/auth/tokens.txt:ro
      - chroma_data:/chroma/data
```

### Step 4: TLS Certificate Setup

```bash
# Generate self-signed certificate (development only)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout server.key \
  -out server.crt \
  -days 365 \
  -subj "/CN=localhost"

# For production, use Let's Encrypt
certbot certonly --standalone -d rag.example.com
```

### Step 5: Secrets Rotation Script

```bash
#!/bin/bash
# rotate_secrets.sh - Rotate database passwords

set -euo pipefail

# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update Neo4j password
docker exec neo4j cypher-shell -u neo4j -p "$OLD_NEO4J_PASSWORD" \
  "ALTER USER neo4j SET PASSWORD '$NEW_PASSWORD'"

# Update secrets file
echo "$NEW_PASSWORD" > secrets/neo4j_password.txt
chmod 600 secrets/neo4j_password.txt

# Restart services
docker-compose restart backend

echo "Neo4j password rotated successfully"
```

## Validation

### Infrastructure Security Testing Checklist

**Container Security:**
- [ ] Containers run as non-root user
- [ ] No privileged containers
- [ ] Resource limits configured
- [ ] Images scanned for vulnerabilities
- [ ] No secrets in environment variables

**Network Security:**
- [ ] TLS/HTTPS enabled
- [ ] Unnecessary ports not exposed
- [ ] Network segmentation implemented
- [ ] Firewall rules configured

**Database Security:**
- [ ] Default passwords changed
- [ ] Authentication enabled
- [ ] TLS connections enforced
- [ ] Audit logging enabled
- [ ] Backups encrypted

**Secrets Management:**
- [ ] No hardcoded secrets in code
- [ ] Secrets loaded from secure storage
- [ ] File permissions restrictive (600)
- [ ] Secrets rotation process documented

### Security Testing Commands

**Test container runs as non-root:**
```bash
# Check user inside container
docker exec rag-backend whoami
# Should output: appuser (not root)

# Check process owner
docker exec rag-backend ps aux
# Should show processes owned by appuser
```

**Test network isolation:**
```bash
# Try to access Neo4j from host (should fail if properly isolated)
curl http://localhost:7474
# Should return: Connection refused

# Access should work from backend container
docker exec rag-backend curl http://neo4j:7474
# Should return: Neo4j browser page
```

**Test TLS configuration:**
```bash
# Check TLS version
openssl s_client -connect rag.example.com:443 -tls1_2
# Should succeed

# Check weak TLS (should fail)
openssl s_client -connect rag.example.com:443 -tls1
# Should fail: protocol version not supported
```

**Scan for vulnerabilities:**
```bash
# Scan Docker image
trivy image rag-backend:latest

# Scan filesystem
trivy fs .

# Scan for secrets in code
trufflehog filesystem . --json
```

## Quick Reference

### Secure Docker Compose Template

```yaml
version: '3.8'

services:
  backend:
    image: rag-backend:latest
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    secrets:
      - database_password
    networks:
      - backend
    environment:
      DATABASE_PASSWORD_FILE: /run/secrets/database_password

secrets:
  database_password:
    file: ./secrets/database_password.txt

networks:
  backend:
    driver: bridge
```

### Security Commands

**Generate strong password:**
```bash
openssl rand -base64 32
```

**Set file permissions:**
```bash
chmod 600 secrets/*.txt
chmod 700 secrets/
```

**Check container security:**
```bash
docker inspect rag-backend | jq '.[0].Config.User'
docker inspect rag-backend | jq '.[0].HostConfig.SecurityOpt'
```

**Backup databases:**
```bash
# Neo4j backup
docker exec neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j_$(date +%Y%m%d).dump

# ChromaDB backup
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz data/chroma/

# SQLite backup
cp data/app.db data/backups/app_$(date +%Y%m%d).db
```

---

**Related Documents:**
- [Application Security](application_security.md) - API security, authentication, input validation
- [AI/LLM Security](ai_llm_security.md) - Prompt injection and RAG-specific threats
- [Security Prevention](security_prevention.md) - Proactive security controls
- [Security Recovery](security_recovery.md) - Backup and disaster recovery

**External References:**
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Neo4j Security Guide](https://neo4j.com/docs/operations-manual/current/security/)
