# Portfolio AI - GitHub Project Scanner

An AI-powered FastAPI application that intelligently scans GitHub repositories, extracts project metadata, and generates detailed project descriptions using LangGraph and Groq LLM. Perfect for building dynamic portfolio applications that automatically display and analyze your GitHub projects.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Environment Variables](#environment-variables)

## ✨ Features

- **Automated GitHub Scanning**: Fetch and analyze GitHub repositories using PyGithub with smart batch limiting (5 projects per run)
- **Smart Update Detection**: Automatically detect repository updates and only reprocess changed projects
- **AI-Powered Analysis**: Extract 8-line project descriptions and programming language percentages using Groq LLM with rate-limit handling
- **AI-Generated Preview Images**: Create beautiful UI/UX mockups for projects using Cloudflare Workers integration
- **Multi-Modal Output**: Generate both mobile (768x1024) and desktop (1024x768) preview images via Cloudinary
- **Project Metadata Extraction**: Automatically capture GitHub links, homepage URLs, and README content
- **Intelligent Caching**: Skip processing unchanged repositories, only update when changes detected
- **Persistent Storage**: Store all project data in MongoDB with efficient bulk write operations
- **LangGraph State Management**: Utilize LangGraph for sophisticated multi-step processing workflows with conditional routing
- **Parallel Processing**: Process multiple projects concurrently using LangGraph's Send API
- **RESTful API**: FastAPI-powered REST endpoints with CORS support for frontend integration
- **Graph Visualization**: Auto-generate Mermaid diagram of the workflow pipeline

## 🛠 Tech Stack

### Backend Framework
- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI server for running FastAPI applications

### AI & LLM
- **LangChain** - LLM orchestration framework
- **LangGraph** - Graph-based state management for AI workflows
- **Groq** - Fast LLM inference with Llama 3.1 model
- **Hugging Face** - ML model hub integration

### Data Processing
- **BeautifulSoup4** - HTML/XML parsing and scraping
- **PyPDF** - PDF document processing
- **Sentence Transformers** - Text embedding for semantic search
- **Rank-BM25** - Text ranking algorithm

### Database & Storage
- **MongoDB** - NoSQL database for project metadata
- **Cloudinary** - Cloud image hosting and optimization
- **Cloudflare Workers** - Serverless function for AI image generation
- **LangSmith** - LLM monitoring and debugging (optional)

### External APIs
- **PyGithub** - GitHub API client for repository analysis
- **Tavily** - AI-powered search tool

### Utilities
- **python-dotenv** - Environment variable management
- **Pydantic** - Data validation and settings management

## 📁 Project Structure

```
Portfolio_AI/
├── main.py                          # FastAPI application entry point
├── pyproject.toml                  # Project configuration and dependencies
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── agents/                         # AI Agent Implementation
│   └── github_project_scanner_agent.py
│       - LangGraph workflow orchestration
│       - GitHub project fetching and analysis
│       - AI-powered project description generation
│
├── api/                            # API Routes
│   └── github_project_route.py
│       - RESTful endpoints for project management
│       - Integration with scanning agents
│
├── models/                         # Data Models
│   └── project.py
│       - Project Pydantic model with fields:
│         * title: Project name
│         * readme: Project README content
│         * description: AI-generated summary
│         * languages: Language breakdown (%)
│         * mobile_url: Mobile preview image
│         * desktop_url: Desktop preview image
│         * updated_at: Last update timestamp
│
├── schemas/                        # Database Schemas & Serializers
│   └── schema.py
│       - MongoDB document serializers
│       - Individual and batch project serialization
│
├── config/                         # Configuration Files
│   ├── cloudinary.py              # Cloudinary image hosting setup
│   └── database.py                # MongoDB connection configuration
│
└── api_test_images/               # Test images for development
```

## 📋 Prerequisites

- **Python 3.13+**
- **MongoDB Atlas** account (cloud database)
- **GitHub Personal Access Token**
- **Groq API Key** (for LLM access)
- **Cloudinary Account** (for image hosting)
- **Tavily API Key** (optional, for enhanced search)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Portfolio_AI
```

### 2. Create Virtual Environment
```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt

# OR using pyproject.toml
pip install -e .
```

## ⚙️ Configuration

### 1. Environment Variables
Create a `.env` file in the root directory:

```env
# GitHub API Configuration
GITHUB_API=your_github_personal_access_token

# LLM Configuration
GROQ_API_KEY=your_groq_api_key

# Database Configuration
MONGODB_URL=your_mongodb_connection_string

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Cloudflare Worker Configuration
CLOUDFLARE_WORKER_URL=https://your-worker.your-subdomain.workers.dev/
CLOUDFLARE_API_KEY=your_worker_auth_key  # Optional, if worker is secured

# Optional: Tavily Search API
TAVILY_API_KEY=your_tavily_api_key

# Optional: LangSmith Monitoring
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=your_project_name
```

### 2. MongoDB Setup
- Create a MongoDB Atlas cluster
- Create a database named `portfolio`
- Create a collection named `projects`
- Update `MONGODB_URL` with your connection string

### 3. Cloudinary Setup
- Sign up at https://cloudinary.com
- Get your credentials from the Dashboard
- Update configuration with API credentials

### 4. GitHub Token
- Generate at https://github.com/settings/tokens
- Require `repo` scope for public/private repository access

### 5. Groq API Key
- Get from https://console.groq.com
- Create an API key for Llama 3.1 8B model access
- Model: `llama-3.1-8b-instant` with temperature 0.5

### 6. Cloudflare Workers Setup
- Create a Cloudflare Worker for AI image generation
- Deploy an image generation endpoint that accepts `prompt` parameter
- Worker should return raw image bytes (PNG/JPG)
- Update `CLOUDFLARE_WORKER_URL` with deployed worker endpoint
- The worker integrates with image generation APIs (e.g., Replicate, Stability AI)
- Response handling includes threading locks to manage rate limits

## 📖 Usage

### Starting the Server

```bash
# Development mode with auto-reload
python main.py

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://127.0.0.1:8000`

### API Documentation
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 🔌 API Endpoints

### Get Projects
```http
GET /projects/agent
```

**Description**: Fetches GitHub repositories and analyzes them using AI. Returns stored projects if new scan is not performed.

**Response Example**:
```json
[
  {
    "id": "507f1f77bcf86cd799439011",
    "title": "Amazing AI Project",
    "readme": "Project README content...",
    "description": "This project implements a state-of-the-art AI model for...",
    "languages": {
      "Python": 85,
      "JavaScript": 10,
      "CSS": 5
    },
    "mobile_url": "https://res.cloudinary.com/.../mobile_preview.png",
    "desktop_url": "https://res.cloudinary.com/.../desktop_preview.png",
    "github_link": "https://github.com/username/amazing-ai-project",
    "live_link": "https://amazing-ai-project.com",
    "updated_at": "2024-05-08T10:30:00Z"
  }
]
```

**Query Parameters**: None

**Authentication**: None (configure CORS origins as needed)

## 🏗 Architecture

### LangGraph Workflow

The application uses **LangGraph** for sophisticated multi-step AI workflows with parallel processing:

```
┌────────────────────────────────────────────┐
│   START                                    │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────┐
│  fetch_all_repos_and_readmes               │
│  - Get all GitHub repositories             │
│  - Check update timestamps vs MongoDB      │
│  - Fetch README content (base64 decode)    │
│  - Limit to 5 projects per batch           │
│  - Skip ignored repos                      │
└────────────────┬─────────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  dispatch_sub_  │
        │    graph        │  (Conditional Routing)
        └────┬──────┬─────┘
             │      │
      route= │      │ route="end"
      "subG  │      │ (no changes)
      raph"  │      │
             ▼      ▼
   ┌──────────┐  ┌────────┐
   │ PARALLEL │  │  END   │
   │PROCESSING│  └────────┘
   └─────┬────┘
         │
         ├─► ┌─────────────────────┐
         │   │ detail_generator    │ (Parallel for each project)
         │   │ - Parse README      │
         │   │ - Groq LLM analyze  │
         │   │ - Extract languages │
         │   │ - Retry on rate lim │
         │   └──────────┬──────────┘
         │              │
         │              ▼
         │   ┌──────────────────────┐
         │   │ image_generator      │
         │   │ - Cloudflare Worker  │
         │   │ - AI mockup creation │
         │   │ - Upload to Cloudify │
         │   │ - Desktop + Mobile   │
         │   └──────────┬───────────┘
         │              │
         └──────────────┘
                 │
                 ▼
    ┌───────────────────────────┐
    │  save_projects            │
    │  - Bulk write to MongoDB  │
    │  - Upsert operations      │
    └───────────────┬───────────┘
                    │
                    ▼
           ┌─────────────────┐
           │      END        │
           └─────────────────┘
```

### State Management

**SuperGraphState**: Aggregates project details across multiple repositories
- `details`: List of project metadata (title, readme, updated_at, github_link, live_link)
- `projects`: List of processed project objects (aggregated from subgraph runs)
- `route`: Determines workflow path ("subGraph" to process or "end" to finish)

**SubGraphState**: Processes individual projects
- `title`: Repository name
- `readme`: Full README content extracted from GitHub
- `description`: AI-generated 8-line professional summary (via Groq LLM)
- `languages`: Dictionary with programming languages and percentage breakdown
- `mobile_url`: Mobile preview image URL (768x1024 - via Cloudinary)
- `desktop_url`: Desktop preview image URL (1024x768 - via Cloudinary)
- `updated_at`: Timestamp of last repository update
- `github_link`: Direct link to the GitHub repository
- `live_link`: Homepage/live project URL if available

## 💾 Database Schema

### MongoDB Collection: `projects`

```json
{
  "_id": ObjectId(),
  "title": "awesome-ai-project",
  "readme": "Full README content...",
  "description": "This project implements a state-of-the-art AI model for semantic search.\nIt leverages LangChain and vector databases for efficient retrieval.\nThe system processes complex queries with natural language understanding.\nOptimized for production deployment with sub-100ms response times.\nSupports multiple embedding models and similarity metrics.\nIncludes comprehensive evaluation metrics and benchmarks.\nFeatures a REST API for easy integration with existing systems.\nProduction-ready with Docker containerization and Kubernetes support.",
  "languages": {
    "Python": 75,
    "JavaScript": 15,
    "CSS": 10
  },
  "mobile_url": "https://res.cloudinary.com/.../mobile_preview.png",
  "desktop_url": "https://res.cloudinary.com/.../desktop_preview.png",
  "updated_at": "2024-05-08T10:30:00Z",
  "github_link": "https://github.com/username/awesome-ai-project",
  "live_link": "https://awesome-ai-project.com"
}
```

### Indexes (Recommended)
```python
# For faster title-based queries
db.projects.create_index("title")

# For sorting by update time
db.projects.create_index([("updated_at", -1)])
```

## ⚡ Implementation Details

### Batch Processing & Rate Limiting
- **Batch Limit**: Processes maximum 5 projects per execution run
- **Groq Rate Limiting**: Implements 5-attempt retry mechanism with 10-second delays on rate limit errors
- **Threading Lock**: Uses `threading.Lock()` for Cloudflare Worker requests to prevent concurrent rate limits
- **Request Throttle**: 2-second buffer between Cloudflare Worker requests

### Smart Update Detection
- Compares repository `updated_at` timestamps against MongoDB stored values
- Only reprocesses projects that have been modified since last run
- Skips unmodified projects entirely (efficient caching)
- Supports partial updates (new projects added while keeping old ones unchanged)

### Repository Ignore List
The agent automatically skips these repositories:
```python
ignore_repo = ["Hatim-Malak", "spring-boot-demo", "spring_security", "lunaris"]
```
Customize by modifying the `ignore_repo` list in `agents/github_project_scanner_agent.py`

### Image Generation Pipeline
1. **Prompt Engineering**: Generates detailed SaaS mockup prompts with design requirements
2. **Cloudflare Worker**: Sends prompt to worker, receives raw image bytes
3. **Cloudinary Upload**: Immediately uploads generated image and stores URL
4. **Dual Views**: Creates both mobile and desktop preview URLs
5. **Error Handling**: 4-attempt retry mechanism with 5-second delays on failures

### Groq LLM Integration
- **Model**: `llama-3.1-8b-instant`
- **Temperature**: 0.5 (balanced creativity and consistency)
- **Task**: Analyzes README to extract 8-line descriptions and language percentages
- **Structured Output**: Uses Pydantic models for guaranteed response format
- **Error Recovery**: Automatic retry with exponential backoff on API failures

### MongoDB Bulk Operations
- Uses `UpdateOne` with `upsert=True` for efficient upserts
- Batches all operations and performs single `bulk_write()` call
- Reports `upserted_count` and `modified_count` for monitoring

### Workflow Visualization
- Automatically generates Mermaid diagram PNG of the entire workflow
- Saved as `project_scanner.png` in the project root
- Useful for documentation and debugging

## 🔐 Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GITHUB_API` | ✅ Yes | GitHub Personal Access Token (repo scope) | `ghp_xxxxxxxxxxxxx` |
| `GROQ_API_KEY` | ✅ Yes | Groq API Key for Llama 3.1 8B model | `gsk_xxxxxxxxxxxxx` |
| `MONGODB_URL` | ✅ Yes | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `CLOUDINARY_CLOUD_NAME` | ✅ Yes | Cloudinary cloud name | `my-cloud-123` |
| `CLOUDINARY_API_KEY` | ✅ Yes | Cloudinary API key for uploads | `123456789012345` |
| `CLOUDINARY_API_SECRET` | ✅ Yes | Cloudinary API secret for uploads | `xxxxxxxxxxxxx` |
| `CLOUDFLARE_WORKER_URL` | ✅ Yes | Cloudflare Worker endpoint for image generation | `https://your-worker.your-subdomain.workers.dev/` |
| `CLOUDFLARE_API_KEY` | ⭕ Optional | Cloudflare Worker authentication token | `xxxxxxxxxxxxx` |
| `TAVILY_API_KEY` | ⭕ Optional | Tavily search API (future integration) | `tvly_xxxxxxxxxxxxx` |
| `LANGSMITH_API_KEY` | ⭕ Optional | LangSmith monitoring and tracing | `ls_xxxxxxxxxxxxx` |
| `LANGSMITH_PROJECT` | ⭕ Optional | LangSmith project name for organization | `portfolio-ai-dev` |

## 🚨 Troubleshooting

### MongoDB Connection Issues
- Verify MongoDB Atlas cluster is running
- Check IP whitelist includes your machine
- Ensure connection string format is correct

### GitHub API Rate Limiting
- Implement request throttling
- Use authenticated requests (GitHub rates authenticated users higher)
- Check rate limits: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit`

### Groq LLM Errors
- Verify API key is valid and has quota
- Check model availability: `llama-3.1-8b-instant`
- Monitor Groq console for error logs

### Cloudinary Upload Failures
- Verify API credentials are correct
- Check upload presets are configured
- Ensure image file sizes are within limits

### Cloudflare Worker Configuration
- Verify worker endpoint URL is correct and accessible
- Check worker is deployed and active
- Ensure CORS headers are properly set in worker
- Monitor Cloudflare Workers dashboard for errors
- Test endpoint with curl: `curl -X POST https://your-worker.workers.dev/ -H "Content-Type: application/json" -d '{"prompt":"test prompt"}'`
- Verify image generation API credentials in worker environment

### Rate Limiting Issues
- **Groq**: Automatically retries with 10s delays (max 5 attempts)
- **Cloudflare**: Uses threading lock to serialize requests
- **GitHub**: Unauthenticated requests limited to 60/hour, authenticated to 5000/hour
- **MongoDB**: Check connection pooling settings if connection errors occur

## 📝 License

[Add your license here]

## 👤 Author

[Your Name/Email]

## 🤝 Contributing

[Add contribution guidelines here]

## 📞 Support

For issues and questions, please open an issue on GitHub or contact the development team.

---

**Last Updated**: May 2024
**Version**: 0.1.0