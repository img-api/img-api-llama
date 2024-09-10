import time
import psutil
import signal

for process in psutil.process_iter(['pid', 'cmdline']):

    print(process.info['cmdline'])
    cmdline_pattern = ['/home/jupyter/LLAMA/venv/bin/python3', '/home/jupyter/LLAMA/venv/bin/llama', 'inference', 'start']

    cmdline = process.info['cmdline']
    if cmdline == cmdline_pattern:
        print(f"Found llama process: PID = {process.info['pid']}, Command Line: {' '.join(cmdline)}")
        process.terminate()  # Gracefully terminate
        process.wait()       # Wait for process to be terminated
