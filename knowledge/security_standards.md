# Security & Compliance Baseline Standards

**Primary Directive for Architecture Design:**
Trust no input. Encrypt everything in transit and at rest.

## 1. Zero Trust AI Architecture
*   **Prompt Isolation:** The system must strictly separate user input from system prompts. Under no circumstances should raw user input be passed directly to an LLM without an intermediating "sanitation" step or clear delineations in the prompt structure (e.g., `<user_input>` XML tags) to prevent Prompt Injection.
*   **Database Access:** AI Agents and LLMs must never have direct SQL or Document Database write access. All data interactions must go through a tightly scoped API layer with strict Rate Limiting and Parameter Validation.

## 2. PII (Personally Identifiable Information) Handling
*   **Data Minimization:** The application must only collect data absolutely necessary for the real estate matching feature. 
*   **Anonymization Before AI:** Before any chat history or user profile is sent to an external API (like Claude or OpenAI) for summarization or analysis, all PII (Names, Phone Numbers, Exact Addresses) must be scrubbed or replaced with generic tokens by a local service.
*   **Storage Compliance:** All user profiles and conversation histories must be stored in databases encrypted at rest using AES-256. The architecture must account for GDPR/CCPA "Right to be Forgotten" implementation.

## 3. Infrastructure Security
*   **VPC Isolation:** All backend compute (Containers, Functions) and databases must reside in private subnets without direct internet access.
*   **API Gateway:** Public access must only be granted through an API Gateway equipped with a Web Application Firewall (WAF) to block DDoS and OWASP Top 10 attacks.
