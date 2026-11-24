"""Nomes de exibição.

O código usa identificadores sem acento (mais simples de digitar e de buscar). Tudo o que é gravado para o
leitor (nomes de arquivos CSV, abas e cabeçalhos do Excel) passa por aqui e sai com a grafia correta.
"""
from __future__ import annotations

import unicodedata

import pandas as pd

TABLE_NAMES = {
    "Calendario": "Calendário",
    "Qualificacao": "Qualificação",
    "Voltas_Rapidas": "Voltas_Rápidas",
    "Validacao": "Validação",
}

COLUMN_NAMES = {
    "Diferenca": "Diferença",
    "Distancia_km": "Distância_km",
    "Extensao_km": "Extensão_km",
    "Formato_Qualificacao": "Formato_Qualificação",
    "Numero": "Número",
    "Pais": "País",
    "Pais_Nascimento": "País_Nascimento",
    "Podios": "Pódios",
    "Posicao": "Posição",
    "Posicao_Campeonato": "Posição_Campeonato",
    "Posicao_Grid": "Posição_Grid",
    "Sessao": "Sessão",
    "Situacao": "Situação",
    "Tempo_Qualificacao": "Tempo_Qualificação",
    "Unidade_de_Potencia": "Unidade_de_Potência",
    "Vitorias": "Vitórias",
    "Volta_Mais_Rapida": "Volta_Mais_Rápida",
    "Voltas_Mais_Rapidas": "Voltas_Mais_Rápidas",
}


def table_name(name: str) -> str:
    return TABLE_NAMES.get(name, name)


def display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Cópia da tabela com os cabeçalhos em português correto."""
    return df.rename(columns=COLUMN_NAMES)


def ascii_slug(text: str) -> str:
    """'Calendário' -> 'calendario' (para identificadores de tabela do Excel)."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
