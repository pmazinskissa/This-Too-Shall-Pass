from typing import Dict, Any, List, Optional
from utils.openai_helper import OpenAIHelper
import re


class SummaryGenerator:
    """Generate structured meeting summaries from transcripts"""

    def __init__(self, openai_helper: OpenAIHelper):
        """
        Initialize the summary generator

        Args:
            openai_helper: Instance of OpenAIHelper for API interactions
        """
        self.openai_helper = openai_helper

    def generate(self, transcript: str, title: str = "",
                 date: str = "", duration: str = "",
                 persona_prompt: str = "", context_prompt: str = "") -> Dict[str, Any]:
        """
        Generate a structured meeting summary from a transcript

        Args:
            transcript: The meeting transcript text
            title: Meeting title
            date: Meeting date
            duration: Meeting duration
            persona_prompt: Custom persona instructions for the AI
            context_prompt: Additional context about the meeting

        Returns:
            Dictionary containing all summary sections
        """
        # Use OpenAI to generate markdown summary
        markdown_summary = self.openai_helper.generate_structured_summary(
            transcript=transcript,
            title=title,
            date=date,
            duration=duration,
            persona_prompt=persona_prompt,
            context_prompt=context_prompt
        )

        # Clean up any markdown formatting markers
        markdown_summary = self._clean_markdown_formatting(markdown_summary)

        # Extract and structure the markdown sections into a dictionary for compatibility
        processed_summary = self._extract_sections_from_markdown(markdown_summary)

        # Store the original markdown for export
        processed_summary['markdown'] = markdown_summary

        return processed_summary

    def _clean_markdown_formatting(self, text: str) -> str:
        """
        Clean up markdown formatting markers like triple backticks with language identifiers

        Args:
            text: The markdown text to clean

        Returns:
            Cleaned markdown text
        """
        # Strip any leading/trailing whitespace
        text = text.strip()

        # Remove opening markdown fence with any language identifier
        if text.startswith("```"):
            # Find the first real content line after the fence
            match = re.search(r'```.*?\n(.*)', text, re.DOTALL)
            if match:
                text = match.group(1)

        # Remove closing markdown fence if it exists
        if text.endswith("```"):
            # Find the last real content before the closing fence
            last_fence_pos = text.rfind("```")
            if last_fence_pos > 0:
                # Look for the last newline before the closing fence
                last_newline = text.rfind("\n", 0, last_fence_pos)
                if last_newline > 0:
                    text = text[:last_newline]

        # If there are any remaining standalone fences in the text (not part of proper code blocks)
        # This is a more aggressive approach and should be used carefully
        lines = text.split("\n")
        clean_lines = []

        in_code_block = False
        for line in lines:
            # Skip standalone backtick lines or language identifier lines
            if line.strip() == "```" or re.match(r'^```\w+$', line.strip()):
                in_code_block = not in_code_block
                continue

            clean_lines.append(line)

        return "\n".join(clean_lines)

    def _extract_sections_from_markdown(self, markdown_text: str) -> Dict[str, Any]:
        """
        Extract structured data from markdown text for template rendering

        Args:
            markdown_text: The markdown summary text

        Returns:
            Dictionary with structured data extracted from markdown
        """
        sections = {
            "executive_summary": "",
            "participants": [],
            "detailed_summary": [],  # This will contain the conversation flow
            "decisions_made": [],
            "actions_planned": [],
            "open_questions": [],
            "risks_mitigations": [],
            "key_quotes": [],
            "sentiment_analysis": "",
            "content_gaps": [],
            "terminology": []
        }

        # Split the markdown by section headers
        section_pattern = r'##\s+\d+\.\s+(.*?)\n(.*?)(?=##\s+\d+\.|$)'
        section_matches = re.findall(section_pattern, markdown_text, re.DOTALL)

        for section_title, section_content in section_matches:
            section_title = section_title.strip()
            section_content = section_content.strip()

            # Process each section based on its title
            if "Executive Summary" in section_title:
                sections["executive_summary"] = section_content

            elif "Participants" in section_title:
                # Extract table rows
                table_pattern = r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|'
                participants = re.findall(table_pattern, section_content)
                # Skip the header row if present
                for i, (name, org, role) in enumerate(participants):
                    if i == 0 and (name.strip() == "Name" or "---" in name):
                        continue
                    sections["participants"].append({
                        "name": name.strip(),
                        "organization": org.strip(),
                        "role": role.strip()
                    })

            elif "Conversation Flow" in section_title:
                # Extract subsections (scenes)
                scene_pattern = r'###\s+(\d+)\s+·\s+(.*?)\n(.*?)(?=###\s+\d+|$)'
                scenes = re.findall(scene_pattern, section_content, re.DOTALL)
                for num, title, content in scenes:
                    sections["detailed_summary"].append({
                        "title": f"{num}. {title.strip()}",
                        "content": content.strip()
                    })

            elif "Decisions Made" in section_title:
                # Extract table rows
                table_pattern = r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|'
                decisions = re.findall(table_pattern, section_content)
                # Skip the header row if present
                for i, (num, decision, details, owner) in enumerate(decisions):
                    if i == 0 and (num.strip() == "#" or "---" in num):
                        continue
                    sections["decisions_made"].append({
                        "decision": decision.strip(),
                        "details": details.strip(),
                        "owner": owner.strip()
                    })

            elif "Actions Planned" in section_title:
                # Extract table rows
                table_pattern = r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|'
                actions = re.findall(table_pattern, section_content)
                # Skip the header row if present
                for i, (action, responsible, timeline, notes) in enumerate(actions):
                    if i == 0 and (action.strip() == "Action" or "---" in action):
                        continue
                    sections["actions_planned"].append({
                        "action": action.strip(),
                        "responsible": responsible.strip(),
                        "timeline": timeline.strip(),
                        "notes": notes.strip()
                    })

            elif "Open Questions" in section_title:
                # Extract table rows
                table_pattern = r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|'
                questions = re.findall(table_pattern, section_content)
                # Skip the header row if present
                for i, (question, context, owner) in enumerate(questions):
                    if i == 0 and (question.strip() == "Question" or "---" in question):
                        continue
                    sections["open_questions"].append({
                        "question": question.strip(),
                        "context": context.strip(),
                        "owner": owner.strip()
                    })

            elif "Risks & Mitigations" in section_title:
                # Extract table rows
                table_pattern = r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|'
                risks = re.findall(table_pattern, section_content)
                # Skip the header row if present
                for i, (risk, impact, mitigation, owner) in enumerate(risks):
                    if i == 0 and (risk.strip() == "Risk" or "---" in risk):
                        continue
                    sections["risks_mitigations"].append({
                        "risk": risk.strip(),
                        "impact": impact.strip(),
                        "mitigation": mitigation.strip(),
                        "owner": owner.strip()
                    })

            elif "Key Quotes" in section_title:
                # Extract blockquotes
                quote_pattern = r'>\s*"(.*?)"\s*–\s*(.*?)(?=\n>|\n\n|$)'
                quotes = re.findall(quote_pattern, section_content)
                for quote_text, attribution in quotes:
                    sections["key_quotes"].append({
                        "quote": quote_text.strip(),
                        "attribution": attribution.strip()
                    })

            elif "Sentiment Analysis" in section_title:
                sections["sentiment_analysis"] = section_content

            elif "Content Gaps" in section_title:
                # Extract bullet points
                bullet_pattern = r'-\s*(.*?)(?=\n-|\n\n|$)'
                gaps = re.findall(bullet_pattern, section_content)
                sections["content_gaps"] = [gap.strip() for gap in gaps]

            elif "Technical Terminology" in section_title or "Acronyms" in section_title:
                # Extract table rows
                table_pattern = r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|'
                terms = re.findall(table_pattern, section_content)
                # Skip the header row if present
                for i, (term, definition) in enumerate(terms):
                    if i == 0 and (term.strip() == "Term" or "---" in term):
                        continue
                    sections["terminology"].append({
                        "term": term.strip(),
                        "definition": definition.strip()
                    })

        return sections