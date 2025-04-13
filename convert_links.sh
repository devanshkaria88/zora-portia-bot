#!/bin/bash
# Script to convert Obsidian wiki links to standard Markdown links

# Define the directory where your markdown files are located
DOCS_DIR="/Users/devansh/web-dev/zora-portia-bot/docs"

# Function to convert wiki links
convert_links() {
    local file=$1
    
    # Replace [[file|text]] with [text](file.md)
    sed -i '' -E 's/\[\[([^|]+)\|([^\]]+)\]\]/[\2](\1.md)/g' "$file"
    
    # Replace [[file#section|text]] with [text](file.md#section)
    sed -i '' -E 's/\[\[([^#]+)#([^|]+)\|([^\]]+)\]\]/[\3](\1.md#\2)/g' "$file"
    
    # Replace [[file]] with [file](file.md)
    sed -i '' -E 's/\[\[([^\]#|]+)\]\]/[\1](\1.md)/g' "$file"
    
    # Replace [[file#section]] with [section](file.md#section)
    sed -i '' -E 's/\[\[([^#]+)#([^\]]+)\]\]/[\2](\1.md#\2)/g' "$file"
    
    echo "Converted links in: $file"
}

# Process each markdown file in the directory
for file in "$DOCS_DIR"/*.md; do
    if [ -f "$file" ]; then
        convert_links "$file"
    fi
done

echo "Link conversion complete!"
