import asyncio
import os
from contextlib import ExitStack
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import Field
from github import Github
from sqlalchemy.orm import Session
import crud, models, schemas
from config import get_settings
from database import SessionLocal
from websocket import manager

UX_AGENT_ROLE = "Lead UX/UI Designer"
STITCH_ARTIFACT_TYPE = "stitch_design"


class GithubRepoReaderTool(BaseTool):
    name: str = "Read Github Codebase File"
    description: str = "Reads the contents of a specific file in the provided GitHub repository. Input MUST be the exact file path (e.g. 'README.md' or 'src/main.py')."
    github_repo_name: str = Field(description="The name of the github repository to read from")

    def _run(self, file_path: str) -> str:
        try:
            g = Github(os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"))
            repo = g.get_repo(self.github_repo_name)
            file_content = repo.get_contents(file_path)
            return file_content.decoded_content.decode("utf-8")
        except Exception as e:
            return f"Error reading from Github: {str(e)}"


class GithubDirectoryListerTool(BaseTool):
    name: str = "List Github Directory Contents"
    description: str = "Lists all files and folders in a specific directory of the GitHub repository. Input should be the directory path (use '' for the root directory)."
    github_repo_name: str = Field(description="The name of the github repository to read from")

    def _run(self, dir_path: str) -> str:
        try:
            g = Github(os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"))
            repo = g.get_repo(self.github_repo_name)
            contents = repo.get_contents(dir_path)
            files = [f"- {f.path} ({f.type})" for f in contents]
            return f"Contents of '{dir_path}':\n" + "\n".join(files)
        except Exception as e:
            return f"Error listing directory from Github: {str(e)}"


def _enter_stitch_adapter(stack: ExitStack, settings) -> list:
    """Enter a Stitch MCP adapter context on the given ExitStack.

    Returns a list of CrewAI tools the UX agent can call. When STITCH_API_KEY is
    unset, returns an empty list so the UX agent runs in legacy text-only mode.
    If adapter init fails for any reason (network, auth, bad URL), we log and
    return [] rather than failing the whole crew run.
    """
    if not settings.stitch_api_key:
        return []

    try:
        from crewai_tools import MCPServerAdapter
    except Exception as e:
        print(f"[stitch] crewai_tools.MCPServerAdapter unavailable: {e}")
        return []

    # Matches Google's official Stitch MCP extension config
    # (https://github.com/gemini-cli-extensions/stitch). Stitch screen generation
    # can take 1-3 minutes per screen, so allow a long per-request timeout.
    server_params = {
        "url": settings.stitch_mcp_url,
        "transport": "streamable-http",
        "headers": {"X-Goog-Api-Key": settings.stitch_api_key},
        "timeout": 300,
    }
    try:
        adapter = stack.enter_context(MCPServerAdapter(server_params))
        tools = list(adapter.tools)
        print(f"[stitch] connected to {settings.stitch_mcp_url} ({len(tools)} tools)")
        return tools
    except Exception as e:
        print(f"[stitch] adapter init failed, falling back to text UX: {e}")
        return []


def _broadcast_sync(run_id: int, message: dict):
    """Fire-and-forget WebSocket broadcast from a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(manager.broadcast(run_id, message))
        else:
            loop.run_until_complete(manager.broadcast(run_id, message))
    except RuntimeError:
        # No event loop available — skip broadcast
        pass


def run_crew_for_project(project_id: int, crew_run_id: int | None = None):
    db = SessionLocal()
    try:
        project = crud.get_project(db, project_id)
        if not project:
            return

        # Update statuses
        crud.update_project_status(db, project_id, "running")
        if crew_run_id:
            crud.update_crew_run_status(db, crew_run_id, "running")
            _broadcast_sync(crew_run_id, {"type": "status", "status": "running"})

        requirements_list = crud.get_requirements(db, project_id)
        req_text = "\n\n".join([r.content for r in requirements_list])
        if not req_text:
            req_text = "No specific requirements provided."

        kb = crud.get_knowledge_base(db, project_id)
        pm_text = kb.pm_guidelines if kb and kb.pm_guidelines else "None provided."
        architect_text = kb.architect_guidelines if kb and kb.architect_guidelines else "None provided."
        systems_text = kb.systems_guidelines if kb and kb.systems_guidelines else "None provided."
        ai_text = kb.ai_guidelines if kb and kb.ai_guidelines else "None provided."
        ux_text = kb.ux_guidelines if kb and kb.ux_guidelines else "None provided."
        security_text = kb.security_standards if kb and kb.security_standards else "None provided."

        # Setup Environment Variables
        os.environ["OPENAI_API_KEY"] = "fake-key-to-bypass-crewai-checks"
        api_key = os.environ.get("GOOGLE_API_KEY")
        settings = get_settings()

        # Parse GitHub URL
        github_url = project.github_url
        if github_url and "github.com/" in github_url:
            github_repo = github_url.split("github.com/")[-1].strip("/")
        elif github_url:
            github_repo = github_url.strip("/")
        else:
            github_repo = None

        gemini_llm = LLM(
            model="gemini/gemini-3.1-pro-preview",
            temperature=0.4,
            api_key=api_key,
        )

        architect_tools = []
        if github_repo:
            repo_reader_tool = GithubRepoReaderTool(github_repo_name=github_repo)
            dir_lister_tool = GithubDirectoryListerTool(github_repo_name=github_repo)
            architect_tools = [repo_reader_tool, dir_lister_tool]

        # Stitch MCP adapter (Phase 2) — lifecycle managed via ExitStack so it's
        # cleanly torn down even if kickoff raises. When STITCH_API_KEY is unset
        # the UX agent falls back to the original text-critique behaviour.
        with ExitStack() as stack:
            stitch_tools = _enter_stitch_adapter(stack, settings)
            stitch_enabled = bool(stitch_tools)

            # Build Agents
            lead_product_manager = Agent(
                role="Lead Product Manager",
                goal="Read the raw product requirements and break it down into strict, atomic features.",
                backstory=f"You are a methodical Product Manager who prevents scope creep. You read messy human ideas and turn them into beautifully structured specs.\n\nMANDATORY GUIDELINES:\n{pm_text}",
                verbose=True,
                allow_delegation=False,
                llm=gemini_llm,
            )

            lead_architect = Agent(
                role="Lead AI Systems Architect",
                goal="Design scalable, robust, and forward-looking solutions mapping business requirements to technical architecture.",
                backstory=f'You are a pragmatic, battle-tested software architect. You favor simplicity over complexity but know when to use advanced design patterns. {"You thoroughly analyze the existing codebase before rendering decisions. " if github_repo else ""}You prefer Python and Next.js.\n\nMANDATORY GUIDELINES:\n{architect_text}',
                verbose=True,
                allow_delegation=True,
                tools=architect_tools,
                llm=gemini_llm,
            )

            systems_engineer = Agent(
                role="Senior Systems Engineer",
                goal="Ensure the architecture translates into a solid, deployable infrastructure, focusing on databases, CI/CD, and cloud services.",
                backstory=f'You live in the terminal. You believe everything should be "infrastructure as code" and despise manual deployment steps. You are deeply familiar with AWS, Docker, and Kubernetes.\n\nMANDATORY GUIDELINES:\n{systems_text}',
                verbose=True,
                allow_delegation=False,
                llm=gemini_llm,
            )

            ai_specialist = Agent(
                role="AI Integration Specialist",
                goal="Identify and design the integration points for Large Language Models and other AI functionalities.",
                backstory=f"You are obsessed with the latest AI models. You know the strengths and weaknesses of Gemini, Claude, and GPT-4.\n\nMANDATORY GUIDELINES:\n{ai_text}",
                verbose=True,
                allow_delegation=False,
                llm=gemini_llm,
            )

            ux_designer = Agent(
                role=UX_AGENT_ROLE,
                goal=(
                    "Generate concrete UI designs (screens + theme) for the product using the Stitch design tools."
                    if stitch_enabled
                    else "Ensure the final software architecture and product design provide an intuitive, seamless, and visually stunning user experience."
                ),
                backstory=f"You are a militant advocate for the end-user. You despise convoluted workflows. \n\nMANDATORY UX GUIDELINES TO FOLLOW:\n{ux_text}",
                verbose=True,
                allow_delegation=False,
                tools=stitch_tools,
                llm=gemini_llm,
            )

            security_agent = Agent(
                role="Chief Information Security Officer (CISO)",
                goal="Audit the architecture, infrastructure, and workflows to ensure maximum security, compliance, and data privacy.",
                backstory=f"You are paranoid by profession. You assume every system will be breached. \n\nMANDATORY SECURITY STANDARDS TO FOLLOW:\n{security_text}",
                verbose=True,
                allow_delegation=False,
                llm=gemini_llm,
            )

            # Build Tasks
            deconstruct_requirements = Task(
                description=f"Analyze the following raw product requirements:\n{req_text}\n\nIdentify the core, distinct features of the application and create a structured breakdown.",
                expected_output="A structured markdown document listing each atomic feature and its core user stories.",
                agent=lead_product_manager,
            )

            if github_repo:
                architect_instruction = "1. READ the feature breakdown produced by the Product Manager to understand the scope.\n2. USE your Github tools to thoroughly explore the current state of the provided repository.\n3. Identify the core components required to build this system and integrate the new features.\n4. Draft a high-level architecture diagram (text-based or Mermaid) showing the relations between systems."
                architect_output = "A comprehensive, technical blueprint of the application architecture, referencing existing code structure and integrating the new feature requests."
            else:
                architect_instruction = "1. READ the feature breakdown produced by the Product Manager to understand the scope.\n2. Identify the core components required to build this system from scratch based on the requirements.\n3. Draft a high-level architecture diagram (text-based or Mermaid) showing the relations between systems."
                architect_output = "A comprehensive, technical blueprint of the application architecture from scratch."

            draft_architecture = Task(
                description=architect_instruction,
                expected_output=architect_output,
                agent=lead_architect,
            )

            plan_infrastructure = Task(
                description="Analyze the architecture drafted by the Lead Architect. Determine the necessary cloud resources (compute, databases, caching). Outline a deployment strategy.",
                expected_output="A bulleted list of required infrastructure components and a step-by-step deployment guide.",
                agent=systems_engineer,
            )

            design_ai_features = Task(
                description="Review the architecture and identify where LLMs or AI agents can provide the most value. Define the required prompts, data pipelines, and API integrations.",
                expected_output="A detailed specification for the AI features, including suggested model choices and data flow diagrams.",
                agent=ai_specialist,
            )

            if stitch_enabled:
                ux_description = (
                    "Use the Stitch design tools to produce concrete UI designs for this product.\n"
                    "1. From the PM's feature breakdown, identify the 3 highest-priority screens "
                    "(e.g. onboarding, primary dashboard, key task flow).\n"
                    "2. For each screen, call the Stitch 'generate screen from text' tool with a clear "
                    "prompt describing the screen's purpose, content, and target user. If the tool "
                    "requires a project_id, list existing projects first and either reuse one or follow "
                    "the tool's instructions to attach the new screen.\n"
                    "3. After each generation, use the asset download tools to capture the screen's "
                    "HTML URL and screenshot URL.\n"
                    "4. Extract the design system tokens (primary color, accent color, font family) "
                    "from the generated screens.\n\n"
                    "Return your final answer as a single JSON object with this exact shape:\n"
                    "{\n"
                    '  "stitch_project_id": "<id or empty string>",\n'
                    '  "screens": [\n'
                    '    {"name": "<screen name>", "description": "<one-line purpose>", "html_url": "<url>", "screenshot_url": "<url>"}\n'
                    "  ],\n"
                    '  "theme": {"primary_color": "<#hex>", "accent_color": "<#hex>", "font_family": "<name>", "notes": "<other tokens>"},\n'
                    '  "design_rationale": "<short paragraph on how the design serves the user>"\n'
                    "}\n\n"
                    "Output ONLY the JSON object — no surrounding prose, no markdown fences."
                )
                ux_expected = "A single JSON object documenting the Stitch project, generated screens (with html_url and screenshot_url for each), theme tokens, and a short design rationale."
            else:
                ux_description = "Critique the technical architecture from the end-user's perspective. Identify potential friction points. Suggest UI components and user flows that simplify complex interactions."
                ux_expected = "A UX review document outlining potential usability issues in the architecture and concrete suggestions for an intuitive user interface layout and flow."

            design_user_experience = Task(
                description=ux_description,
                expected_output=ux_expected,
                agent=ux_designer,
            )

            audit_security = Task(
                description="Review the architecture, infrastructure plan, and AI design. Identify potential vulnerabilities, ensure proper data encryption strategies are implemented, and verify compliance with standard privacy regulations (e.g., GDPR/CCPA concepts).",
                expected_output="A security audit report detailing identified risks and mandatory changes required to secure the architecture before deployment.",
                agent=security_agent,
            )

            # Start Execution
            development_team = Crew(
                agents=[lead_product_manager, lead_architect, systems_engineer, ai_specialist, ux_designer, security_agent],
                tasks=[deconstruct_requirements, draft_architecture, plan_infrastructure, design_ai_features, design_user_experience, audit_security],
                process=Process.sequential,
                memory=True,
                embedder={
                    "provider": "google-generativeai",
                    "config": {
                        "model": "models/embedding-001",
                        "api_key": api_key,
                    },
                },
            )

            # Kickoff
            result = development_team.kickoff()

            # Save Outputs to Database
            for task in development_team.tasks:
                output_content = task.output.raw if task.output else "No output"
                artifact_type = (
                    STITCH_ARTIFACT_TYPE
                    if stitch_enabled and task.agent.role == UX_AGENT_ROLE
                    else None
                )
                output = schemas.AgentOutputCreate(
                    agent_name=task.agent.role,
                    task_name=task.description[:50] + "...",
                    output_content=output_content,
                    artifact_type=artifact_type,
                )
                db_output = crud.create_agent_output(db, project_id, output, crew_run_id=crew_run_id)

                # Broadcast via WebSocket
                if crew_run_id:
                    _broadcast_sync(crew_run_id, {
                        "type": "agent_output",
                        "agent_name": task.agent.role,
                        "task_name": task.description[:50] + "...",
                        "output_content": output_content,
                        "artifact_type": artifact_type,
                        "output_id": db_output.id,
                    })

            crud.update_project_status(db, project_id, "completed")
            if crew_run_id:
                crud.update_crew_run_status(db, crew_run_id, "completed")
                _broadcast_sync(crew_run_id, {"type": "status", "status": "completed"})

    except Exception as e:
        error_msg = str(e)
        crud.update_project_status(db, project_id, f"error: {error_msg}")
        if crew_run_id:
            crud.update_crew_run_status(db, crew_run_id, "error", error_message=error_msg)
            _broadcast_sync(crew_run_id, {"type": "status", "status": "error", "error": error_msg})
    finally:
        db.close()
