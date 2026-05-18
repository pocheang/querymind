"""Check system configuration."""

from app.core.config import get_settings

s = get_settings()
print(f'Model Backend: {s.model_backend}')
print(f'Chat Model: {s.ollama_chat_model if s.model_backend == "ollama" else s.openai_chat_model}')
print(f'Reasoning Model Backend: {s.reasoning_model_backend or "same as chat"}')
print(f'Data Directory: {s.data_dir}')
