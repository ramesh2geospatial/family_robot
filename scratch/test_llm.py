import asyncio
import sys

from packages.core.cognition.llm_client import LlamaLLMClient
from packages.core.config import load_config


async def main():
    config = load_config()
    print(f"Using model: {config.llm_model_path}")
    print("Loading LLM client...")

    llm = LlamaLLMClient(
        model_path=config.llm_model_path,
        n_ctx=config.llm_n_ctx,
        n_threads=config.llm_n_threads,
    )

    # Simple prompt
    prompt = "Introduce yourself in one sentence."
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    system = "You are FamilyRobot, a helpful and warm family companion."

    print(f"\nPrompt: {prompt}")
    print("Thinking...")

    response = await llm.generate(prompt, system=system)
    print(f"\nResponse:\n{response}\n")


if __name__ == "__main__":
    asyncio.run(main())
