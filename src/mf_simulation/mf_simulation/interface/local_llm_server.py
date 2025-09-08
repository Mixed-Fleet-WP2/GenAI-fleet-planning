import os
import instructor
from openai import OpenAI
from pydantic import BaseModel

from llama_cpp.llama_speculative import LlamaPromptLookupDecoding

from llama_cpp import Llama

MODEL = "Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf"

# https://python.useinstructor.com/integrations/llama-cpp-python/
def main():

    llama_client = Llama(model_path=os.path.expanduser(f"~/llama.cpp/build/bin/{MODEL}"),
                n_gpu_layers=-1,
                verbose=True,
                logits_all=True,
                draft_model=LlamaPromptLookupDecoding(num_pred_tokens=2),
                chat_format="chatml"
                )

    create = instructor.patch(
       # The original create_chat_completion_openai_v1 function
       # that the instructor wraps with additional functionality
        create=llama_client.create_chat_completion_openai_v1,
        mode=instructor.Mode.JSON
    )

    class UserDetail(BaseModel):
        name: str
        age: int


    user = create(
            messages=[
                {
                    "role": "user",
                    "content": "Extract `Jason is 30 years old`",
                }
            ],
            response_model=UserDetail,
            max_retries=5
        )

    print(user)


if __name__ == "__main__":
    main()