import openai
import json
import re
import markdown
from typing import Dict, Any, Optional, List


class OpenAIHelper:
    """Helper class for interacting with OpenAI API"""

    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        """
        Initialize the OpenAI helper

        Args:
            api_key: OpenAI API key
            model: Model to use for text generation
        """
        openai.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None,
                      temp: float = 0.7, max_tokens: int = 4000) -> str:
        """
        Generate text using OpenAI's API

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temp: Temperature for text generation (not used with current model)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=max_tokens
                # Temperature parameter removed as it's not supported
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"OpenAI API Error: {str(e)}")

    def chunk_text(self, text: str, max_chunk_size: int = 15000) -> List[str]:
        """
        Break down large text into smaller chunks

        Args:
            text: The large text to chunk
            max_chunk_size: Maximum size of each chunk in characters

        Returns:
            List of text chunks
        """
        # If text is small enough, return as is
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by paragraphs (respecting natural text boundaries)
        paragraphs = text.split('\n\n')

        for paragraph in paragraphs:
            # If adding this paragraph exceeds the chunk size, start a new chunk
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += '\n\n'
                current_chunk += paragraph

        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def generate_structured_summary(self, transcript: str,
                                    title: str, date: str,
                                    duration: str,
                                    persona_prompt: str = "",
                                    context_prompt: str = "") -> str:
        """
        Generate a structured meeting summary in Markdown format

        Args:
            transcript: Meeting transcript text
            title: Meeting title
            date: Meeting date
            duration: Meeting duration
            persona_prompt: Custom persona instructions for the AI
            context_prompt: Additional context about the meeting

        Returns:
            String containing structured summary in Markdown format
        """
        # Check if transcript is too large
        if len(transcript) > 100000:  # Approximately 25k tokens
            return self.generate_summary_from_large_transcript(
                transcript=transcript,
                title=title,
                date=date,
                duration=duration,
                persona_prompt=persona_prompt,
                context_prompt=context_prompt
            )

        # Base system prompt - conditionally apply persona
        if persona_prompt:
            system_prompt = f"""
            {persona_prompt}

            While maintaining the above persona, your task is to create a comprehensive meeting summary in markdown format.

            Even though you're {persona_prompt}, you still need to follow these format requirements:

            Your output must be structured in exactly the format below with numbered sections 1-11.
            Each section must follow the specified format, but your tone, vocabulary, and style should reflect {persona_prompt}.
            """
        else:
            system_prompt = """
            You are an expert in analyzing and summarizing business meeting transcripts. Your task is to extract key information and create a comprehensive structured summary.
            """

        # Add the common structure requirements
        system_prompt += """
        Your task is to produce a Markdown summary document of the meeting transcript provided. The output **must** use exactly the structure and formatting described here—no more, no fewer sections—so it can be repeated reliably across different calls:
        You MUST analyze the transcript thoroughly and extract specific details - do not provide generic or placeholder responses.


        ## 1. Executive Summary 
        - **Output:** A two paragraph summary that captures the key points, outcomes, and significance of the meeting:
          - **Paragraph 1:** Why we met, the major context, and overall aims. 
          - **Paragraph 2:** Key agreements, tone, and top take-aways. 
        - **Style:** Active voice, plain business language, ~120–150 words per paragraph, no bullet lists.

        ## 2. Participants 
        - **Output:** A three-column Markdown table: 
          | Name | Organization / Title | Meeting Role | 
          - Pull names from every speaker introduction. 
          - Capture the exact "Organization / Title" string if stated; attempt to ascertain accurate Organization/Title for each participant; else use "(Affiliation not stated)". 
          - Derive a concise "Meeting Role" (e.g., "Executive sponsor", "Change-management lead").
          - Ensure that each participant is represented but do not duplicate participants.

        ## 3. Conversation Flow Summary 
        - **Output:** Eight to twelve numbered "scenes" (or adjust to the natural breaks in the transcript). 
          - Each scene gets a `### n · Title` heading (3–5 words). 
          - Under each, write **MINIMUM 3-4 detailed sentences** (this is mandatory) summarizing: main discussion point(s), key participants, and notable tone or reaction. Each scene must have at least 50-75 words to provide sufficient detail. 
          - Keep tense past, third-person, no bullets.
          - The entire conversation flow section should be comprehensive and detailed, as it is the most important part of the summary.
          - For each scene, specifically identify: 1) What specifically was discussed, 2) Who the main speakers were, 3) What perspectives were shared, and 4) How the conversation progressed.

        ## 4. Decisions Made 
        - **Output:** A four-column Markdown table: 
          | # | Decision | Details | Owner(s) | 
          - Extract every firm decision (words like "agreed", "decided", "confirmed"). 
          - "Decision" = 3–7 word noun phrase; "Details" ≤25 words; "Owner(s)" = comma-separated names.

        ## 5. Actions Planned 
        - **Output:** A four-column Markdown table: 
          | Action | Responsible | Timeline | Notes | 
          - Find "action" statements ("we will", "please", "I'll", etc.). 
          - Convert relative dates (e.g. "next week") into calendar dates. 

        ## 6. Open Questions 
        - **Output:** A three-column Markdown table: 
          | Question | Context | Owner | 
          - Identify questions that received no definitive answer in the meeting transcript. 
          - Keep them as direct quotes or close paraphrases.

        ## 7. Risks & Mitigations 
        - **Output:** A four-column Markdown table: 
          | Risk | Impact | Mitigation | Owner | 
          - Capture any "risk", "concern", or "issue" language, pair with nearby mitigation suggestions.

        ## 8. Key Quotes 
        - **Output:** 3-5 block-quoted lines (`> "…"`) of quotes that were of particular importance within the meeting. Prioritize quotes that support the executive summary.
          - IMPORTANT: Do NOT include any quotes from SSA members or employees. Only include quotes from external participants, clients, vendors, or consultants.
          - Each quote should be ≤50 words and must include speaker attribution (e.g. `– Name`).
          - If you cannot find enough important quotes from non-SSA participants, include fewer quotes rather than using quotes from SSA members.
          - Double-check each attribution to ensure it is not from someone affiliated with SSA.

        ## 9. Sentiment Analysis 
        - **Output:** One short paragraph, at least 3 sentences, naming the overall tone (e.g. "constructively optimistic"), the main positive driver (if present), and main concern (if present).

        ## 10. Content Gaps 
        - **Output:** A list of what should have been discussed but wasn't, of what questions should have been asked but weren't, missing topics, missing people, etc. Use your best judgement to identify the missing elements of the meeting. For each content gap include a short description of the gap and potential remediation.

        ## 11. Technical Terminology & Acronyms 
        - **Output:** A two-column Markdown table: 
          | Term | Definition | 
          - Gather all capitalized tokens or acronyms ≥2 characters used ≥2 times. 
          - Provide a one-sentence plain-English definition for each. Use your knowledge to define the terms that are not explicitly detailed in the transcript but add a disclaimer for those.
        """

        # If there's a persona prompt, add a reminder at the end
        if persona_prompt:
            system_prompt += f"""

            IMPORTANT REMINDER: While following these structural requirements, make sure your entire summary reflects {persona_prompt}. Your tone, vocabulary, explanations, and perspective should clearly demonstrate this persona throughout all sections.
            """

        # Construct user prompt
        user_prompt = f"""
        Please analyze and create a comprehensive markdown summary from this meeting transcript.

        MEETING METADATA:
        Title: {title}
        Date: {date}
        Duration: {duration}
        """

        # Add context prompt if provided
        if context_prompt:
            user_prompt += f"""
        MEETING CONTEXT:
        {context_prompt}
        """

        user_prompt += f"""
        MEETING TRANSCRIPT:
        {transcript}

        Provide a thorough, detailed analysis of this specific transcript in Markdown format following the structure in your instructions. Extract actual names, roles, decisions, actions, and quotes from the transcript. Do not provide generic placeholders - if information isn't present, indicate this fact.
        """

        # Add persona reminder to user prompt if provided
        if persona_prompt:
            user_prompt += f"""

        REMEMBER: You must maintain the persona of {persona_prompt} throughout your entire summary, in every section.
        """

        user_prompt += """
        IMPORTANT NOTES: 
        1. For the Conversation Flow Summary section, each scene MUST include at least 3-4 detailed sentences (minimum 50-75 words per scene) with specific information about what was discussed, who spoke, and how the conversation progressed. This level of detail is absolutely required.

        2. For the Key Quotes section, DO NOT include quotes from SSA members or employees. Only select quotes from external participants, clients, vendors, or consultants. If you can't find enough non-SSA quotes, include fewer quotes rather than using any from SSA members.
        """

        try:
            return self.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=4000
            )

        except Exception as e:
            raise Exception(f"Failed to generate summary: {str(e)}")

    def generate_summary_from_large_transcript(self, transcript: str,
                                               title: str, date: str,
                                               duration: str,
                                               persona_prompt: str = "",
                                               context_prompt: str = "") -> str:
        """
        Generate a structured meeting summary from a large transcript
        by breaking it into chunks and returning markdown

        Args:
            transcript: Large meeting transcript text
            title: Meeting title
            date: Meeting date
            duration: Meeting duration
            persona_prompt: Custom persona instructions for the AI
            context_prompt: Additional context about the meeting

        Returns:
            Combined markdown string containing structured summary
        """
        print(f"Processing large transcript of {len(transcript)} characters.")

        # Break transcript into manageable chunks
        chunks = self.chunk_text(transcript, max_chunk_size=7500)  # Even smaller chunks for better processing
        print(f"Split into {len(chunks)} chunks for detailed analysis.")

        # Process each chunk separately
        chunk_analyses = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i + 1} of {len(chunks)}...")

            # Base system prompt for chunk analysis with persona if provided
            if persona_prompt:
                system_prompt = f"""
                {persona_prompt}

                While maintaining this persona, you are analyzing one section of a longer meeting transcript.

                Extract key information from this transcript section including:
                1. A brief summary of the main points discussed in this section (2-3 sentences)
                2. Any participants mentioned with their roles or affiliations
                  - IMPORTANT: Only note organizations or titles that are EXPLICITLY stated in the text
                  - For any participant whose organization or title is not clearly stated, mark as "(Affiliation not stated)"
                  - Clearly mark participants from SSA (the host organization) vs external participants
                3. Key discussion topics (with minimum 3-4 sentences of detail per topic)
                4. Any decisions made
                5. Any actions planned
                6. Any open questions raised
                7. Any risks or concerns mentioned
                8. Notable quotes from participants (clearly indicate which quotes are from non-SSA/external participants)
                9. Any technical terms or acronyms used

                Respond in plain text, organized by the categories above. Be specific and extract actual details from the transcript.
                Your analysis should reflect your persona in tone, vocabulary and style.
                """
            else:
                system_prompt = """
                You are an expert in analyzing business meeting transcripts. You are currently analyzing one section of a longer transcript.

                Extract key information from this transcript section including:
                1. A brief summary of the main points discussed in this section (2-3 sentences)
                2. Any participants mentioned with their roles or affiliations
                  - IMPORTANT: Only note organizations or titles that are EXPLICITLY stated in the text
                  - For any participant whose organization or title is not clearly stated, mark as "(Affiliation not stated)"
                  - Clearly mark participants from SSA (the host organization) vs external participants
                3. Key discussion topics (with minimum 3-4 sentences of detail per topic)
                4. Any decisions made
                5. Any actions planned
                6. Any open questions raised
                7. Any risks or concerns mentioned
                8. Notable quotes from participants (clearly indicate which quotes are from non-SSA/external participants)
                9. Any technical terms or acronyms used

                Respond in plain text, organized by the categories above. Be specific and extract actual details from the transcript.
                """

            # Construct user prompt
            user_prompt = f"""
            This is PART {i + 1} of {len(chunks)} of a meeting transcript titled "{title}" from {date or 'unknown date'} lasting {duration or 'unknown duration'}.
            """

            # Add context prompt if provided
            if context_prompt and i == 0:  # Only add to the first chunk to avoid repetition
                user_prompt += f"""
            MEETING CONTEXT:
            {context_prompt}
            """

            user_prompt += f"""
            Analyze this transcript section thoroughly and extract all relevant information:

            {chunk}

            Provide detailed, specific information from THIS section in an organized format.
            """

            # Add persona reminder if needed
            if persona_prompt:
                user_prompt += f"""

            IMPORTANT: Maintain the persona of {persona_prompt} in your analysis. Your tone, vocabulary, and style should reflect this persona.
            """

            user_prompt += """
            IMPORTANT NOTES:
            1. For participant affiliations, ONLY note organizations or titles that are EXPLICITLY stated in the text.
            2. For any quotes you extract, clearly mark which are from SSA members (the host organization) versus external participants (clients, consultants, vendors, etc.).
            """

            try:
                response = self.generate_text(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    max_tokens=3000
                )
                chunk_analyses.append(response)
            except Exception as e:
                print(f"Error processing chunk {i + 1}: {str(e)}")
                # Continue even if one chunk fails
                continue

        # Now generate a consolidated markdown summary using the chunk analyses
        if persona_prompt:
            consolidation_system_prompt = f"""
            {persona_prompt}

            While maintaining this persona, your task is to create a comprehensive meeting summary in markdown format.

            Even though you're {persona_prompt}, you still need to follow these format requirements:

            Your output must be structured in exactly the format below with numbered sections 1-11.
            Each section must follow the specified format, but your tone, vocabulary, and style should reflect {persona_prompt}.

            You are an expert in analyzing and summarizing business meeting transcripts. Your task is to extract key information and create a comprehensive structured summary.
            """
        else:
            consolidation_system_prompt = """
            You are an expert in analyzing and summarizing business meeting transcripts. Your task is to extract key information and create a comprehensive structured summary.
            """

        consolidation_system_prompt += """
        Your task is to produce a Markdown summary document of the meeting transcript provided. The output **must** use exactly the structure and formatting described here—no more, no fewer sections—so it can be repeated reliably across different calls:
        You MUST analyze the transcript thoroughly and extract specific details - do not provide generic or placeholder responses.


        ## 1. Executive Summary 
        - **Output:** A two paragraph summary that captures the key points, outcomes, and significance of the meeting:
          - **Paragraph 1:** Why we met, the major context, and overall aims. 
          - **Paragraph 2:** Key agreements, tone, and top take-aways. 
        - **Style:** Active voice, plain business language, ~120–150 words per paragraph, no bullet lists.

        ## 2. Participants 
        - **Output:** A three-column Markdown table: 
          | Name | Organization / Title | Meeting Role | 
          - Pull names from every speaker introduction. 
          - Capture the exact "Organization / Title" string if stated; attempt to ascertain accurate Organization/Title for each participant; else use "(Affiliation not stated)". 
          - Derive a concise "Meeting Role" (e.g., "Executive sponsor", "Change-management lead").
          - Ensure that each participant is represented but do not duplicate participants.

        ## 3. Conversation Flow Summary 
        - **Output:** Eight to twelve numbered "scenes" (or adjust to the natural breaks in the transcript). 
          - Each scene gets a `### n · Title` heading (3–5 words). 
          - Under each, write **MINIMUM 3-4 detailed sentences** (this is mandatory) summarizing: main discussion point(s), key participants, and notable tone or reaction. Each scene must have at least 50-75 words to provide sufficient detail. 
          - Keep tense past, third-person, no bullets.
          - The entire conversation flow section should be comprehensive and detailed, as it is the most important part of the summary.
          - For each scene, specifically identify: 1) What specifically was discussed, 2) Who the main speakers were, 3) What perspectives were shared, and 4) How the conversation progressed.

        ## 4. Decisions Made 
        - **Output:** A four-column Markdown table: 
          | # | Decision | Details | Owner(s) | 
          - Extract every firm decision (words like "agreed", "decided", "confirmed"). 
          - "Decision" = 3–7 word noun phrase; "Details" ≤25 words; "Owner(s)" = comma-separated names.

        ## 5. Actions Planned 
        - **Output:** A four-column Markdown table: 
          | Action | Responsible | Timeline | Notes | 
          - Find "action" statements ("we will", "please", "I'll", etc.). 
          - Convert relative dates (e.g. "next week") into calendar dates. 

        ## 6. Open Questions 
        - **Output:** A three-column Markdown table: 
          | Question | Context | Owner | 
          - Identify questions that received no definitive answer in the meeting transcript. 
          - Keep them as direct quotes or close paraphrases.

        ## 7. Risks & Mitigations 
        - **Output:** A four-column Markdown table: 
          | Risk | Impact | Mitigation | Owner | 
          - Capture any "risk", "concern", or "issue" language, pair with nearby mitigation suggestions.

        ## 8. Key Quotes 
        - **Output:** 3-5 block-quoted lines (`> "…"`) of quotes that were of particular importance within the meeting. Prioritize quotes that support the executive summary.
          - IMPORTANT: Do NOT include any quotes from SSA members or employees. Only include quotes from external participants, clients, vendors, or consultants.
          - Each quote should be ≤50 words and must include speaker attribution (e.g. `– Name`).
          - If you cannot find enough important quotes from non-SSA participants, include fewer quotes rather than using quotes from SSA members.
          - Double-check each attribution to ensure it is not from someone affiliated with SSA.

        ## 9. Sentiment Analysis 
        - **Output:** One short paragraph, at least 3 sentences, naming the overall tone (e.g. "constructively optimistic"), the main positive driver (if present), and main concern (if present).

        ## 10. Content Gaps 
        - **Output:** A list of what should have been discussed but wasn't, of what questions should have been asked but weren't, missing topics, missing people, etc. Use your best judgement to identify the missing elements of the meeting. For each content gap include a short description of the gap and potential remediation.

        ## 11. Technical Terminology & Acronyms 
        - **Output:** A two-column Markdown table: 
          | Term | Definition | 
          - Gather all capitalized tokens or acronyms ≥2 characters used ≥2 times. 
          - Provide a one-sentence plain-English definition for each. Use your knowledge to define the terms that are not explicitly detailed in the transcript but add a disclaimer for those.
        """

        # If there's a persona prompt, add a reminder at the end
        if persona_prompt:
            consolidation_system_prompt += f"""

            IMPORTANT REMINDER: While following these structural requirements, make sure your entire summary reflects {persona_prompt}. Your tone, vocabulary, explanations, and perspective should clearly demonstrate this persona throughout all sections.
            """

        # Create a consolidated prompt with the chunk analyses
        separator = "=" * 50
        chunk_analyses_text = separator.join(chunk_analyses)

        consolidation_user_prompt = f"""
        Create a comprehensive markdown summary of a meeting titled "{title}" that took place on {date or 'unknown date'} lasting {duration or 'unknown duration'}.
        """

        # Add context prompt if provided
        if context_prompt:
            consolidation_user_prompt += f"""
        MEETING CONTEXT:
        {context_prompt}
        """

        consolidation_user_prompt += f"""
        Below are analyses of different chunks of the meeting transcript. Please consolidate these into a single coherent summary following the markdown structure in your instructions.

        CHUNK ANALYSES:
        {separator}
        {chunk_analyses_text}
        {separator}

        Create a well-structured markdown summary that captures the key elements from all these analyses, eliminating duplications and organizing the information logically.
        """

        # Add persona reminder to user prompt if provided
        if persona_prompt:
            consolidation_user_prompt += f"""

        REMEMBER: You must maintain the persona of {persona_prompt} throughout your entire summary, in every section. Your vocabulary, tone, and style should clearly reflect this persona while still following the required structure.
        """

        consolidation_user_prompt += """
        IMPORTANT NOTES: 
        1. For the Conversation Flow Summary section, each scene MUST include at least 3-4 detailed sentences (minimum 50-75 words per scene) with specific information about what was discussed, who spoke, and how the conversation progressed. This level of detail is absolutely required.

        2. For the Key Quotes section, DO NOT include quotes from SSA members or employees. Only select quotes from external participants, clients, vendors, or consultants. If you can't find enough non-SSA quotes, include fewer quotes rather than using any from SSA members.
        """

        try:
            consolidated_summary = self.generate_text(
                prompt=consolidation_user_prompt,
                system_prompt=consolidation_system_prompt,
                max_tokens=4000
            )
            print("Large transcript processing complete.")
            return consolidated_summary

        except Exception as e:
            print(f"Error generating consolidated summary: {str(e)}")
            # Create a simple fallback summary
            fallback_summary = f"""
## 1. Executive Summary

This meeting titled '{title}' faced technical processing challenges. The transcript was too large for complete analysis and some information may be missing.

Despite processing limitations, a partial summary is provided below. It's recommended to review the original transcript for complete understanding of all discussed topics.

## 2. Participants

| Name | Organization / Title | Meeting Role |
|------|---------------------|--------------|
| (Unable to extract complete participant list due to processing limitations) | | |

## 3. Conversation Flow Summary

### 1 · Meeting overview

The meeting covered multiple topics that could not be fully processed due to the large transcript size.

## 4. Decisions Made

| # | Decision | Details | Owner(s) |
|---|----------|---------|----------|
| 1 | Review transcript manually | The system was unable to fully process this large transcript | All participants |

## 5. Actions Planned

| Action | Responsible | Timeline | Notes |
|--------|------------|----------|-------|
| Review original transcript | All participants | As soon as possible | Due to processing limitations |

## 9. Sentiment Analysis

The sentiment analysis could not be completed due to processing limitations with this large transcript.

## 10. Content Gaps

- Complete analysis of the transcript
- Detailed extraction of all meeting elements

## 11. Technical Terminology & Acronyms

| Term | Definition |
|------|------------|
| N/A | No terminology could be reliably extracted due to processing limitations |
"""
            return fallback_summary