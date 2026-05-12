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
RESEARCHER_AGENT_ROLE = "Market Discovery Researcher"
MARKET_RESEARCH_ARTIFACT_TYPE = "market_research"


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


class WebResearchTool(BaseTool):
    """Grounded web search powered by Gemini + Google Search.

    Uses the `google.genai` SDK's GoogleSearch tool so the model retrieves and
    cites real-time web content. The Market Researcher calls this multiple times
    per crew run to investigate different angles (market sizing, competitors,
    customer behaviour, regulatory landscape, etc.).
    """

    name: str = "Web Research"
    description: str = (
        "Search the web for current information about markets, customers, competitors, "
        "and industry trends. Returns a grounded answer with citations to real URLs. "
        "Use focused, specific queries — one topic per call (e.g. 'TAM for US "
        "subcontractor invoicing software 2025'). Call this tool multiple times to "
        "triangulate different angles of a research question."
    )

    def _run(self, query: str) -> str:
        import time
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )
        model_name = os.environ.get("GEMINI_MODEL") or "gemini-2.5-pro"

        # Retry transient 5xx with exponential backoff. Gemini preview models
        # frequently return 503 UNAVAILABLE during peak hours.
        last_err: Exception | None = None
        response = None
        for attempt in range(5):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=query,
                    config=config,
                )
                break
            except Exception as e:
                last_err = e
                msg = str(e)
                is_transient = (
                    "503" in msg or "UNAVAILABLE" in msg
                    or "overloaded" in msg.lower() or "high demand" in msg.lower()
                    or "RESOURCE_EXHAUSTED" in msg or "429" in msg
                )
                if not is_transient or attempt == 4:
                    return f"Web research failed: {type(e).__name__}: {msg}"
                backoff = min(2 ** attempt, 16)  # 1, 2, 4, 8, 16 seconds
                print(f"[web-research] {type(e).__name__} on attempt {attempt + 1}; backing off {backoff}s")
                time.sleep(backoff)

        if response is None:
            return f"Web research failed after retries: {last_err}"

        try:
            text = (response.text or "").strip() or "(no answer returned)"
            citations: list[str] = []
            try:
                gm = response.candidates[0].grounding_metadata
                for chunk in (gm.grounding_chunks or []):
                    web = getattr(chunk, "web", None)
                    uri = getattr(web, "uri", None) if web else None
                    if uri:
                        title = (getattr(web, "title", "") or "").strip()
                        citations.append(f"- {title}: {uri}" if title else f"- {uri}")
            except (AttributeError, IndexError):
                pass
            if citations:
                return f"{text}\n\nSources:\n" + "\n".join(citations[:10])
            return text
        except Exception as e:
            return f"Web research result parse failed: {type(e).__name__}: {str(e)}"


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


def _make_task_callback(db, project_id: int, crew_run_id: int | None,
                        agent_role: str, task_label: str, artifact_type: str | None):
    """Build a per-Task callback that persists + broadcasts each agent's output
    the moment its task finishes, instead of waiting for the whole crew to
    complete. Makes LiveTeamView actually live."""

    def _cb(task_output):
        try:
            content = getattr(task_output, "raw", None) or str(task_output) or "No output"
        except Exception:
            content = "No output"
        try:
            output = schemas.AgentOutputCreate(
                agent_name=agent_role,
                task_name=task_label,
                output_content=content,
                artifact_type=artifact_type,
            )
            db_output = crud.create_agent_output(db, project_id, output, crew_run_id=crew_run_id)
            if crew_run_id:
                _broadcast_sync(crew_run_id, {
                    "type": "agent_output",
                    "agent_name": agent_role,
                    "task_name": task_label,
                    "output_content": content,
                    "artifact_type": artifact_type,
                    "output_id": db_output.id,
                })
        except Exception as e:
            print(f"[task-callback] persist failed for {agent_role}: {type(e).__name__}: {e}")

    return _cb


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

        # Build the brief from the project's title + description + every
        # appended `requirements` row. Earlier this only included the
        # requirements rows, so projects whose intent lived in the description
        # field (the common case) reached the researcher as "No specific
        # requirements provided." and the agents hallucinated unrelated
        # products.
        requirements_list = crud.get_requirements(db, project_id)
        brief_parts: list[str] = []
        if project.title:
            brief_parts.append(f"Product name: {project.title}")
        if project.description:
            brief_parts.append(f"Product description / goal:\n{project.description}")
        if requirements_list:
            joined_reqs = "\n\n".join(r.content for r in requirements_list if r.content)
            if joined_reqs.strip():
                brief_parts.append(f"Additional requirements / notes:\n{joined_reqs}")
        req_text = "\n\n".join(brief_parts) if brief_parts else "No specific requirements provided."

        kb = crud.get_knowledge_base(db, project_id)
        pm_text = kb.pm_guidelines if kb and kb.pm_guidelines else "None provided."
        architect_text = kb.architect_guidelines if kb and kb.architect_guidelines else "None provided."
        systems_text = kb.systems_guidelines if kb and kb.systems_guidelines else "None provided."
        ai_text = kb.ai_guidelines if kb and kb.ai_guidelines else "None provided."
        ux_text = kb.ux_guidelines if kb and kb.ux_guidelines else "None provided."
        security_text = kb.security_standards if kb and kb.security_standards else "None provided."

        # Setup Environment Variables
        os.environ["OPENAI_API_KEY"] = "fake-key-to-bypass-crewai-checks"
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        # Newer crewai's Chroma-backed memory checks this env var explicitly
        # rather than reading from the embedder config dict.
        if api_key and not os.environ.get("CHROMA_GOOGLE_GENAI_API_KEY"):
            os.environ["CHROMA_GOOGLE_GENAI_API_KEY"] = api_key
        settings = get_settings()

        # Parse GitHub URL
        github_url = project.github_url
        if github_url and "github.com/" in github_url:
            github_repo = github_url.split("github.com/")[-1].strip("/")
        elif github_url:
            github_repo = github_url.strip("/")
        else:
            github_repo = None

        # Per-project model selection wins, falls back to the server default.
        model_name = (getattr(project, "llm_model", None) or "").strip() or settings.gemini_model
        # WebResearchTool reads GEMINI_MODEL via env, so propagate for this run.
        os.environ["GEMINI_MODEL"] = model_name
        gemini_llm = LLM(
            model=f"gemini/{model_name}",
            temperature=0.4,
            api_key=api_key,
            # Auto-retry transient 5xx. litellm uses exponential backoff.
            num_retries=5,
            timeout=120,
        )

        architect_tools = []
        if github_repo:
            repo_reader_tool = GithubRepoReaderTool(github_repo_name=github_repo)
            dir_lister_tool = GithubDirectoryListerTool(github_repo_name=github_repo)
            architect_tools = [repo_reader_tool, dir_lister_tool]

        # Phase 3a: market discovery toggle. Defaults to True if the column
        # hasn't migrated yet (getattr fallback) so legacy code paths still work.
        discovery_enabled = bool(getattr(project, "discovery_enabled", True))

        # Stitch MCP adapter (Phase 2) — lifecycle managed via ExitStack so it's
        # cleanly torn down even if kickoff raises. When STITCH_API_KEY is unset
        # the UX agent falls back to the original text-critique behaviour.
        with ExitStack() as stack:
            stitch_tools = _enter_stitch_adapter(stack, settings)
            stitch_enabled = bool(stitch_tools)

            # Phase 3a: optional Market Discovery Researcher agent (runs first).
            market_researcher = None
            market_research_task = None
            if discovery_enabled:
                market_researcher = Agent(
                    role=RESEARCHER_AGENT_ROLE,
                    goal=(
                        "Investigate the market, target customers, and competitive landscape for "
                        "the proposed product. Produce a structured discovery brief that downstream "
                        "agents will use to make grounded scope, architecture, and security decisions."
                    ),
                    backstory=(
                        "You are a former Forrester/Gartner analyst turned product strategist. "
                        "You operate in the Teresa Torres continuous discovery tradition: every "
                        "requirement must trace to a named customer opportunity, every opportunity "
                        "must trace to a real market signal. You are skeptical of unsourced claims "
                        "and you size markets honestly — including admitting when an answer is "
                        "'this is a niche.' You always cite specific sources."
                    ),
                    verbose=True,
                    allow_delegation=False,
                    tools=[WebResearchTool()],
                    llm=gemini_llm,
                )

                market_research_task = Task(
                    description=(
                        f"Conduct deep market discovery for the following proposed product:\n\n"
                        f"=== Raw requirements / brief ===\n{req_text}\n\n"
                        "Use the Web Research tool repeatedly to investigate (one focused query per "
                        "call):\n"
                        "  1. Target customers — who experiences the problem most acutely? What are "
                        "     their demographics, behaviours, and current alternatives?\n"
                        "  2. Market sizing — TAM, SAM, and SOM with cited sources. Be honest about "
                        "     niche markets.\n"
                        "  3. Competitive landscape — 3-5 closest competitors, their positioning, "
                        "     and the gaps they leave.\n"
                        "  4. Customer jobs-to-be-done — what hire criteria would make someone "
                        "     switch from the status quo?\n"
                        "  5. Regulatory / compliance landscape — anything (GDPR, HIPAA, SOC2, "
                        "     industry-specific) that affects how this product must be built?\n"
                        "  6. Mobile vs. desktop usage patterns in this market — does the primary "
                        "     persona work primarily on mobile, desktop, or both?\n\n"
                        "Then synthesize an opportunity tree in the Teresa Torres tradition: a top-"
                        "level outcome, customer opportunities as branches (with evidence), and "
                        "candidate solutions as leaves.\n\n"
                        "Return your final answer as a SINGLE JSON object with this exact shape "
                        "(no markdown fences, no prose around it):\n"
                        "{\n"
                        '  "icp": {\n'
                        '    "primary_persona": "<one paragraph>",\n'
                        '    "alternative_personas": ["<paragraph each>"],\n'
                        '    "jobs_to_be_done": [\n'
                        '      {"job": "<verb-noun statement>", "current_alternative": "<status quo>", "trigger": "<what makes them switch>"}\n'
                        "    ]\n"
                        "  },\n"
                        '  "market_sizing": {\n'
                        '    "tam": "<size + source>",\n'
                        '    "sam": "<size + source>",\n'
                        '    "som": "<size + source>",\n'
                        '    "growth_rate": "<CAGR + source>",\n'
                        '    "notes": "<caveats and assumptions>"\n'
                        "  },\n"
                        '  "competitive_landscape": [\n'
                        '    {"name": "<competitor>", "positioning": "<their pitch>", "weakness": "<gap we exploit>", "url": "<homepage>"}\n'
                        "  ],\n"
                        '  "opportunity_tree": {\n'
                        '    "outcome": "<top-level business outcome>",\n'
                        '    "opportunities": [\n'
                        "      {\n"
                        '        "name": "<customer opportunity>",\n'
                        '        "evidence": "<citation/quote>",\n'
                        '        "sub_opportunities": ["<branches>"],\n'
                        '        "candidate_solutions": ["<leaves>"]\n'
                        "      }\n"
                        "    ]\n"
                        "  },\n"
                        '  "key_insights_for_architecture": [\n'
                        '    "<one bullet per cross-cutting decision: mobile-first? hardware? offline? compliance regime? scale tier? integration priorities?>"\n'
                        "  ],\n"
                        '  "citations": ["<url>", ...]\n'
                        "}"
                    ),
                    expected_output=(
                        "A single JSON object documenting the ICP/JTBD, market sizing (TAM/SAM/SOM), "
                        "competitive landscape, opportunity tree, key insights for architecture, and "
                        "a citations list."
                    ),
                    agent=market_researcher,
                    callback=_make_task_callback(
                        db, project_id, crew_run_id,
                        RESEARCHER_AGENT_ROLE, "Market discovery research", MARKET_RESEARCH_ARTIFACT_TYPE,
                    ),
                )

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
            if discovery_enabled:
                pm_description = (
                    "FIRST, carefully read the Market Discovery Researcher's output (it precedes "
                    "your task). Map each candidate feature to one or more opportunities from the "
                    "opportunity tree. Prioritize features that address the highest-evidence "
                    "opportunities and the primary persona's top jobs-to-be-done. Reject scope "
                    "that doesn't trace to a real customer job.\n\n"
                    f"THEN analyze the following raw product requirements:\n{req_text}\n\n"
                    "Identify the core, distinct features of the application and create a "
                    "structured breakdown. For each feature, note which opportunity (by name) it "
                    "addresses."
                )
                pm_expected = (
                    "A structured markdown document listing each atomic feature with: its user "
                    "stories, the opportunity from the discovery tree it serves, and which JTBD "
                    "it advances."
                )
            else:
                pm_description = (
                    f"Analyze the following raw product requirements:\n{req_text}\n\n"
                    "Identify the core, distinct features of the application and create a "
                    "structured breakdown."
                )
                pm_expected = "A structured markdown document listing each atomic feature and its core user stories."

            deconstruct_requirements = Task(
                description=pm_description,
                expected_output=pm_expected,
                agent=lead_product_manager,
                callback=_make_task_callback(
                    db, project_id, crew_run_id,
                    lead_product_manager.role, "Decompose requirements", None,
                ),
            )

            discovery_preamble = (
                "FIRST, read the Market Researcher's `key_insights_for_architecture` array and "
                "the primary persona from the ICP. Use those insights to drive form-factor "
                "(mobile-first vs. desktop vs. hardware), infrastructure scale, integration "
                "priorities, and security tier. Cite the insight you are acting on for each "
                "major architectural decision.\n\nTHEN: "
                if discovery_enabled
                else ""
            )
            if github_repo:
                architect_instruction = (discovery_preamble +
                    "1. READ the feature breakdown produced by the Product Manager to understand the scope.\n2. USE your Github tools to thoroughly explore the current state of the provided repository.\n3. Identify the core components required to build this system and integrate the new features.\n4. Draft a high-level architecture diagram (text-based or Mermaid) showing the relations between systems.")
                architect_output = "A comprehensive, technical blueprint of the application architecture, referencing existing code structure and integrating the new feature requests."
            else:
                architect_instruction = (discovery_preamble +
                    "1. READ the feature breakdown produced by the Product Manager to understand the scope.\n2. Identify the core components required to build this system from scratch based on the requirements.\n3. Draft a high-level architecture diagram (text-based or Mermaid) showing the relations between systems.")
                architect_output = "A comprehensive, technical blueprint of the application architecture from scratch."

            draft_architecture = Task(
                description=architect_instruction,
                expected_output=architect_output,
                agent=lead_architect,
                callback=_make_task_callback(
                    db, project_id, crew_run_id,
                    lead_architect.role, "Draft architecture", None,
                ),
            )

            plan_infrastructure = Task(
                description="Analyze the architecture drafted by the Lead Architect. Determine the necessary cloud resources (compute, databases, caching). Outline a deployment strategy.",
                expected_output="A bulleted list of required infrastructure components and a step-by-step deployment guide.",
                agent=systems_engineer,
                callback=_make_task_callback(
                    db, project_id, crew_run_id,
                    systems_engineer.role, "Plan infrastructure", None,
                ),
            )

            design_ai_features = Task(
                description="Review the architecture and identify where LLMs or AI agents can provide the most value. Define the required prompts, data pipelines, and API integrations.",
                expected_output="A detailed specification for the AI features, including suggested model choices and data flow diagrams.",
                agent=ai_specialist,
                callback=_make_task_callback(
                    db, project_id, crew_run_id,
                    ai_specialist.role, "Design AI features", None,
                ),
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

            ux_artifact_type = STITCH_ARTIFACT_TYPE if stitch_enabled else None
            design_user_experience = Task(
                description=ux_description,
                expected_output=ux_expected,
                agent=ux_designer,
                callback=_make_task_callback(
                    db, project_id, crew_run_id,
                    UX_AGENT_ROLE, "Design user experience", ux_artifact_type,
                ),
            )

            audit_security = Task(
                description="Review the architecture, infrastructure plan, and AI design. Identify potential vulnerabilities, ensure proper data encryption strategies are implemented, and verify compliance with standard privacy regulations (e.g., GDPR/CCPA concepts).",
                expected_output="A security audit report detailing identified risks and mandatory changes required to secure the architecture before deployment.",
                agent=security_agent,
                callback=_make_task_callback(
                    db, project_id, crew_run_id,
                    security_agent.role, "Audit security", None,
                ),
            )

            # Start Execution
            crew_agents = [lead_product_manager, lead_architect, systems_engineer, ai_specialist, ux_designer, security_agent]
            crew_tasks = [deconstruct_requirements, draft_architecture, plan_infrastructure, design_ai_features, design_user_experience, audit_security]
            if discovery_enabled and market_researcher and market_research_task:
                # Researcher runs first; PM + Architect read its output from the
                # prior task's context (CrewAI passes raw outputs forward in
                # Process.sequential even without memory enabled).
                crew_agents.insert(0, market_researcher)
                crew_tasks.insert(0, market_research_task)

            # memory=False: avoids CrewAI's OpenAI-dependent memory analyzer,
            # which was failing on 401s and adding minutes of retry latency per
            # run. Sequential mode still passes prior task outputs forward.
            development_team = Crew(
                agents=crew_agents,
                tasks=crew_tasks,
                process=Process.sequential,
                memory=False,
            )

            # Kickoff. Per-task callbacks (attached above) persist + broadcast
            # each agent's output the moment its task finishes, so LiveTeamView
            # is actually live instead of getting everything in one burst at the
            # end.
            development_team.kickoff()

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
