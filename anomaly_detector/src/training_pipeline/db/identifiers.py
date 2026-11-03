import re


def quoted_table_name(value: str) -> str:
    """Accept one table identifier, never SQL expressions or paths."""
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}', value):
        raise ValueError('Invalid source table name')
    return f'"{value}"'
