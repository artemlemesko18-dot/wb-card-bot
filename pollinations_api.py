import random
import urllib.parse

import aiohttp


async def generate_image_via_pollinations(prompt: str, model: str = "flux") -> bytes | None:
    """
    Generate image bytes via Pollinations AI without API key.
    Returns image bytes or None on failure.
    """
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1, 10_000_000)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1024&height=1024&model={model}&nologo=true&seed={seed}"
    )
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                print(f"Pollinations AI error: {response.status}")
                return None
        except Exception as exc:
            print(f"Pollinations AI exception: {exc}")
            return None
