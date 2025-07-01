# CustomLangGraphChatBot

A modular, extensible chatbot for automated code review of GitHub repositories, built using [LangGraph](https://github.com/langchain-ai/langgraph). This project is designed to analyze code, generate review reports, and handle workflow logic for code review automation, especially for MCP server repositories.

## Features
- **Automated code review**: Analyze code from GitHub repositories and generate review reports.
- **Workflow orchestration**: Uses LangGraph to manage review steps, error handling, and branching logic.
- **Extensible nodes**: Each workflow step is a modular async function, making it easy to add or modify logic.
- **Ready for API integration**: Easily connect to FastAPI or other frameworks for chatbot or web API interfaces.

## Project Structure
```
CustomLangGraphChatBot/
│
├── state.py        # Defines the workflow state model (ReviewState)
├── nodes.py        # Async node functions for each workflow step
├── workflow.py     # LangGraph workflow builder and conditional logic
├── analysis.py     # Code analysis logic (placeholder, extend as needed)
├── README.md       # Project documentation
└── ...             # (Add API, GitHub integration, etc. as needed)
```

### File Overview
- **state.py**: Contains the `ReviewState` TypedDict, which holds all state information for the workflow.
- **nodes.py**: Implements async functions for each workflow node (e.g., start review, analyze code, generate report, error handler).
- **workflow.py**: Wires up the workflow using LangGraph, including conditional branching and error handling.
- **analysis.py**: Provides a basic code analysis function; extend this for deeper code review logic.

## Getting Started

### Prerequisites
- Python 3.9+
- [LangGraph](https://github.com/langchain-ai/langgraph) and [LangChain](https://github.com/langchain-ai/langchain)
- (Optional) FastAPI for API endpoints

### Installation
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd CustomLangGraphChatBot
   ```
2. Install dependencies:
   ```bash
   pip install langgraph langchain fastapi
   ```
3. (Optional) Add your own API layer or GitHub integration as needed.

## Usage
- Implement your code review logic in `analysis.py`.
- Add or modify workflow nodes in `nodes.py`.
- Adjust workflow logic in `workflow.py`.
- (Optional) Expose the workflow via an API (e.g., FastAPI) for chatbot or web integration.

## Contributing
We welcome contributions! To get started:
1. Fork the repository and create your branch from `main`.
2. Add or modify features (see project structure above).
3. Write clear commit messages and document your code.
4. Open a pull request with a description of your changes.

### Suggestions for Contributors
- Add new workflow nodes for additional review steps.
- Improve code analysis logic in `analysis.py`.
- Integrate with GitHub APIs for automated repo fetching.
- Add API endpoints for chatbot/web integration.

## License
[MIT](LICENSE)

## Contact
For questions or suggestions, please open an issue or contact the maintainers. 