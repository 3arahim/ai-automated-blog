import os
import re
import feedparser
import random
import glob
import json
from ollama import Client
from datetime import datetime
import time

RSS_FEED_URL = "https://techcrunch.com/feed/"
OLLAMA_MODEL = "llama3"
ASTRO_BLOG_DIR = "./astro_blog/src/content/blog/"
HUMANIZER_RULES_FILE = "humanizer_rules.txt"
AFFILIATE_JSON = "affiliate_products.json"

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

def get_affiliate_product_via_llm(title, description, client):
    if not os.path.exists(AFFILIATE_JSON):
        # Fallback if json is missing
        return {"name": "ChatGPT Plus", "link": "https://chat.openai.com/", "benefit": "Access advanced AI for all tasks."}
        
    with open(AFFILIATE_JSON, "r", encoding="utf-8") as f:
        products = json.load(f)
        
    categories = list(products.keys())
    categories_str = ", ".join(f"'{c}'" for c in categories)
    
    classification_prompt = f"""
Analyze the following article topic:
Title: {title}
Summary: {description}

Based on this topic, strictly select ONE category from the following list that matches best:
[{categories_str}]

Only output the EXACT category name. No other text. If no specific category matches, output 'General Assistant'.
"""
    # Use a simpler/shorter max-token generation for classification if possible, but standard chat is fine
    response = client.chat(model=OLLAMA_MODEL, messages=[
        {'role': 'user', 'content': classification_prompt}
    ])
    
    result = response['message']['content'].strip('\'" \n')
    
    # Check if the LLM hallucinated, if so fallback safely
    for cat in products:
        if cat.lower() in result.lower():
            print(f"  -> Categorized as: {cat}")
            return products[cat]
            
    print("  -> Categorized as: General Assistant (Fallback)")
    return products.get("General Assistant", {"name": "General Tool", "link": "#", "benefit": "Improve your workflow."})

def get_random_internal_links(exclude_slug, num_links=2):
    files = glob.glob(os.path.join(ASTRO_BLOG_DIR, "*.md"))
    valid_files = [f for f in files if exclude_slug not in f]
    
    if not valid_files:
        return ""
        
    selected_files = random.sample(valid_files, min(num_links, len(valid_files)))
    links = []
    
    for filepath in selected_files:
        slug = os.path.basename(filepath).replace('.md', '')
        title = "Read More"
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'title:\s*"([^"]+)"', content)
                if match:
                    title = match.group(1)
        except Exception:
            pass
        links.append(f"- [{title}](/blog/{slug}/)")
        
    if links:
        links_text = "\n".join(links)
        return f"\n\n## Read More\n\n{links_text}\n"
    return ""

def generate_article(item, system_prompt, client):
    title = item.get('title', 'No Title')
    description = item.get('description', '')
    
    # Remove HTML tags from description if present
    description = re.sub(r'<[^>]+>', '', description)
    
    print("Determining best affiliate product...")
    product = get_affiliate_product_via_llm(title, description, client)
    
    prompt = f"""
Please write a short, engaging article about the following topic:
Title: {title}
Summary: {description}

Please follow these strict formatting rules:
1. Start your response with exactly this line: "META_DESCRIPTION: [Write a 1-sentence SEO meta description here]"
2. Provide the rest of the article body underneath it. Do not include introductory conversation.
3. Use Markdown H2 (##) and H3 (###) tags properly to structure the article and make it easy for search engines to read. Do NOT use an H1 (#) tag.
4. Product Injection: We want to recommend the product '{product['name']}'. Ensure you embed its exact affiliate link: {product['link']}. 
You must weave its primary benefit ("{product['benefit']}") safely and naturally into the narrative of the main article content without sounding like an abrupt advertisement. Make it flow logically!
"""
    print("Generating full article from model...")
    response = client.chat(model=OLLAMA_MODEL, messages=[
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt}
    ])
    
    return response['message']['content'], product['name']

def create_markdown_file(item, raw_content):
    title = item.get('title', 'Unknown Title')
    
    # Simple slug generation
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if not slug:
        slug = f"article-{int(time.time())}"
        
    filename = os.path.join(ASTRO_BLOG_DIR, f"{slug}.md")
    
    # Optional: check if file already exists to avoid duplicates
    if os.path.exists(filename):
        print(f"Skipping {slug}, already exists.")
        return False

    # Extract Meta Description
    meta_desc_match = re.search(r'^META_DESCRIPTION:\s*(.*)', raw_content, flags=re.MULTILINE | re.IGNORECASE)
    if meta_desc_match:
        meta_description = meta_desc_match.group(1).strip()
        # Remove the meta description line from content
        content = re.sub(r'^META_DESCRIPTION:\s*.*\n*', '', raw_content, count=1, flags=re.MULTILINE | re.IGNORECASE).strip()
    else:
        # Fallback if AI fails to format properly
        safe_title = title.replace('"', '\\"')
        meta_description = f"Read about {safe_title}"
        content = raw_content

    # Clean up any residual meta description prefixes it might have left
    content = re.sub(r'^\**META_DESCRIPTION\**:\s*', '', content, flags=re.MULTILINE | re.IGNORECASE).strip()

    # Escape quotes in meta variables
    safe_title = title.replace('"', '\\"')
    safe_desc = meta_description.replace('"', '\\"')
    
    pub_date = datetime.now().strftime("%b %d %Y")
    
    frontmatter = f"""---
title: "{safe_title}"
description: "{safe_desc}"
pubDate: "{pub_date}"
heroImage: "/blog-placeholder-about.jpg"
---
"""
    # Append Internal links
    internal_links_section = get_random_internal_links(slug, num_links=2)
    content += internal_links_section
        
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
    client = Client(host='http://localhost:11434')
    
    entries_to_process = feed.entries[:3]
    
    for item in entries_to_process:
        print(f"Starting article for: {item.get('title', 'No Title')}")
        try:
            raw_content, product_name = generate_article(item, system_prompt, client)
            create_markdown_file(item, raw_content)
        except Exception as e:
            print(f"Failed to generate article: {e}")
        
    print("Generation complete.")

if __name__ == "__main__":
    main()
