curl http://localhost:11434/api/generate -d '{"model": "llama3.1", "keep_alive": -1}'

ollama ps

. .venv/bin/activate


python3 ollama_toolcall.py
