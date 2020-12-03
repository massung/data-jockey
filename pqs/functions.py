import itertools
import pandas as pd
import math
import numbers


def series_function():
    """
    Wrap a standard function to allow for a Series of values to
    be applied instead.
    """
    def decorator(f):
        def handler(*xs):
            is_series = any(isinstance(x, pd.Series) for x in xs)

            if is_series:
                args = zip(*(x.array if isinstance(x, pd.Series) else itertools.repeat(x) for x in xs))

                # return a series of the results
                return pd.Series(f(*xs) for xs in args)

            # just return the scalar of the function
            return f(*xs)

        return handler
    return decorator


def unknown_function(f):
    """
    Simple handler for an unknown function.
    """
    def handler(*args):
        raise RuntimeError(f'Unknown function {f}')

    return handler


def is_na(x):
    """
    Helper function, acts like a unary operator.is_na.
    """
    return x.isna() if isinstance(x, pd.Series) else x is None or math.isnan(x)


def is_not_na(x):
    """
    Helper function, acts like a unary operator.is_not_na.
    """
    return x.notna() if isinstance(x, pd.Series) else not (x is None or math.isnan(x))


def is_in(a, b, **kwargs):
    """
    Test if an element is within the series.
    """
    if not isinstance(b, pd.Series):
        b = pd.Series([b])

    return b.str.contains(a, case=False, **kwargs)


def not_in(a, b, **kwargs):
    """
    Test if an element is within the series.
    """
    if not isinstance(b, pd.Series):
        b = pd.Series([b])

    return ~b.str.contains(a, case=False, **kwargs)


@series_function()
def iota(n):
    """
    Return a list of integers.
    """
    return list(range(n))


@series_function()
def if_(c, t, e):
    """
    Return t or e based on condition.
    """
    return t if c else e


@series_function()
def if_na(x, alt):
    """
    Return x if not na, otherwise alt.
    """
    return alt if (math.isnan(x) if isinstance(x, numbers.Number) else (x is None)) else x


@series_function()
def get_item(a, i):
    """
    Return an item from an array.
    """
    if getattr(a, '__getitem__'):
        try:
            return a[i]
        except KeyError:
            pass
        except IndexError:
            pass

    return None
