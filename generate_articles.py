import os
import re
import feedparser
from ollama import Client
from datetime import datetime
import time

RSS_FEED_URL = "https://techcrunch.com/feed/"
OLLAMA_MODEL = "llama3"
ASTRO_BLOG_DIR = "./astro_blog/src/content/blog/"
HUMANIZER_RULES_FILE = "humanizer_rules.txt"
AFFILIATE_LINK_PLACEHOLDER = "[YOUR_AFFILIATE_LINK_HERE]"

def ensure_directory():
    if not os.path.exists(ASTRO_BLOG_DIR):
        os.makedirs(ASTRO_BLOG_DIR)

def get_system_prompt():
    if os.path.exists(HUMANIZER_RULES_FILE):
        with open(HUMANIZER_RULES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return content
    return "You are an expert tech writer."

def generate_article(item, system_prompt, client):
    title = item.get('title', 'No Title')
    description = item.get('description', '')
    
    # Remove HTML tags from description if present
    description = re.sub(r'<[^>]+>', '', description)
    
    prompt = f"""
Please write a short, engaging article about the following topic:
Title: {title}
Summary: {description}

Make sure to insert the following placeholder exactly as written somewhere naturally in the text: {AFFILIATE_LINK_PLACEHOLDER}

The output should be formatted as markdown content (without frontmatter), and do not include any introductory conversation (like "Here is the article").
"""
    print("Generating from model...")
    response = client.chat(model=OLLAMA_MODEL, messages=[
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt}
    ])
    
    return response['message']['content']

def create_markdown_file(item, content):
    title = item.get('title', 'Unknown Title')
    
    # Simple slug generation
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if not slug:
        slug = f"article-{int(time.time())}"
        
    # Get current date formatted for Astro
    pub_date = datetime.now().strftime("%b %d %Y")
    
    # Escape quotes in title
    safe_title = title.replace('"', '\\"')
    
    # Generate generic description from title if needed
    safe_desc = f"Read about {safe_title}"
    
    frontmatter = f"""---
title: "{safe_title}"
description: "{safe_desc}"
pubDate: "{pub_date}"
heroImage: "/blog-placeholder-about.jpg"
---
"""
    
    filename = os.path.join(ASTRO_BLOG_DIR, f"{slug}.md")
    
    # Optional: check if file already exists to avoid duplicates
    if os.path.exists(filename):
        print(f"Skipping {slug}, already exists.")
        return False
        
    with open(filename, "w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + content)
        
    print(f"Created: {filename}")
    return True

def main():
    ensure_directory()
    
    print(f"Fetching RSS feed from: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)
    
    if not feed.entries:
         print("No entries found in the RSS feed.")
         return
         
    system_prompt = get_system_prompt()
    client = Client(host='http://localhost:11434') # assuming local default
    
    # Process only the 3 latest entries
    entries_to_process = feed.entries[:3]
    
    for item in entries_to_process:
        print(f"Starting article for: {item.get('title', 'No Title')}")
        try:
            content = generate_article(item, system_prompt, client)
            create_markdown_file(item, content)
        except Exception as e:
            print(f"Failed to generate article: {e}")
        
    print("Generation complete.")

if __name__ == "__main__":
    main()
