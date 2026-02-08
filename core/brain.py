import os
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from core.models import Task, Resource

class GeminiBrain:
    """
    The Intelligence Layer - Uses Google Gemini to understand natural language
    and convert it into structured data for the scheduler.
    """
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.parser_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.chat_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        try:
            self.pdf_model = genai.GenerativeModel('gemini-2.5-pro')
        except Exception:
            self.pdf_model = self.parser_model
    
    def parse_requirements(
        self, 
        requirements_text: str, 
        resources: List[Resource],
        document_text: Optional[str] = None,
        project_id: str = "P1"
    ) -> List[Task]:
        """
        Takes unstructured project requirements and returns structured tasks.
        
        This is where the "magic" happens - Gemini converts human language
        into precise, machine-readable task definitions.
        
        Args:
            requirements_text: Manual text description of requirements
            resources: Available team members
            document_text: Optional extracted text from uploaded document
            project_id: ID of the project these tasks belong to
            
        Returns:
            List of Task objects
        """
        
        resource_list = ", ".join([f"{r.id} ({r.name} - {r.role})" for r in resources])
        
        # Determine which source to use
        source_text = requirements_text
        source_type = "user-provided description"
        
        if document_text and len(document_text.strip()) > 100:
            # Prefer document if it has substantial content
            source_text = document_text
            source_type = "uploaded document"
        
        # If both exist, combine them
        if document_text and requirements_text and len(requirements_text.strip()) > 20:
            source_text = f"**Manual Description:**\n{requirements_text}\n\n**Document Content:**\n{document_text}"
            source_type = "combined sources"
        
        prompt = f"""You are a senior project manager analyzing requirements from {source_type}. Convert the following into a structured list of tasks.

**Source:** {source_type}

**Project Requirements:**
{source_text}

**Available Team Members:**
{resource_list}

**Instructions:**
1. **Extract Project Metadata:** If present in the document, identify:
   - Project timeline/deadlines
   - Key stakeholders
   - Budget constraints
   - Technical requirements
   
2. **Break Down Into Tasks:** Create discrete, actionable tasks from:
   - Requirements sections
   - Technical specifications
   - Features described
   - Deliverables mentioned
   
3. **Task Properties:**
   - Assign unique ID (T1, T2, T3, etc.)
   - Estimate duration in hours (4-8 hours/day max per person)
   - Set complexity: "low", "medium", or "high"
   - Identify dependencies (which tasks must finish first)
   - Assign to team members based on roles
   - Set priority (1-5, where 1 is highest)

4. **Complexity Guidelines:**
   - **Low:** Simple, well-defined tasks with minimal unknowns
   - **Medium:** Standard tasks requiring some problem-solving
   - **High:** Complex tasks with significant technical challenges

**Output Format (JSON only, no markdown):**
Return a valid JSON array of task objects. Each task must have:
- id: string (e.g., "T1")
- name: string (clear, actionable task name)
- duration_hours: integer (realistic estimate)
- dependencies: array of task IDs (e.g., ["T1", "T2"])
- assigned_to: string (resource ID) or null
- priority: integer (1-5)
- complexity: string ("low", "medium", or "high")

```json
[
  {{
    "id": "T1",
    "name": "Task name",
    "duration_hours": 8,
    "dependencies": [],
    "assigned_to": "resource_id",
    "priority": 1
  }}
]
```

Return ONLY the JSON array, no additional text."""

        try:
            response = self.parser_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up the response (remove markdown code blocks if present)
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            tasks_data = json.loads(response_text)
            
            # Convert to Task objects
            tasks = [Task(**task_dict) for task_dict in tasks_data]
            
            return tasks
            
        except Exception as e:
            raise Exception(f"Failed to parse requirements: {str(e)}")

    def extract_project_brief(self, pdf_text: str) -> Dict[str, Any]:
        """
        Parse a PDF project brief with Gemini 2.5 Pro and return structured JSON:
        - tasks: list of { name, priority, required_skillset }
        - baseline_requirements: str
        - estimated_man_hours: int
        - project_deadline: str (YYYY-MM-DD)
        - project_name: str (optional)
        """
        prompt = """You are a senior project manager. Extract structured data from this project brief.

**Document text:**
"""
        prompt += pdf_text[:120000]  # cap input size
        prompt += """

**Output (valid JSON only, no markdown):**
{
  "project_name": "string or null",
  "baseline_requirements": "string summary of key requirements",
  "estimated_man_hours": number (total estimated person-hours),
  "project_deadline": "YYYY-MM-DD or null",
  "tasks": [
    {
      "name": "Task name",
      "priority": "High" | "Medium" | "Low",
      "required_skillset": "e.g. Backend, Frontend, DevOps",
      "estimated_hours": number,
      "dependencies": ["task name or id if mentioned"] or []
    }
  ]
}

Return ONLY the JSON object, no other text."""

        try:
            response = self.pdf_model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            return json.loads(text)
        except Exception as e:
            raise Exception(f"PDF brief extraction failed: {str(e)}")

    def interpret_chat(self, user_message: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interprets natural language updates and converts them to state modifications.
        
        Examples:
        - "John is sick tomorrow" -> Update John's availability
        - "Add a new task for database setup" -> Create new task
        - "Task T3 is taking longer" -> Update duration
        """
        
        prompt = f"""You are a project management assistant. The user wants to update the project.

**Current Project State:**
```json
{json.dumps(current_state, indent=2)}
```

**User Request:**
{user_message}

**Your Task:**
Interpret the request and return a JSON object with ONE of these actions:

1. Add a task:
{{
  "action": "add_task",
  "task": {{
    "id": "T_new",
    "name": "Task name",
    "duration_hours": 8,
    "dependencies": [],
    "assigned_to": "resource_id",
    "priority": 1
  }}
}}

2. Update a task:
{{
  "action": "update_task",
  "task_id": "T1",
  "updates": {{
    "duration_hours": 16
  }}
}}

3. Remove a task:
{{
  "action": "remove_task",
  "task_id": "T1"
}}

4. Add a resource:
{{
  "action": "add_resource",
  "resource": {{
    "id": "R_new",
    "name": "Person Name",
    "role": "Role"
  }}
}}

5. Conversational response (if request is unclear):
{{
  "action": "clarify",
  "message": "I need more information about..."
}}

Return ONLY the JSON object, no additional text."""

        try:
            response = self.chat_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up markdown
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            action = json.loads(response_text)
            return action
            
        except Exception as e:
            return {
                "action": "clarify",
                "message": f"I couldn't understand that request. Error: {str(e)}"
            }
    
    def generate_summary(self, schedule: List[Dict]) -> str:
        """
        Generates a natural language summary of the project schedule.
        """
        
        prompt = f"""You are a project manager. Summarize this project schedule in 2-3 sentences for stakeholders.

**Schedule:**
```json
{json.dumps(schedule, indent=2)}
```

Focus on:
- Project duration
- Key milestones
- Resource allocation
- Any potential bottlenecks

Keep it concise and executive-friendly."""

        try:
            response = self.chat_model.generate_content(prompt)
            return response.text.strip()
        except:
            return "Schedule generated successfully."
