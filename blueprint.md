# Canon OS — ENTERPRISE BLUEPRINT
## Autonomous Digital Marketing & Content Generation Platform
## Version: 1.0 | Document Class: MASTER SPECIFICATION
### Date: 2026-07-16 | Generated: 2026-07-10

> **READ FIRST — DOCUMENT AUTHORITY**
> This document is the single source of truth for the Canon OS platform. All implementation, validation, and enforcement must align with this blueprint. The checklist.md is the enforcement companion — it may never lead the blueprint.
> **Rollback Tag:** `[SYS-OVERVIEW-v1]`

---

## Table of Contents

- [PART I: Vision & Architecture](#part-i-vision--architecture)
- [PART II: Module Registry](#part-ii-module-registry)
- [PART III: Specifications](#part-iii-specifications)
- [PART IV: Data Architecture](#part-iv-data-architecture)
- [PART V: Change Control](#part-v-change-control)
- [PART VI: Phase Checklists](#part-vi-phase-checklists)
- [PART VII: Quality Standards](#part-vii-quality-standards)
- [PART VIII: Forever System Compliance](#part-viii-forever-system-compliance)

---

# PART I: Vision & Architecture

> **Rollback Tag:** `[SYS-OVERVIEW-v1]`

## 1.1 Executive Summary

Canon OS is an enterprise-grade autonomous marketing platform that transforms minimal user input (image + optional sentence) into complete advertising campaigns. The system handles end-to-end content creation, multi-platform distribution, analytics-driven optimization, and adaptive content evolution — all controlled through a unified dashboard. Generation is **local-first but API-adaptable**: every modality runs on local models for zero cost and zero data leakage, or routes to a cloud provider through a pluggable backend registry when scale or capability demands it — it is not strictly local.

**Core Capabilities:**
- **Instant Ad Generation:** Upload image + tagline → 30-second professional commercial
- **Autonomous Campaign Engine:** Define brand identity → self-triggering content pipeline
- **Multi-Platform Distribution:** Auto-post to Instagram, TikTok, YouTube, LinkedIn, Twitter, Facebook
- **Adaptive Learning:** Content evolves based on engagement metrics and platform algorithms
- **Unified Control:** Single dashboard for all campaigns, analytics, and platform management
- **Full Creative Studio:** Image generation, inpainting / outpainting / photo editing, video, text/script/copy, voiceover (TTS), transcription (STT), and music — local or API

**Target Users:**
- Small business owners without marketing teams
- E-commerce brands needing consistent social presence
- Agencies managing multiple client campaigns
- Content creators scaling video / image production

**Differentiators:**
- Zero manual intervention after initial brand setup
- AI-driven content optimization based on real engagement data
- Cross-platform format adaptation (vertical/horizontal/square)
- Brand consistency enforcement across all generated content
- Local-first, API-adaptable backends — runtime-switchable per modality
- Cost-effective alternative to traditional marketing agencies

## 1.2 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Canon OS PLATFORM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   USER LAYER     │
│  (Dashboard UI)  │
└────────┬─────────┘
         │ HTTPS/WebSocket
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (REST + GraphQL)                       │
│  Authentication │ Rate Limiting │ Request Routing │ API Versioning       │
└────────┬─────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────┬──────────────────┬──────────────────┐
         ▼                  ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ BRAND IDENTITY  │ │ CONTENT ENGINE  │ │ SOCIAL ORCHEST. │ │  ANALYTICS      │
│    SERVICE      │ │    SERVICE      │ │    SERVICE      │ │   SERVICE       │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BACKEND REGISTRY (local ↔ API)                         │
│  per-modality adapter selection: local model OR cloud provider API          │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI/ML GENERATION LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Video Gen    │  │ Image Gen    │  │ Audio Gen    │  │ Text Gen     │    │
│  │ (Wan / local)│  │ (SD / inpaint)│  │ (TTS / STT)  │  │ (Qwen / etc) │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐                                                        │
│  │ Music Gen    │                                                        │
│  └──────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STORAGE & QUEUE LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PostgreSQL   │  │ Redis Cache  │  │ S3/MinIO     │  │ RabbitMQ     │    │
│  │ (Metadata)   │  │ (Sessions)   │  │ (Assets)     │  │ (Job Queue)  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SOCIAL PLATFORM INTEGRATIONS                          │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │Instagram│ │ TikTok │ │YouTube │ │LinkedIn│ │Twitter │ │Facebook│        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1.3 Core Workflows

### Workflow 1: Instant Ad Generation (30-Second Commercial)

```
User uploads image + optional tagline
         │
         ▼
Brand Analysis (AI extracts colors, style, mood, product type)
         │
         ▼
Script Generation (Qwen generates 30-sec commercial script)
         │
         ▼
Storyboard Creation (8-12 scenes with shot descriptions)
         │
         ▼
Video Generation (local Wan / cloud provider renders each scene)
         │
         ▼
Audio Generation (voiceover + background music)
         │
         ▼
Assembly (FFmpeg combines video + audio + transitions)
         │
         ▼
Quality Check (automated review for brand consistency)
         │
         ▼
Delivery (download link + preview in dashboard)
```

### Workflow 2: Autonomous Campaign Pipeline

```
User defines brand identity (logo, colors, tone, target audience)
         │
         ▼
Campaign Scheduler (user sets posting frequency: 3x/week, daily, etc.)
         │
         ▼
Content Calendar Generator (AI plans next 30 days of content)
         │
         ▼
Batch Content Generation (parallel video/image/text creation)
         │
         ▼
Platform Adaptation (resize/reformat for each social platform)
         │
         ▼
Auto-Post Queue (scheduled posting at optimal times)
         │
         ▼
Performance Tracking (engagement metrics per post)
         │
         ▼
Adaptive Learning (adjust future content based on top performers)
         │
         ▼
Loop back to Content Calendar Generator (continuous evolution)
```

### Workflow 3: Multi-Platform Distribution

```
Single content asset (video/image/text)
         │
         ▼
Platform Detection (identify target platforms: Instagram, TikTok, etc.)
         │
         ▼
Format Adaptation:
  ├─ Instagram: 1:1 or 4:5, <60 sec, caption ≤2200 chars
  ├─ TikTok: 9:16, <60 sec, trending audio
  ├─ YouTube: 16:9, <10 min, SEO-optimized title/description
  ├─ LinkedIn: 16:9 or 1:1, professional tone
  └─ Twitter: 16:9, <2:20, concise copy
         │
         ▼
Caption Generation (platform-specific copy + hashtags)
         │
         ▼
Posting API Integration (OAuth + platform-specific endpoints)
         │
         ▼
Confirmation + Analytics Link (track performance per platform)
```

### Workflow 4: Image & Photo Studio (Generation + Inpainting)

```
User opens canvas with source image
         │
         ▼
Prompt / region / mask selection (brush, lasso, or full-frame)
         │
         ▼
Backend selection (local SD/InvokeAI OR cloud image-edit API)
         │
         ▼
Generate or Inpaint / Outpaint / Restyle region
         │
         ▼
Flash-tier preview → final render on approval
         │
         ▼
Checksum + store asset (integrity verified on save)
```

## 1.4 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript + Tailwind | Dashboard UI, real-time updates, canvas |
| **Backend** | Node.js + Express + GraphQL (Python services for AI) | API layer, business logic |
| **AI/ML** | Qwen, Wan, local SD/InvokeAI, Whisper, TTS/music (local or API) | Content generation |
| **Video Processing** | FFmpeg + Python | Assembly, transcoding, effects |
| **Backend Registry** | Pluggable adapters (local ↔ API) | Runtime-switchable per modality |
| **Database** | PostgreSQL 15 + Redis 7 | Metadata, caching, sessions |
| **Object Storage** | MinIO / AWS S3 | Video/image/audio assets |
| **Queue** | RabbitMQ + Bull | Job orchestration, retries |
| **Social APIs** | Platform-specific SDKs | Instagram Graph API, TikTok API, etc. |
| **Analytics** | PostgreSQL + Grafana | Performance tracking, dashboards |
| **Deployment** | Docker + Kubernetes (local or cloud) | Containerization, scaling |
| **Monitoring** | Prometheus + Grafana | System health, alerting |

## 1.5 Non-Functional Requirements

### Performance Budgets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Ad generation latency | <5 minutes | End-to-end from upload to delivery |
| Video rendering speed | 2x real-time | 30-sec video rendered in <15 sec |
| API response time | <200ms (p95) | Dashboard operations |
| Concurrent users | 1000 | Simultaneous dashboard sessions |
| Queue throughput | 100 jobs/min | Content generation pipeline |
| Social posting latency | <10 sec | From queue to platform confirmation |

### Scalability

- **Horizontal scaling:** Stateless microservices behind load balancer
- **Database sharding:** Partition by user_id for multi-tenant isolation
- **CDN integration:** CloudFront/Cloudflare for asset delivery
- **Auto-scaling:** Kubernetes HPA based on queue depth + CPU usage

### Security

- **Authentication:** JWT + OAuth 2.0 (Google, GitHub)
- **Authorization:** RBAC (Admin, Manager, Viewer roles)
- **Data encryption:** AES-256 at rest, TLS 1.3 in transit
- **Secrets management:** HashiCorp Vault or AWS Secrets Manager
- **Social API keys:** Encrypted per-user, never logged

### Reliability

- **SLA target:** 99.9% uptime (8.76 hours downtime/year max)
- **Backup strategy:** Daily PostgreSQL dumps, S3 versioning enabled
- **Disaster recovery:** Multi-region deployment (US-East + EU-West)
- **Circuit breakers:** Fail gracefully if social APIs rate-limited

### Cost Optimization

- **Model tiering:** Flash models for iteration, quality for final
- **Batch processing:** Generate 30 days of content in one job
- **Asset compression:** H.264 for video, WebP for images
- **Cold storage:** Archive old campaigns to S3 Glacier after 90 days
- **Backend selection:** Default local (zero cost); API only when needed

---


# PART II: Module Registry

> **Rollback Tag:** `[MODULE-REGISTRY-v1]`

## Module Index

| Module ID | Module Name | Feature Flag | Description |
|--------|-------------|--------------|-------------|
| MOD-001 | Brand Identity Manager | FEAT_BRAND_IDENTITY | Extract and store brand DNA from user input |
| MOD-002 | Script Generator | FEAT_SCRIPT_GEN | Generate commercial scripts from brand + tagline |
| MOD-003 | Storyboard Engine | FEAT_STORYBOARD | Convert scripts to visual scene breakdowns |
| MOD-004 | Video Renderer | FEAT_VIDEO_RENDER | Generate video scenes using local Wan / cloud provider |
| MOD-005 | Audio Generator | FEAT_AUDIO_GEN | Create voiceovers and background music (TTS / music) |
| MOD-006 | Video Assembler | FEAT_ASSEMBLY | Combine video + audio + transitions via FFmpeg |
| MOD-007 | Campaign Scheduler | FEAT_CAMPAIGN_SCHED | Plan and trigger autonomous content pipelines |
| MOD-008 | Content Calendar | FEAT_CONTENT_CALENDAR | Generate 30-day content plans |
| MOD-009 | Platform Adapter | FEAT_PLATFORM_ADAPT | Resize/reformat content per platform specs |
| MOD-010 | Social Poster | FEAT_SOCIAL_POST | Auto-post to Instagram, TikTok, YouTube, etc. |
| MOD-011 | Analytics Tracker | FEAT_ANALYTICS | Track engagement metrics per post/platform |
| MOD-012 | Adaptive Learner | FEAT_ADAPTIVE_LEARN | Optimize future content based on performance data |
| MOD-013 | Dashboard UI | FEAT_DASHBOARD | Unified control panel for all campaigns |
| MOD-014 | User Management | FEAT_USER_MGMT | Authentication, authorization, multi-tenant |
| MOD-015 | API Gateway | FEAT_API_GATEWAY | REST + GraphQL endpoints, rate limiting |
| MOD-016 | Job Queue | FEAT_JOB_QUEUE | RabbitMQ orchestration for async tasks |
| MOD-017 | Asset Storage | FEAT_ASSET_STORAGE | S3/MinIO integration for video/image/audio |
| MOD-018 | Quality Checker | FEAT_QUALITY_CHECK | Automated brand consistency validation |
| MOD-019 | Notification System | FEAT_NOTIFICATIONS | Email/SMS alerts for campaign status |
| MOD-020 | Billing Integration | FEAT_BILLING | Stripe integration for subscription management |
| MOD-021 | Image and Photo Studio | FEAT_IMAGE_STUDIO | Image generation plus inpaint/outpaint/restyle on canvas |
| MOD-022 | Backend Registry | FEAT_BACKEND_REGISTRY | Per-modality local to API adapter selection and provider keys |
| MOD-023 | STT Transcriber | FEAT_STT | Speech-to-text transcription (local Whisper or API) |
| MOD-024 | Model Management | FEAT_MODEL_MANAGEMENT | Local model install/catalog plus provider key management |

## Module Dependencies

    MOD-001 (Brand Identity)
        depends on MOD-002, MOD-003, MOD-021, MOD-018
    MOD-002 (Script Generator) -> MOD-003 (Storyboard Engine)
    MOD-003 (Storyboard Engine) -> MOD-004 (Video Renderer)
    MOD-004 (Video Renderer) -> MOD-006 (Video Assembler)
    MOD-005 (Audio Generator) -> MOD-006 (Video Assembler)
    MOD-006 (Video Assembler) -> MOD-009 (Platform Adapter)
    MOD-007 (Campaign Scheduler) -> MOD-008, MOD-010
    MOD-008 (Content Calendar) -> MOD-002, MOD-004
    MOD-009 (Platform Adapter) -> MOD-010 (Social Poster)
    MOD-010 (Social Poster) -> MOD-011 (Analytics Tracker)
    MOD-011 (Analytics Tracker) -> MOD-012 (Adaptive Learner)
    MOD-012 (Adaptive Learner) -> MOD-008 (feedback loop)
    MOD-022 (Backend Registry) -> MOD-021, MOD-004, MOD-005, MOD-023 (selects local or API per modality)

## Feature Flag Configuration

All feature flags follow the pattern FEAT_[A-Z][A-Z0-9_]+.

| Flag | Default | Environment Override | Description |
|------|---------|---------------------|-------------|
| FEAT_BRAND_IDENTITY | enabled | CANON_OS_BRAND_IDENTITY | Enable brand extraction |
| FEAT_SCRIPT_GEN | enabled | CANON_OS_SCRIPT_GEN | Enable script generation |
| FEAT_STORYBOARD | enabled | CANON_OS_STORYBOARD | Enable storyboard creation |
| FEAT_VIDEO_RENDER | enabled | CANON_OS_VIDEO_RENDER | Enable video rendering |
| FEAT_AUDIO_GEN | enabled | CANON_OS_AUDIO_GEN | Enable audio generation |
| FEAT_ASSEMBLY | enabled | CANON_OS_ASSEMBLY | Enable video assembly |
| FEAT_CAMPAIGN_SCHED | enabled | CANON_OS_CAMPAIGN_SCHED | Enable campaign scheduling |
| FEAT_CONTENT_CALENDAR | enabled | CANON_OS_CONTENT_CALENDAR | Enable content calendar |
| FEAT_PLATFORM_ADAPT | enabled | CANON_OS_PLATFORM_ADAPT | Enable platform adaptation |
| FEAT_SOCIAL_POST | enabled | CANON_OS_SOCIAL_POST | Enable social posting |
| FEAT_ANALYTICS | enabled | CANON_OS_ANALYTICS | Enable analytics tracking |
| FEAT_ADAPTIVE_LEARN | enabled | CANON_OS_ADAPTIVE_LEARN | Enable adaptive learning |
| FEAT_DASHBOARD | enabled | CANON_OS_DASHBOARD | Enable dashboard UI |
| FEAT_USER_MGMT | enabled | CANON_OS_USER_MGMT | Enable user management |
| FEAT_API_GATEWAY | enabled | CANON_OS_API_GATEWAY | Enable API gateway |
| FEAT_JOB_QUEUE | enabled | CANON_OS_JOB_QUEUE | Enable job queue |
| FEAT_ASSET_STORAGE | enabled | CANON_OS_ASSET_STORAGE | Enable asset storage |
| FEAT_QUALITY_CHECK | enabled | CANON_OS_QUALITY_CHECK | Enable quality checking |
| FEAT_NOTIFICATIONS | disabled | CANON_OS_NOTIFICATIONS | Enable notifications (opt-in) |
| FEAT_BILLING | disabled | CANON_OS_BILLING | Enable billing (premium only) |
| FEAT_IMAGE_STUDIO | enabled | CANON_OS_IMAGE_STUDIO | Enable image generation plus inpainting |
| FEAT_BACKEND_REGISTRY | enabled | CANON_OS_BACKEND_REGISTRY | Enable local to API backend selection |
| FEAT_STT | enabled | CANON_OS_STT | Enable speech-to-text transcription |
| FEAT_MODEL_MANAGEMENT | enabled | CANON_OS_MODEL_MANAGEMENT | Enable local model plus key management |

---



# PART III: Specifications

> **Rollback Tag:** `[SPECS-v1]`

## 3.1 Feature Specification: Instant Ad Generation (MOD-001 through MOD-006)

```yaml
FEATURE_NAME: Instant Ad Generation
FEATURE_ID: FEAT_INSTANT_AD
MODULES: [MOD-001, MOD-002, MOD-003, MOD-004, MOD-005, MOD-006]
DESCRIPTION: Transform user-uploaded image + optional tagline into 30-second professional commercial
USER_STORY: As a small business owner, I want to upload my product photo and get a polished video ad without hiring an agency
ACCEPTANCE_CRITERIA:
  - User can upload image (JPG/PNG/WebP, max 10MB)
  - User can optionally provide tagline (max 200 chars)
  - System extracts brand colors, style, mood from image
  - System generates 30-second script with 8-12 scenes
  - System renders video scenes using local Wan / cloud provider
  - System generates voiceover (male/female/neutral voice options)
  - System adds background music (royalty-free library)
  - System assembles final video (1080p, H.264, <60MB)
  - User can preview video in dashboard
  - User can download video (MP4 format)
INPUTS:
  - image_file: binary (required)
  - tagline: string (optional, max 200 chars)
  - voice_preference: enum [male, female, neutral] (default: neutral)
  - music_style: enum [upbeat, calm, dramatic, none] (default: upbeat)
OUTPUTS:
  - video_url: string (S3/MinIO presigned URL)
  - video_duration: integer (seconds)
  - video_resolution: string (e.g., "1920x1080")
  - video_size_mb: float
  - generation_time_seconds: integer
  - brand_analysis: object (extracted colors, style, mood)
ERROR_STATES:
  - IMAGE_TOO_LARGE: "Image exceeds 10MB limit. Please compress and retry."
  - INVALID_FORMAT: "Unsupported image format. Use JPG, PNG, or WebP."
  - GENERATION_TIMEOUT: "Video generation took too long. Try a simpler tagline."
  - AI_SERVICE_UNAVAILABLE: "AI generation service temporarily unavailable. Retry in 5 minutes."
  - ASSEMBLY_FAILED: "Video assembly failed. Contact support with job ID: {job_id}"
PERFORMANCE:
  - Target: <5 minutes end-to-end
  - p95: <7 minutes
  - Timeout: 10 minutes (fail gracefully)
TESTING:
  - Unit: Test brand extraction, script generation, scene rendering
  - Integration: Test full pipeline from upload to delivery
  - E2E: User uploads image -> downloads video in <5 min
  - Load: 100 concurrent ad generations, queue handles backlog
ROLLBACK PROCEDURE:
  - Disable FEAT_INSTANT_AD flag
  - Queue pauses new jobs, completes in-flight
  - Rollback to previous version (v-1)
  - Notify affected users via email
```

## 3.2 Feature Specification: Autonomous Campaign Pipeline (MOD-007, MOD-008, MOD-012)

```yaml
FEATURE_NAME: Autonomous Campaign Pipeline
FEATURE_ID: FEAT_CAMPAIGN_PIPELINE
MODULES: [MOD-007, MOD-008, MOD-012]
DESCRIPTION: Self-triggering content pipeline that generates and posts content on user-defined schedule
USER_STORY: As an e-commerce brand, I want to set up a campaign once and have it run autonomously for months
ACCEPTANCE_CRITERIA:
  - User defines brand identity (logo, colors, tone, target audience)
  - User sets posting frequency (e.g., 3x/week, daily)
  - User specifies platforms (Instagram, TikTok, YouTube, etc.)
  - System generates 30-day content calendar
  - System batch-generates all content for next 30 days
  - System auto-posts content at optimal times (per-platform)
  - System tracks engagement metrics per post
  - System adapts future content based on top performers
  - System notifies user of campaign milestones (weekly report)
INPUTS:
  - brand_identity: object (logo, colors, tone, audience)
  - posting_frequency: enum [daily, 3x_week, 2x_week, weekly]
  - platforms: array [instagram, tiktok, youtube, linkedin, twitter, facebook]
  - campaign_duration_days: integer (default: 30, max: 90)
  - start_date: datetime (default: now)
OUTPUTS:
  - campaign_id: UUID
  - content_calendar: array of scheduled posts
  - total_posts: integer
  - estimated_reach: integer (based on follower count)
  - campaign_status: enum [scheduled, active, paused, completed]
ERROR_STATES:
  - INCOMPLETE_BRAND: "Brand identity incomplete. Provide logo, colors, and tone."
  - INVALID_FREQUENCY: "Posting frequency must be daily, 3x/week, 2x/week, or weekly."
  - NO_PLATFORMS: "Select at least one platform for the campaign."
  - SCHEDULING_CONFLICT: "Campaign overlaps with existing campaign on same platform."
  - BATCH_GENERATION_FAILED: "Failed to generate batch content. Retry or reduce scope."
  - SOCIAL_AUTH_EXPIRED: "Social platform authentication expired. Reconnect {platform}."
PERFORMANCE:
  - Calendar generation: <30 seconds
  - Batch generation (30 posts): <2 hours
  - Posting latency: <10 seconds per platform
  - Adaptive learning cycle: <5 minutes per post
TESTING:
  - Unit: Test calendar generation, scheduling logic, adaptive algorithm
  - Integration: Test full pipeline from brand setup to first post
  - E2E: User sets up campaign -> system posts autonomously for 7 days
  - Load: 50 concurrent campaigns, 1000 posts/day total
ROLLBACK PROCEDURE:
  - Pause all active campaigns (FEAT_CAMPAIGN_PIPELINE disabled)
  - Preserve scheduled posts in queue (don't delete)
  - Rollback to previous version
  - Resume campaigns after verification
```

## 3.3 Feature Specification: Multi-Platform Distribution (MOD-009, MOD-010)

```yaml
FEATURE_NAME: Multi-Platform Distribution
FEATURE_ID: FEAT_MULTI_PLATFORM
MODULES: [MOD-009, MOD-010]
DESCRIPTION: Adapt and post content to multiple social platforms with platform-specific formatting
USER_STORY: As a content creator, I want to post once and have it automatically formatted for all my platforms
ACCEPTANCE_CRITERIA:
  - System detects target platforms from campaign settings
  - System resizes video/image per platform specs (aspect ratio, duration, file size)
  - System generates platform-specific captions (length, hashtags, tone)
  - System posts via official APIs (Instagram Graph API, TikTok API, etc.)
  - System handles OAuth authentication per platform
  - System tracks posting status per platform (success/failure)
  - System retries failed posts (exponential backoff, max 3 attempts)
INPUTS:
  - content_asset: object (video_url or image_url)
  - platforms: array [instagram, tiktok, youtube, linkedin, twitter, facebook]
  - caption: string (base caption, adapted per platform)
  - scheduled_time: datetime (optional, default: now)
OUTPUTS:
  - posting_results: array of {platform, status, post_url, error_message}
  - total_success: integer
  - total_failed: integer
ERROR_STATES:
  - PLATFORM_UNSUPPORTED: "Platform {platform} not supported."
  - OAUTH_EXPIRED: "Authentication expired for {platform}. Reconnect in dashboard."
  - RATE_LIMITED: "Rate limited by {platform}. Retry in {retry_after} seconds."
  - FORMAT_CONVERSION_FAILED: "Failed to convert content for {platform}."
  - POSTING_FAILED: "Posting to {platform} failed: {error_message}"
  - API_QUOTA_EXCEEDED: "API quota exceeded for {platform}."
PERFORMANCE:
  - Format adaptation: <5 seconds per platform
  - Posting latency: <10 seconds per platform
  - Retry logic: 3 attempts with 1s, 2s, 4s delays
  - Total time (6 platforms): <60 seconds
TESTING:
  - Unit: Test format adaptation, caption generation, OAuth handling
  - Integration: Test posting to sandbox/test accounts
  - E2E: User posts content -> appears on all platforms within 1 minute
  - Load: 100 concurrent multi-platform posts
ROLLBACK PROCEDURE:
  - Disable FEAT_MULTI_PLATFORM flag
  - Queue pauses new posts, completes in-flight
  - Rollback to previous version
  - Manually verify recent posts on each platform
```

## 3.4 Feature Specification: Unified Dashboard (MOD-013, MOD-014)

```yaml
FEATURE_NAME: Unified Dashboard
FEATURE_ID: FEAT_DASHBOARD
MODULES: [MOD-013, MOD-014]
DESCRIPTION: Single control panel for managing all campaigns, content, analytics, and settings
USER_STORY: As a marketing manager, I want one place to see all my campaigns and their performance
ACCEPTANCE_CRITERIA:
  - Dashboard shows overview of all active campaigns
  - Dashboard displays real-time analytics (views, likes, shares, comments)
  - Dashboard allows pausing/resuming campaigns
  - Dashboard shows content calendar with drag-and-drop scheduling
  - Dashboard provides content library (all generated videos/images)
  - Dashboard supports multi-user access (Admin, Manager, Viewer roles)
  - Dashboard sends notifications for campaign milestones
  - Dashboard works on desktop and tablet (responsive design)
  - Dashboard includes the Image & Photo Studio canvas (MOD-021)
  - Dashboard includes backend/provider selector (MOD-022)
INPUTS:
  - user_id: UUID (authenticated user)
  - dashboard_section: enum [overview, campaigns, content, analytics, studio, settings]
OUTPUTS:
  - campaigns: array of active/paused/completed campaigns
  - analytics: object (total views, engagement rate, top posts)
  - content_library: array of generated assets (video/image)
  - notifications: array of unread notifications
ERROR_STATES:
  - UNAUTHORIZED: "You don't have permission to access this dashboard section."
  - DATA_LOAD_FAILED: "Failed to load dashboard data. Refresh page or contact support."
  - WEBSOCKET_DISCONNECTED: "Real-time updates unavailable. Check internet connection."
PERFORMANCE:
  - Dashboard load time: <2 seconds
  - Real-time updates: <500ms latency (WebSocket)
  - API response time: <200ms (p95)
  - Concurrent users: 1000 simultaneous sessions
TESTING:
  - Unit: Test React components, state management, API calls
  - Integration: Test dashboard <-> backend API <-> database
  - E2E: User logs in -> views campaigns -> pauses campaign -> sees update
  - Load: 1000 concurrent dashboard sessions, <2s load time
  - Accessibility: WCAG 2.1 AA compliance
ROLLBACK PROCEDURE:
  - Disable FEAT_DASHBOARD flag (fallback to API-only access)
  - Preserve user sessions (don't force logout)
  - Rollback to previous version
```

## 3.5 Feature Specification: Analytics & Adaptive Learning (MOD-011, MOD-012)

```yaml
FEATURE_NAME: Analytics & Adaptive Learning
FEATURE_ID: FEAT_ANALYTICS_ADAPTIVE
MODULES: [MOD-011, MOD-012]
DESCRIPTION: Track engagement metrics and optimize future content based on performance data
USER_STORY: As a brand manager, I want my campaigns to get better over time based on what works
ACCEPTANCE_CRITERIA:
  - System tracks views, likes, shares, comments per post
  - System calculates engagement rate (interactions / reach)
  - System identifies top-performing content (top 20%)
  - System extracts patterns from top performers (colors, music, captions)
  - System adjusts future content calendar based on patterns
  - System provides weekly performance reports (email + dashboard)
  - System A/B tests content variations (2 versions, pick winner)
  - System respects platform algorithm changes (re-weight metrics)
INPUTS:
  - post_id: UUID
  - platform: enum [instagram, tiktok, youtube, linkedin, twitter, facebook]
  - metrics: object (views, likes, shares, comments, reach)
  - timestamp: datetime
OUTPUTS:
  - engagement_rate: float (0.0 to 1.0)
  - top_performers: array of post_ids (top 20%)
  - patterns: object (successful colors, music styles, caption length)
  - optimization_suggestions: array of recommended changes
  - weekly_report: object (summary, trends, recommendations)
ERROR_STATES:
  - METRICS_UNAVAILABLE: "Platform {platform} metrics API temporarily unavailable."
  - INSUFFICIENT_DATA: "Need at least 10 posts before adaptive learning kicks in."
  - A_B_TEST_INCONCLUSIVE: "A/B test results not statistically significant. Extend test."
  - ALGORITHM_SHIFT: "Platform {platform} algorithm changed. Re-calibrating metrics."
PERFORMANCE:
  - Metrics ingestion: <1 second per post
  - Pattern extraction: <5 minutes per 100 posts
  - Adaptive learning cycle: <5 minutes per post
  - Weekly report generation: <30 seconds
TESTING:
  - Unit: Test engagement rate, pattern extraction, A/B test logic
  - Integration: Test metrics pipeline
  - E2E: Post 20 pieces -> system identifies top -> adjusts next batch
  - Load: 10,000 posts/day
ROLLBACK PROCEDURE:
  - Disable FEAT_ADAPTIVE_LEARN flag (revert to static content calendar)
  - Preserve historical metrics data
  - Rollback to previous version
```

## 3.6 Feature Specification: Image & Photo Studio (Generation + Inpainting) (MOD-021)

```yaml
FEATURE_NAME: Image & Photo Studio
FEATURE_ID: FEAT_IMAGE_STUDIO
MODULES: [MOD-021, MOD-022]
DESCRIPTION: Generate images and edit photos (inpaint, outpaint, mask, restyle) on a canvas; local or API backend
USER_STORY: As a creator, I want to generate and retouch images for my brand without a designer or paid SaaS
ACCEPTANCE_CRITERIA:
  - System generates images from prompt + brand palette
  - System in/outpaints masked regions on an uploaded photo
  - System restyles a region (e.g., background swap) preserving subject
  - System supports brush/lasso/full-frame masking on canvas
  - System selects backend per MOD-022 (local SD/InvokeAI or cloud image API)
  - Flash-tier preview renders first; final render only on approval
  - Every saved asset is checksummed (integrity verified on save)
INPUTS:
  - source_image: binary (optional, required for inpaint/outpaint)
  - prompt: string (max 1000 chars)
  - mask: object (region or brush strokes)
  - mode: enum [generate, inpaint, outpaint, restyle]
  - backend: enum [local, api] (default: local)
OUTPUTS:
  - image_url: string (S3/MinIO presigned URL)
  - resolution: string
  - checksum: string (sha256)
  - backend_used: enum [local, api]
ERROR_STATES:
  - MODEL_OOM: "Local model out of memory. Dropping resolution and retrying."
  - BACKEND_DOWN: "Selected backend unavailable. Offering alternate backend."
  - INVALID_MASK: "Mask does not cover any editable region."
PERFORMANCE:
  - Flash preview: <15 seconds
  - Final render: <90 seconds (local), <30 seconds (api)
TESTING:
  - Unit: Test masking, backend selection, checksum write
  - Integration: Test full generate + inpaint roundtrip
  - E2E: Upload photo -> inpaint background -> download
ROLLBACK PROCEDURE:
  - Disable FEAT_IMAGE_STUDIO
  - Preserve generated assets
  - Rollback to previous version
```

## 3.7 Feature Specification: Backend Registry (Local <-> API) (MOD-022, MOD-024)

```yaml
FEATURE_NAME: Backend Registry
FEATURE_ID: FEAT_BACKEND_REGISTRY
MODULES: [MOD-022, MOD-024]
DESCRIPTION: Per-modality adapter selection between local models and cloud provider APIs; runtime-switchable
USER_STORY: As an operator, I want to choose per modality whether generation runs locally (zero cost) or via API (scale)
ACCEPTANCE_CRITERIA:
  - System exposes a per-modality backend catalog (image, video, audio, text, stt, music)
  - Each modality defaults to local (zero cost / zero data leakage)
  - API backend is opt-in per modality via provider key
  - Provider keys stored by reference only (encrypted at rest, never logged)
  - Switching backend at runtime does not require restart for stateless modalities
  - If an API backend is unavailable, system does NOT silently fall back to a paid API
INPUTS:
  - modality: enum [image, video, audio, text, stt, music]
  - backend: enum [local, api]
  - provider_key_ref: string (required when backend=api)
OUTPUTS:
  - effective_backend: enum [local, api]
  - status: enum [ok, key_missing, key_expired, unavailable]
ERROR_STATES:
  - KEY_MISSING: "Provider key not configured for {modality}. Configure key or use local."
  - KEY_EXPIRED: "Provider key expired for {modality}. Renew key."
  - API_UNAVAILABLE: "API backend for {modality} unavailable. Local backend remains default."
PERFORMANCE:
  - Backend switch: <1 second (stateless modalities)
  - Key validation: <2 seconds
TESTING:
  - Unit: Test adapter resolution, key-reference handling
  - Integration: Test local->api switch per modality
  - E2E: Generate with local, switch to api, generate again
ROLLBACK PROCEDURE:
  - Reset all modalities to local (safe default)
  - Rollback to previous version

## 3.8 Screen Registry

> Parser-tracked screens. Each maps 1:1 to a SPEC above. The loop-enforced checklist reads these.

### Screen 1.1 — Brand Setup (Onboarding)
- SPEC Ref: SPEC-001 | FEATURE FLAG | FEAT_BRAND_IDENTITY | ROLLBACK TAG | [SPECS-v1]

### Screen 2.1 — Campaign Studio
- SPEC Ref: SPEC-002 | FEATURE FLAG | FEAT_CAMPAIGN_PIPELINE | ROLLBACK TAG | [SPECS-v1]

### Screen 3.1 — Social Distribution
- SPEC Ref: SPEC-003 | FEATURE FLAG | FEAT_MULTI_PLATFORM | ROLLBACK TAG | [SPECS-v1]

### Screen 4.1 — Dashboard (Overview / Analytics / Settings)
- SPEC Ref: SPEC-004 | FEATURE FLAG | FEAT_DASHBOARD | ROLLBACK TAG | [SPECS-v1]

### Screen 5.1 — Analytics & Adaptive Learning
- SPEC Ref: SPEC-005 | FEATURE FLAG | FEAT_ANALYTICS_ADAPTIVE | ROLLBACK TAG | [SPECS-v1]

### Screen 6.1 — Image & Photo Studio
- SPEC Ref: SPEC-006 | FEATURE FLAG | FEAT_IMAGE_STUDIO | ROLLBACK TAG | [SPECS-v1]

### Screen 7.1 — Backend Registry & Model Management
- SPEC Ref: SPEC-007 | FEATURE FLAG | FEAT_BACKEND_REGISTRY | ROLLBACK TAG | [SPECS-v1]

---


# PART IV: Data Architecture

> **Rollback Tag:** `[DATA-ARCH-v1]`

## 4.1 Database Schema (PostgreSQL)

### Core Tables

```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'manager', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Brand Identities
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) NOT NULL,
    secondary_color VARCHAR(7),
    tone VARCHAR(50) CHECK (tone IN ('professional', 'casual', 'playful', 'luxury', 'minimalist')),
    target_audience TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_brands_user_id ON brands(user_id);

-- Campaigns
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'active', 'paused', 'completed')),
    posting_frequency VARCHAR(50) CHECK (posting_frequency IN ('daily', '3x_week', '2x_week', 'weekly')),
    platforms TEXT[] NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    duration_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX idx_campaigns_brand_id ON campaigns(brand_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- Content Assets (videos, images, audio)
CREATE TABLE content_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL CHECK (asset_type IN ('video', 'image', 'audio', 'text')),
    title VARCHAR(255),
    description TEXT,
    file_url VARCHAR(500) NOT NULL,
    file_size_mb FLOAT,
    duration_seconds INTEGER,
    resolution VARCHAR(20),
    format VARCHAR(50),
    checksum VARCHAR(64) NOT NULL,
    backend_used VARCHAR(20) DEFAULT 'local',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_assets_campaign_id ON content_assets(campaign_id);
CREATE INDEX idx_content_assets_brand_id ON content_assets(brand_id);
CREATE INDEX idx_content_assets_type ON content_assets(asset_type);

-- Scheduled Posts
CREATE TABLE scheduled_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    content_asset_id UUID NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('instagram', 'tiktok', 'youtube', 'linkedin', 'twitter', 'facebook')),
    caption TEXT,
    hashtags TEXT[],
    scheduled_at TIMESTAMPTZ NOT NULL,
    posted_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'posted', 'failed', 'cancelled')),
    post_url VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheduled_posts_campaign_id ON scheduled_posts(campaign_id);
CREATE INDEX idx_scheduled_posts_platform ON scheduled_posts(platform);
CREATE INDEX idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX idx_scheduled_posts_scheduled_at ON scheduled_posts(scheduled_at);

-- Analytics Metrics
CREATE TABLE analytics_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheduled_post_id UUID NOT NULL REFERENCES scheduled_posts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    engagement_rate FLOAT,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_metrics_post_id ON analytics_metrics(scheduled_post_id);
CREATE INDEX idx_analytics_metrics_platform ON analytics_metrics(platform);
CREATE INDEX idx_analytics_metrics_collected_at ON analytics_metrics(collected_at);

-- Social Platform Auth (OAuth tokens)
CREATE TABLE social_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('instagram', 'tiktok', 'youtube', 'linkedin', 'twitter', 'facebook')),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    account_id VARCHAR(255),
    account_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, platform)
);

CREATE INDEX idx_social_auth_user_id ON social_auth(user_id);
CREATE INDEX idx_social_auth_platform ON social_auth(platform);

-- Provider Keys (backend registry, by reference only)
CREATE TABLE provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    modality VARCHAR(20) NOT NULL CHECK (modality IN ('image', 'video', 'audio', 'text', 'stt', 'music')),
    provider VARCHAR(50) NOT NULL,
    key_ref VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, modality, provider)
);

CREATE INDEX idx_provider_keys_user_id ON provider_keys(user_id);

-- Job Queue (RabbitMQ metadata)
CREATE TABLE job_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_job_queue_status ON job_queue(status);
CREATE INDEX idx_job_queue_priority ON job_queue(priority DESC);
CREATE INDEX idx_job_queue_created_at ON job_queue(created_at);

-- Agent Logs (every create/verify agent output, by phase)
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phase_index INTEGER NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    role VARCHAR(32) NOT NULL,
    action VARCHAR(32) NOT NULL CHECK (action IN ('create', 'verify', 'revise')),
    artifact_path TEXT,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_logs_phase ON agent_logs(phase_index);
CREATE INDEX idx_agent_logs_agent ON agent_logs(agent_id);

-- Audit Trail (append-only, never purged)
CREATE TABLE audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(128) NOT NULL,
    target VARCHAR(256),
    detail JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_trail_created ON audit_trail(created_at);

-- Backups & Archives
CREATE TABLE backups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(32) NOT NULL CHECK (kind IN ('daily', 'weekly', 'archive')),
    location VARCHAR(500) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Policy / Compliance Rules
CREATE TABLE policy_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction VARCHAR(32) NOT NULL,
    rule_type VARCHAR(64) NOT NULL,
    constraint_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_policy_rules_jurisdiction ON policy_rules(jurisdiction);
```

## 4.2 Migration Convention

All schema changes require a migration file named `V{NNN}__description.sql`
(e.g. `V001__init_schema.sql`) with a matching rollback file
`V{NNN}__description.down.sql`, referenced in the Global Change Log (Part V).

## 4.3 API Contracts (REST + GraphQL)

### REST Endpoints

```yaml
# Authentication
POST /api/v1/auth/register
  Request: { email, password, name }
  Response: { user_id, access_token, refresh_token }

POST /api/v1/auth/login
  Request: { email, password }
  Response: { access_token, refresh_token }

POST /api/v1/auth/refresh
  Request: { refresh_token }
  Response: { access_token }

# Brands
GET /api/v1/brands
  Response: { brands: [{ id, name, logo_url, primary_color, ... }] }
POST /api/v1/brands
  Request: { name, logo_file, primary_color, tone, target_audience }
  Response: { brand_id, ... }
GET /api/v1/brands/:id
  Response: { id, name, logo_url, primary_color, ... }
PUT /api/v1/brands/:id
  Request: { name?, primary_color?, tone?, ... }
  Response: { id, ... }
DELETE /api/v1/brands/:id
  Response: { success: true }

# Campaigns
GET /api/v1/campaigns
  Query: ?status=active&platform=instagram
  Response: { campaigns: [{ id, name, status, platforms, ... }] }
POST /api/v1/campaigns
  Request: { brand_id, name, posting_frequency, platforms, start_date, duration_days }
  Response: { campaign_id, content_calendar, total_posts }
GET /api/v1/campaigns/:id
  Response: { id, name, status, platforms, posts: [...], analytics: {...} }
PUT /api/v1/campaigns/:id
  Request: { status?, posting_frequency?, ... }
  Response: { id, ... }
POST /api/v1/campaigns/:id/pause
  Response: { success: true }
POST /api/v1/campaigns/:id/resume
  Response: { success: true }

# Image & Photo Studio (MOD-021)
POST /api/v1/studio/generate
  Request: { prompt, backend?, mode? }
  Response: { job_id, status }
POST /api/v1/studio/inpaint
  Request: { source_image, mask, prompt, backend? }
  Response: { job_id, status }
GET /api/v1/studio/:job_id
  Response: { job_id, status, image_url?, checksum? }

# Backend Registry (MOD-022)
GET /api/v1/backends
  Response: { modalities: [{ modality, effective, status }] }
POST /api/v1/backends/select
  Request: { modality, backend, provider_key_ref? }
  Response: { effective_backend, status }

# Content Generation
POST /api/v1/generate/ad
  Request: { image_file, tagline?, voice_preference?, music_style? }
  Response: { job_id, status: "processing", estimated_time: 300 }
GET /api/v1/generate/:job_id
  Response: { job_id, status, video_url?, error_message? }

# Social Platforms
GET /api/v1/social/accounts
  Response: { accounts: [{ platform, account_name, connected: true }] }
POST /api/v1/social/connect/:platform
  Request: { access_token, refresh_token, account_id }
  Response: { success: true }
POST /api/v1/social/disconnect/:platform
  Response: { success: true }

# Analytics
GET /api/v1/analytics/overview
  Response: { total_views, total_likes, engagement_rate, top_posts: [...] }
GET /api/v1/analytics/campaign/:id
  Response: { campaign_id, posts: [{ post_id, platform, metrics: {...} }] }
GET /api/v1/analytics/report/weekly
  Response: { report_url, generated_at }

# Notifications
GET /api/v1/notifications
  Query: ?unread=true
  Response: { notifications: [{ id, type, title, message, is_read }] }
PUT /api/v1/notifications/:id/read
  Response: { success: true }
```


# PART V: Change Control

> **Rollback Tag:** `[CHANGE-CONTROL-v1]`

## 5.1 Contributor Rules

1. **All changes must be documented in CHANGELOG.md** before merging.
2. **Never delete or modify existing changelog entries** — append only.
3. **Feature flags required** for all new features (FEAT_* naming convention).
4. **Database migrations must be reversible** — include rollback scripts (`V{NNN}__*.down.sql`).
5. **API changes require versioning** — use `/api/v1/`, `/api/v2/` prefixes.
6. **Performance budgets must be maintained** — no regression beyond 10% threshold.
7. **Security review required** for authentication, authorization, and data handling changes.
8. **Testing coverage must not decrease** — new code requires unit + integration tests.

## 5.2 Change Log Format

```markdown
## CL-NNN
Date        : YYYY-MM-DD
Author      : Name <email>
Type        : feature | bugfix | refactor | docs | chore
Modules     : MOD-001, MOD-002
Description : Brief description of the change
Impact      : Low | Medium | High
Testing     : Unit | Integration | E2E | Load
Rollback    : Steps to rollback this change
```

## 5.3 Global Change Log

## CL-0001
Date        : 2026-07-16
Author      : Canon OS Foundation <foundation@canon-os.local>
Type        : feature
Modules     : MOD-001, MOD-004, MOD-021, MOD-022
Description : Establish Canon OS blueprint from foundation. Add full creative-studio
              scope (image generation, inpainting/photo editing, video, audio, STT,
              music), local-first-but-API-adaptable backend registry, and unify with
              the adforge 7-agent / 7-phase loop-enforced chain and two-review mechanism.
Impact      : High
Testing     : Validator 34/34, checklist generated (loop mode), 7 phases / 24 modules / 7 screens
Rollback    : Revert blueprint.md to prior commit; regenerate checklist from prior blueprint

## CL-0002
Date        : 2026-07-16
Author      : Canon OS Foundation <foundation@canon-os.local>
Type        : feature
Modules     : MOD-021, MOD-022, MOD-024
Description : Add Image & Photo Studio (MOD-021), Backend Registry (MOD-022), and
              Model Management (MOD-024) so generation is not strictly local and
              covers paint/photo in addition to the creative campaign pipeline.
Impact      : Medium
Testing     : Validator pass; SPEC-006 / SPEC-007 added; Screen 6.1 / Screen 7.1 added
Rollback    : Disable FEAT_IMAGE_STUDIO / FEAT_BACKEND_REGISTRY flags; revert specs

## 5.4 Versioning Strategy

- **Major (1.0 -> 2.0):** Breaking API changes, database schema migrations
- **Minor (1.0 -> 1.1):** New features, non-breaking API additions
- **Patch (1.0.0 -> 1.0.1):** Bug fixes, performance improvements, security patches

## 5.5 Rollback Procedures

### Database Rollback
```bash
pg_dump canon-os_db > backup_$(date +%Y%m%d_%H%M%S).sql
psql canon-os_db < migrations/V{NNN}__*.down.sql
python3 scripts/verify_rollback.py --cl CL-NNN
```

### API Rollback
```bash
kubectl set env deployment/canon-os-api API_VERSION=v1
kubectl rollout restart deployment/canon-os-api
```

### Feature Flag Rollback
```bash
curl -X POST https://api.canon-os.io/admin/flags \
  -d '{"flag": "FEAT_NEW_FEATURE", "enabled": false}' \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---


# PART VI: Phase Checklists

> **Rollback Tag:** `[PHASE-CHECKLISTS-v1]`

> **Enforcement:** This checklist is generated from the blueprint and enforced by
> the loop-enforcer (`canon-os-chain.py` -> `.blueprint-chain/canon-os-blueprint.json`).
> Each phase is `locked` until the prior phase is verified `complete`. A phase
> carries a **create** deliverable AND a **peer-verify** deliverable (a dedicated
> reviewer agent, never the creator). Once complete, a phase is never re-opened.
> The final phase is the **holistic Director review**: "would this be released?"

## Agent Roster (adforge 7-agent division)

| Agent | Phase ownership | Create role | Peer-verify role |
|-------|-----------------|-------------|------------------|
| foundation-engineer | PHASE-0 | repo, DB, API skeleton | foundation-reviewer |
| ai-engine | PHASE-1 | brand extract, script, storyboard, video, audio, assembly | ai-engine-reviewer |
| content-orchestrator | PHASE-2 | campaign, calendar, batch, adapt | content-reviewer |
| social-integrator | PHASE-3 | social API integrations, posting | social-reviewer |
| frontend-engineer | PHASE-4 | dashboard, studio canvas, backend selector UI | frontend-reviewer |
| data-scientist | PHASE-5 | analytics, adaptive learning | analytics-reviewer |
| devops-engineer | PHASE-6 | docker, k8s, CI/CD, monitoring | devops-reviewer |

---

### PHASE-0: Foundation
> **Rollback Tag:** `[PHASE-0-v1]`
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|--------------|--------------|--------------|-----------------|----------|
| Repo access | FEAT_USER_MGMT | repo init, Dockerfile, CI | health 200 | RB-000 |
| PHASE-0.1 | FEAT_USER_MGMT | project structure (src/, tests/, docs/) | tree exists | RB-000 |
| PHASE-0.2 | FEAT_ASSET_STORAGE | DB schema init (V001__init_schema.sql) | psql applies | RB-000 |
| PHASE-0.3 | FEAT_API_GATEWAY | API skeleton (Express+GraphQL, /health) | health 200 | RB-000 |
| PHASE-0.4 | FEAT_USER_MGMT | auth (JWT register/login) | token issued | RB-000 |
| PHASE-0.5 | FEAT_USER_MGMT | user mgmt (RBAC) | role enforced | RB-000 |
| PHASE-0.6 | FEAT_ASSET_STORAGE | object storage (MinIO/S3) | upload/download | RB-000 |
| PHASE-0.7 | FEAT_JOB_QUEUE | job queue (RabbitMQ) | job enqueues | RB-000 |
| PHASE-0.8 | FEAT_OBSERVABILITY | logging framework | structured logs | RB-000 |
| PHASE-0.9 | FEAT_QUALITY_CHECK | error middleware | centralized errors | RB-000 |
| Peer verify | FEAT_USER_MGMT | reviews/phase-0-verify.md | reviewer confirms runnable | RB-000 |

### PHASE-1: Core AI Engine
> **Rollback Tag:** `[PHASE-1-v1]`
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|--------------|--------------|--------------|-----------------|----------|
| PHASE-0 complete | FEAT_AI_GENERATION | brand extraction (MOD-001) | colors extracted | RB-001 |
| PHASE-1.2 | FEAT_SCRIPT_GEN | script gen (MOD-002) | 30s script | RB-001 |
| PHASE-1.3 | FEAT_STORYBOARD | storyboard (MOD-003) | 8-12 scenes | RB-001 |
| PHASE-1.4 | FEAT_VIDEO_RENDER | video render (MOD-004, local Wan/API) | scene renders | RB-001 |
| PHASE-1.5 | FEAT_AUDIO_GEN | audio (MOD-005, TTS/music) | voiceover+music | RB-001 |
| PHASE-1.6 | FEAT_ASSEMBLY | assembly (MOD-006, FFmpeg) | mp4 output | RB-001 |
| PHASE-1.7 | FEAT_IMAGE_STUDIO | image gen + inpaint (MOD-021) | canvas renders | RB-001 |
| PHASE-1.8 | FEAT_BACKEND_REGISTRY | backend registry (MOD-022) | local<->api switch | RB-001 |
| PHASE-1.9 | FEAT_STT | transcription (MOD-023) | transcript | RB-001 |
| PHASE-1.10 | FEAT_QUALITY_CHECK | quality checker (MOD-018) | brand-consistency | RB-001 |
| Peer verify | FEAT_AI_GENERATION | reviews/phase-1-verify.md | reviewer confirms E2E ad | RB-001 |

### PHASE-2: Content Generation
> **Rollback Tag:** `[PHASE-2-v1]`
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|--------------|--------------|--------------|-----------------|----------|
| PHASE-1 complete | FEAT_CAMPAIGN_SCHED | campaign svc (MOD-007) | campaign created | RB-002 |
| PHASE-2.2 | FEAT_CONTENT_CALENDAR | calendar (MOD-008) | 30-day plan | RB-002 |
| PHASE-2.3 | FEAT_CAMPAIGN_SCHED | batch gen | 30 posts | RB-002 |
| PHASE-2.4 | FEAT_PLATFORM_ADAPT | platform adapt (MOD-009) | resized | RB-002 |
| PHASE-2.5 | FEAT_PLATFORM_ADAPT | caption gen | per-platform | RB-002 |
| PHASE-2.6 | FEAT_CAMPAIGN_SCHED | scheduler | optimal times | RB-002 |
| PHASE-2.7 | FEAT_DASHBOARD | campaign API | CRUD+pause | RB-002 |
| Peer verify | FEAT_CONTENT_CALENDAR | reviews/phase-2-verify.md | reviewer confirms calendar | RB-002 |

### PHASE-3: Social Integration
> **Rollback Tag:** `[PHASE-3-v1]`
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|--------------|--------------|--------------|-----------------|----------|
| PHASE-2 complete | FEAT_SOCIAL_POST | IG/TikTok/YT/LI/X/FB (MOD-010) | sandbox post | RB-003 |
| PHASE-3.6 | FEAT_SOCIAL_POST | posting svc (retry/backoff) | 3 attempts | RB-003 |
| PHASE-3.7 | FEAT_ANALYTICS | metrics ingest (MOD-011) | engagement | RB-003 |
| PHASE-3.8 | FEAT_SOCIAL_POST | account mgmt API | connect/disconnect | RB-003 |
| PHASE-3.9 | FEAT_SOCIAL_POST | token refresh | auto-renew | RB-003 |
| Peer verify | FEAT_SOCIAL_POST | reviews/phase-3-verify.md | reviewer confirms multi-post | RB-003 |

### PHASE-4: UI Dashboard
> **Rollback Tag:** `[PHASE-4-v1]`
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|--------------|--------------|--------------|-----------------|----------|
| PHASE-3 complete | FEAT_DASHBOARD | layout, auth UI (MOD-013) | login works | RB-004 |
| PHASE-4.3 | FEAT_BRAND_IDENTITY | brand mgmt UI | CRUD brand | RB-004 |
| PHASE-4.4 | FEAT_DASHBOARD | campaign mgmt UI | pause/resume | RB-004 |
| PHASE-4.5 | FEAT_CONTENT_CALENDAR | calendar UI (drag-drop) | reschedule | RB-004 |
| PHASE-4.6 | FEAT_ASSET_STORAGE | content library UI | grid+download | RB-004 |
| PHASE-4.7 | FEAT_ANALYTICS_ADAPTIVE | analytics charts | top posts | RB-004 |
| PHASE-4.8 | FEAT_IMAGE_STUDIO | studio canvas UI (MOD-021) | inpaint flow | RB-004 |
| PHASE-4.9 | FEAT_BACKEND_REGISTRY | backend selector UI (MOD-022) | switch backend | RB-004 |
| Peer verify | FEAT_DASHBOARD | reviews/phase-4-verify.md | reviewer confirms WCAG AA | RB-004 |

### PHASE-5: Analytics & Optimization
> **Rollback Tag:** `[PHASE-5-v1]`
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|--------------|--------------|--------------|-----------------|----------|
| PHASE-4 complete | FEAT_ANALYTICS | aggregation (MOD-011) | rollups | RB-005 |
| PHASE-5.2 | FEAT_ANALYTICS | engagement rate | computed | RB-005 |
| PHASE-5.4 | FEAT_ADAPTIVE_LEARN | pattern extraction (MOD-012) | patterns | RB-005 |
| PHASE-5.5 | FEAT_ADAPTIVE_LEARN | adaptive algo | calendar adj | RB-005 |
| PHASE-5.6 | FEAT_ADAPTIVE_LEARN | A/B test | winner | RB-005 |
| PHASE-5.7 | FEAT_ANALYTICS | weekly report | PDF+email | RB-005 |
| Peer verify | FEAT_ADAPTIVE_LEARN | reviews/phase-5-verify.md | reviewer confirms learning loop | RB-005 |

### PHASE-6: Deployment + Final Holistic Review
> **Rollback Tag:** `[PHASE-6-v1]`
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|--------------|--------------|--------------|-----------------|----------|
| PHASE-5 complete | FEAT_DEPLOYMENT | docker images (MOD-014) | build ok | RB-006 |
| PHASE-6.2 | FEAT_DEPLOYMENT | k8s manifests | apply ok | RB-006 |
| PHASE-6.4 | FEAT_DEPLOYMENT | CI/CD (GitHub Actions) | test+audit | RB-006 |
| PHASE-6.5 | FEAT_ASSET_STORAGE | prod migrations (zero-downtime) | applies | RB-006 |
| PHASE-6.6 | FEAT_USER_MGMT | secrets mgmt | vault ok | RB-006 |
| PHASE-6.12 | FEAT_OBSERVABILITY | backups + DR | dump+verify | RB-006 |
| **FINAL HOLISTIC REVIEW** | FEAT_QUALITY_CHECK | reviews/phase-6-director.md | Director: "would this be released?" | RB-006 |
| Peer verify | FEAT_DEPLOYMENT | reviews/phase-6-verify.md | reviewer confirms whole-repo integrity | RB-006 |

---


# PART VII: Quality Standards

> **Rollback Tag:** `[QUALITY-v1]`

## 7.1 Testing Requirements

- **Unit tests:** 80%+ line coverage (Jest for Node.js, pytest for Python)
- **Integration tests:** All API endpoints tested with real database
- **E2E tests:** All user workflows tested (Playwright for frontend)
- **Load tests:** Performance budgets met under 1000 concurrent users

### Testing Tiers
```bash
npm test                 # Tier 1: unit
npm run test:integration # Tier 2: API + DB + queue
npm run test:e2e         # Tier 3: full user workflows
npm run test:load        # Tier 4: performance under stress
```

## 7.2 Code Quality Standards

- Lint: eslint (JS/TS), black + flake8 + mypy (Python), sqlfluff (SQL)
- Review checklist: naming, no hardcoded secrets, error handling, input validation, structured logs, tests, docs

## 7.3 Performance Budgets

| Metric | Target |
|--------|--------|
| API response p95 | <200ms |
| Dashboard load | <2s |
| Ad generation | <5 min |
| Video render | 2x real-time |
| Queue throughput | 100 jobs/min |
| Social post latency | <10 sec |

## 7.4 Security Standards (OWASP Top 10)

- Injection (parameterized queries), Broken Auth (JWT+refresh, rate limit), Sensitive Data (HTTPS, encrypted secrets),
- Access Control (RBAC, no IDOR), XSS (CSP, encode), Vulnerable Components (npm audit, Snyk), Logging (structured, alert)
- Secrets: never committed; provider keys stored by reference only (MOD-022)

## 7.5 Cost & Token Optimization

- Flash-first: flash models for iteration, quality for final (model-map.yaml)
- regenerate-only-failures: never discard passing work
- retrieve-don't-remember: semantic search over full context
- working-memory-isolation: load only agent identity + inputs
- Cost guard: alert at 75%, hard stop at 95% (model-map.yaml cost_tracking)

## 7.6 Monitoring & Alerting

- Prometheus metrics + Grafana dashboards (API, queue, social, content, users)
- Alerts: high error rate, queue backlog, disk space, social API quota

---

# PART VIII: Forever System Compliance

> **Rollback Tag:** `[FOREVER-v1]`

Canon OS is built as a Forever System: layerable, adaptable, integrable,
platform/path agnostic. These rules are binding architectural constraints.

## 8.1 Singular Source of Truth
- One blueprint (`blueprint.md`) is the single spec. The checklist is generated
  FROM it and never leads it. One module per concern (Part II index). No parallel
  re-implementations. The backend registry (MOD-022) is the ONE place backend
  selection happens — modalities route through it, never hardcode a provider.

## 8.2 Self-Resolving Paths
- All paths resolve `env -> home -> default`, FRESH per call. No hardcoded
  `/home/ubuntu/...` in shippable code. The studio runs on any machine/container.

## 8.3 Layered, Never Rewritten
- Updates add versioned layers (CL-NNNN, V{NNN}__ migrations). Rollback = pop a
  layer. A reload that mutates truth is a rewrite — forbidden.

## 8.4 Fail-Closed, Tamper-Evident
- Block when unsure. Integrity checksums on every asset (content_assets.checksum).
- Audit trail is append-only and never purged. Hash changes are visible, not protective.
- No claim of "tamper-proof" with a 32-bit hash.

## 8.5 Platform/Path Agnostic + Modular
- Local-first AND API-adaptable (MOD-022). Plugins are real registered units
  (adapter files in app/dashboard/backends/), not strings in docs.

## 8.6 Continuously-Reminded Character
- The .agent enforcer re-asserts foundational policy at EVERY action (affirmative
  assert, not just a deny-rule). Character lives in `.agent/constitution.yaml`,
  `enforcer.yaml`, `habits/habits.yaml`, `policy.yaml`, `model-map.yaml`.
- Identity is immutable and inherited, never regenerated.

## 8.7 Verifiable Without Reading Code
- `validate_blueprint.py` -> 34/34 green = truth. CI runs it on push. The owner
  watches the badge, not the diff.

## 8.8 Two-Review Quality Mechanism (doctrine-backed)
- **In-phase peer verification:** every phase, a dedicated reviewer agent (never
  the creator) confirms the work is actually functional/correct. The loop-enforcer
  locks the phase on pass; a locked phase is never re-opened.
- **Final holistic review:** Director pass over the whole repo — "would this be
  released?" — wholesome code intact, structure streamlined.

## 8.9 Cost Guard
- Token/credit cost tracked (model-map.yaml). Alert at 75%, hard stop at 95%.

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| Brand Identity | Logo, colors, tone, target audience that defines a brand |
| Campaign | Autonomous content pipeline with defined frequency and platforms |
| Content Asset | Generated video, image, audio, or text file |
| Engagement Rate | (likes + shares + comments) / reach |
| Platform Adaptation | Resizing/reformatting content per platform specs |
| Adaptive Learning | Optimizing future content based on performance data |
| Backend Registry | Per-modality local<->API adapter selection (MOD-022) |
| Image & Photo Studio | Generation + inpaint/outpaint/restyle on canvas (MOD-021) |
| Job Queue | RabbitMQ queue for async tasks |
| Feature Flag | Runtime toggle (FEAT_*) |
| Rollback Tag | Git tag marking a stable version for rollback |

## Appendix B: External Dependencies

| Service | Purpose | Fallback |
|---------|---------|----------|
| Qwen | Text generation (scripts, captions) | Other local LLM |
| Wan | Video generation (scenes) | Cloud video provider |
| SD / InvokeAI | Image generation + inpainting | Cloud image API |
| Whisper | Transcription (STT) | Cloud STT API |
| ElevenLabs / Suno | Voiceover / music | Local music model |
| Instagram Graph API | Posting + analytics | Manual posting |
| TikTok / YouTube / LinkedIn / X / Facebook API | Posting + analytics | Manual posting |
| AWS S3 | Object storage | MinIO (self-hosted) |
| CloudFront | CDN | Cloudflare |
| PostgreSQL | Metadata storage | MySQL |
| Redis | Caching + sessions | Memcached |
| RabbitMQ | Job queue | Bull (Redis-based) |

## Appendix C: Future Enhancements

- [ ] AI Video Editing: automatic scene transitions, color grading
- [ ] E-commerce Integration: Shopify/WooCommerce feed -> product ads
- [ ] Multi-Language: captions + voiceovers in 10+ languages
- [ ] AR Filters: custom Instagram/TikTok AR filters
- [ ] Billboard / TV spot generation (broadcast quality)
