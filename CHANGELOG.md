# Changelog

All notable changes to the DraCor MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Input validation**: Added `validate_name()` helper function that validates corpus and play name parameters against a whitelist regex (`^[a-zA-Z0-9_-]+$`). This prevents potential path traversal attacks since these values are interpolated into API URL paths. Applied to all 17 resource and tool functions that accept `corpus_name` or `play_name` parameters.

- **Request timeouts**: Added `DEFAULT_TIMEOUT = 30` constant and applied 30-second timeout to all 10 `requests.get()` calls. This prevents the server from hanging indefinitely if the DraCor API is slow or unresponsive.

### Fixed

- **CSV parsing**: Replaced manual string splitting (`line.split(',')`) with Python's `csv` module in `analyze_character_relations()`. Manual splitting fails on quoted fields that contain commas or newlines. The `csv.reader` handles all edge cases per RFC 4180.

- **XML/TEI parsing**: Replaced regex-based XML parsing with `xml.etree.ElementTree` in `analyze_full_text()`. Regex cannot reliably parse XML due to nested tags, CDATA sections, XML entities, and namespaces. Added `TEI_NS` namespace constant for proper namespace-aware XPath queries. Added `ET.ParseError` fallback for graceful degradation.

- **Exception handling**: Replaced 5 bare `except:` clauses with `except Exception:` in `search_plays()`, `analyze_character_relations()`, and `find_character_across_plays()`. Bare `except:` catches `SystemExit` and `KeyboardInterrupt`, which prevents graceful shutdown via Ctrl+C.

### Changed

- Added imports: `csv`, `io`, `xml.etree.ElementTree as ET` (all standard library)
- Added constants: `DEFAULT_TIMEOUT`, `VALID_NAME_PATTERN`, `TEI_NS`
- Text samples in `analyze_full_text()` now use `ET.tostring(..., method='text')` to extract clean text content from XML elements

## [0.1.0] - Initial Release

### Added

- FastMCP implementation (`dracor_mcp_fastmcp.py`) with decorator-based API
- Resources for accessing corpora, plays, characters, text, and network data
- Tools: `search_plays`, `compare_plays`, `analyze_character_relations`, `analyze_play_structure`, `find_character_across_plays`, `analyze_full_text`
- Prompt templates for play analysis, character analysis, network analysis, and more
- Support for TEI XML and plain text retrieval
- Docker support
- UV package manager support
