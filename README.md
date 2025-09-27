# Coach AI

An intelligent fitness coach AI agent that leverages your workout data to create personalized training plans, track your progress, and manage comprehensive workout databases. Built with LlamaIndex ReActAgent and featuring local data storage with TinyDB.

## 🚀 Features

### Core Capabilities
- **Personalized Training Plans**: Creates custom workout plans based on your fitness goals and current performance
- **Comprehensive User Profiles**: Manage detailed fitness profiles with workout preferences and goals
- **Local Workout Database**: Store and manage training plans locally using TinyDB (no cloud dependency)
- **Progress Tracking**: Monitor workout completion, performance notes, and training adherence
- **Adaptive Planning**: Updates workout plans based on your performance and feedback
- **Multi-Platform Integration**: Strava integration with plans for MyFitnessPal, Garmin, and other platforms
- **Evidence-Based Coaching**: Uses exercise physiology principles and data analysis for recommendations

### Advanced Features
- **MCP Server Architecture**: Modular tool system using Model Context Protocol
- **LLM Provider Flexibility**: Switch between OpenAI and Azure OpenAI models
- **Real-time Web Search**: Integrated Tavily search for up-to-date fitness information
- **Structured Data Validation**: Robust input validation with comprehensive error handling
- **Memory Retention**: Conversation memory across sessions for personalized interactions

### Workout Database Tools
- **User Profile Management**: Create, update, and retrieve user fitness profiles
- **Workout Planning**: Add structured workouts with detailed descriptions and success criteria
- **Progress Tracking**: Mark workouts complete with performance notes
- **Analytics**: Comprehensive statistics on workout completion rates and trends
- **Date Range Queries**: Filter workouts by date ranges for planning and analysis
- **Data Export**: Backup and restore workout database

## 📋 Setup Instructions

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key or Azure OpenAI access
- Tavily Search API key

### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/AchintyaX/coach-ai.git
cd coach-ai

# Install packages using uv
uv sync
```

### 2. API Keys Setup

#### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key for your `.env` file

#### Tavily Search API Key
1. Visit [Tavily AI](https://tavily.com/)
2. Sign up for an account
3. Generate an API key from your dashboard
4. Copy the key for your `.env` file

#### Azure OpenAI (Alternative to OpenAI)
1. Create an Azure OpenAI resource in Azure portal
2. Deploy a model (e.g., gpt-4o-mini, gpt-5-mini)
3. Get endpoint, API key, deployment name, and API version

### 3. Strava Authentication Setup

Run the authentication setup script to configure your Strava credentials:

```bash
uv run python scripts/setup_auth.py
```

This script will:
- Guide you through creating a Strava API application
- Help you obtain the necessary API credentials
- Set up OAuth tokens for accessing your Strava data

### 4. Environment Configuration

Create a `.env` file in the project root with the following variables:

```bash
# LLM Provider Selection (choose one)
LLM_PROVIDER=openai  # or "azure" for Azure OpenAI

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=sk-proj-your_openai_api_key_here

# Azure OpenAI Configuration (if using Azure)
AZURE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_API_KEY=your_azure_api_key_here
AZURE_DEPLOYMENT_NAME=your_deployment_name
AZURE_MODEL_NAME=gpt-4o-mini
AZURE_API_VERSION=2024-12-01-preview

# Tavily Search API Configuration
TAVILY_API_KEY=your_tavily_api_key_here

# Strava API Configuration (populated by setup_auth.py)
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_ACCESS_TOKEN=your_strava_access_token
STRAVA_REFRESH_TOKEN=your_strava_refresh_token

# Optional: Export Configuration
ROUTE_EXPORT_PATH=./strava-exports
```

### 5. Running the Agent

Start the fitness coach AI agent:

```bash
uv run python main.py
```

The agent will:
- Automatically check and start the MCP Strava server if needed
- Initialize the local workout database (stored in `data/workout_database.json`)
- Load all MCP tools (Strava, Tavily search, workout database)
- Start an interactive CLI session

### 6. Using the Agent

Once running, you can interact with the coach using natural language:

#### User Profile Management
- "Create a user profile for me with 5 workout days per week"
- "Update my running goals to prepare for a half marathon"
- "Show me my current fitness profile"

#### Workout Planning
- "Add a strength workout to my plan for tomorrow"
- "Plan a 5K tempo run for Wednesday"
- "Create a weekly training schedule"

#### Progress Tracking
- "Mark today's workout as completed"
- "Show me my workout completion rate this month"
- "Get my workouts from last week"

#### Strava Integration
- "Analyze my recent running performance"
- "What are my fitness trends over the last month?"
- "Show me my heart rate zones"

#### General Coaching
- "Create a 12-week marathon training plan"
- "Search for the latest research on interval training"
- "What should I focus on for injury prevention?"

#### System Commands
- Type `quit`, `exit`, or `q` to stop the agent

## 🏗️ Architecture

### System Components

- **LlamaIndex ReActAgent**: Intelligent reasoning and tool orchestration
- **MCP (Model Context Protocol)**: Standardized tool communication protocol
- **FastMCP Workout Server**: Local workout database management via STDIO transport
- **TinyDB**: Lightweight local database for workout data storage
- **Tavily Search**: Real-time web search and information retrieval
- **Strava MCP Server**: Activity data and athlete statistics
- **OpenAI/Azure OpenAI**: Flexible LLM provider support

### Data Storage

- **Local Storage**: All workout plans and user profiles stored locally using TinyDB
- **No Cloud Dependency**: Your training data remains on your local system
- **JSON Format**: Human-readable data format for easy backup and portability
- **Automatic Backups**: Built-in database backup functionality

### MCP Tools Available

#### Workout Database Tools (8 tools)
1. `create_user_profile` - Create comprehensive user fitness profiles
2. `get_user_profile` - Retrieve user information and statistics
3. `update_user_goals` - Modify fitness objectives
4. `add_workout` - Add structured workouts to training plans
5. `mark_workout_completed` - Track workout completion with notes
6. `get_user_workouts_by_date_range` - Query workouts by date
7. `list_all_users` - Database user management
8. `get_database_statistics` - Analytics and system health metrics

#### Strava Tools (6 tools)
- Athlete profile and statistics
- Recent activities and detailed activity data
- Activity streams (heart rate, power, GPS data)
- Heart rate and power zones

#### Tavily Search Tools (4 tools)
- Web search for real-time fitness information
- Content extraction from specific URLs
- Website crawling and mapping
- Research and evidence-based recommendations


## 🔧 Development

### Project Structure

```
coach-ai/
├── main.py                     # Main agent application with enhanced logging
├── workout_db_server.py        # FastMCP server for workout database
├── strava_server.py            # MCP server for Strava integration
├── prompts.py                  # Agent persona and system prompts
├── tools/
│   ├── workout_db_tools.py     # TinyDB workout database management
│   ├── user_profile_schema.py  # Pydantic models for data validation
│   └── [strava tools...]       # Individual Strava API tools
├── data/
│   └── workout_database.json   # Local TinyDB database (auto-created)
├── scripts/
│   └── setup_auth.py          # Strava authentication setup
└── tests/                     # Test suite
```

### Key Dependencies

- **LlamaIndex**: Agent framework and MCP integration
- **FastMCP**: MCP server framework
- **TinyDB**: Local JSON database
- **Pydantic**: Data validation and schemas
- **Loguru**: Enhanced logging
- **Python-dotenv**: Environment variable management

## 🤝 Contributing

We welcome contributions to expand the Coach AI platform! Here's how to contribute:

### Before Contributing

1. **Open an Issue First**: Before starting any work, please [open an issue on GitHub](https://github.com/AchintyaX/coach-ai/issues) to discuss:
   - New feature ideas
   - Bug reports
   - Integration requests
   - Documentation improvements

2. **Discussion**: We'll discuss the proposal, provide guidance, and ensure it aligns with the project goals.

### Priority Contribution Areas

We're particularly interested in contributions for:

#### MCP Server Integrations
- **MyFitnessPal**: Nutrition tracking and meal planning integration
- **Garmin Connect**: Advanced fitness metrics and device data
- **Fitbit**: Activity tracking and health metrics
- **Apple Health**: Comprehensive health data integration
- **Polar**: Heart rate training and recovery metrics
- **Oura Ring**: Sleep and recovery tracking
- **Whoop**: Recovery and strain metrics

#### Database Enhancements
- **Data Export/Import**: CSV, JSON, and other format support
- **Backup Automation**: Scheduled backups and cloud sync options
- **Multi-user Support**: Family or team workout management
- **Data Visualization**: Charts and progress graphs

#### Features
- **Advanced Periodization**: Smart training plan algorithms
- **Injury Prevention**: Risk assessment and recommendations
- **Nutrition Integration**: Meal planning and macro tracking
- **Recovery Optimization**: Sleep and rest day planning
- **Performance Prediction**: AI-powered performance forecasting
- **Workout Streaming**: Real-time workout guidance

#### Technical Improvements
- **Alternative LLM Providers**: Anthropic Claude, local models
- **Mobile App Interface**: React Native or Flutter app
- **Web Dashboard**: Browser-based interface
- **API Development**: REST API for third-party integrations
- **Container Support**: Docker deployment options

### Development Process

1. Fork the repository
2. Create a feature branch from `main`
3. Implement your changes following the existing code style
4. Add tests if applicable
5. Update documentation as needed
6. Submit a pull request referencing the original issue

### Code Standards

- Follow existing code formatting and style
- Add proper error handling and logging
- Include docstrings for new functions and classes
- Use type hints for better code clarity
- Test your changes thoroughly
- Update the README if adding new features
- Ensure TinyDB schema compatibility

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter issues:

1. Check existing [GitHub issues](https://github.com/AchintyaX/coach-ai/issues)
2. Review the enhanced debug output for detailed error information
3. Check the `data/workout_database.json` file for data integrity
4. Verify all environment variables are correctly set
5. Open a new issue with detailed information about the problem
6. Include logs and error messages when possible

### Common Issues

- **API Key Issues**: Verify OpenAI/Azure OpenAI and Tavily API keys are valid
- **LLM Provider**: Ensure `LLM_PROVIDER` is set to either "openai" or "azure" in `.env`
- **Database Access**: Ensure `data/` directory has write permissions
- **MCP Server Startup**: Check that FastMCP and required dependencies are installed
- **Strava Authentication**: Re-run `setup_auth.py` if Strava tools fail

---

**Note**: This project is under active development. Features and APIs may change as we improve the platform. Your workout data is stored locally and remains private to your system.