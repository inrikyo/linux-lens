#!/usr/bin/env python
import json
import sys
import re
import easyocr
from PIL import Image
import numpy as np

def format_with_layout(result, img_width, img_height):
    """
    Reconstruct text layout using bounding box coordinates.
    Preserves indentation, spacing, and structure.
    """
    if not result:
        return ""
    
    # Group by Y-coordinate (vertical position)
    lines = {}
    tolerance = img_height * 0.02  # 2% tolerance for same line
    
    for bbox, text, confidence in result:
        # Get center Y of bounding box
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        
        # Find which line this belongs to
        line_key = None
        for key in lines:
            if abs(key - y_center) < tolerance:
                line_key = key
                break
        
        if line_key is None:
            line_key = y_center
            lines[line_key] = []
        
        # Store text with its X position
        x_min = bbox[0][0]
        lines[line_key].append((x_min, text))
    
    # Sort lines by Y position (top to bottom)
    sorted_lines = sorted(lines.items())
    
    # Build text with preserved indentation
    formatted_lines = []
    for _, line_items in sorted_lines:
        # Sort by X position (left to right)
        line_items.sort(key=lambda x: x[0])
        
        # Calculate indentation levels
        if line_items:
            min_x = line_items[0][0]
            # Estimate character width (rough but effective)
            char_width = img_width / 100
            
            # Build line with spaces for indentation
            line_parts = []
            last_x = min_x
            
            for x, text in line_items:
                # Calculate spaces needed based on X position difference
                if x > last_x + char_width:
                    spaces = min(int((x - last_x) / char_width), 8)  # Max 8 spaces
                    line_parts.append(' ' * spaces)
                
                line_parts.append(text)
                last_x = x + (len(text) * char_width)
            
            formatted_lines.append(''.join(line_parts))
    
    return '\n'.join(formatted_lines)

def detect_and_format_code(text):
    """
    Detect code blocks and format them with markdown
    Also detects language when possible
    """
    if not text:
        return text
    
    lines = text.split('\n')
    in_code_block = False
    code_lines = []
    formatted_lines = []
    
    # Patterns for code detection
    code_patterns = [
        r'^\s{2,}',           # Indented lines
        r'^\t',                # Tab indentation
        r'\{|\}',              # Braces
        r'\(.*\)\s*\{',       # Function definition
        r'def\s+\w+\s*\(',    # Python function
        r'class\s+\w+',       # Python class
        r'import\s+\w+',      # Import statements
        r'from\s+\w+\s+import', # From imports
        r'if\s+.*:$',         # Python if statement
        r'for\s+.*:$',        # Python for loop
        r'while\s+.*:$',      # Python while loop
        r'=\s*\[|\{|\(',      # Data structures
        r';\s*$',             # Semicolon endings
        r'```',               # Already markdown
        r'//|/\*|\*/',        # Comments
        r'<[^>]+>',           # HTML tags
        r'^\d+\.\s',          # Numbered lists
        r'[-*•]\s',           # Bullet points
    ]
    
    # Language detection
    def detect_language(code_block):
        code_text = '\n'.join(code_block)
        if re.search(r'def\s+\w+\s*\(.*\):', code_text):
            return 'python'
        elif re.search(r'function\s+\w+\s*\(', code_text) or re.search(r'const\s+\w+\s*=', code_text):
            return 'javascript'
        elif re.search(r'#include|int\s+main|printf', code_text):
            return 'c'
        elif re.search(r'<\w+>.*</\w+>', code_text):
            return 'html'
        elif re.search(r'SELECT.*FROM|INSERT INTO|CREATE TABLE', code_text, re.IGNORECASE):
            return 'sql'
        elif re.search(r'package\s+main|func\s+\w+\s*\(', code_text):
            return 'go'
        elif re.search(r'println|System\.out\.print', code_text):
            return 'java'
        return ''
    
    i = 0
    while i < len(lines):
        line = lines[i]
        is_code = False
        
        # Check if line looks like code
        for pattern in code_patterns:
            if re.search(pattern, line):
                is_code = True
                break
        
        # Special case: single line that's obviously code
        if not is_code and len(line) > 30 and ('{' in line or '}' in line or ';' in line):
            is_code = True
        
        if is_code and not in_code_block:
            # Start code block
            in_code_block = True
            code_lines = [line]
        elif is_code and in_code_block:
            # Continue code block
            code_lines.append(line)
        elif not is_code and in_code_block:
            # End code block
            if code_lines:
                lang = detect_language(code_lines)
                formatted_lines.append(f'```{lang}')
                formatted_lines.extend(code_lines)
                formatted_lines.append('```')
                code_lines = []
            in_code_block = False
            formatted_lines.append(line)
        else:
            # Regular text
            formatted_lines.append(line)
        
        i += 1
    
    # Close any open code block
    if in_code_block and code_lines:
        lang = detect_language(code_lines)
        formatted_lines.append(f'```{lang}')
        formatted_lines.extend(code_lines)
        formatted_lines.append('```')
    
    return '\n'.join(formatted_lines)

def smart_formatting(text):
    """
    Additional smart formatting for better readability
    """
    if not text:
        return text
    
    # Fix common OCR mistakes in code
    replacements = {
        '|': 'I',    # Pipe to I (sometimes misread)
        '0': 'O',    # Zero to O (context-aware would be better)
        '1': 'l',    # One to l (for code)
        '£': '#',    # Pound to hash
        '©': '//',   # Copyright to comment
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Preserve multiple spaces (important for code)
    # But clean up excessive ones
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Don't strip trailing spaces if they're meaningful
        if line.startswith('    '):  # Code indentation
            cleaned_lines.append(line.rstrip())  # Only remove trailing
        else:
            cleaned_lines.append(line.strip())
    
    return '\n'.join(cleaned_lines)

def get_reader():
    global reader
    if reader is None:
        reader = easyocr.Reader(
            ['en'],
            gpu=False,
            verbose=False
        )
    return reader

def ocr_with_layout(img_path):
    reader = get_reader()
    img = Image.open(img_path)
    img_width, img_height = img.size

    result = reader.readtext(
        img_path,
        detail=1,
        paragraph=False,
        width_ths=0.5,
        add_margin=0.1
    )

    text = format_with_layout(result, img_width, img_height)
    text = detect_and_format_code(text)
    text = smart_formatting(text)

    return text

def main():
    """Main worker loop"""
    print("OCR Worker v2.0 - Layout Preservation + Code Detection", file=sys.stderr)
    print("Ready for requests", file=sys.stderr)
    sys.stderr.flush()
    
    for line in sys.stdin:
        try:
            data = json.loads(line.strip())
            img_path = data.get("image_path")
            
            if not img_path:
                response = {"success": False, "error": "No image path"}
                print(json.dumps(response))
                sys.stdout.flush()
                continue
            
            # Perform OCR with layout and code detection
            text = ocr_with_layout(img_path)
            
            response = {"success": True, "text": text}
            print(json.dumps(response))
            sys.stdout.flush()
            
        except json.JSONDecodeError as e:
            response = {"success": False, "error": f"JSON decode error: {e}"}
            print(json.dumps(response))
            sys.stdout.flush()
        except Exception as e:
            response = {"success": False, "error": str(e)}
            print(json.dumps(response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()