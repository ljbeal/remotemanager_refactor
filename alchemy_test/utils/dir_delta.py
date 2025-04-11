import os


def dir_delta(base: str, test: str) -> int:
    """
    Counts the directory level difference between `base` and `test`

    e.g:
    if `base` is a _subdirectory_ of `test`, the number will be -ve

    Args:
        base:
            base directory to test from
        test:
            directory to query

    Returns:
        int
    """
    # make sure we have abspaths for commonprefix
    base = os.path.abspath(base)
    test = os.path.abspath(test)
    # if the paths are equal, return False
    if base == test:
        return 0
    # get the common part of the path to remove
    mix = os.path.commonpath([base, test])
    # delete the common from both paths
    diff_neg = len(base.replace(mix, "").split(os.sep))
    diff_pos = len(test.replace(mix, "").split(os.sep))

    return diff_pos - diff_neg
