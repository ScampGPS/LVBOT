# CLV Tennis Bot

A sophisticated Telegram bot system that automates tennis court reservations at Club La Villa with advanced features for performance optimization, multi-user support, and intelligent court assignment.

## System Overview

LVBot is a comprehensive tennis court reservation automation system built with Python, Playwright, and Telegram Bot API. It features a layered architecture designed for reliability, performance, and scalability for a private tennis club environment.

## Features

- **Automated Reservations**: Books courts exactly 48 hours in advance with smart retry logic
- **Performance Optimization**: Up to 200x faster operation with browser pooling and speed modes
- **Multi-User Support**: Intelligent court assignment for multiple users booking same timeslot
- **Advanced Scheduling**: Queue-based reservation system with priority handling
- **Browser Pool Management**: Pre-warmed browser instances eliminate startup overhead
- **Performance Monitoring**: Real-time website performance tracking with adaptive timeouts
- **User Authorization**: Secure user management with admin controls
- **Telegram Integration**: Full-featured bot interface for easy interaction

## Refactor Status (August 2025)

Refactor tracking now lives in `docs/refactor_roadmap.md` with implementation details collected in `docs/refactor_plan.md`.
Phase 0.5 archiving is complete and Phase 1 (architecture & naming) has
introduced new scaffolding:

- `infrastructure/settings.py` centralises runtime configuration loading.
- Packages under `automation/{browser,executors,availability}` and
  `domain/{queue,models}` support incremental module moves.
- `docs/refactor_plan.md` captures the module migration targets and sequencing for the bot runtime refactor.

Sections below describe the legacy layout; prefer the roadmap documents for the
latest structure until the refactor concludes.

## Architecture

### Core Components

#### 1. **Telegram Bot Interface** (`run_bot.py`)
The main entry point providing user interaction through Telegram:
- **BotConfig**: Central configuration with hardcoded users and settings
- **UserProfile**: User data management (name, email, phone, preferences)
- **ReservationQueue**: Manages pending bookings with scheduling
- **AuthorizationManager**: Controls user access and permissions
- **ReservationScheduler**: Thread-based executor for timed reservations

#### 2. **Web Automation Engine** (`playwright_bot.py`)
Core automation using Playwright for web interactions:
- **TennisBot**: Main automation class handling the booking flow
- **IframeHandler**: Specialized handler for iframe navigation with retries
- Speed optimization with configurable multipliers (1x-200x)
- Smart waiting mechanisms for dynamic content
- Complete reservation workflow automation

#### 3. **Browser Pool System** (`browser_pool.py` and variants)
Advanced browser instance management:
- **BrowserPool**: Maintains pre-warmed browser instances
- **BrowserInstance**: Wrapper with health monitoring
- Automatic instance recycling and health checks
- Variants: `browser_pool_persistent.py`, `browser/pools/specialized.py`
- Dramatic performance improvements by eliminating startup time

#### 4. **Court Assignment Logic** (`court_assignment_manager.py`)
Intelligent court allocation for multiple users:
- **CourtAssignmentManager**: Conflict-free court distribution
- Priority system: Admin > Premium > Regular users
- Overflow handling for high-demand timeslots
- Fair allocation based on user preferences

#### 5. **Performance Monitoring** (`performance_monitor.py`)
Real-time system health tracking:
- **WebsitePerformanceMonitor**: Tracks response times and health
- **SmartTimeoutManager**: Adaptive timeout adjustments
- Alert system for performance degradation
- Historical tracking and trend analysis

### Additional Components

#### Bot Variants
- **telegram_bot_enhanced.py**: Enhanced version with browser pooling
- **telegram_bot_ultimate.py**: Ultimate performance with all optimizations
- **telegram_bot_performance.py**: Performance-focused implementation
- **run_bot.py**: Convenience launcher around the async bot

#### Testing & Performance
- **performance_test_*.py**: Various performance testing scripts
- **test_all_features.py**: Comprehensive feature testing
- **quick_performance_test_improved.py**: Quick performance validation
- **extreme_speed_mode.py**: Maximum speed configuration

#### Utilities
- **async_tennis_executor.py**: Asynchronous execution handler
- **multi_user_booking_example.py**: Multi-user booking demonstration

## File Structure

```
LVBot/
├── Core Bot Files
│   ├── run_bot.py                      # Main Telegram bot launcher
│   ├── playwright_bot.py               # Core web automation
│   ├── browser_pool.py                 # Browser instance pooling
│   ├── court_assignment_manager.py     # Court allocation logic
│   └── performance_monitor.py          # Performance tracking
│
├── Bot Variants
│   ├── telegram_bot_enhanced.py        # Enhanced with pooling
│   ├── telegram_bot_ultimate.py        # All optimizations
│   ├── telegram_bot_performance.py     # Performance-focused
│   └── botapp/                         # Telegram bot modules
│
├── Configuration & Data
│   ├── config/.env.example             # Environment variable template
│   ├── data/authorized_users.json      # Authorized user IDs
│   ├── data/users.json                 # User profile storage
│   ├── data/queue.json                 # Reservation queue
│   └── requirements.txt                # Python dependencies
│
├── Deployment
│   ├── Dockerfile                      # Container configuration
│   ├── docker-compose.yml              # Multi-container setup
│   ├── deploy-to-gcp.sh               # GCP deployment script
│   ├── quick-deploy.sh                # Quick deployment script
│   ├── startup-script.sh              # VM startup configuration
│   └── DEPLOY.md                      # Deployment documentation
│
├── Testing & Performance
│   ├── performance_test_*.py          # Performance test variants
│   ├── test_all_features.py           # Feature testing
│   ├── test_simple.py                 # Basic tests
│   └── test_playwright_real.py        # Real browser tests
│
└── Documentation
    ├── README.md                      # This file
    └── TODO.md                        # Development tasks
```

## Technical Details

### Dependencies
- **python-telegram-bot==20.7**: Telegram bot framework
- **playwright==1.40.0**: Web automation library
- **pytz==2023.3.post1**: Timezone handling

### Key Design Patterns
- **Thread-based Concurrency**: Multiple user handling
- **Context Managers**: Resource management (browsers)
- **Strategy Pattern**: Court assignment algorithms
- **Observer Pattern**: Performance monitoring alerts
- **Retry Mechanisms**: Robust error handling

### Performance Optimizations
- Pre-warmed browser pools eliminate ~3-5 second startup time
- Configurable speed multipliers (up to 200x faster operations)
- Resource blocking for faster page loads
- Smart waiting instead of fixed delays
- Concurrent execution for multiple reservations

### Data Storage
- **data/authorized_users.json** (if used): List of authorized Telegram user IDs
- **data/users.json**: User profiles and preferences
- **queue.json**: Pending reservation requests
- All data persisted in JSON format for simplicity

## Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from @BotFather)
- Your Telegram User ID (from @userinfobot)

### Local Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Copy the template and create your `.env` file:
   ```bash
   cp config/.env.example .env
   ```
   Then set the values:
   ```
   BOT_TOKEN=your_bot_token_here
   ADMIN_USER_ID=your_telegram_user_id
   ```

4. Run the bot:
   ```bash
   python run_bot.py
   ```

## Deployment

### Google Cloud Platform Hosting

The bot is currently hosted on Google Cloud Compute Engine with the following configuration:

#### Instance Details
- **Instance Name**: clv-bot-vm
- **Zone**: us-east1-c
- **Machine Type**: e2-micro (1 vCPU, 1GB memory)
- **IP Address**: 34.23.240.53
- **Operating System**: Ubuntu/Debian
- **Cost**: Free tier eligible (~$0-5/month)

#### Accessing the Instance

1. **Via Google Cloud Shell**:
   ```bash
   # List instances
   gcloud compute instances list
   
   # SSH into the bot instance
   gcloud compute ssh clv-bot-vm --zone=us-east1-c
   ```

2. **Managing the Bot Process**:
   ```bash
   # Check if bot is running
   ps aux | grep run_bot
   
   # Stop the bot
   kill [PID]  # Replace [PID] with actual process ID
   
   # Start the bot
   cd ~/  # Or wherever your bot files are located
   python run_bot.py
   ```

3. **Running in Background**:
   ```bash
   # Run with nohup to persist after SSH disconnect
   nohup python run_bot.py > tennis_bot.log 2>&1 &
   
   # Or use screen (if installed)
   screen -S tennis-bot
   python run_bot.py
   # Press Ctrl+A, then D to detach
   ```

See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions and automated setup scripts.

### Docker Deployment

Build and run with Docker (for local testing or container-based deployment):
```bash
docker-compose build
docker-compose up -d
```

## Usage

1. Start the bot: `/start`
2. Check availability for a date
3. Book a court at your preferred time
4. The bot will automatically attempt the reservation 48 hours before

### Bot Commands
- `/start` - Initialize bot and show welcome message
- `/book` - Start booking process
- `/status` - Check reservation queue status
- `/cancel` - Cancel pending reservations
- Admin commands available for user management

## Configuration

The bot starts attempting reservations 15 seconds before the 48-hour booking window opens to ensure the best chance of securing your preferred court. Configuration includes:

- **Timing**: 15-second buffer before booking window
- **Retries**: Up to 50 retry attempts
- **Speed Modes**: Normal (1x) to Extreme (200x)
- **Browser Pool**: 3-5 pre-warmed instances
- **Court Preferences**: Ordered list per user

## Security Notes

This system is designed for a private tennis club with:
- Hardcoded authorized users
- Admin-only user management
- No public registration
- Telegram-based authentication

## License

Private project - All rights reserved
