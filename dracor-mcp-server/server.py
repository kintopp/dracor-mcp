#!/usr/bin/env python3
"""
DraCor MCP Server - HTTP streaming server implementation.

This module contains the MCP server definition with all resources, tools, and prompts
for interacting with the Drama Corpora Project (DraCor) API v1.  It is configured for
stateless HTTP deployment (e.g. Railway) with DNS rebinding protection disabled.
"""

from typing import Any, Dict, Optional
import requests
import re
import csv
import io
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import os

# Base API URL for DraCor v1
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


# Validation pattern for Wikidata IDs (Q followed by digits)
VALID_WIKIDATA_PATTERN = re.compile(r'^Q\d+$')


def validate_wikidata_id(wikidata_id: str) -> str:
    """Validate Wikidata ID format (Q followed by digits, e.g. Q42)."""
    if not wikidata_id:
        raise ValueError("wikidata_id cannot be empty")
    if not VALID_WIKIDATA_PATTERN.match(wikidata_id):
        raise ValueError("Invalid wikidata_id: must be Q followed by digits (e.g., Q42)")
    return wikidata_id


def get_first_author(play_data: Dict, default: str = None) -> Optional[str]:
    """Extract the first author name from play data, or return a default."""
    authors = play_data.get("authors")
    if authors:
        return authors[0].get("name", default)
    return default


# Configure transport security for Railway deployment
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

# Create the FastMCP server instance with HTTP configuration
mcp = FastMCP(
    "DraCor API v1",
    stateless_http=True,
    transport_security=transport_security,
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


def api_request(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Make a request to the DraCor API v1."""
    url = f"{DRACOR_API_BASE_URL}/{endpoint}"
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Resource implementations
# ---------------------------------------------------------------------------

@mcp.resource("info://")
def get_api_info() -> Dict:
    """Get API information and version details."""
    try:
        return api_request("info")
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpora://")
def get_corpora() -> Dict:
    """List of all available corpora (collections of plays)."""
    try:
        return {"corpora": api_request("corpora")}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpus://{corpus_name}")
def get_corpus(corpus_name: str) -> Dict:
    """Information about a specific corpus."""
    try:
        validate_name(corpus_name, "corpus_name")
        return api_request(f"corpora/{corpus_name}")
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpus_metadata://{corpus_name}")
def get_corpus_metadata(corpus_name: str) -> Dict:
    """Get metadata for all plays in a corpus."""
    try:
        validate_name(corpus_name, "corpus_name")
        return {"metadata": api_request(f"corpora/{corpus_name}/metadata")}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("plays://{corpus_name}")
def get_plays(corpus_name: str) -> Dict:
    """List of plays in a specific corpus."""
    try:
        validate_name(corpus_name, "corpus_name")
        corpus_data = api_request(f"corpora/{corpus_name}")
        return {"plays": corpus_data.get("plays", [])}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("play://{corpus_name}/{play_name}")
def get_play(corpus_name: str, play_name: str) -> Dict:
    """Information about a specific play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        return api_request(f"corpora/{corpus_name}/plays/{play_name}")
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("play_metrics://{corpus_name}/{play_name}")
def get_play_metrics(corpus_name: str, play_name: str) -> Dict:
    """Get network metrics for a specific play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        return api_request(f"corpora/{corpus_name}/plays/{play_name}/metrics")
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("characters://{corpus_name}/{play_name}")
def get_characters(corpus_name: str, play_name: str) -> Dict:
    """List of characters in a specific play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        return {"characters": api_request(f"corpora/{corpus_name}/plays/{play_name}/characters")}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("spoken_text://{corpus_name}/{play_name}")
def get_spoken_text(corpus_name: str, play_name: str) -> Dict:
    """Get the spoken text for a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return {"text": response.text}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("spoken_text_by_character://{corpus_name}/{play_name}")
def get_spoken_text_by_character(corpus_name: str, play_name: str) -> Dict:
    """Get spoken text for each character in a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        return {"text_by_character": api_request(f"corpora/{corpus_name}/plays/{play_name}/spoken-text-by-character")}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("stage_directions://{corpus_name}/{play_name}")
def get_stage_directions(corpus_name: str, play_name: str) -> Dict:
    """Get all stage directions of a play (plain text)."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/stage-directions"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return {"text": response.text}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("network_data://{corpus_name}/{play_name}")
def get_network_data(corpus_name: str, play_name: str) -> Dict:
    """Get network data of a play in CSV format."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/networkdata/csv"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return {"csv_data": response.text}
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
        return {"relations": response.json()}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("full_text://{corpus_name}/{play_name}")
def get_full_text(corpus_name: str, play_name: str) -> Dict:
    """Get the full text of a play in plain text format."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        stage_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/stage-directions"
        stage_response = requests.get(stage_url, timeout=DEFAULT_TIMEOUT)
        stage_response.raise_for_status()

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
        return {"tei_text": response.text}
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("character_by_wikidata://{wikidata_id}")
def get_plays_with_character(wikidata_id: str) -> Dict:
    """List plays having a character identified by Wikidata ID."""
    try:
        validate_wikidata_id(wikidata_id)
        return {"plays": api_request(f"character/{wikidata_id}")}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

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
        corpora_result = get_corpora()
        if "error" in corpora_result:
            return {"error": corpora_result["error"]}

        all_corpora = corpora_result.get("corpora", [])
        if corpus_name:
            target_corpora = [corp for corp in all_corpora if corpus_name.lower() in corp.get("name", "").lower()]
        else:
            target_corpora = all_corpora

        results = []
        detailed_results = []

        for corpus in target_corpora:
            current_corpus_name = corpus.get("name")

            plays_result = get_plays(current_corpus_name)
            if "error" in plays_result:
                continue

            for play in plays_result.get("plays", []):
                # Apply text search filter
                if query:
                    searchable_text = " ".join([
                        play.get("title", ""),
                        " ".join(a.get("name", "") for a in play.get("authors", [])),
                        play.get("subtitle", ""),
                        play.get("originalTitle", ""),
                    ]).lower()
                    if query.lower() not in searchable_text:
                        continue

                # Apply country filter
                if country:
                    play_country = " ".join([
                        play.get("writtenIn", ""),
                        play.get("printedIn", ""),
                        " ".join(a.get("country", "") for a in play.get("authors", [])),
                    ]).lower()
                    if country.lower() not in play_country:
                        continue

                # Apply language filter
                if language:
                    if language.lower() not in play.get("originalLanguage", "").lower():
                        continue

                # Apply author filter
                if author:
                    author_names = [a.get("name", "").lower() for a in play.get("authors", [])]
                    if not any(author.lower() in name for name in author_names):
                        continue

                # Apply year range filter
                if year_from or year_to:
                    play_year = play.get("yearNormalized") or play.get("yearWritten") or play.get("yearPrinted")
                    if play_year is not None:
                        if year_from and play_year < year_from:
                            continue
                        if year_to and play_year > year_to:
                            continue

                # Fetch characters once for both character_name and gender_filter checks
                characters_list = None
                if character_name or gender_filter:
                    try:
                        current_play_name = play.get("name")
                        characters_result = get_characters(current_corpus_name, current_play_name)
                        if "error" not in characters_result:
                            characters_list = characters_result.get("characters", [])
                    except Exception:
                        pass

                # Apply character name filter
                if character_name:
                    if characters_list is None:
                        continue
                    if not any(character_name.lower() in c.get("name", "").lower() for c in characters_list):
                        continue

                # Apply gender ratio filter
                if gender_filter:
                    if characters_list is not None:
                        try:
                            male_count = sum(1 for c in characters_list if c.get("gender") == "MALE")
                            female_count = sum(1 for c in characters_list if c.get("gender") == "FEMALE")
                            total = male_count + female_count

                            if total > 0:
                                female_ratio = female_count / total
                                if gender_filter == "female_dominated" and female_ratio <= 0.5:
                                    continue
                                elif gender_filter == "male_dominated" and female_ratio >= 0.5:
                                    continue
                                elif gender_filter == "balanced" and (female_ratio < 0.4 or female_ratio > 0.6):
                                    continue
                        except Exception:
                            pass

                # All filters passed -- add to results
                results.append({
                    "corpus": current_corpus_name,
                    "play": play
                })

                # Collect detailed info for the first 5 matches
                if len(detailed_results) < 5:
                    try:
                        current_play_name = play.get("name")
                        play_info = get_play(current_corpus_name, current_play_name)

                        if "error" not in play_info:
                            detailed_results.append({
                                "corpus": current_corpus_name,
                                "play_name": current_play_name,
                                "title": play.get("title"),
                                "author": get_first_author(play, "Unknown"),
                                "year": play.get("yearNormalized"),
                                "language": play.get("originalLanguage"),
                                "characters": len(play_info.get("characters", [])),
                                "link": f"https://dracor.org/{current_corpus_name}/{current_play_name}"
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

        return {
            "plays": [
                {
                    "title": play1.get("title"),
                    "author": get_first_author(play1),
                    "year": play1.get("yearNormalized"),
                    "metrics": metrics1
                },
                {
                    "title": play2.get("title"),
                    "author": get_first_author(play2),
                    "year": play2.get("yearNormalized"),
                    "metrics": metrics2
                }
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def analyze_character_relations(corpus_name: str, play_name: str) -> Dict:
    """Analyze the character relationships in a play."""
    try:
        validate_name(corpus_name, "corpus_name")
        validate_name(play_name, "play_name")

        play = api_request(f"corpora/{corpus_name}/plays/{play_name}")
        characters = api_request(f"corpora/{corpus_name}/plays/{play_name}/characters")

        # Fetch co-occurrence network (CSV format)
        url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/networkdata/csv"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        char_lookup = {char.get("id"): char.get("name") for char in characters}

        # Parse CSV network data into relation dicts
        relations = []
        rows = list(csv.reader(io.StringIO(response.text)))
        for row in rows[1:]:  # skip header
            if len(row) >= 4:
                source, target = row[0], row[2]
                try:
                    weight = int(row[3])
                except ValueError:
                    weight = 0
                relations.append({
                    "source": char_lookup.get(source, source),
                    "source_id": source,
                    "target": char_lookup.get(target, target),
                    "target_id": target,
                    "weight": weight
                })

        relations.sort(key=lambda x: x.get("weight", 0), reverse=True)

        # Fetch explicit (formal) relations if available
        formal_relations = []
        try:
            relations_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/relations/csv"
            relations_response = requests.get(relations_url, timeout=DEFAULT_TIMEOUT)
            if relations_response.status_code == 200:
                rel_rows = list(csv.reader(io.StringIO(relations_response.text)))
                for row in rel_rows[1:]:  # skip header
                    if len(row) >= 4:
                        source, target = row[0], row[2]
                        formal_relations.append({
                            "source": char_lookup.get(source, source),
                            "target": char_lookup.get(target, target),
                            "type": row[3]
                        })
        except Exception:
            formal_relations = []

        metrics = api_request(f"corpora/{corpus_name}/plays/{play_name}/metrics")

        return {
            "play": {
                "title": play.get("title"),
                "author": get_first_author(play),
                "year": play.get("yearNormalized")
            },
            "totalCharacters": len(characters),
            "totalRelations": len(relations),
            "strongestRelations": relations[:10],
            "weakestRelations": relations[-10:] if len(relations) >= 10 else relations,
            "formalRelations": formal_relations,
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
        characters = api_request(f"corpora/{corpus_name}/plays/{play_name}/characters")

        # Classify segments into acts and scenes
        acts = []
        scenes = []
        for segment in play.get("segments", []):
            segment_type = segment.get("type")
            if segment_type == "act":
                acts.append({
                    "number": segment.get("number"),
                    "title": segment.get("title")
                })
            elif segment_type == "scene":
                scenes.append({
                    "number": segment.get("number"),
                    "title": segment.get("title"),
                    "speakers": segment.get("speakers", [])
                })

        # Count characters by gender
        gender_counts = {"MALE": 0, "FEMALE": 0, "UNKNOWN": 0}
        for character in characters:
            gender = character.get("gender")
            if gender in gender_counts:
                gender_counts[gender] += 1

        # Build speaking distribution sorted by word count
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
            speaking_distribution.sort(key=lambda x: x["words"], reverse=True)

        return {
            "title": play.get("title"),
            "authors": [a.get("name") for a in play.get("authors", [])],
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
            "speakingDistribution": speaking_distribution[:10],
        }
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

                title_elem = root.find('.//tei:titleStmt/tei:title', TEI_NS)
                if title_elem is None:
                    title_elem = root.find('.//{http://www.tei-c.org/ns/1.0}title')
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Unknown"

                author_elems = root.findall('.//tei:titleStmt/tei:author', TEI_NS)
                if not author_elems:
                    author_elems = root.findall('.//{http://www.tei-c.org/ns/1.0}author')
                authors = [a.text.strip() for a in author_elems if a.text] or ["Unknown"]

                acts = root.findall('.//{http://www.tei-c.org/ns/1.0}div[@type="act"]')
                scenes = root.findall('.//{http://www.tei-c.org/ns/1.0}div[@type="scene"]')
                speeches = root.findall('.//{http://www.tei-c.org/ns/1.0}sp')
                stage_directions = root.findall('.//{http://www.tei-c.org/ns/1.0}stage')

                act_count = len(acts)
                scene_count = len(scenes)
                speech_count = len(speeches)
                stage_direction_count = len(stage_directions)

            except ET.ParseError:
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
            "play": play_info,
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
        dialogue_count = text_content.count("\n\nDIALOGUE:")
        direction_count = text_content.count("\n\nSTAGE DIRECTIONS:")
        result["analysis"] = {
            "text_length": len(text_content),
            "character_count": len(characters.get("characters", [])),
            "dialogue_to_direction_ratio": dialogue_count / direction_count if direction_count > 0 else None
        }

        return result
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

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
