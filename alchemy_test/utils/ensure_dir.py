import os


def ensure_dir(dir: str) -> str:
    """
    Ensure that string path to `dir` is correctly formatted
    ONLY ensures that the folder name ends with a "/", does not produce an
    abspath

    Args:
        dir (str):
            path to dir

    Returns (str):
        ensured dir path
    """
    return os.path.join(dir, " ").strip()
