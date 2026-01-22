#!/usr/bin/env python3
"""
DraCor MCP Server - Core server implementation.

This module contains the MCP server definition with all resources, tools, and prompts
for interacting with the Drama Corpora Project (DraCor) API v1.
"""

from typing import Dict, List, Optional, Any, Union
import requests
import re
import csv
import io
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP
import os

# Base API URL for DraCor v1
# Set the Base URL in the environment variable DRACOR_API_BASE_URL
DRACOR_API_BASE_URL = str(os.environ.get("DRACOR_API_BASE_URL", "https://dracor.org/api/v1"))

# Default timeout for HTTP requests (in seconds)
DEFAULT_TIMEOUT = 30

# Validation pattern for corpus/play names (alphanumeric, hyphens, underscores only)
VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

# TEI XML namespace
TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def validate_name(name: str, param_name: str = "name") -> str:
    """Validate corpus/play names contain only safe characters."""
    if not name:
        raise ValueError(f"{param_name} cannot be empty")
    if not VALID_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid {param_name}: only alphanumeric, hyphens, underscores allowed")
    return name


# Create the FastMCP server instance with HTTP configuration
mcp = FastMCP(
    "DraCor API v1",
    stateless_http=True,  # Enable stateless HTTP mode for scalable deployment
)


# Health check endpoint for Railway deployment
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Railway."""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "status": "healthy",
        "service": "dracor-mcp-server",
        "transport": "streamable-http"
    })


# Helper function to make API requests
def api_request(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Make a request to the DraCor API v1."""
    url = f"{DRACOR_API_BASE_URL}/{endpoint}"
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

# Resource implementations using decorators
@mcp.resource("info://")
def get_api_info() -> Dict:
    """Get API information and version details."""
    try:
        info = api_request("info")
        return info
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpora://")
def get_corpora() -> Dict:
    """List of all available corpora (collections of plays)."""
    try:
        # The include parameter needs to be handled differently as it's not in the URI
        # We'll handle it as a query parameter in the implementation
        corpora = api_request("corpora")
        return {"corpora": corpora}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpus://{corpus_name}")
def get_corpus(corpus_name: str) -> Dict:
    """Information about a specific corpus."""
    try:
        validate_name(corpus_name, "corpus_name")
        corpus = api_request(f"corpora/{corpus_name}")
        return corpus
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpus_metadata://{corpus_name}")
def get_corpus_metadata(corpus_name: str) -> Dict:
    """Get metadata for all plays in a corpus."""
    try:
        validate_name(corpus_name, "corpus_name")
        metadata = api_request(f"corpora/{corpus_name}/metadata")
        return {"metadata": metadata}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("plays://{corpus_name}")
def get_plays(corpus_name: str) -> Dict:
    """List of plays in a specific corpus."""
    try:
        validate_name(corpus_name, "corpus_name")
        corpus = api_request(f"corpora/{corpus_name}")
        return {"plays": corpus.get("plays", [])}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("play://{corpus_name}/{play_name}")
def get_play(corpus_name: str, play_name: str) -> Dict:
    """Information about a specific play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        play = api_request(f"corpora/{corpus_name}/plays/{play_name}")
        return play
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("play_metrics://{corpus_name}/{play_name}")
def get_play_metrics(corpus_name: str, play_name: str) -> Dict:
    """Get network metrics for a specific play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        metrics = api_request(f"corpora/{corpus_name}/plays/{play_name}/metrics")
        return metrics
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("characters://{corpus_name}/{play_name}")
def get_characters(corpus_name: str, play_name: str) -> Dict:
    """List of characters in a specific play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        characters = api_request(f"corpora/{corpus_name}/plays/{play_name}/characters")
        return {"characters": characters}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("spoken_text://{corpus_name}/{play_name}")
def get_spoken_text(corpus_name: str, play_name: str) -> Dict:
    """Get the spoken text for a play, with optional filters (gender, relation, role) as query parameters."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        # For now, we won't use optional query parameters since they're causing issues
        # We can implement this differently once we better understand the FastMCP API
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        text = response.text

        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("spoken_text_by_character://{corpus_name}/{play_name}")
def get_spoken_text_by_character(corpus_name: str, play_name: str) -> Dict:
    """Get spoken text for each character in a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        text_by_character = api_request(f"corpora/{corpus_name}/plays/{play_name}/spoken-text-by-character")
        return {"text_by_character": text_by_character}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("stage_directions://{corpus_name}/{play_name}")
def get_stage_directions(corpus_name: str, play_name: str) -> Dict:
    """Get all stage directions of a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        # Note: This endpoint returns plain text, not JSON
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/stage-directions"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        text = response.text

        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("network_data://{corpus_name}/{play_name}")
def get_network_data(corpus_name: str, play_name: str) -> Dict:
    """Get network data of a play in CSV format."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        # Note: This endpoint returns CSV, not JSON
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/networkdata/csv"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        csv_data = response.text

        return {"csv_data": csv_data}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("relations://{corpus_name}/{play_name}")
def get_relations(corpus_name: str, play_name: str) -> Dict:
    """Get character relation data for a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/relations"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        relations = response.json()

        return {"relations": relations}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("full_text://{corpus_name}/{play_name}")
def get_full_text(corpus_name: str, play_name: str) -> Dict:
    """Get the full text of a play in plain text format."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        # The DraCor API doesn't have a direct plain text endpoint
        # Use the spoken-text endpoint which returns plain text of all dialogue
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        # Get stage directions too
        stage_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/stage-directions"
        stage_response = requests.get(stage_url, timeout=DEFAULT_TIMEOUT)
        stage_response.raise_for_status()

        # Combine both for a more complete text representation
        text = f"DIALOGUE:\n\n{response.text}\n\nSTAGE DIRECTIONS:\n\n{stage_response.text}"

        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("tei_text://{corpus_name}/{play_name}")
def get_tei_text(corpus_name: str, play_name: str) -> Dict:
    """Get the full TEI XML text of a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/tei"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        tei_text = response.text

        return {"tei_text": tei_text}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("character_by_wikidata://{wikidata_id}")
def get_plays_with_character(wikidata_id: str) -> Dict:
    """List plays having a character identified by Wikidata ID."""
    try:
        plays = api_request(f"character/{wikidata_id}")
        return {"plays": plays}
    except Exception as e:
        return {"error": str(e)}

# Tool implementations using decorators
@mcp.tool()
def search_plays(
    query: str = None,
    corpus_name: str = None,
    character_name: str = None,
    country: str = None,
    language: str = None,
    author: str = None,
    year_from: int = None,
    year_to: int = None,
    gender_filter: str = None
) -> Dict:
    """
    Advanced search for plays in the DraCor database with multiple filter options.

    Parameters:
    - query: General text search across title, subtitle, and author
    - corpus_name: Specific corpus to search within (e.g., "shake", "ger", "rus", "span", "dutch")
    - character_name: Name of a character that should appear in the play
    - country: Country of origin for the play
    - language: Language of the play
    - author: Name of the playwright
    - year_from: Starting year for date range filter
    - year_to: Ending year for date range filter
    - gender_filter: Filter by plays with a certain gender ratio ("female_dominated", "male_dominated", "balanced")
    """
    try:
        # Get corpora to search in
        corpora_result = get_corpora()
        if "error" in corpora_result:
            return {"error": corpora_result["error"]}

        all_corpora = corpora_result.get("corpora", [])
        target_corpora = []

        # Filter corpora if specified
        if corpus_name:
            target_corpora = [corp for corp in all_corpora if corpus_name.lower() in corp.get("name", "").lower()]
        else:
            target_corpora = all_corpora

        # Initialize results
        results = []
        detailed_results = []

        # For each corpus, search for plays
        for corpus in target_corpora:
            corpus_name = corpus.get("name")

            # Get all plays from this corpus
            plays_result = get_plays(corpus_name)
            if "error" in plays_result:
                continue

            # Iterate through plays and apply filters
            for play in plays_result.get("plays", []):
                # Initialize as a match until proven otherwise by filters
                is_match = True

                # Apply general text search if specified
                if query and is_match:
                    searchable_text = (
                        play.get("title", "") + " " +
                        " ".join([a.get("name", "") for a in play.get("authors", [])]) + " " +
                        play.get("subtitle", "") + " " +
                        play.get("originalTitle", "")
                    ).lower()

                    if query.lower() not in searchable_text:
                        is_match = False

                # Apply country filter if specified
                if country and is_match:
                    play_country = (
                        play.get("writtenIn", "") + " " +
                        play.get("printedIn", "") + " " +
                        " ".join([a.get("country", "") for a in play.get("authors", [])])
                    ).lower()

                    if country.lower() not in play_country:
                        is_match = False

                # Apply language filter if specified
                if language and is_match:
                    if language.lower() not in play.get("originalLanguage", "").lower():
                        is_match = False

                # Apply author filter if specified
                if author and is_match:
                    author_names = [a.get("name", "").lower() for a in play.get("authors", [])]
                    if not any(author.lower() in name for name in author_names):
                        is_match = False

                # Apply year range filter if specified
                if (year_from or year_to) and is_match:
                    play_year = play.get("yearNormalized") or play.get("yearWritten") or play.get("yearPrinted") or 0

                    if year_from and play_year < year_from:
                        is_match = False

                    if year_to and play_year > year_to:
                        is_match = False

                # If character name is specified, need to check character list
                if character_name and is_match:
                    try:
                        # Get characters for this play
                        play_name = play.get("name")
                        characters_result = get_characters(corpus_name, play_name)

                        if "error" not in characters_result:
                            character_found = False
                            for character in characters_result.get("characters", []):
                                if character_name.lower() in character.get("name", "").lower():
                                    character_found = True
                                    break

                            if not character_found:
                                is_match = False
                        else:
                            # If we can't get characters, we assume it's not a match
                            is_match = False
                    except Exception:
                        # If error occurs, we assume it's not a match
                        is_match = False

                # Apply gender filter if specified
                if gender_filter and is_match:
                    try:
                        # Get characters for this play
                        play_name = play.get("name")
                        characters_result = get_characters(corpus_name, play_name)

                        if "error" not in characters_result:
                            male_count = sum(1 for c in characters_result.get("characters", []) if c.get("gender") == "MALE")
                            female_count = sum(1 for c in characters_result.get("characters", []) if c.get("gender") == "FEMALE")
                            total = male_count + female_count

                            if total > 0:
                                female_ratio = female_count / total

                                if gender_filter == "female_dominated" and female_ratio <= 0.5:
                                    is_match = False
                                elif gender_filter == "male_dominated" and female_ratio >= 0.5:
                                    is_match = False
                                elif gender_filter == "balanced" and (female_ratio < 0.4 or female_ratio > 0.6):
                                    is_match = False
                    except Exception:
                        # If error occurs, we keep it as a match
                        pass

                # If all filters passed, add to results
                if is_match:
                    # Add basic info to results
                    results.append({
                        "corpus": corpus_name,
                        "play": play
                    })

                    # Try to add more detailed info for top results
                    if len(detailed_results) < 5:
                        try:
                            play_name = play.get("name")
                            # Get more details
                            play_info = get_play(corpus_name, play_name)

                            if "error" not in play_info:
                                detailed_results.append({
                                    "corpus": corpus_name,
                                    "play_name": play_name,
                                    "title": play.get("title"),
                                    "author": play.get("authors", [{}])[0].get("name") if play.get("authors") else "Unknown",
                                    "year": play.get("yearNormalized"),
                                    "language": play.get("originalLanguage"),
                                    "characters": len(play_info.get("characters", [])),
                                    "link": f"https://dracor.org/{corpus_name}/{play_name}"
                                })
                        except Exception:
                            pass

        return {
            "count": len(results),
            "results": results,
            "top_results": detailed_results,
            "filters_applied": {
                "query": query,
                "corpus_name": corpus_name,
                "character_name": character_name,
                "country": country,
                "language": language,
                "author": author,
                "year_range": f"{year_from}-{year_to}" if year_from or year_to else None,
                "gender_filter": gender_filter
            }
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def compare_plays(
    corpus_name1: str,
    play_name1: str,
    corpus_name2: str,
    play_name2: str
) -> Dict:
    """Compare two plays in terms of metrics and structure."""
    try:
        validate_name(corpus_name1, "corpus_name1")
        validate_name(play_name1, "play_name1")
        validate_name(corpus_name2, "corpus_name2")
        validate_name(play_name2, "play_name2")
        play1 = api_request(f"corpora/{corpus_name1}/plays/{play_name1}")
        play2 = api_request(f"corpora/{corpus_name2}/plays/{play_name2}")

        metrics1 = api_request(f"corpora/{corpus_name1}/plays/{play_name1}/metrics")
        metrics2 = api_request(f"corpora/{corpus_name2}/plays/{play_name2}/metrics")

        # Compile comparison data
        comparison = {
            "plays": [
                {
                    "title": play1.get("title"),
                    "author": play1.get("authors", [{}])[0].get("name") if play1.get("authors") else None,
                    "year": play1.get("yearNormalized"),
                    "metrics": metrics1
                },
                {
                    "title": play2.get("title"),
                    "author": play2.get("authors", [{}])[0].get("name") if play2.get("authors") else None,
                    "year": play2.get("yearNormalized"),
                    "metrics": metrics2
                }
            ]
        }

        return comparison
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def analyze_character_relations(corpus_name: str, play_name: str) -> Dict:
    """Analyze the character relationships in a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        # Get play data
        play = api_request(f"corpora/{corpus_name}/plays/{play_name}")

        # Get character data
        characters = api_request(f"corpora/{corpus_name}/plays/{play_name}/characters")

        # Get network data in CSV format
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/networkdata/csv"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        csv_data = response.text

        # Parse CSV data to extract relations using proper CSV parser
        relations = []
        csv_reader = csv.reader(io.StringIO(csv_data))
        rows = list(csv_reader)
        if len(rows) > 1:  # Skip header
            for row in rows[1:]:
                if len(row) >= 4:
                    source = row[0]
                    target = row[2]
                    try:
                        weight = int(row[3])
                    except ValueError:
                        weight = 0

                    # Find character names from IDs
                    source_name = None
                    target_name = None
                    for char in characters:
                        if char.get("id") == source:
                            source_name = char.get("name")
                        if char.get("id") == target:
                            target_name = char.get("name")

                    relations.append({
                        "source": source_name or source,
                        "source_id": source,
                        "target": target_name or target,
                        "target_id": target,
                        "weight": weight
                    })

        # Sort by weight to identify strongest relationships
        relations.sort(key=lambda x: x.get("weight", 0), reverse=True)

        # Try to get relations data if available
        try:
            relations_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/relations/csv"
            relations_response = requests.get(relations_url, timeout=DEFAULT_TIMEOUT)
            formal_relations = []

            if relations_response.status_code == 200:
                csv_reader = csv.reader(io.StringIO(relations_response.text))
                rel_rows = list(csv_reader)
                if len(rel_rows) > 1:  # Skip header
                    for row in rel_rows[1:]:
                        if len(row) >= 4:
                            source = row[0]
                            target = row[2]
                            relation_type = row[3]

                            # Find character names from IDs
                            source_name = None
                            target_name = None
                            for char in characters:
                                if char.get("id") == source:
                                    source_name = char.get("name")
                                if char.get("id") == target:
                                    target_name = char.get("name")

                            formal_relations.append({
                                "source": source_name or source,
                                "target": target_name or target,
                                "type": relation_type
                            })
        except Exception:
            formal_relations = []

        # Get metrics
        metrics = api_request(f"corpora/{corpus_name}/plays/{play_name}/metrics")

        return {
            "play": {
                "title": play.get("title"),
                "author": play.get("authors", [{}])[0].get("name") if play.get("authors") else None,
                "year": play.get("yearNormalized")
            },
            "totalCharacters": len(characters),
            "totalRelations": len(relations),
            "strongestRelations": relations[:10],  # Top 10 strongest relations
            "weakestRelations": relations[-10:] if len(relations) >= 10 else relations,  # Bottom 10
            "formalRelations": formal_relations,  # Explicit relations if available
            "metrics": metrics
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def analyze_play_structure(corpus_name: str, play_name: str) -> Dict:
    """Analyze the structure of a play including acts, scenes, and metrics."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        play = api_request(f"corpora/{corpus_name}/plays/{play_name}")
        metrics = api_request(f"corpora/{corpus_name}/plays/{play_name}/metrics")

        # Extract structural information from segments
        acts = []
        scenes = []
        for segment in play.get("segments", []):
            if segment.get("type") == "act":
                acts.append({
                    "number": segment.get("number"),
                    "title": segment.get("title")
                })
            elif segment.get("type") == "scene":
                scenes.append({
                    "number": segment.get("number"),
                    "title": segment.get("title"),
                    "speakers": segment.get("speakers", [])
                })

        # Get character data
        characters = api_request(f"corpora/{corpus_name}/plays/{play_name}/characters")

        # Count characters by gender
        gender_counts = {"MALE": 0, "FEMALE": 0, "UNKNOWN": 0}
        for character in characters:
            gender = character.get("gender")
            if gender in gender_counts:
                gender_counts[gender] += 1

        # Get spoken text by character data
        spoken_text_by_char = api_request(f"corpora/{corpus_name}/plays/{play_name}/spoken-text-by-character")

        # Calculate total words and distribution
        total_words = sum(char.get("numOfWords", 0) for char in characters)
        speaking_distribution = []

        if total_words > 0:
            for char in characters:
                char_words = char.get("numOfWords", 0)
                speaking_distribution.append({
                    "character": char.get("name"),
                    "words": char_words,
                    "percentage": round((char_words / total_words) * 100, 2)
                })

            # Sort by word count
            speaking_distribution.sort(key=lambda x: x["words"], reverse=True)

        # Get structural information
        structure = {
            "title": play.get("title"),
            "authors": [author.get("name") for author in play.get("authors", [])],
            "year": play.get("yearNormalized"),
            "yearWritten": play.get("yearWritten"),
            "yearPrinted": play.get("yearPrinted"),
            "yearPremiered": play.get("yearPremiered"),
            "acts": acts,
            "scenes": scenes,
            "numOfActs": len(acts),
            "numOfScenes": len(scenes),
            "segments": metrics.get("segments"),
            "dialogues": metrics.get("dialogues"),
            "wordCount": total_words,
            "characters": {
                "total": len(characters),
                "byGender": gender_counts
            },
            "speakingDistribution": speaking_distribution[:10],  # Top 10 characters by speaking time
        }

        return structure
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def find_character_across_plays(character_name: str) -> Dict:
    """Find a character across multiple plays in the DraCor database."""
    try:
        all_corpora = api_request("corpora")
        matches = []

        for corpus in all_corpora:
            corpus_name = corpus["name"]
            corpus_data = api_request(f"corpora/{corpus_name}")

            for play in corpus_data.get("plays", []):
                play_name = play.get("name")

                try:
                    characters = api_request(f"corpora/{corpus_name}/plays/{play_name}/characters")

                    for character in characters:
                        if character_name.lower() in (character.get("name") or "").lower():
                            matches.append({
                                "corpus": corpus_name,
                                "play": play.get("title"),
                                "character": character.get("name"),
                                "gender": character.get("gender"),
                                "numOfSpeechActs": character.get("numOfSpeechActs"),
                                "numOfWords": character.get("numOfWords")
                            })
                except Exception:
                    continue

        return {"matches": matches}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool("analyze_full_text")
def analyze_full_text(corpus_name: str, play_name: str) -> Dict:
    """Analyze the full text of a play, including dialogue and stage directions."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        # Get the TEI XML as primary source
        tei_result = get_tei_text(corpus_name, play_name)
        if "error" in tei_result:
            # Fall back to the plain text if TEI fails
            full_text = get_full_text(corpus_name, play_name)
            if "error" in full_text:
                return {"error": full_text["error"]}
            has_tei = False
            text_content = full_text["text"]
        else:
            has_tei = True
            tei_text = tei_result["tei_text"]

            # Parse TEI XML with proper XML parser
            try:
                root = ET.fromstring(tei_text)

                # Extract title (try with namespace first, then without)
                title_elem = root.find('.//tei:titleStmt/tei:title', TEI_NS)
                if title_elem is None:
                    title_elem = root.find('.//{http://www.tei-c.org/ns/1.0}title')
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Unknown"

                # Extract authors
                author_elems = root.findall('.//tei:titleStmt/tei:author', TEI_NS)
                if not author_elems:
                    author_elems = root.findall('.//{http://www.tei-c.org/ns/1.0}author')
                authors = [a.text.strip() for a in author_elems if a.text] or ["Unknown"]

                # Extract structural elements
                acts = root.findall('.//{http://www.tei-c.org/ns/1.0}div[@type="act"]')
                scenes = root.findall('.//{http://www.tei-c.org/ns/1.0}div[@type="scene"]')
                speeches = root.findall('.//{http://www.tei-c.org/ns/1.0}sp')
                stage_directions = root.findall('.//{http://www.tei-c.org/ns/1.0}stage')

                act_count = len(acts)
                scene_count = len(scenes)
                speech_count = len(speeches)
                stage_direction_count = len(stage_directions)

            except ET.ParseError:
                # Fallback if XML parsing fails
                title = "Unknown"
                authors = ["Unknown"]
                act_count = scene_count = speech_count = stage_direction_count = 0
                speeches = []
                stage_directions = []

            # Also get the plain text for easier processing
            full_text = get_full_text(corpus_name, play_name)
            text_content = full_text.get("text", "")

        # Get play metadata
        play_info = get_play(corpus_name, play_name)
        if "error" in play_info:
            return {"error": play_info["error"]}

        # Get character list
        characters = get_characters(corpus_name, play_name)
        if "error" in characters:
            return {"error": characters["error"]}

        result = {
            "play": play_info.get("play", {}),
            "characters": characters.get("characters", []),
            "text": text_content,
        }

        # Add TEI-specific analysis if available
        if has_tei:
            result["tei_analysis"] = {
                "title": title,
                "authors": authors,
                "structure": {
                    "acts": act_count,
                    "scenes": scene_count,
                    "speeches": speech_count,
                    "stage_directions": stage_direction_count
                },
                "text_sample": {
                    "first_speech": ET.tostring(speeches[0], encoding='unicode', method='text').strip() if speeches else "",
                    "first_stage_direction": ET.tostring(stage_directions[0], encoding='unicode', method='text').strip() if stage_directions else ""
                }
            }

        # Add basic text analysis in either case
        result["analysis"] = {
            "text_length": len(text_content),
            "character_count": len(characters.get("characters", [])),
            "dialogue_to_direction_ratio": text_content.count("\n\nDIALOGUE:") /
                                          (text_content.count("\n\nSTAGE DIRECTIONS:") or 1)
        }

        return result
    except Exception as e:
        return {"error": str(e)}

# Prompt templates using decorators
@mcp.prompt()
def analyze_play(corpus_name: str, play_name: str) -> str:
    """Create a prompt for analyzing a specific play."""
    return f"""
    You are a drama analysis expert who can help analyze plays from the DraCor (Drama Corpora Project) database.

    You have access to the following play:

    Corpus: {corpus_name}
    Play: {play_name}

    Analyze this play in terms of:
    1. Basic information (title, author, year)
    2. Structure (acts, scenes)
    3. Character relationships
    4. Key metrics and statistics

    Please provide a comprehensive analysis including:
    - Historical context of the play
    - Structural analysis
    - Character analysis
    - Network analysis (how characters relate to each other)
    - Notable aspects of this play compared to others from the same period
    """

@mcp.prompt()
def character_analysis(corpus_name: str, play_name: str, character_id: str) -> str:
    """Create a prompt for analyzing a specific character."""
    return f"""
    You are a drama character analysis expert who can help analyze characters from plays in the DraCor database.

    You have access to the following character:

    Corpus: {corpus_name}
    Play: {play_name}
    Character: {character_id}

    Analyze this character in terms of:
    1. Basic information (name, gender)
    2. Importance in the play (based on speech counts, words spoken)
    3. Relationships with other characters
    4. Character development throughout the play

    Please provide a comprehensive character analysis that could help researchers or students understand this character better.
    """

@mcp.prompt()
def network_analysis(corpus_name: str, play_name: str) -> str:
    """Create a prompt for analyzing a character network."""
    return f"""
    You are a network analysis expert who can help analyze character networks from plays in the DraCor database.

    You have access to the following play network:

    Corpus: {corpus_name}
    Play: {play_name}

    Analyze this play's character network in terms of:
    1. Overall network structure and density
    2. Central characters (highest degree, betweenness)
    3. Character communities or groups
    4. Strongest and weakest relationships
    5. How the network structure relates to the themes of the play

    Please provide a comprehensive network analysis that could help researchers understand the social dynamics in this play.
    """

@mcp.prompt()
def comparative_analysis(corpus_name1: str, play_name1: str, corpus_name2: str, play_name2: str) -> str:
    """Create a prompt for comparing two plays."""
    return f"""
    You are a drama analysis expert who can help compare plays from the DraCor database.

    You have access to the following two plays:

    Play 1:
    Corpus: {corpus_name1}
    Play: {play_name1}

    Play 2:
    Corpus: {corpus_name2}
    Play: {play_name2}

    Compare these plays in terms of:
    1. Basic information (title, author, year)
    2. Structure (acts, scenes, length)
    3. Character count and dynamics
    4. Network complexity and density
    5. Historical context and significance

    Please provide a comprehensive comparative analysis that highlights similarities and differences between these plays.
    """

@mcp.prompt()
def gender_analysis(corpus_name: str, play_name: str) -> str:
    """Create a prompt for analyzing gender representation in a play."""
    return f"""
    You are a scholar specializing in gender studies and dramatic literature. You've been asked to analyze gender representation in a drama.

    Corpus: {corpus_name}
    Play: {play_name}

    Please analyze the play in terms of:
    1. Gender distribution of characters
    2. Speaking time and importance of male vs. female characters
    3. Relationships between characters of different genders
    4. Historical context of gender representation in this period
    5. Notable aspects of gender portrayal in this play

    Your analysis should consider both quantitative data (number of characters, speaking lines) and qualitative aspects (power dynamics, character development).
    """

@mcp.prompt()
def historical_context(corpus_name: str, play_name: str) -> str:
    """Create a prompt for analyzing the historical context of a play."""
    return f"""
    You are a theater historian who specializes in putting dramatic works in their historical context.

    Corpus: {corpus_name}
    Play: {play_name}

    Please provide a detailed analysis of the historical context of this play, including:
    1. Political and social climate when the play was written
    2. Theatrical conventions of the period
    3. How contemporary events might have influenced the play
    4. Reception of the play when it was first performed
    5. The play's significance in the author's body of work
    6. How the play reflects or challenges the values of its time

    Your analysis should help modern readers and scholars understand the play within its original historical framework.
    """

@mcp.prompt("full_text_analysis")
def full_text_analysis_prompt() -> str:
    """Template for analyzing the full text of a play."""
    return """
    I'll analyze the full text of {play_title} by {author} from the {corpus_name} corpus.

    ## Basic Information
    - Title: {play_title}
    - Author: {author}
    - Written: {written_year}
    - Premiere: {premiere_date}

    ## Full Text Analysis

    {analysis}

    ## Key Themes and Motifs

    {themes}

    ## Language and Style

    {style}

    ## Historical and Cultural Context

    {context}
    """

@mcp.prompt("character_tagging_analysis")
def character_tagging_analysis(corpus_name: str = "dutch", play_name: str = None) -> str:
    """Template for analyzing character ID tagging issues in plays.

    Parameters:
    - corpus_name: The corpus to analyze (default: "dutch")
    - play_name: The specific play to analyze
    """
    prompt_text = f"""
    Your task is to analyze '{play_name}' from the {corpus_name} corpus in the DraCor database to identify character ID tagging issues. Specifically:

    1. Perform a comprehensive analysis of:
       * Character relations
       * Full text (especially TEI format)
       * Play structure

    2. Identify all possible inconsistencies in character ID tagging, including:
       * Spelling variations of character names
       * Character name confusion or conflation
       * Historical spelling variants
       * Discrepancies between character IDs and stage directions

    3. Create a detailed report of potential character ID tagging errors in a structured table format with the following columns:
       * Text ID: {corpus_name}/{play_name}
       * Current character ID used in the database
       * Problematic variant(s) found in the text
       * Type of error (spelling, variation, confusion, etc.)
       * Explanation of the issue
    """

    # If no specific play is provided, add instructions to select one
    if not play_name:
        prompt_text = """
        Your task is to analyze a play from the {corpus_name} corpus in the DraCor database to identify character ID tagging issues.

        First, use the search_plays tool to find available plays in the {corpus_name} corpus, then select one for analysis.

        Once you've selected a play, perform a comprehensive analysis of:
        1. Character relations
        2. Full text (especially TEI format)
        3. Play structure

        Identify all possible inconsistencies in character ID tagging, including:
        * Spelling variations of character names
        * Character name confusion or conflation
        * Historical spelling variants
        * Discrepancies between character IDs and stage directions

        Create a detailed report of potential character ID tagging errors in a structured table format with the following columns:
        * Text ID (unique identifier for the play)
        * Current character ID used in the database
        * Problematic variant(s) found in the text
        * Type of error (spelling, variation, confusion, etc.)
        * Explanation of the issue
        """

    return prompt_text
