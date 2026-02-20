# Fitness Coach

AI-powered personal cycling coach with Intervals.icu integration. Analyzes your training, assesses fitness, and plans nutrition — all in Polish.

## Features

- **Training Analysis** — AI summaries of completed rides with power zone breakdown, TSS, IF, NP
- **Fitness Assessment** — CTL/ATL/TSB tracking with form status and readiness scoring (1-10)
- **Nutrition Planning** — Cycling-specific macro plans based on training load (carb periodization, on-bike fueling)
- **Wellness Monitoring** — HRV, resting HR, sleep, weight trend analysis
- **Discord Bot** — Slash commands: `/summary`, `/week`, `/nutrition`, `/status`
- **REST API** — FastAPI with auto-generated docs at `/docs`
- **Auto-sync** — Background scheduler syncs data from Intervals.icu

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Discord Bot │────▶│   Services   │────▶│  Intervals.icu  │
│  (py-cord)   │     │              │     │     REST API     │
└─────────────┘     │  AIEngine    │     └─────────────────┘
                    │  Analyzer    │
┌─────────────┐     │  Tracker     │     ┌─────────────────┐
│  FastAPI     │────▶│  Planner     │────▶│  OpenAI GPT-4o  │
│  REST API    │     │              │     └─────────────────┘
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   SQLite DB  │
                    │  (aiosqlite) │
                    └──────────────┘
```

## Tech Stack

- **Python 3.11+** with async/await
- **FastAPI** + Uvicorn — REST API
- **py-cord** — Discord bot with slash commands
- **SQLAlchemy 2.0** + aiosqlite — async ORM with SQLite
- **httpx** — async HTTP client for Intervals.icu
- **OpenAI** — GPT-4o for training analysis and nutrition planning
- **APScheduler** — background data sync
- **Docker** — multi-arch (amd64 + arm64) for Raspberry Pi

## Quick Start

### Prerequisites

- Python 3.11+
- [Intervals.icu](https://intervals.icu) account with API key
- OpenAI API key
- Discord bot token (from [Discord Developer Portal](https://discord.com/developers/applications))

### Local Development

```bash
# Clone
git clone https://github.com/jowsiewski/fitness-coach.git
cd fitness-coach

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys

# Create data directory
mkdir -p data

# Run
python -m src.main
```

### Docker (Raspberry Pi / Server)

```bash
# Clone and configure
git clone https://github.com/jowsiewski/fitness-coach.git
cd fitness-coach
cp .env.example .env
# Edit .env with your API keys

# Run with Docker Compose
docker compose up -d

# Or pull pre-built image from GHCR
docker pull ghcr.io/jowsiewski/fitness-coach:latest
```

## Configuration

All settings via environment variables (or `.env` file):

| Variable | Description | Default |
|---|---|---|
| `INTERVALS_API_KEY` | Intervals.icu API key | (required) |
| `INTERVALS_ATHLETE_ID` | Athlete ID (`0` = auto from key) | `0` |
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o` |
| `DISCORD_BOT_TOKEN` | Discord bot token | (optional) |
| `DISCORD_GUILD_ID` | Discord server ID for slash commands | (optional) |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite+aiosqlite:///./data/fitness_coach.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SYNC_INTERVAL_MINUTES` | Data sync interval | `60` |

## Discord Commands

| Command | Description |
|---|---|
| `/summary` | AI summary of your last ride |
| `/week` | Weekly training summary with stats |
| `/nutrition` | Today's nutrition plan with macros |
| `/status` | Current form, readiness, and recommendation |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/activities?days=7` | Recent activities |
| `GET` | `/api/activities/{id}` | Activity details |
| `GET` | `/api/activities/{id}/summary` | AI activity summary |
| `GET` | `/api/fitness/status` | Form status (CTL/ATL/TSB) |
| `GET` | `/api/fitness/readiness` | Training readiness score |
| `GET` | `/api/fitness/recommendation` | AI training recommendation |
| `GET` | `/api/nutrition/today` | Today's nutrition plan |
| `GET` | `/api/nutrition/plan?date=YYYY-MM-DD` | Nutrition plan for date |
| `GET` | `/api/wellness?days=30` | Wellness data |
| `GET` | `/api/wellness/trends?days=30` | AI wellness trend analysis |

Full API docs available at `http://localhost:8000/docs` when running.

## Development

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/ --ignore-missing-imports

# Test
pytest tests/ -v

# All checks
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/ --ignore-missing-imports && pytest tests/ -v
```

## CI/CD

- **CI** — Runs on every push/PR to `main`: ruff lint, ruff format, mypy, pytest
- **Docker** — Builds multi-arch image (amd64 + arm64) and pushes to GHCR on push to `main`

## Roadmap

- [ ] Veloplanner integration (route planning)
- [ ] Daily Discord reports (scheduled at 20:00)
- [ ] Open Food Facts API integration
- [ ] CTL/ATL/TSB trend charts
- [ ] Telegram bot support
- [ ] Training plan generation

## License

MIT
