import os

from google import genai
from google.genai import types


def create_model(
    system_prompt,
    model="gemini-2.5-flash-preview-04-17",
    settings={
        'temperature': 0.5,
        'top_p': 0.95,
        'top_k': 64,
        'max_output_tokens': 65536,
        'response_mime_type': "text/plain"
    },
    thinking=False
):
    # model = "gemini-2.5-pro-exp-03-25"
    # model = "gemini-2.0-flash-thinking-exp-01-21"
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    generate_content_config = types.GenerateContentConfig(
        temperature=settings.get('temperature', 0.5),
        top_p=settings.get('top_p', 0.95),
        top_k=settings.get('top_k', 64),
        max_output_tokens=settings.get('max_output_tokens', 65536),
        response_mime_type=settings.get('response_mime_type', "text/plain"),
        system_instruction=[
            types.Part.from_text(text=system_prompt),
        ],
        thinking_config=types.ThinkingConfig(thinking_budget=2048 if thinking else 0)
    )

    _stats = {
            "calls": 0,
            "prompt_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0,
    }

    def invoke(file=None, prompt=''):
        parts = []

        
        if file is not None:
            files = [
                client.files.upload(file=file),
            ]
            parts.append(
                types.Part.from_uri(
                    file_uri=files[0].uri,
                    mime_type=files[0].mime_type,
                )
            )
        
        parts.append(types.Part.from_text(text=prompt))
        
        contents = [
            types.Content(
                role="user",
                parts=parts,
            ),
        ]
        
        # 2. Make the LLM call
        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=generate_content_config,
        )

        # print(response)
        # if not response.candidates:
        #     print("✘  no candidates returned")
        #     print("   prompt_feedback:", getattr(response, "prompt_feedback", None))
        #     print("   filters        :", getattr(response, "filters", None))

        # 3. Harvest token usage --------------------------
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            _stats["prompt_tokens"]   += usage.prompt_token_count or 0
            _stats["response_tokens"] += usage.candidates_token_count or 0
            _stats["total_tokens"]    += usage.total_token_count or 0

        # >>> NEW: show this call + running totals
            print(
                f"[LLM #{_stats['calls']+1}] "
                f"prompt={usage.prompt_token_count}  "
                f"resp={usage.candidates_token_count}  "
                f"total_calls ={_stats['calls']}  "
                f"total_prompt ={_stats['prompt_tokens']}  "
                f"total_response ={_stats['response_tokens']}  "
                f"→ total so far={_stats['total_tokens']}"
            )

        # 4. Increment call counter
        _stats["calls"] += 1

        return response

    invoke.stats = _stats
    return invoke


def create_embedding_model(
    model='gemini-embedding-exp-03-07',
    task_type='SEMANTIC_SIMILARITY'
):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    def create_embedding(content, default_as_list=False):
        result = client.models.embed_content(
            model=model,
            contents=content,
            config=types.EmbedContentConfig(task_type=task_type)
        )
        if default_as_list or len(result.embeddings) > 1:
            return list(map(lambda r: r.values, result.embeddings))
        return result.embeddings[0].values

    return create_embedding
