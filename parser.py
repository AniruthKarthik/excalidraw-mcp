def parse_architecture(prompt: str):
    """Very basic parser"""

    separators = [",", "\n", "-"]

    for sep in separators:
        prompt = prompt.replace(sep, "|")

    parts = [p.strip() for p in prompt.split("|") if p.strip()]

    return parts
