# VidFlow - AI Video MLOps Platform

**Upload. Transcribe. Search by timestamp. Deploy on Kubernetes.**

A production-style video platform with FFmpeg transcoding, Whisper transcription, semantic search (Qdrant), and a full DevOps stack — Docker, Kafka, Cassandra, Terraform, and GitHub Actions CI/CD.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SOURCE & DELIVERY                                                          │
│                                                                             │
│  Git (GitHub) ──push──► GitHub Actions ──► Docker build ──► ECR           │
│                                │                              │             │
│                                └── tests + lint               ▼             │
│                                                         Helm deploy         │
│                                                         Terraform (AWS)     │
│                                                         EKS + S3 + RDS      │
│                                                                             │
│  Local dev: docker-compose up -d  (same services, runs on one machine)      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  RUNTIME — REQUEST PATH (sync, milliseconds)                                │
│                                                                             │
│  Client (Next.js)                                                           │
│       │                                                                     │
│       ▼                                                                     │
│  API Gateway (Nginx)  ── rate limit / route / throttle ──►                  │
│       │                                                                     │
│       ├──► user-service        (auth, JWT)          ──► PostgreSQL, Redis   │
│       ├──► video-service       (upload, metadata)   ──► MinIO, PostgreSQL   │
│       ├──► search-service      (semantic search)    ──► Qdrant, Cassandra   │
│       ├──► analytics-service   (watch events)       ──► Cassandra, Redis   │
│       └──► recommendation-service                   ──► PostgreSQL, Redis │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  RUNTIME — PROCESSING PATH (async, minutes)                                 │
│                                                                             │
│  video-service uploads file ──► MinIO + PostgreSQL                          │
│       │                                                                     │
│       └──► Kafka: video.uploaded                                            │
│                 │                                                           │
│                 ▼                                                           │
│            transcoder-worker (FFmpeg)  ──► MinIO (transcoded + thumbnail)   │
│                 │                                                           │
│                 └──► Kafka: video.transcoded                                │
│                           │                                                 │
│                           ▼                                                 │
│                      transcriber-worker (Whisper) ──► Cassandra (chunks)    │
│                           │                                                 │
│                           └──► Kafka: video.transcribed                     │
│                                     │                                       │
│                                     ▼                                       │
│                                embedder-worker ──► Qdrant (vectors)         │
│                                                └──► PostgreSQL (summary)  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  DATA LAYER — each store has one job                                        │
│                                                                             │
│  PostgreSQL   users, video metadata, ownership, AI summaries (relational)   │
│  Cassandra    watch events, transcript chunks, interaction streams        │
│  Redis        hot cache, search cache, rate-limit counters, sessions        │
│  MinIO / S3   raw videos, transcoded files, thumbnails (object blobs)     │
│  Qdrant       transcript embeddings for semantic + timestamp search       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  OBSERVABILITY — cross-cutting (all services & workers)                     │
│                                                                             │
│  Prometheus (metrics: latency, errors, queue depth) ──► Grafana           │
│  ELK: Elasticsearch + Logstash + Kibana (centralized JSON logs)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Design rule:** APIs return fast; Kafka workers handle slow work (transcode, transcribe, embed).

## Quick Start

```bash
# Start all infrastructure + services locally
docker-compose up -d

# Frontend (dev mode)
cd frontend && npm install && npm run dev

# API docs
open http://localhost:8000/docs      # Video service
open http://localhost:8001/docs      # User service
open http://localhost:8002/docs      # Search service
open http://localhost:3000           # Frontend
open http://localhost:9090           # Prometheus
open http://localhost:3001           # Grafana (admin/admin)
open http://localhost:5601           # Kibana
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 80 | Nginx rate limiting + routing |
| Video Service | 8000 | Upload, metadata, processing status |
| User Service | 8001 | Auth, users, permissions |
| Search Service | 8002 | Semantic + timestamp search |
| Analytics Service | 8003 | Watch events, metrics |
| Recommendation Service | 8004 | Content recommendations |
| Transcoder Worker | — | FFmpeg transcoding + thumbnails |
| Transcriber Worker | — | Whisper transcription |
| Embedder Worker | — | Embeddings + summaries |

## Infrastructure

- **PostgreSQL** — users, uploads, ownership, billing metadata
- **Cassandra** — watch history, transcript chunks, interaction events
- **Redis** — caching, rate limits, sessions
- **Kafka** — async processing pipeline
- **MinIO** — S3-compatible object storage
- **Qdrant** — vector embeddings for semantic search

## Deployment

```bash
# Terraform (AWS EKS)
cd infrastructure/terraform && terraform init && terraform apply

# Helm deploy to EKS
helm upgrade --install ai-video ./helm/ai-video-platform -n ai-video --create-namespace
```

## CI/CD

GitHub Actions builds Docker images, runs tests, pushes to ECR, and deploys via Helm on merge to `main`.
