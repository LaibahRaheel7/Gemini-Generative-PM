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
        self.parser_model = genai.GenerativeModel('gemini-3-flash-preview')
        self.chat_model = genai.GenerativeModel('gemini-3-flash-preview')
        # Use same model as parser to avoid Pro quota limits on free tier (429 on gemini-3-pro)
        self.pdf_model = self.parser_model
    
    def parse_requirements(
        self,
        requirements_text: str,
        resources: List[Resource],
        document_text: Optional[str] = None,
        project_id: str = "P1",
    ) -> Dict[str, Any]:
        """
        Parses requirements into a feature-based breakdown with PM-style strategy
        (portal-first vs feature-first) and detailed timeline per feature.
        Returns a dict: strategy, feature_breakdown, tasks (list of task dicts).
        """
        resource_list = ", ".join([f"{r.id} ({r.name} - {r.role})" for r in resources])

        source_text = requirements_text
        source_type = "user-provided description"
        if document_text and len(document_text.strip()) > 100:
            source_text = document_text
            source_type = "uploaded document"
        if document_text and requirements_text and len(requirements_text.strip()) > 20:
            source_text = f"**Manual Description:**\n{requirements_text}\n\n**Document Content:**\n{document_text}"
            source_type = "combined sources"

        prompt = f"""You are a senior Technical PM aligning resources and planning delivery. Think like a PM: decide whether to execute by **portal/section** or by **feature/flow**, then produce a detailed feature-based breakdown with time per feature and per task.

**Source:** {source_type}

**Project Requirements:**
{source_text}

**Available Team Members:**
{resource_list}

——— YOUR THINKING (PM DECISION) ———
1. **Identify structure:** Does the project have clear **portals** (e.g. Admin Portal, Client Portal, Public Site) or **flows** (e.g. Auth, Onboarding, Reporting) or both? List them.
2. **Choose approach (and justify in strategy.rationale):**
   - **portal_first:** Complete one portal/section end-to-end (all its features and flows) before moving to the next. Choose when: portals are independent, different teams own different portals, or you want early delivery of one full product slice.
   - **feature_first:** Complete one feature/flow across all portals (e.g. "Auth" everywhere, then "Dashboard" everywhere). Choose when: shared components matter, one tech lead owns a flow, or you want to minimize context switching and reuse.
3. **Feature breakdown:** For each feature or portal (depending on approach), list:
   - name, short description
   - total_hours (sum of its task durations)
   - order (1, 2, 3 …) in the timeline
   - task IDs that belong to it
4. **Tasks:** Create concrete tasks (id, name, duration_hours, dependencies, assigned_to from team, priority 1–5, complexity low/medium/high, required_skillset, **feature** = parent feature/portal name). Use 6h effective day and +20% buffer where appropriate. Dependencies must respect the chosen approach (portal or feature order).

**Output (valid JSON only, no markdown):**
{{
  "strategy": {{
    "approach": "portal_first" | "feature_first",
    "rationale": "2–4 sentences: why this approach fits this project and team (like a PM explaining to a stakeholder).",
    "summary": "One-line summary, e.g. 'Complete Admin Portal first, then Client Portal.'"
  }},
  "feature_breakdown": [
    {{
      "feature_name": "string",
      "description": "string",
      "total_hours": number,
      "order": number,
      "task_ids": ["T1", "T2"],
      "phase": "optional phase name e.g. Foundation, MVP, Phase 2"
    }}
  ],
  "tasks": [
    {{
      "id": "T1",
      "name": "string",
      "duration_hours": number,
      "dependencies": [],
      "assigned_to": "resource_id or null",
      "priority": 1,
      "complexity": "low|medium|high",
      "required_skillset": "string or null",
      "feature": "parent feature name from feature_breakdown"
    }}
  ]
}}

Return ONLY the JSON object, no additional text."""

        try:
            response = self.parser_model.generate_content(prompt)
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            data = json.loads(response_text)
            # Normalize: ensure strategy and feature_breakdown exist
            if "strategy" not in data:
                data["strategy"] = {"approach": "feature_first", "rationale": "", "summary": ""}
            if "feature_breakdown" not in data:
                data["feature_breakdown"] = []
            if "tasks" not in data:
                data["tasks"] = []
            return data
        except Exception as e:
            raise Exception(f"Failed to parse requirements: {str(e)}")

    def extract_project_brief(self, pdf_text: str) -> Dict[str, Any]:
        """
        Parse a PDF project brief: extract features, infer team/project structure,
        and produce a feature-driven timeline with developer-realistic task estimates.
        """
        prompt = """
You are an expert Technical Program Manager and Lead Engineer. Your job is to:
1) Extract the **features** the team must deliver and use them to drive the timeline.
2) Infer **project structure** (phases, MVP vs later, milestones) and **team context** (roles, capacity, constraints) from the document.
3) Assign an **appropriate timeline** per feature and per task based on that structure and team situation.
4) Apply "Developer Reality" to every estimate so timelines are executable, not optimistic.

——— STEP 1: FEATURE EXTRACTION ———
- Identify every **deliverable feature** (user-facing or technical): e.g. "User auth", "Dashboard", "API v1", "Admin panel".
- For each feature: name, 1–2 sentence description, business priority (High/Medium/Low), and suggested **delivery order** (what must come first for dependencies or MVP).
- Group tasks under features so the timeline is **feature-driven**, not a flat list.

——— STEP 2: PROJECT & TEAM CONTEXT ———
- From the document, infer: stated deadlines, team size or roles, tech stack, external dependencies, risk areas (e.g. "waiting on design", "third-party API").
- Assume a **realistic team situation**: mixed experience, meetings/overhead, and handoffs. If the doc mentions specific roles (e.g. "2 backend, 1 frontend"), use that to balance work and timeline.
- If no team is specified, assume a small cross-functional team and assign required_skillset per task (Backend, Frontend, Full-Stack, DevOps, Design, QA, etc.) so a scheduler can assign real people later.

——— STEP 3: DEVELOPER REALITY (APPLY TO ALL ESTIMATES) ———
- **6-Hour Rule:** Count only 6 hours of effective focus time per person per day (meetings, context switch, breaks).
- **Bug & Edge-Case Buffer:** Add +20% to implementation estimates for debugging, edge cases, and rework.
- **Context Switching:** If a task uses a different tech or skill than the previous one, add a small ramp (e.g. +1–2 hours for first task in that area).
- **Uncertainty:** For vague or high-risk items, use "high" complexity and higher hours; for clear, scoped work, use "low" or "medium".

——— STEP 4: TIMELINE FROM FEATURES ———
- Order **features** by dependency and priority (e.g. Auth → Dashboard → Reports).
- For each feature, break it into **concrete tasks** with: name, required_skillset, estimated_hours (after buffers), dependencies (by task name or logical order), and priority.
- Derive **project_deadline** from: (a) any explicit date in the doc, or (b) sum of feature timelines with buffers; if neither is possible, set project_deadline to null.
- **estimated_man_hours** must equal the sum of all task estimated_hours (already buffered).

——— DOCUMENT ———
"""
        prompt += pdf_text[:120000]  # cap input size
        prompt += """

——— OUTPUT (valid JSON only, no markdown) ———
{
  "project_name": "string or null",
  "baseline_requirements": "string summary of key requirements and constraints",
  "estimated_man_hours": number (sum of all task estimated_hours),
  "project_deadline": "YYYY-MM-DD or null",
  "features": [
    {
      "name": "Feature name",
      "description": "short description",
      "priority": "High" | "Medium" | "Low",
      "delivery_order": number (1 = first to deliver),
      "suggested_weeks": number or null
    }
  ],
  "tasks": [
    {
      "name": "Task name",
      "priority": "High" | "Medium" | "Low",
      "required_skillset": "e.g. Backend, Frontend, DevOps",
      "estimated_hours": number (with 6h rule and +20% buffer already applied),
      "dependencies": ["task name"] or [],
      "feature": "parent feature name (optional)"
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
