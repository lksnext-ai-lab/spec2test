# Input Processor Module

A specialized component of the TFM-LLM2e system that processes and analyzes input files for automated test scenario generation. This module serves as an MCP (Model Context Protocol) server that can handle video recordings of browser sessions plus PDF, Markdown, and plain text documentation, extracting valuable information for test automation.

## Features

- **Video Processing**: Analyzes MP4 recordings of browser sessions to extract UI interactions, workflows, and user journeys
- **PDF Processing**: Extracts requirements, specifications, and business rules from PDF documents
- **Markdown Processing**: Reads Markdown documents and enriches local image references with generated descriptions when available
- **Text Processing**: Reads plain text documents without additional preprocessing
- **Intelligent Caching**: Implements SHA-256 hash-based caching to avoid reprocessing files
- **MCP Server**: Provides tools accessible via Model Context Protocol for integration with AI agents
- **Structured Output**: Formats analysis results for automated test scenario generation

## Architecture

The module consists of two main components:

1. **`FileProcessor`** (`file_processor.py`): Core processing logic for analyzing files
2. **`FastMCP Server`** (`main.py`): MCP server exposing processing capabilities as tools

## File Processing Capabilities

### Video Analysis (.mp4)
The video processor uses a multimodal LLM to analyze browser session recordings and extract:

- **Visual Elements**: Layout, navigation bars, forms, buttons, input fields, tables, modals
- **User Interactions**: Complete user journey, form submissions, navigation flows
- **Key Functionality**: CRUD operations, search/filter functionality, main features
- **Detailed Timeline**: Timestamped action sequences with specific data entered
- **Technical Details**: URLs, error messages, data models, API calls
- **Test Automation Data**: Reusable patterns, edge cases, data dependencies

> **Note on video processing per provider:**
> - **Google Gemini** — native video upload (base64-encoded MP4).
> - **OpenAI / Anthropic** — frames are extracted at 2 s intervals and sent as `image_url` content blocks (max 20 frames).
> - **DeepSeek** — text-only provider. No vision/multimodal API support (as of May 2026). Falls back to metadata-only analysis: frame count, timestamps, resolution changes. For full visual analysis, use Google Gemini or OpenAI.

### PDF Analysis (.pdf)
The PDF processor extracts text content and uses LLM analysis to identify:

- **Requirements**: Key specifications and functional requirements
- **User Stories**: Use cases and user scenarios
- **Business Rules**: Constraints and validation rules
- **Data Models**: Entities and data structures
- **Workflows**: Process flows and business logic
- **Acceptance Criteria**: Test conditions and success metrics

### Markdown Analysis (.md)
Markdown files are read directly and, when a Google API key is available, local image references are enriched with generated descriptions before the content is summarized.

### Text Analysis (.txt)
Plain text files are read directly without preprocessing and summarized with the same document analysis flow used for other documentation inputs.

## API Reference

The module exposes three MCP tools:

### `process_files`
Processes all supported files in the configured input directory (`/app/inputs/`).

**Parameters:**
- The input and cache directories are currently fixed by the MCP server at
   `/app/inputs/` and `/app/inputs/.cache/`.

**Returns:**
- Detailed analysis results for all processed files, formatted for test scenario generation

**Example:**
```python
# Process all files in the directory mounted as /app/inputs
result = await process_files()
```

### `list_processed_files`
Lists all processed files with metadata.

**Parameters:**
- No parameters. The cache directory is `/app/inputs/.cache/`.

**Returns:**
- CSV-formatted list with original filename, format, file size, and unique hash identifier

**Example:**
```python
# List all processed files
files_list = await list_processed_files()
```

### `get_processed_content`
Retrieves detailed analysis results for a specific file.

**Parameters:**
- `file_hash` (str, required): SHA-256 hash of the processed file

**Returns:**
- Complete analysis results for the specified file

**Example:**
```python
# Get content for a specific file
content = await get_processed_content(file_hash="abc123def456...")
```

### `get_all_processed_content`

Returns the complete cached content for every processed file as a JSON array. This is
useful when a downstream generator needs to combine several documents and recordings.

## Core Classes

### FileProcessor

The main processing class that handles file analysis and caching.

#### Constructor
```python
FileProcessor(input_dir="/app/inputs/", cache_dir="/app/inputs/.cache/")
```

#### Key Methods

**`process_all_files() -> List[str]`**
- Processes all supported files in the input directory
- Returns list of file hashes for successfully processed files

**`process_file(file_path: Path) -> Optional[str]`**
- Processes a single file based on its format
- Returns file hash if successful, None otherwise

**`get_cached_content(file_hash: str) -> Optional[str]`**
- Retrieves cached content by hash
- Returns cached analysis or None if not found

**`get_file_hash(file_path: Path) -> str`**
- Generates SHA-256 hash of file content
- Used for caching and file identification

**`is_processed(file_hash: str) -> bool`**
- Checks if file is already processed and cached
- Prevents unnecessary reprocessing

#### Private Methods

**`process_video(file_path: Path) -> str`**
- Processes MP4 video files using Gemini 2.0 Flash
- Extracts UI elements, workflows, and interaction patterns

**`process_pdf(file_path: Path) -> str`**
- Extracts text from PDF files using PyPDF2
- Analyzes content for requirements and specifications

**`process_text_document(file_path: Path) -> str`**
- Reads Markdown and plain text files
- Enriches Markdown images when preprocessing is available
- Analyzes content for requirements and specifications

**`create_cache_file(file_path: Path, file_hash: str, processed_content: str)`**
- Creates cache file with metadata and processed content
- Stores results in CSV format with analysis content

## Installation & Setup

### Requirements
```bash
pip install -r requirements.txt
```

**Dependencies:**
- `langgraph`: Graph-based workflow management
- `langchain`: LLM integration framework
- `langchain-google-genai`: Google Gemini integration
- `google-generativeai`: Google AI client
- `langchain-mcp-adapters`: MCP protocol adapters
- `PyPDF2`: PDF processing library

### Environment Variables
Ensure you have the following environment variables set:
- `GOOGLE_API_KEY`: Your Google AI API key for Gemini access

### Docker Usage

Build the Docker image:
```bash
docker build -t input-processor .
```

Run the container:
```bash
docker run -d -p 8003:8000 -v /path/to/inputs:/app/inputs input-processor
```

The container listens on port `8000`; `8003` is only the example host port. With the
root Compose file, use `http://localhost:8003/mcp`.

### Direct Usage

Run the MCP server:
```bash
python src/main.py
```

Or process files directly:
```bash
python src/file_processor.py
```

## Usage Examples

### Basic Processing Workflow

1. **Place files in input directory**
   - Add MP4 video recordings of browser sessions
   - Add PDF, Markdown, or text documents with requirements/specifications

2. **Process all files**
   ```python
   result = await process_files()
   ```

3. **List processed files**
   ```python
   files_list = await list_processed_files()
   ```

4. **Retrieve specific content**
   ```python
   content = await get_processed_content(file_hash="your_file_hash")
   ```

### Integration with Test Generation

The processed content is specifically formatted for automated test scenario generation:

```python
# Get processed video analysis
video_analysis = await get_processed_content(video_hash)
# Contains: UI elements, user workflows, interaction patterns

# Get processed document requirements
document_requirements = await get_processed_content(document_hash)
# Contains: User stories, business rules, acceptance criteria, and Markdown image context when available

# Use both for comprehensive test generation
test_scenarios = generate_test_scenarios(video_analysis, document_requirements)
```

## File Structure

```
input-processor/
├── src/
│   ├── main.py              # MCP server implementation
│   ├── file_processor.py    # Core processing logic
├── Dockerfile               # Container configuration
├── requirements.txt         # Python dependencies
└── README.md               # This documentation
```

## Output Format

### Video Analysis Output
```
File Hash: abc123def456...
Original Name: browser_session.mp4
Format: .mp4
File Size: 15728640

PROCESSED CONTENT:
==================

**Visual Elements and UI Components:**
- Navigation bar with logo, menu items, user profile
- Search form with input field and filter dropdown
- Data table with sortable columns
- Modal dialogs for form submissions

**User Interactions and Workflows:**
(0:00) Home Page: User lands on dashboard
(0:03) Click "Search": User clicks search button
(0:05) Enter Query: User types "test data" in search field
...

**Test Scenario Relevance:**
- Login workflow automation
- Search functionality testing
- Form validation scenarios
```

### PDF Analysis Output
```
File Hash: def789ghi012...
Original Name: requirements.pdf
Format: .pdf
File Size: 2048576

PROCESSED CONTENT:
==================

**Key Requirements:**
- User authentication system
- Data validation rules
- Search and filtering capabilities

**User Stories:**
- As a user, I want to search for records
- As an admin, I want to manage user accounts

**Business Rules:**
- Passwords must be at least 8 characters
- Search results limited to 100 items
...
```

## Error Handling

The module includes comprehensive error handling:

- **File Access Errors**: Graceful handling of missing or inaccessible files
- **Processing Errors**: Continued processing even if individual files fail
- **Cache Errors**: Automatic cache directory creation and validation
- **LLM Errors**: Retry logic and fallback mechanisms
- **PDF Encryption**: Automatic decryption attempts for encrypted PDFs

## Performance Considerations

- **Caching**: Processed files are cached to avoid redundant processing
- **Memory Management**: Large files are processed in chunks
- **Async Processing**: MCP server supports concurrent requests
- **Resource Limits**: Configurable timeouts and retry mechanisms

## Integration Points

This module integrates with other TFM-LLM2e components:

1. **Gherkin Generator**: Consumes processed analysis for feature file generation
2. **Step Definition Generator**: Uses UI analysis for test automation code
3. **Web Crawler**: Complements video analysis with additional site structure data

## Contributing

When extending this module:

1. Add new file format support by extending `supported_formats`
2. Implement new processing methods following the existing pattern
3. Update the MCP tools to expose new functionality
4. Ensure proper error handling and caching
5. Add comprehensive documentation for new features

## License

This module is part of the TFM-LLM2e project and follows the same licensing terms.
