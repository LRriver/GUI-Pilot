import os
from openai import OpenAI

# Set VLM_API_KEY in the process environment before running this script.
client = OpenAI(
    base_url=os.environ.get("DEBUG_API_URL", "https://ark.cn-beijing.volces.com/api/v3"),
    api_key=os.environ.get("VLM_API_KEY"),
)

response = client.chat.completions.create(
    model=os.environ.get("DEBUG_MODEL_ID", "doubao-seed-1-6-vision-250815"),
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
                    },
                },
                {"type": "text", "text": "这是哪里？"},
            ],
        }
    ],
)

print(response.choices[0])
