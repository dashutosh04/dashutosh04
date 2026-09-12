"""Update the account-owned repository section in the profile README."""

import json
import html
import os
from urllib.parse import quote, urlparse
import urllib.parse
import urllib.request


OWNER = "dashutosh04"
README_PATH = "README.md"
START = "<!-- REPOSITORIES:START -->"
END = "<!-- REPOSITORIES:END -->"
MAX_DESCRIPTION_LENGTH = 140


def fetch_repositories():
    query = urllib.parse.urlencode(
        {"per_page": "100", "sort": "updated", "direction": "desc", "type": "owner"}
    )
    request = urllib.request.Request(
        f"https://api.github.com/users/{OWNER}/repos?{query}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-updater"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        repositories = json.load(response)
    repositories = [
        repo
        for repo in repositories
        if repo.get("owner", {}).get("login") == OWNER
        and not repo.get("fork")
        and not repo.get("archived")
        and not repo.get("is_template")
    ]
    return sorted(repositories, key=lambda repo: (repo.get("updated_at", ""), repo.get("created_at", "")), reverse=True)


def escape(value):
    return html.escape(str(value or "").replace("|", "\\|").replace("\n", " ").strip(), quote=True)


def repository_url(repo):
    parsed = urlparse(repo.get("html_url", ""))
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.path.strip("/").split("/")[0] != OWNER:
        raise ValueError(f"Unexpected repository owner or URL: {repo.get('html_url')}")
    return html.escape(repo["html_url"], quote=True)


def topics(repo):
    values = repo.get("topics", [])[:3]
    if not values:
        return ""
    return " ".join(f"<code>#{escape(topic)}</code>" for topic in values)


def shorten(value):
    value = str(value or "No description yet.").replace("\n", " ").strip()
    if len(value) <= MAX_DESCRIPTION_LENGTH:
        return value
    return value[: MAX_DESCRIPTION_LENGTH - 3].rstrip() + "..."


def badge(url, alt):
    return f"![{alt}]({url}?style=flat-square&label=)"


def language_badge(repo):
    language = repo.get("language") or "N/A"
    language_path = quote(str(language), safe="")
    return f"![Language](https://img.shields.io/badge/Language-{language_path}-3776AB?style=flat-square)"


def repository_badges(repo):
    owner = quote(OWNER, safe="")
    name = quote(repo["name"], safe="")
    base = f"https://img.shields.io/github"
    return {
        "language": language_badge(repo),
        "stars": badge(f"{base}/stars/{owner}/{name}", "Stars"),
        "forks": badge(f"{base}/forks/{owner}/{name}", "Forks"),
        "updated": badge(f"{base}/last-commit/{owner}/{name}", "Last commit"),
    }


def render(repositories):
    rows = [
        "| Repository | About | Language | Stars | Forks | Last Commit |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for repo in repositories[:6]:
        name = escape(repo["name"])
        description = escape(shorten(repo.get("description")))
        topic_badges = topics(repo)
        about = description + (f"<br>{topic_badges}" if topic_badges else "")
        badges = repository_badges(repo)
        rows.append(
            f"| [📁 {name}]({repository_url(repo)}) | {about} | "
            f"{badges['language']} | {badges['stars']} | {badges['forks']} | {badges['updated']} |"
        )
    if len(rows) == 2:
        rows.append("| No public repositories found yet. | | N/A | 0 | 0 | N/A |")
    return "\n".join(rows)


def main():
    with open(README_PATH, encoding="utf-8") as readme_file:
        readme = readme_file.read()
    if START not in readme or END not in readme:
        raise ValueError("Repository markers are missing from README.md")
    generated = render(fetch_repositories())
    before, remainder = readme.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = f"{before}{START}\n{generated}\n{END}{after}"
    with open(README_PATH, "w", encoding="utf-8", newline="\n") as readme_file:
        readme_file.write(updated)


if __name__ == "__main__":
    main()
