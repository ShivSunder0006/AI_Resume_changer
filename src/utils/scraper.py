"""
Utility for scraping and extracting text from URLs for context enrichment.
"""

from loguru import logger
import urllib.request
import json
import re

def extract_github_repos(username: str) -> str:
    """Extracts public repositories and descriptions for a Github user."""
    try:
        url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            repos = json.loads(response.read().decode())
        
        extracted = []
        for repo in repos:
            name = repo.get("name", "")
            desc = repo.get("description", "") or "No description provided."
            lang = repo.get("language", "") or "Unknown language"
            extracted.append(f"- **{name}** ({lang}): {desc}")
            
        if extracted:
            return "### Recent GitHub Projects:\n" + "\n".join(extracted)
        return ""
    except Exception as e:
        logger.warning(f"Failed to extract github repos for {username}: {e}")
        return ""

def enrich_from_urls(urls: str) -> str:
    """Basic extraction of profile info from provided URLs."""
    if not urls:
        return ""
        
    context_blocks = []
    
    # Check for github
    urls_list = [u.strip() for u in urls.split() if u.strip()]
    for url in urls_list:
        if "github.com/" in url:
            paths = url.split("github.com/")
            if len(paths) > 1:
                username = paths[1].split("/")[0]
                gh_text = extract_github_repos(username)
                if gh_text:
                    context_blocks.append(gh_text)
                    
        # Note: We can expand this with BeautifulSoup for general portfolios in the future
        # For now, Github gives the highest signal-to-noise ratio for skills.
        elif "shivsunder06.netlify.app" in url:
             context_blocks.append("### Personal Portfolio Context:\n- Web Developer and AI Engineer specializing in Next.js, FastAPI, and Agentic RAG Systems.")
             
    if context_blocks:
        return "\n\n--- EXTERNAL PROFILE CONTEXT ---\n" + "\n\n".join(context_blocks) + "\n--------------------------------"
    return ""
