from openai import OpenAI
from pydantic import BaseModel
import instructor

# https://ollama.readthedocs.io/en/openai/
#https://python.useinstructor.com/blog/2024/03/07/open-source-local-structured-output-pydantic-json-openai/#exploring-different-openai-clients-with-instructor

class UserDetail(BaseModel):
    name: str
    age: int

client = instructor.from_openai(
    OpenAI(
        # Ollama allows us to use the OpenAI API interface
        # v1 is the api version to which the rest of the url
        # path is appended

        base_url="http://192.168.0.104:11434/v1",
        api_key="ollama",  # required, but unused
    ),
    mode=instructor.Mode.JSON,
)

# Internally, this appends /chat/completions to the base_url?
user = client.chat.completions.create(
    model="llama-3.1-8B",
    messages=[
        {
            "role": "user",
            "content": "Jason is 30 years old",
        }
    ],
    response_model=UserDetail,
)

print(user)
#> name='Jason' age=30