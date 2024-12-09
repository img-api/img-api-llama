import ollama

print(str(ollama.show('llama3.3')))

response = ollama.chat(model='llama3.3', messages=[
  {
    'role': 'user',
    'content': 'Why is the sky blue?',
  },
])

print(response['message']['content'])
