import streamlit as st
import json
import re
from typing import Dict, List, Any, Optional
import requests
import os
os.environ["GEMINI_API_KEY"] = "AIzaSyDvQq3Oy473VEX9qj7UiqIoTR70uIhD_2w"

class GradingService:
    """Service for grading assignments using Google Gemini API"""

    def __init__(self):
        """Initialize the grading service with Google Gemini API"""
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

        if not self.api_key:
            st.warning("Gemini API key not found in environment variables")

    def grade_assignment(self, text_content: str, total_marks: int,
                         custom_criteria: Dict[str, int], additional_instructions: str,
                         detect_multiple_questions: bool = True) -> Dict[str, Any]:
        """
        Grade an assignment using DeepSeek AI

        Args:
            text_content: The extracted text from the assignment
            total_marks: Total marks available for the assignment
            custom_criteria: Dictionary of custom grading criteria and their marks
            additional_instructions: Additional context for grading
            detect_multiple_questions: Whether to detect and grade multiple questions

        Returns:
            Dictionary containing grading results and feedback
        """
        try:
            if not self.api_key:
                return self._create_error_result("Gemini API key not configured")

            # Prepare the grading prompt
            prompt = self._create_grading_prompt(
                text_content, total_marks, custom_criteria,
                additional_instructions, detect_multiple_questions
            )

            # Make API request to Gemini
            response = self._call_gemini_api(prompt)

            if response:
                return self._parse_grading_response(response, total_marks, custom_criteria)
            else:
                return self._create_error_result("Failed to get response from Gemini AI")

        except Exception as e:
            st.error(f"Error during grading: {str(e)}")
            return self._create_error_result(str(e))

    def _create_grading_prompt(self, text_content: str, total_marks: int,
                               custom_criteria: Dict[str, int], additional_instructions: str,
                               detect_multiple_questions: bool) -> str:
        """Create a comprehensive prompt for the AI grading system"""

        prompt = f"""You are an expert academic grader. Your task is to grade the following assignment/exam submission fairly and provide detailed, constructive feedback.

ASSIGNMENT CONTENT TO GRADE:
{text_content}

GRADING PARAMETERS:
- Total Marks Available: {total_marks}
- Detect Multiple Questions: {detect_multiple_questions}

"""

        # Add custom criteria if provided
        if custom_criteria:
            prompt += "CUSTOM GRADING CRITERIA:\n"
            for criterion, marks in custom_criteria.items():
                prompt += f"- {criterion}: {marks} marks\n"
            prompt += "\n"

        # Add additional instructions
        if additional_instructions:
            prompt += f"ADDITIONAL GRADING INSTRUCTIONS:\n{additional_instructions}\n\n"

        # Add specific instructions for multiple questions
        if detect_multiple_questions:
            prompt += """MULTIPLE QUESTIONS DETECTION:
Please identify if there are multiple distinct questions or parts in this submission. If so, grade each question/part separately.

"""

        # Add response format instructions
        prompt += """RESPONSE FORMAT:
Please respond with a JSON object containing the following structure:

{
    "total_score": <numerical score out of total marks>,
    "percentage": <percentage score>,
    "overall_feedback": "<comprehensive feedback explaining the grade>",
    "strengths": ["<list of strengths identified>"],
    "areas_for_improvement": ["<list of areas needing improvement>"],
    "criteria_scores": {
        "<criterion_name>": <score for this criterion>
    },
    "questions": [
        {
            "question_number": <number>,
            "question_text": "<brief description of the question>",
            "score": <score for this question>,
            "max_score": <maximum possible score>,
            "feedback": "<specific feedback for this question>"
        }
    ],
    "grade_justification": "<detailed explanation of how the grade was determined>"
}

GRADING GUIDELINES:
1. Be fair and consistent in your evaluation
2. Provide specific, actionable feedback
3. Consider the context and level of the assignment
4. Look for understanding of concepts, not just correct answers
5. Award partial credit where appropriate
6. Be constructive in your criticism
7. Highlight both strengths and areas for improvement

Please ensure your response is valid JSON format."""

        return prompt

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Make API call to Gemini"""
        try:
            headers = {
                "Content-Type": "application/json"
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"You are an expert academic grader. Always respond with valid JSON format as requested.\n\n{prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 2000
                }
            }

            url = f"{self.base_url}?key={self.api_key}"

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()
                candidates = response_data.get('candidates', [])
                if candidates and 'content' in candidates[0]:
                    parts = candidates[0]['content'].get('parts', [])
                    if parts and 'text' in parts[0]:
                        return parts[0]['text']
                return None
            else:
                st.error(f"Gemini API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            st.error(f"Network error calling Gemini API: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Unexpected error calling Gemini API: {str(e)}")
            return None

    def _parse_grading_response(self, response: str, total_marks: int,
                                custom_criteria: Dict[str, int]) -> Dict[str, Any]:
        """Parse the JSON response from DeepSeek AI"""
        try:
            # Clean the response to extract JSON
            response = response.strip()

            # Find JSON content (sometimes wrapped in markdown code blocks)
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_content = response[json_start:json_end]
                else:
                    json_content = response

            # Parse JSON
            grading_data = json.loads(json_content)

            # Validate and normalize the response
            normalized_result = {
                'total_score': min(grading_data.get('total_score', 0), total_marks),
                'percentage': grading_data.get('percentage', 0),
                'feedback': self._combine_feedback(grading_data),
                'criteria_scores': grading_data.get('criteria_scores', {}),
                'questions': grading_data.get('questions', []),
                'strengths': grading_data.get('strengths', []),
                'areas_for_improvement': grading_data.get('areas_for_improvement', []),
                'grade_justification': grading_data.get('grade_justification', '')
            }

            # Recalculate percentage if needed
            if normalized_result['total_score'] > 0:
                normalized_result['percentage'] = (normalized_result['total_score'] / total_marks) * 100

            return normalized_result

        except json.JSONDecodeError as e:
            st.error(f"Error parsing AI response as JSON: {str(e)}")
            # Fallback: try to extract basic information from text
            return self._fallback_text_parsing(response, total_marks)
        except Exception as e:
            st.error(f"Error processing grading response: {str(e)}")
            return self._create_error_result(str(e))

    def _combine_feedback(self, grading_data: Dict) -> str:
        """Combine different feedback components into a comprehensive response"""
        feedback_parts = []

        # Overall feedback
        if grading_data.get('overall_feedback'):
            feedback_parts.append(grading_data['overall_feedback'])

        # Strengths
        if grading_data.get('strengths'):
            strengths_text = "**Strengths:**\n" + "\n".join(f"• {strength}" for strength in grading_data['strengths'])
            feedback_parts.append(strengths_text)

        # Areas for improvement
        if grading_data.get('areas_for_improvement'):
            improvement_text = "**Areas for Improvement:**\n" + "\n".join(
                f"• {area}" for area in grading_data['areas_for_improvement'])
            feedback_parts.append(improvement_text)

        # Grade justification
        if grading_data.get('grade_justification'):
            feedback_parts.append(f"**Grade Justification:**\n{grading_data['grade_justification']}")

        return "\n\n".join(feedback_parts)

    def _fallback_text_parsing(self, response: str, total_marks: int) -> Dict[str, Any]:
        """Fallback method to extract grading information from text response"""
        try:
            # Try to extract score from text
            score_match = re.search(r'(?:score|marks?)[:\s]*(\d+)(?:/(\d+))?', response, re.IGNORECASE)

            if score_match:
                score = int(score_match.group(1))
                max_score = int(score_match.group(2)) if score_match.group(2) else total_marks

                # Adjust score to match total_marks scale
                if max_score != total_marks:
                    score = (score / max_score) * total_marks

                score = min(score, total_marks)
            else:
                score = 0

            return {
                'total_score': score,
                'percentage': (score / total_marks) * 100 if total_marks > 0 else 0,
                'feedback': response,
                'criteria_scores': {},
                'questions': [],
                'strengths': [],
                'areas_for_improvement': [],
                'grade_justification': 'Grading performed using fallback text analysis.'
            }

        except Exception:
            return self._create_error_result("Failed to parse grading response")

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error result"""
        return {
            'total_score': 0,
            'percentage': 0,
            'feedback': f"Error during grading: {error_message}",
            'criteria_scores': {},
            'questions': [],
            'strengths': [],
            'areas_for_improvement': [],
            'grade_justification': 'Grading failed due to technical error.'
        }

    def validate_api_connection(self) -> bool:
        """Test if the Gemini API is accessible"""
        if not self.api_key:
            return False

        try:
            # Make a simple test request
            headers = {
                "Content-Type": "application/json"
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Hello, this is a test message."
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 10
                }
            }

            url = f"{self.base_url}?key={self.api_key}"

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            )

            return response.status_code == 200

        except Exception:
            return False
