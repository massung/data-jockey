import itertools
import pandas as pd


def args_env(args):
    """
    Create a dictionary of enumerated arguments.
    """
    return {str(i): str(v) for i, v in enumerate(args)}


def create_frame(data):
    """
    Creates a DataFrame from a list tuples: (column, value). If any
    value is a Series, then all values will repeat to match the series
    length.
    """
    result = pd.DataFrame()

    # sort columns by series then scalar
    if data:
        cols = sorted(data, key=lambda col: not isinstance(col[1], pd.Series))

        # calculate the size of the resulting frame
        n = len(cols[0][1]) if isinstance(cols[0][1], pd.Series) else 1

        # add series columns first, then scalars
        for col, value in cols:
            result[col] = value if isinstance(value, pd.Series) else pd.Series([value] * n)

    # re-order by the column order
    return result[[col for col, _ in data]]
