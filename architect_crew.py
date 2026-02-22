import os
from crewai import Agent, Task, Crew, Process, LLM

from crewai.tools import BaseTool
from pydantic import Field
from github import Github

# Ask for the API keys if they aren't already set in the environment.
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    api_key = input("Please enter your GOOGLE_API_KEY (it will not be saved): ").strip()
    os.environ["GOOGLE_API_KEY"] = api_key

github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
if not github_token:
    github_token = input("Please enter your GITHUB_PERSONAL_ACCESS_TOKEN (needed to read the codebase): ").strip()
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token

github_repo = input("\nPlease enter the GITHUB_REPO_URL you want the Architect to analyze (e.g., 'chrispainter/claude_skills'): ").strip()

# Initialize the Gemini model
# We are telling the agents to use Gemini Pro to do their thinking
gemini_llm = LLM(
    model="gemini/gemini-2.5-pro", 
    temperature=0.4, # A lower temperature keeps the architect grounded and focused on facts
    api_key=api_key
)

# ==========================================
# 2. CREATE GITHUB CODEBASE TOOL
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

# Instantiate the tools with the target repo
repo_reader_tool = GithubRepoReaderTool(github_repo_name=github_repo)
dir_lister_tool = GithubDirectoryListerTool(github_repo_name=github_repo)

# ==========================================
# 3. HIRE YOUR TEAM (AGENTS)
# ==========================================

lead_architect = Agent(
    role='Lead Cloud Architect',
    goal='Analyze the current codebase structure and design the high-level blueprint for a scalable, AI-integrated website application.',
    backstory='You are a seasoned software architect. You excel at reading existing codebase structures and mapping out exactly what frontend and backend technologies are needed to build on top of them.',
    verbose=True,
    allow_delegation=False,
    tools=[repo_reader_tool, dir_lister_tool],
    llm=gemini_llm
)

systems_engineer = Agent(
    role='Cloud Systems Engineer',
    goal='Plan the database structure and cloud hosting setup based on the architect blueprint.',
    backstory='You are a practical, detail-oriented cloud engineer. You focus on databases, security, and making sure the website will not crash if thousands of people use it at once.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

ai_specialist = Agent(
    role='AI Integration Specialist',
    goal='Determine the best way to plug AI features into the website.',
    backstory='You are a cutting-edge AI developer. You know exactly when to use an OpenAI, Claude, or Gemini API, a vector database, or prompt engineering to make a website feel smart.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

ux_designer = Agent(
    role='Lead UX/UI Designer',
    goal='Design simple, clean, and intuitive user flows and interfaces that follow modern patterns for web, iOS, and Android.',
    backstory='You are a master Product Designer obsessed with clean aesthetics and seamless user journeys. You understand exactly how modern apps should feel and look across all devices, prioritizing simplicity over complexity.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

security_agent = Agent(
    role='Security & Compliance Lead',
    goal='Review the architecture, infrastructure, and AI integration for vulnerabilities, data privacy risks (GDPR/HIPAA/CCPA), and prompt injection risks.',
    backstory='You are a paranoid but brilliant Cybersecurity Expert. You look for ways systems can be hacked, how data could leak, and ensure all AI features are safe from malicious manipulation.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

# ==========================================
# 4. ASSIGN THEIR JOBS (TASKS)
# ==========================================

draft_architecture = Task(
    description=f'1. Use your tools to list the files in the root directory of the {github_repo} repository.\n2. Read at least 2 key files (like READMEs, SKILL.md, package.json, or application code) to understand what this project is.\n3. Based on what you learn about the existing codebase AND the following project idea: {{topic}}, create a step-by-step technical blueprint explaining how to integrate the new features into the existing architecture.',
    expected_output='A clear, bulleted blueprint document of the website architecture, explicitly incorporating context from the existing GitHub repository.',
    agent=lead_architect
)

plan_infrastructure = Task(
    description='Review the architecture blueprint. Decide what database to use (like PostgreSQL or MongoDB) and suggest where to host the website (like AWS or Vercel). Explain why.',
    expected_output='A summary of the recommended database and cloud hosting setup.',
    agent=systems_engineer
)

design_ai_features = Task(
    description='Review the architecture and infrastructure plans. Suggest 2 specific ways AI can be integrated into this website to improve the user experience, and explain technically how to build them.',
    expected_output='A short report detailing 2 AI features and the required tools/APIs to build them.',
    agent=ai_specialist
)

audit_security = Task(
    description='Review the proposed architecture, infrastructure, and AI features. Identify the top 3 security or compliance risks (like prompt injection, data leaks, or regulatory issues) and how to mitigate them.',
    expected_output='A security audit report listing 3 major risks, categorized by severity, with clear technical mitigation strategies.',
    agent=security_agent
)

design_user_experience = Task(
    description='Based on the architecture and AI features proposed, map out the 3 core screens the user will interact with (e.g., Landing Page, AI Chat Interface, Search Results). Detail the key UI components on each screen and explain the user flow between them, ensuring it works seamlessly on both mobile (iOS/Android) and web.',
    expected_output='A detailed UX/UI flow document describing the layout, key components, and user interactions for 3 core screens.',
    agent=ux_designer
)

# ==========================================
# 5. START THE WORK (THE CREW)
# ==========================================

architect_crew = Crew(
    agents=[lead_architect, systems_engineer, ai_specialist, ux_designer, security_agent],
    tasks=[draft_architecture, plan_infrastructure, design_ai_features, design_user_experience, audit_security],
    process=Process.sequential 
)

my_website_idea = "A real estate website that helps users find homes by chatting with an AI about their lifestyle, rather than just using search filters."

print("\nStarting the Architect Design Studio...\n")
result = architect_crew.kickoff(inputs={'topic': my_website_idea})

print("\n==========================================")
print("FINAL ARCHITECT REPORT:")
print("==========================================")
print(result)
