import re

MINOR_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "nor",
    "for",
    "so",
    "yet",
    "at",
    "by",
    "in",
    "of",
    "on",
    "to",
    "up",
    "from",
    "with",
}


def to_title_case(text: str) -> str:
    """
    Converts text to title case, ignoring minor words unless they are the first word.
    """
    if not text:
        return ""

    words = text.split()
    if not words:
        return ""

    cased_words = []
    for i, word in enumerate(words):
        lower_word = word.lower()
        # Capitalize if it's the first word or not a minor word
        if i == 0 or lower_word not in MINOR_WORDS:
            cased_words.append(word.capitalize())
        else:
            cased_words.append(lower_word)

    return " ".join(cased_words)


def sanitize_filename(text: str) -> str:
    """
    Removes characters that are unsafe for filenames.
    """
    # Keep alphanumeric, dashes, spaces, underscores, periods
    # Remove slashes, colons, etc.
    safe_text = re.sub(r'[\\/*?:"<>|]', "", text)
    return safe_text.strip()


def get_last_name(full_name: str) -> str:
    """
    Extracts the last name from a full name string.
    Assumes "First Last" or "First Middle Last".
    """
    if not full_name:
        return "Unknown"

    parts = full_name.strip().split()
    if not parts:
        return "Unknown"

    return parts[-1]
