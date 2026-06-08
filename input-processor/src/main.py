import uvicorn
import csv
import json
from io import StringIO
from mcp.server.fastmcp import FastMCP
from file_processor import FileProcessor
from pathlib import Path

mcp = FastMCP("TFM-InputProcessor", stateless_http=True, json_response=True)

# Initialize the processor once
processor = FileProcessor()

@mcp.tool()
async def process_files(
) -> str:
    """
    Process and analyze files for automated test scenario generation.
    
    Supports video recordings (MP4) of browser sessions and documentation files
    in PDF, Markdown, and plain text formats.
    Videos are analyzed to extract UI interactions, workflows, and user journeys.
    PDFs are processed to extract requirements, specifications, and business rules.
    Markdown files enrich local images with generated descriptions when available,
    while text files are read without preprocessing.
    
    Returns:
        JSON string containing a list of processed file hashes and metadata:
        - Original Name: Original filename
        - Format: File format (.mp4, .pdf, .md, .txt)
        - File Size: Size in bytes
        - Hash: Unique identifier for retrieving content
    """
    input_dir: str = "/app/inputs/"
    cache_dir: str = "/app/inputs/.cache/"

    processor.input_dir = Path(input_dir)
    processor.cache_dir = Path(cache_dir)
    processor.cache_dir.mkdir(exist_ok=True)
    
    processed_files = processor.process_all_files()
    
    if not processed_files:
        return json.dumps([])
    
    # Return metadata for processed files
    results = []
    for file_hash in processed_files:
        cache_file = processor.cache_dir / f"{file_hash}.txt"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        results.append({
                            "Original Name": row.get("original_name", ""),
                            "Format": row.get("format", ""),
                            "File Size": row.get("file_size", ""),
                            "Hash": row.get("hash", "")
                        })
                        break
            except Exception as e:
                print(f"Error reading cache file {cache_file.name}: {str(e)}")
                continue
    
    return json.dumps(results)

@mcp.tool()
async def list_processed_files() -> str:
    """
    List all processed files with their identifiers.
    
    Returns a simple list of available processed files showing only the filename
    and unique hash identifier needed for content retrieval.
        
    Returns:
        JSON string containing a list of file objects:
        - Original Name: Original filename
        - Hash: Unique identifier for retrieving file content
    """
    cache_dir: str = "/app/inputs/.cache/"
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return json.dumps([])
    
    cache_files = list(cache_path.glob("*.txt"))
    if not cache_files:
        return json.dumps([])
    
    results = []
    
    for cache_file in cache_files:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only return name and hash
                    results.append({
                        "Original Name": row.get("original_name", ""),
                        "Hash": row.get("hash", "")
                    })
                    break
        except Exception as e:
            print(f"Error reading cache file {cache_file.name}: {str(e)}")
            continue
    
    return json.dumps(results)

@mcp.tool()
async def get_processed_content(file_hash: str = "") -> str:
    """
    Retrieve detailed analysis results for a single file.
    
    Returns the complete processed analysis of a specific file, ready for use in
    generating automated test scenarios. Content includes UI element identification,
    user workflow analysis, requirements extraction, and technical details needed
    for test automation.
    
    Args:
        file_hash: SHA-256 hash of the processed file (obtain from list_processed_files)
    
    Returns:
        Complete analysis results including:
        - Video files: UI components, user interactions, workflows, timestamps, technical details
                - Document files (.pdf, .md, .txt): Requirements, user stories, business rules,
                    data models, acceptance criteria, and image context when available
        All structured for automated test scenario generation
    """
    if not file_hash or not file_hash.strip():
        return "Error: file_hash parameter is required and cannot be empty. Use list_processed_files to get available hashes."
    
    content = processor.get_cached_content(file_hash)
    if content:
        return content
    return f"No cached content found for hash: {file_hash}. Use list_processed_files to see available files."

@mcp.tool()
async def get_all_processed_content() -> str:
    """
    Retrieve detailed analysis results for all processed files.
    
    Returns the complete processed analysis of all available files in a single request.
    Use this when you need all file content at once without making individual calls
    for each file hash.
    
    Returns:
        JSON string containing a list of processed file objects:
        - file_hash: Unique identifier for the file
        - content: Detailed analysis results including UI components, workflows,
                   requirements, user stories, and business rules
    """
    cache_dir: str = "/app/inputs/.cache/"
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return json.dumps([])
    
    cache_files = list(cache_path.glob("*.txt"))
    if not cache_files:
        return json.dumps([])
    
    results = []
    
    for cache_file in cache_files:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    file_hash = row.get("Hash", "")
                    if file_hash:
                        content = processor.get_cached_content(file_hash)
                        if content:
                            results.append({
                                "file_hash": file_hash,
                                "content": content
                            })
                    break
        except Exception as e:
            print(f"Error reading cache file {cache_file.name}: {str(e)}")
            continue
    
    return json.dumps(results)

if __name__ == "__main__":
    """Run the MCP server"""
    # Assign app to variable to avoid "ASGI app factory detected" warning
    app = mcp.streamable_http_app
    uvicorn.run(app, host="0.0.0.0", port=8000)