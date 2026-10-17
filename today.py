"""Update Public Repos and GitHub Stars in profile SVGs (public repositories only)."""
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

USERNAME = os.environ.get('GITHUB_USERNAME', 'Valenkra')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
SVG_FILES = [Path('light-mode.svg'), Path('dark-mode.svg')]


def get_public_stats():
    repos = []
    page = 1
    while True:
        url = f'https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}'
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-svg-updater', 'X-GitHub-Api-Version': '2022-11-28'}
        if TOKEN:
            headers['Authorization'] = f'Bearer {TOKEN}'
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                batch = json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'GitHub API returned HTTP {error.code}: {error.read().decode("utf-8", "replace")[:400]}') from error
        if not isinstance(batch, list):
            raise RuntimeError(f'Unexpected API response: {batch!r}')
        repos.extend(repo for repo in batch if not repo.get('fork') and not repo.get('private'))
        if len(batch) < 100:
            break
        page += 1
    return {'repo_data': len(repos), 'star_data': sum(repo['stargazers_count'] for repo in repos)}


def update_file(path, stats):
    if not path.exists():
        print(f'Skipping missing file: {path}')
        return
    svg = path.read_text(encoding='utf-8')
    for element_id, value in stats.items():
        pattern = rf'(<tspan\b(?=[^>]*\bid=["\']{re.escape(element_id)}["\'])[^>]*>)(.*?)(</tspan>)'
        svg, count = re.subn(pattern, lambda m: m.group(1) + str(value) + m.group(3), svg, count=1, flags=re.S)
        if count != 1:
            raise RuntimeError(f'{path}: missing <tspan id="{element_id}">; file not written')
    path.write_text(svg, encoding='utf-8')
    print(f'Updated {path}: {stats}')


if __name__ == '__main__':
    stats = get_public_stats()
    print(f'{USERNAME}: {stats}')
    for file in SVG_FILES:
        update_file(file, stats)
