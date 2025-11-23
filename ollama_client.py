import ollama
from ollama import ResponseError
import time
import platform
import os
import queue
from config import MAX_RETRIES, FORBIDDEN_KEYWORDS

def _get_ollama_options(use_gpu: bool) -> dict:
    """Builds the options dict for the Ollama client based on settings."""
    options = {}
    system = platform.system()

    if use_gpu:
        if system == "Darwin": # macOS
            options['num_gpu'] = 1 # Use Metal
        elif system == "Linux":
            options['num_gpu'] = 99 # Use all available CUDA layers
        elif system == "Windows":
            options['num_gpu'] = 99 # Use all available CUDA/ROCm layers
        else:
            options['num_gpu'] = 1 # Default request
    else:
        options['num_gpu'] = 0 # Force CPU
        try:
            # Use slightly fewer than all cores to keep UI responsive
            cores = os.cpu_count()
            options['num_thread'] = max(1, cores - 2 if cores else 4)
        except:
            options['num_thread'] = 4 # Failsafe

    return options

def _is_response_valid(reply: str) -> bool:
    """
    Checks if the first sentence of the reply contains forbidden keywords.
    """
    s = reply.strip()
    # Find the end of the first sentence (., !, ?)
    end_indices = [s.find(p) for p in '.!?']
    end_indices = [i for i in end_indices if i != -1]

    if not end_indices:
        # If no sentence end, check the first 150 chars
        first_sentence = s[:150].lower()
    else:
        # Check content up to the first sentence end
        first_sentence = s[:min(end_indices) + 1].lower()

    # Check for any forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in first_sentence:
            return False
    return True

def execute_ollama_call(
    client: ollama.Client,
    selected_model: str,
    use_gpu: bool,
    messages_for_call: list,
    logic_queue: queue.Queue
) -> tuple[str, float, bool]:
    """
    Executes the Ollama chat call with retry logic.

    Returns:
        tuple[str, float, bool]: (reply, elapsed_time, success_flag)
    """
    valid_response_received = False
    reply = ""
    elapsed_time = 0
    
    options = _get_ollama_options(use_gpu)

    for attempt in range(MAX_RETRIES):
        try:
            # Start timer
            start_time = time.perf_counter()

            response = client.chat(
                model=selected_model,
                messages=messages_for_call,
                stream=False,
                options=options
            )

            # End timer
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time

            reply = response.get('message', {}).get('content', '')

            if _is_response_valid(reply):
                valid_response_received = True
                return reply, elapsed_time, True # Success
            else:
                # Invalid response, log and add correction prompt
                logic_queue.put(("LOG", "\n[Chatbot is rethinking...]"))
                correction_prompt = "That was not a valid response. You must stay on topic and answer the user's last request. Do not mention that you are an AI."
                messages_for_call.append({'role': 'user', 'content': correction_prompt})
                # Loop continues to next attempt

        except ResponseError as e:
            # Handle API error (e.g., timeout)
            logic_queue.put(("LOG", f"\n[!!] Ollama Error (Attempt {attempt+1}/{MAX_RETRIES}): {e.error} [!!]"))
            time.sleep(1) # Wait before retrying
        except Exception as e:
            # Handle other Python errors
            logic_queue.put(("LOG", f"\n[!!] THREAD ERROR (Attempt {attempt+1}/{MAX_RETRIES}): {e} [!!]"))
            time.sleep(1) # Wait before retrying

    # All retries failed
    return reply, elapsed_time, False