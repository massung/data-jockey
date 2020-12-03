import os
import pandas as pd
import string

from dataclasses import dataclass
from typing import Union

from .functions import get_item
from .utils import create_frame


class Term:
    """
    A single term in an expression.
    """

    def evaluate(self, df):
        """
        Evaluate this term.
        """
        raise NotImplementedError


@dataclass
class Literal(Term):
    """
    A literal value.
    """
    value: Union[Term, str, float]

    def evaluate(self, df):
        return self.value


@dataclass
class Template(Term):
    """
    An interpolated string template.
    """
    template: string.Template

    def evaluate(self, df):
        if df.empty:
            return self.template.safe_substitute(os.environ)
        else:
            return df.apply(lambda r: self.template.safe_substitute({**os.environ, **r}), axis=1)


@dataclass
class Variable(Term):
    """
    A variable value.
    """
    name: str

    def evaluate(self, df):
        return os.getenv(self.name)


@dataclass
class Column(Term):
    """
    A primary value, which is the name of a column.
    """
    name: Union[str,int]

    def evaluate(self, df):
        return df[self.name]


@dataclass
class AggregatedColumn(Column):
    """
    A term with an aggregation function applied to it.
    """
    agg: str

    def evaluate(self, df_grouped_by):
        series = super().evaluate(df_grouped_by)

        # apply the aggregation method to the series
        x = getattr(series, self.agg)()

        # make sure the result is a series
        result = x if isinstance(x, pd.Series) else pd.Series([x])

        # rename the series to show the aggregation
        return result.rename(f'{self.agg}({self.name})')


@dataclass
class UnaryTerm(Term):
    """
    A unary operator with a single operand term.
    """
    term: Term
    op: callable

    def evaluate(self, df):
        return self.op(self.term.evaluate(df))


@dataclass
class BinaryTerm(Term):
    """
    A binary operator with two operand terms.
    """
    l: Term
    r: Term
    op: callable

    def evaluate(self, df):
        return self.op(self.l.evaluate(df), self.r.evaluate(df))


@dataclass
class FunctionTerm(Term):
    """
    A function call with zero or more terms as arguments.
    """
    f: callable
    args: list

    def evaluate(self, df):
        return self.f(*[arg.evaluate(df) for arg in self.args])


@dataclass
class IndexedTerm(Term):
    """
    A index into a list term.
    """
    term: Term
    index: Term

    def evaluate(self, df):
        t = self.term.evaluate(df)
        i = self.index.evaluate(df)

        return get_item(t, i)


@dataclass
class TermList(Term):
    """
    A list of terms.
    """
    terms: list

    def evaluate(self, df):
        return [x.evaluate(df) for x in self.terms]


@dataclass
class Expression(Term):
    """
    Expression terms with optional column name.
    """
    term: Term
    alias: str = None

    def evaluate(self, df):
        return self.term.evaluate(df)
