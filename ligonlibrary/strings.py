#!/usr/bin/env python3
"""Handy string functions.
"""
from fuzzywuzzy import fuzz

def normalized(s,case='lower'):
    """
    Normalizes the input string by performing several transformations:
    - Lowercasing the string
    - Stripping leading and trailing white spaces
    - Collapsing multiple white spaces into a single space
    - Replacing hyphens with spaces
    """
    import re
    # Convert case
    if case=='lower':
        s = s.lower()
    elif case=='upper':
        s = s.upper()
    elif case=='title':
        s = s.title()

    # Replace hyphens with spaces
    s = s.replace('-', ' ')
    # Strip leading/trailing spaces and collapse multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def similar(str1, str2, similarity_threshold=85):
    """
    Determines if two strings are similar based on specified criteria.

    Parameters:
    - str1 (str): First string to compare.
    - str2 (str): Second string to compare.
    - similarity_threshold (int): The score threshold above which strings are considered similar (0-100). Default is 85.

    Returns:
    - bool: True if the strings are similar, False otherwise.
    """


    # Normalize both input strings
    normalized_str1 = normalized(str1)
    normalized_str2 = normalized(str2)

    # Use fuzzy string matching to get a similarity score
    similarity_score = fuzz.ratio(normalized_str1, normalized_str2)

    # Return True if the similarity score is above the threshold
    return similarity_score >= similarity_threshold
