# Project Roadmap: CustomLangGraphChatBot

This roadmap outlines the key tasks and milestones for building and improving the LangGraph-based code review chatbot for GitHub repositories.

## Milestone 1: Core Workflow
- [x] Define workflow state model (`ReviewState`)
- [x] Implement basic workflow nodes (start, analyze, report, error handler)
- [x] Build workflow orchestration with LangGraph
- [x] Add placeholder code analysis logic

## Milestone 2: Code Review Logic
- [ ] Implement real code analysis for **Python** (linting, complexity, best practices)
- [ ] Implement real code analysis for **TypeScript**
- [ ] Generate detailed review reports with actionable feedback

## Milestone 3: GitHub Integration
- [ ] Integrate with GitHub API for repository fetching
- [ ] Support authentication and private repositories
- [ ] Handle pull requests and commit-specific reviews

## Milestone 4: API & Chatbot Interface
- [ ] Expose workflow via FastAPI endpoints
- [ ] Build a simple web/chatbot interface for user interaction
- [ ] Add webhook support for GitHub events (optional)

## Milestone 5: Extensibility & Collaboration
- [ ] Modularize node logic for easy extension
- [ ] Add configuration options for custom review rules
- [ ] Write developer documentation and usage examples
- [ ] Add tests and CI/CD integration

## How to Contribute
- Pick an open task or suggest a new feature via issues.
- Fork the repo, create a branch, and submit a pull request.
- See `README.md` for setup and contribution guidelines.
- See `.cursor/` for project-specific development rules and guidelines.
- we would be tackling generic code review for all programming languages on future release. Our Focus being on the know languages for now 

---

*This roadmap will evolve as the project grows. Suggestions and contributions are welcome!* 