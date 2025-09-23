# Coach AI

An intelligent fitness coach AI agent that leverages your workout data to create personalized training plans and track your progress.

## Features

- **Personalized Training Plans**: Creates custom workout plans based on your fitness goals and current performance
- **Progress Tracking**: Monitors your workout progress and provides data-driven insights
- **Adaptive Planning**: Updates workout plans based on your performance and feedback
- **Multi-Platform Integration**: Currently supports Strava with plans to add MyFitnessPal, Garmin, and other health tracking platforms
- **Evidence-Based Coaching**: Uses exercise physiology principles and data analysis for recommendations

## Setup Instructions

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Install Dependencies

```bash
# Install packages using uv
uv sync
```

### 2. Setup Authentication

Run the authentication setup script to configure your Strava credentials:

```bash
uv run python scripts/setup_auth.py
```

This script will:
- Guide you through creating a Strava API application
- Help you obtain the necessary API credentials
- Set up OAuth tokens for accessing your Strava data

### 3. Environment Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Azure OpenAI Configuration
AZURE_ENDPOINT=your_azure_endpoint_here
AZURE_API_KEY=your_azure_api_key_here
AZURE_DEPLOYMENT_NAME=your_deployment_name
AZURE_MODEL_NAME=your_model_name
AZURE_API_VERSION=2024-12-01-preview

# Strava API Configuration (populated by setup_auth.py)
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_ACCESS_TOKEN=your_strava_access_token
STRAVA_REFRESH_TOKEN=your_strava_refresh_token

# Optional: Export Configuration
ROUTE_EXPORT_PATH=./strava-exports
```

### 4. Running the Agent

Start the fitness coach AI agent:

```bash
uv run python main.py
```

The agent will:
- Automatically check and start the MCP Strava server if needed
- Load your athlete profile using your Strava client ID
- Start an interactive CLI session

### 5. Using the Agent

Once running, you can interact with the coach by typing commands like:
- "Analyze my recent running performance"
- "Create a 12-week marathon training plan"
- "What are my fitness trends over the last month?"
- Type `quit`, `exit`, or `q` to stop the agent

## Architecture

The system uses:
- **LlamaIndex ReAct Agent**: For intelligent reasoning and tool use
- **MCP (Model Context Protocol)**: For accessing Strava data via server
- **Azure OpenAI**: For the underlying language model
- **Custom Prompts**: Fitness coach persona with evidence-based approach

## Contributing

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

#### Features
- Advanced periodization algorithms
- Injury prevention recommendations  
- Nutrition planning and tracking
- Recovery and sleep optimization
- Performance prediction models

#### Improvements
- Better error handling and user experience
- Additional language model providers
- Mobile app interface
- Web dashboard
- Export capabilities for training plans

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
- Include docstrings for new functions
- Test your changes thoroughly
- Update the README if adding new features

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter issues:
1. Check existing [GitHub issues](https://github.com/AchintyaX/coach-ai/issues)
2. Open a new issue with detailed information about the problem
3. Include logs and error messages when possible

---

**Note**: This project is under active development. Features and APIs may change as we improve the platform.