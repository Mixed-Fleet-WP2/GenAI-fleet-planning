# import os
# import instructor

# # Must not include the file itself, only directory
# # See implementation:
# # https://github.com/abetlen/llama-cpp-python/blob/c37132bac860fcc333255c36313f89c4f49d4c8d/llama_cpp/_ctypes_extensions.py#L23
# # https://github.com/abetlen/llama-cpp-python/blob/c37132bac860fcc333255c36313f89c4f49d4c8d/llama_cpp/llama_cpp.py#L35
# DEFAULT_LLAMA_SHARED_LIB = os.path.expanduser("~/llama.cpp/build/bin/")
# LLAMA_CPP_LIB = os.getenv('LLAMA_SHARED_LIB', DEFAULT_LLAMA_SHARED_LIB)

# # Set the environment variable for the llama.cpp shared library that is already
# # installed on the system.
# # See: https://www.reddit.com/r/LocalLLaMA/comments/15u74ku/what_happened_to_the_llamacpppython_project/

# # How to use the existing llama.cpp installation:
# # https://github.com/abetlen/llama-cpp-python/issues/1070#issuecomment-1881737418

# os.environ['LLAMA_CPP_LIB_PATH'] = LLAMA_CPP_LIB


# #from llama_cpp import Llama

# MODEL = "Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf"

# def main():

#     # llm = Llama(model_path=os.path.expanduser(f"~/llama.cpp/build/bin/{MODEL}"),
#     #             n_gpu_layers=-1)

#     # output = llm.create_completion(
#     #     "What is the meaning of life?", max_tokens=100,
#     #     echo=True
#     # )

#     # print(output)

#     client = instructor.from_provider()

import instructor
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional

def main():
    # Create OpenAI client pointing to your llama-server
    # Default llama-server runs on http://localhost:8080
    client = OpenAI(
        base_url="http://localhost:8080/v1",  # llama-server OpenAI-compatible endpoint
        api_key="not-needed"  # llama-server doesn't require auth by default
    )
    
    # Wrap the client with instructor

    # For the function calling (which is the default mode i.e instructor.Mode.TOOLS) that is required for structured inputs to work 
    # https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md

    # If the function calling is not desired, use instructor.Mode.JSON
    instructor_client = instructor.from_openai(client, mode=instructor.Mode.JSON)
    
    # Define your response model
    class LifeMeaning(BaseModel):
        main_theme: str
        key_points: List[str]
        philosophical_school: Optional[str] = None
        confidence: float
    
    # Use structured extraction
    response = instructor_client.chat.completions.create(
        model="gpt-3.5-turbo",  # This is ignored by llama-server, it uses whatever model you loaded
        messages=[
            {"role": "user", "content": "What is the meaning of life? Please provide a structured response."}
        ],
        response_model=LifeMeaning,
        max_tokens=1000,
    )
    
    print(f"Main theme: {response.main_theme}")
    print(f"Key points: {response.key_points}")
    print(f"Philosophical school: {response.philosophical_school}")
    print(f"Confidence: {response.confidence}")

if __name__ == "__main__":
    main()