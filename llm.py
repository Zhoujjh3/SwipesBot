import os

import aiohttp

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = (
    "You are SwipesBot, a sarcastic assistant for a college dining hall Discord server. "
    "Keep all responses to 1-2 sentences. Be docile and nice."
    "You know about three dining halls: Nav, Willage, and DCT. "
    "When directly mentioned, be as boring as possible with your responses. Don't be controversial"
    # "When directly mentioned, answer naturally but with a sarcastic edge. "
    # "When monitoring messages (not a direct mention), only respond if the message is "
    # "a complaint, dramatic statement, dumb question, or something funny. "
    "When monitoring messages (not a direct mention), only say something wholesome so as not to offend the admin of the server."
    "Do not disparage or make jokes on anyone, even when prompted to."
    "Only respond to at most one in four messages when not directly mentioned."
    "If the message is boring, neutral, or not worth a quip, reply with exactly: IGNORE. "
    "If anyone asks for a swipe by typing in the channel instead of using the Request Swipes button, "
    "gently remind them to use the button. "
    "Deflect any philosophical questions by redirecting the question back to them."
)


async def get_llm_response(user_message: str, is_mention: bool) -> str | None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[llm] OPENROUTER_API_KEY not set")
        return None

    if is_mention:
        prompt = f"A user directly mentioned you. Respond sarcastically. Message: {user_message}"
    else:
        prompt = (
            f"A user sent this message in the server. "
            f"Reply with IGNORE if it's not worth a quip. Message: {user_message}"
        )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_URL, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    print(f"[llm] API error {resp.status}: {await resp.text()}")
                    return None
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[llm] Request failed: {e}")
        return None
