import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import DirectoryReadTool
from crewai.tools import BaseTool
from pydantic import Field
from github import Github
from sqlalchemy.orm import Session
import crud, models, schemas
from database import SessionLocal

class GithubRepoReaderTool(BaseTool):
    name: str = "Read Github Codebase File"
    description: str = "Reads the contents of a specific file in the provided GitHub repository. Input MUST be the exact file path (e.g. 'README.md' or 'src/main.py')."
    github_repo_name: str = Field(description="The name of the github repository to read from")
    
    def _run(self, file_path: str) -> str:
        try:
            g = Github(os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"))
            repo = g.get_repo(self.github_repo_name)
            file_content = repo.get_contents(file_path)
            return file_content.decoded_content.decode('utf-8')
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

def run_crew_for_project(project_id: int):
    # Setup DB session
    db = SessionLocal()
    try:
        # Fetch Project Data
        project = crud.get_project(db, project_id)
        if not project:
            return
            
        crud.update_project_status(db, project_id, "running")
        
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

        # Setup Environment Variables (Assumes they are loaded in the environment)
        os.environ["OPENAI_API_KEY"] = "fake-key-to-bypass-crewai-checks"
        api_key = os.environ.get("GOOGLE_API_KEY")
        
        # Parse GitHub URL
        github_url = project.github_url
        if github_url and "github.com/" in github_url:
            github_repo = github_url.split("github.com/")[-1].strip("/")
        elif github_url:
            github_repo = github_url.strip("/")
        else:
            github_repo = None

        gemini_llm = LLM(
            model="gemini/gemini-1.5-pro", 
            temperature=0.4,
            api_key=api_key
        )

        architect_tools = []
        if github_repo:
            repo_reader_tool = GithubRepoReaderTool(github_repo_name=github_repo)
            dir_lister_tool = GithubDirectoryListerTool(github_repo_name=github_repo)
            architect_tools = [repo_reader_tool, dir_lister_tool]

        # Build Agents
        lead_product_manager = Agent(
            role='Lead Product Manager',
            goal='Read the raw product requirements and break it down into strict, atomic features.',
            backstory=f'You are a methodical Product Manager who prevents scope creep. You read messy human ideas and turn them into beautifully structured specs.\n\nMANDATORY GUIDELINES:\n{pm_text}',
            verbose=True,
            allow_delegation=False,
            llm=gemini_llm
        )

        lead_architect = Agent(
            role='Lead AI Systems Architect',
            goal='Design scalable, robust, and forward-looking solutions mapping business requirements to technical architecture.',
            backstory=f'You are a pragmatic, battle-tested software architect. You favor simplicity over complexity but know when to use advanced design patterns. {"You thoroughly analyze the existing codebase before rendering decisions. " if github_repo else ""}You prefer Python and Next.js.\n\nMANDATORY GUIDELINES:\n{architect_text}',
            verbose=True,
            allow_delegation=True,
            tools=architect_tools,
            llm=gemini_llm
        )

        systems_engineer = Agent(
            role='Senior Systems Engineer',
            goal='Ensure the architecture translates into a solid, deployable infrastructure, focusing on databases, CI/CD, and cloud services.',
            backstory=f'You live in the terminal. You believe everything should be "infrastructure as code" and despise manual deployment steps. You are deeply familiar with AWS, Docker, and Kubernetes.\n\nMANDATORY GUIDELINES:\n{systems_text}',
            verbose=True,
            allow_delegation=False,
            llm=gemini_llm
        )

        ai_specialist = Agent(
            role='AI Integration Specialist',
            goal='Identify and design the integration points for Large Language Models and other AI functionalities.',
            backstory=f'You are obsessed with the latest AI models. You know the strengths and weaknesses of Gemini, Claude, and GPT-4.\n\nMANDATORY GUIDELINES:\n{ai_text}',
            verbose=True,
            allow_delegation=False,
            llm=gemini_llm
        )

        ux_designer = Agent(
            role='Lead UX/UI Designer',
            goal='Ensure the final software architecture and product design provide an intuitive, seamless, and visually stunning user experience.',
            backstory=f'You are a militant advocate for the end-user. You despise convoluted workflows. \n\nMANDATORY UX GUIDELINES TO FOLLOW:\n{ux_text}',
            verbose=True,
            allow_delegation=False,
            llm=gemini_llm
        )

        security_agent = Agent(
            role='Chief Information Security Officer (CISO)',
            goal='Audit the architecture, infrastructure, and workflows to ensure maximum security, compliance, and data privacy.',
            backstory=f'You are paranoid by profession. You assume every system will be breached. \n\nMANDATORY SECURITY STANDARDS TO FOLLOW:\n{security_text}',
            verbose=True,
            allow_delegation=False,
            llm=gemini_llm
        )

        # Build Tasks
        deconstruct_requirements = Task(
            description=f'Analyze the following raw product requirements:\n{req_text}\n\nIdentify the core, distinct features of the application and create a structured breakdown.',
            expected_output='A structured markdown document listing each atomic feature and its core user stories.',
            agent=lead_product_manager
        )

        if github_repo:
            architect_instruction = '1. READ the feature breakdown produced by the Product Manager to understand the scope.\n2. USE your Github tools to thoroughly explore the current state of the provided repository.\n3. Identify the core components required to build this system and integrate the new features.\n4. Draft a high-level architecture diagram (text-based or Mermaid) showing the relations between systems.'
            architect_output = 'A comprehensive, technical blueprint of the application architecture, referencing existing code structure and integrating the new feature requests.'
        else:
            architect_instruction = '1. READ the feature breakdown produced by the Product Manager to understand the scope.\n2. Identify the core components required to build this system from scratch based on the requirements.\n3. Draft a high-level architecture diagram (text-based or Mermaid) showing the relations between systems.'
            architect_output = 'A comprehensive, technical blueprint of the application architecture from scratch.'

        draft_architecture = Task(
            description=architect_instruction,
            expected_output=architect_output,
            agent=lead_architect
        )

        plan_infrastructure = Task(
            description='Analyze the architecture drafted by the Lead Architect. Determine the necessary cloud resources (compute, databases, caching). Outline a deployment strategy.',
            expected_output='A bulleted list of required infrastructure components and a step-by-step deployment guide.',
            agent=systems_engineer
        )

        design_ai_features = Task(
            description='Review the architecture and identify where LLMs or AI agents can provide the most value. Define the required prompts, data pipelines, and API integrations.',
            expected_output='A detailed specification for the AI features, including suggested model choices and data flow diagrams.',
            agent=ai_specialist
        )

        design_user_experience = Task(
            description='Critique the technical architecture from the end-user\'s perspective. Identify potential friction points. Suggest UI components and user flows that simplify complex interactions.',
            expected_output='A UX review document outlining potential usability issues in the architecture and concrete suggestions for an intuitive user interface layout and flow.',
            agent=ux_designer
        )

        audit_security = Task(
            description='Review the architecture, infrastructure plan, and AI design. Identify potential vulnerabilities, ensure proper data encryption strategies are implemented, and verify compliance with standard privacy regulations (e.g., GDPR/CCPA concepts).',
            expected_output='A security audit report detailing identified risks and mandatory changes required to secure the architecture before deployment.',
            agent=security_agent
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
                }
            }
        )

        # Kickoff
        result = development_team.kickoff()
        
        # Save Outputs to Database
        # Since standard kickoff returns a CrewOutput string, we will just save the final result from each task.
        for task in development_team.tasks:
            crud.create_agent_output(db, project_id, schemas.AgentOutputCreate(
                agent_name=task.agent.role,
                task_name=task.description[:50] + "...",
                output_content=task.output.raw if task.output else "No output"
            ))

        crud.update_project_status(db, project_id, "completed")
    except Exception as e:
        crud.update_project_status(db, project_id, f"error: {str(e)}")
    finally:
        db.close()
