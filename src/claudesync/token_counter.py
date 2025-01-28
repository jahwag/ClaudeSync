# src/claudesync/token_counter.py

import logging
import tiktoken
import os
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class TokenCounter:
    """Counts tokens in text content using TikToken with cl100k_base encoding."""
    
    def __init__(self):
        """Initialize the token counter with cl100k_base encoding."""
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error(f"Failed to initialize TikToken encoding: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in the given text using cl100k_base encoding.
        
        Args:
            text (str): The text to count tokens in
            
        Returns:
            int: Number of tokens in the text
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return 0

    def count_file_tokens(self, file_path: str) -> Tuple[int, bool]:
        """
        Count tokens in a file.
        
        Args:
            file_path (str): Path to the file to count tokens in
            
        Returns:
            Tuple[int, bool]: (token count, success flag)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.count_tokens(content), True
        except UnicodeDecodeError:
            logger.warning(f"File {file_path} is not valid UTF-8 text")
            return 0, False
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return 0, False

def count_project_tokens(config, files_config, root_path: str) -> Dict[str, int]:
    """
    Count tokens in all files that would be synchronized.
    
    Args:
        config: Configuration manager instance
        files_config: Files configuration dictionary
        root_path (str): Root path of the project
        
    Returns:
        Dict[str, int]: Dictionary mapping file paths to token counts
    """
    from claudesync.utils import get_local_files
    
    # Get files that would be synced using existing logic
    files_to_sync = get_local_files(config, root_path, files_config)
    
    token_counter = TokenCounter()
    token_counts = {}
    total_tokens = 0
    failed_files = []
    
    for rel_path in files_to_sync:
        full_path = os.path.join(root_path, rel_path)
        tokens, success = token_counter.count_file_tokens(full_path)
        if success:
            token_counts[rel_path] = tokens
            total_tokens += tokens
        else:
            failed_files.append(rel_path)
            
    return {
        'files': token_counts,
        'total': total_tokens,
        'failed_files': failed_files
    }
