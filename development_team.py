import os
os.environ["OPENAI_API_KEY"] = "fake-key-to-bypass-crewai-checks"

from crewai import Agent, Task, Crew, Process, LLM
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai_tools import FileReadTool, FileWriterTool, DirectoryReadTool
from crewai.tools import BaseTool
from pydantic import Field
from github import Github

# ==========================================
# 1. ENVIRONMENT CONFIGURATION
# ==========================================
# Hack to bypass CrewAI's aggressive default OpenAI initialization checks
os.environ["OPENAI_API_KEY"] = "fake-key-to-bypass-crewai-checks"

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    api_key = input("Please enter your GOOGLE_API_KEY (it will not be saved): ").strip()

github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
if not github_token:
    github_token = input("Please enter your GITHUB_PERSONAL_ACCESS_TOKEN (for reading the codebase): ").strip()
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token

# Ask for the Github Repository URL.
github_repo = os.environ.get("GITHUB_REPO_URL")
if not github_repo:
    github_repo = input("Please enter the Github Repository you want the architect to analyze (e.g., 'chrispainter/claude_skills'): ").strip()
    os.environ["GITHUB_REPO_URL"] = github_repo

# Initialize the Gemini model
# We are telling the agents to use Gemini Pro to do their thinking
gemini_llm = LLM(
    model="gemini/gemini-3.1-pro", 
    temperature=0.4, # A lower temperature keeps the architect grounded and focused on facts
    api_key=api_key
)

# ==========================================
# 2. CREATE CUSTOM TOOLS
# ==========================================

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
            if "404" in str(e):
                # If file not found, let's try to just list the directory contents to help the agent
                try:
                    dir_path = "/".join(file_path.split("/")[:-1])
                    contents = repo.get_contents(dir_path)
                    files = [f.path for f in contents]
                    return f"Error: File '{file_path}' not found. Here are the files available in that directory: {', '.join(files)}"
                except:
                    return f"Error: Could not read file path '{file_path}'."
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

# Instantiate the Github tools with the target repo
repo_reader_tool = GithubRepoReaderTool(github_repo_name=github_repo)
dir_lister_tool = GithubDirectoryListerTool(github_repo_name=github_repo)

# Instantiate the Local File Tools for the Product Manager and Architect
requirements_reader = FileReadTool(file_path='requirements.md')
feature_writer = FileWriterTool()
feature_directory_reader = DirectoryReadTool(directory='features')

# ==========================================
# 3. LOAD AGENT KNOWLEDGE BASE
# ==========================================

base_dir = os.path.dirname(os.path.abspath(__file__))

# Read the knowledge base files manually to inject into agent backstories
try:
    with open(os.path.join(base_dir, "knowledge/ux_guidelines.md"), "r") as f:
        ux_knowledge_text = f.read()
except FileNotFoundError:
    ux_knowledge_text = "No UX guidelines found."

try:
    with open(os.path.join(base_dir, "knowledge/security_standards.md"), "r") as f:
        security_knowledge_text = f.read()
except FileNotFoundError:
    security_knowledge_text = "No Security standards found."


# ==========================================
# 4. HIRE YOUR TEAM (AGENTS)
# ==========================================

lead_product_manager = Agent(
    role='Lead Product Manager',
    goal='Read the raw product requirements document and break it down into strict, atomic feature files to ensure modular development.',
    backstory='You are a methodical Product Manager who prevents scope creep. You read messy human ideas and turn them into beautifully structured, isolated feature specs.',
    verbose=True,
    allow_delegation=False,
    tools=[requirements_reader, feature_writer],
    llm=gemini_llm
)

lead_architect = Agent(
    role='Lead AI Systems Architect',
    goal='Design scalable, robust, and forward-looking solutions mapping business requirements to technical architecture.',
    backstory='You are a pragmatic, battle-tested software architect. You favor simplicity over complexity but know when to use advanced design patterns. You thoroughly analyze the existing codebase before rendering decisions. You prefer Python and Next.js.',
    verbose=True,
    allow_delegation=True,
    tools=[repo_reader_tool, dir_lister_tool, feature_directory_reader],
    llm=gemini_llm
)

systems_engineer = Agent(
    role='Senior Systems Engineer',
    goal='Ensure the architecture translates into a solid, deployable infrastructure, focusing on databases, CI/CD, and cloud services.',
    backstory='You live in the terminal. You believe everything should be "infrastructure as code" and despise manual deployment steps. You are deeply familiar with AWS, Docker, and Kubernetes.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

ai_specialist = Agent(
    role='AI Integration Specialist',
    goal='Identify and design the integration points for Large Language Models and other AI functionalities.',
    backstory='You are obsessed with the latest AI models. You know the strengths and weaknesses of Gemini, Claude, and GPT-4. You focus on prompt engineering, RAG architectures, and ensuring AI features actually solve user problems.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

ux_designer = Agent(
    role='Lead UX/UI Designer',
    goal='Ensure the final software architecture and product design provide an intuitive, seamless, and visually stunning user experience.',
    backstory=f'You are a militant advocate for the end-user. You despise convoluted workflows, hidden menus, and jarring visual transitions. You believe that great software should feel invisible and require zero training.\n\nMANDATORY UX GUIDELINES TO FOLLOW:\n{ux_knowledge_text}',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

security_agent = Agent(
    role='Chief Information Security Officer (CISO)',
    goal='Audit the architecture, infrastructure, and workflows to ensure maximum security, compliance, and data privacy.',
    backstory=f'You are paranoid by profession. You assume every system will be breached and design accordingly. You focus on Zero Trust, principle of least privilege, and strict compliance with global data privacy laws.\n\nMANDATORY SECURITY STANDARDS TO FOLLOW:\n{security_knowledge_text}',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

# ==========================================
# 5. ASSIGN THEIR JOBS (TASKS)
# ==========================================

deconstruct_requirements = Task(
    description='1. Read the `requirements.md` file to understand the overall project.\n2. Identify the core, distinct features of the application.\n3. For each feature you identify, use your tool to create a new markdown file inside the `features/` directory (e.g., `features/conversational_search.md`). The file should contain a clear description of that specific feature and any user stories.',
    expected_output='Multiple atomic markdown files created in the `features/` directory, one for each feature.',
    agent=lead_product_manager
)

draft_architecture = Task(
    description='1. READ the contents of the `features/` directory produced by the Product Manager to understand the scope.\n2. USE your Github tools to thoroughly explore the current state of the provided repository.\n3. Identify the core components required to build this system and integrate the new features.\n4. Draft a high-level architecture diagram (text-based or Mermaid) showing the relations between systems.',
    expected_output='A comprehensive, technical blueprint of the application architecture, referencing existing code structure and integrating the new feature requests.',
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

# ==========================================
# 6. START THE WORK (THE CREW)
# ==========================================

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

print("Starting the Development Team...")
print("The Product Manager is reading requirements.md and breaking it into atomic feature files...")
print("The rest of the team will then design the architecture based on those specific files.")
print("==========================================")

# Start the crew's execution
result = development_team.kickoff()

print("\n\nFINAL DEVELOPMENT TEAM REPORT:")
print("==========================================")
print(result)
