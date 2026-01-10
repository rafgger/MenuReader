import io
import mimetypes
import os
from google.genai import types
from google import genai


class AIClient:
    def _get_default_config(self):
        """Get default config with current environment variables"""
        return {
            "ai_model": os.getenv("AI_MODEL"),
            "temperature": 0.5,
            "max_output_tokens": 2048,
            "top_p": 0.95,
            "top_k": 40,
            "response_mime_type": "application/json",
            "thinking_budget": int(os.getenv("THINKING_BUDGET", -1)),
            "include_thoughts": os.getenv("INCLUDE_THOUGHTS", "true").lower() == "true",
            "response_schema": {
                "type": "object",
                "properties": {
                    "selected_task_id": {"type": "string"},
                    "suggested_task_name": {"type": "string"},
                    "confidence_score": {"type": "number"},
                },
                "required": ["confidence_score"],
            },
        }

    def __init__(self, img_bytes, prompt):
        api_key = (
            os.getenv("GOOGLE_API_KEY")
            or os.getenv("Google_Gemini_API")
            or os.getenv("GEMINI_API_KEY")
        )
        if not api_key:
            raise ValueError(
                "Google GenAI API key must be provided either as an argument or via the GOOGLE_API_KEY environment variable."
            )
        self.client = genai.Client(api_key=api_key)
        self.config = self._get_default_config()
        self.prompt = prompt
        self.img_input = {"mime_type": "image/png", "data": img_bytes}

    def generate_content(self):
        return self.client.models.generate_content(
            model=self.config["ai_model"],
            contents=[self.user_content()],
            config=types.GenerateContentConfig(
                temperature=self.config["temperature"],
                top_p=self.config["top_p"],
                top_k=self.config["top_k"],
                response_mime_type=self.config["response_mime_type"],
                response_schema=self.config["response_schema"],
                thinking_config=types.ThinkingConfig(
                    thinking_budget=self.config["thinking_budget"],
                    include_thoughts=self.config["include_thoughts"],
                ),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )

    def user_content(self):
        return types.Content(
            role="user",
            parts=[
                self._as_image_part(),
                types.Part(text=self.prompt),
            ],
        )

    def _as_image_part(self) -> types.Part:
        """
        Converts various image formats (bytes, BytesIO, file path, Part, or dict) into a Google GenAI types.Part object.
        Normalizes different image representations into a consistent format for the GenAI API.
        """
        # bytes / bytearray / BytesIO
        if isinstance(self.img_input, (bytes, bytearray)):
            return types.Part(
                inline_data=types.Blob(mime_type="image/png", data=self.img_input)
            )
        if isinstance(self.img_input, io.BytesIO):
            return types.Part(
                inline_data=types.Blob(
                    mime_type="image/png", data=self.img_input.getvalue()
                )
            )
        # file path
        if isinstance(self.img_input, str) and os.path.exists(self.img_input):
            mime = mimetypes.guess_type(self.img_input)[0] or "image/png"
            with open(self.img_input, "rb") as f:
                return types.Part(inline_data=types.Blob(mime_type=mime, data=f.read()))
        # already a Part? accept it
        if isinstance(self.img_input, types.Part):
            return self.img_input
        # dict from old SDK? try to coerce
        if (
            isinstance(self.img_input, dict)
            and "mime_type" in self.img_input
            and "data" in self.img_input
        ):
            return types.Part(
                inline_data=types.Blob(
                    mime_type=self.img_input["mime_type"], data=self.img_input["data"]
                )
            )
        raise TypeError(
            "Unsupported img_input format; provide bytes/BytesIO/path/Part/dict{mime_type,data}."
        )
