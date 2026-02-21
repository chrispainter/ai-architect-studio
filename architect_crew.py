import os
from crewai import Agent, Task, Crew, Process, LLM

# Ask for the API key if it isn't already set in the environment.
# This makes it easy to just run the script and paste the key!
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    api_key = input("Please enter your GOOGLE_API_KEY (it will not be saved): ").strip()
    os.environ["GOOGLE_API_KEY"] = api_key

# Initialize the Gemini model
# We are telling the agents to use Gemini Pro to do their thinking
gemini_llm = LLM(
    model="gemini/gemini-2.5-pro", 
    temperature=0.4, # A lower temperature keeps the architect grounded and focused on facts
    api_key=api_key
)

# ==========================================
# 2. HIRE YOUR TEAM (AGENTS)
# ==========================================

lead_architect = Agent(
    role='Lead Cloud Architect',
    goal='Design the high-level blueprint for a scalable, AI-integrated website application.',
    backstory='You are a seasoned software architect. You excel at listening to a user concept and mapping out exactly what frontend and backend technologies are needed to build it.',
    verbose=True,
    allow_delegation=False,
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

security_agent = Agent(
    role='Security & Compliance Lead',
    goal='Review the architecture, infrastructure, and AI integration for vulnerabilities, data privacy risks (GDPR/HIPAA/CCPA), and prompt injection risks.',
    backstory='You are a paranoid but brilliant Cybersecurity Expert. You look for ways systems can be hacked, how data could leak, and ensure all AI features are safe from malicious manipulation.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

# ==========================================
# 3. ASSIGN THEIR JOBS (TASKS)
# ==========================================

draft_architecture = Task(
    description='Analyze the following project idea: {topic}. Create a step-by-step technical blueprint explaining what programming languages and frameworks should be used to build it.',
    expected_output='A clear, bulleted blueprint document of the website architecture.',
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

# ==========================================
# 4. START THE WORK (THE CREW)
# ==========================================

architect_crew = Crew(
    agents=[lead_architect, systems_engineer, ai_specialist, security_agent],
    tasks=[draft_architecture, plan_infrastructure, design_ai_features, audit_security],
    process=Process.sequential 
)

my_website_idea = "A real estate website that helps users find homes by chatting with an AI about their lifestyle, rather than just using search filters."

print("\nStarting the Architect Design Studio...\n")
result = architect_crew.kickoff(inputs={'topic': my_website_idea})

print("\n==========================================")
print("FINAL ARCHITECT REPORT:")
print("==========================================")
print(result)
