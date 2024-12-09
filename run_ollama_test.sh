curl http://localhost:11434/api/generate -d '{"model": "llama3.3", "keep_alive": -1, "options": { "num_ctx": 16384 }}'

ollama ps

. .venv/bin/activate


python3 ollama_toolcall.py
