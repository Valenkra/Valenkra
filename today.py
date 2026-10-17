
import os
import re
import json
import urllib.request
from pathlib import Path

# ==========================================
# CONFIGURACIÓN
# ==========================================

USERNAME = os.environ.get("GITHUB_USERNAME", "").strip()
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

SVG_FILES = [
    Path("light-mode.svg"),
    Path("dark-mode.svg"),
]

# ==========================================
# CONSULTA A LA API DE GITHUB
# ==========================================

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    followers {
      totalCount
    }

    repositoriesContributedTo(
      contributionTypes: [
        COMMIT,
        ISSUE,
        PULL_REQUEST,
        REPOSITORY
      ],
      includeUserRepositories: false
    ) {
      totalCount
    }

    contributionsCollection {
      totalCommitContributions
    }

    repositories(
      first: 100,
      after: $after,
      ownerAffiliations: OWNER,
      isFork: false
    ) {
      totalCount

      pageInfo {
        hasNextPage
        endCursor
      }

      nodes {
        stargazerCount
      }
    }
  }
}
"""


def graphql(query, variables):
    body = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-updater",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("errors"):
        raise RuntimeError(result["errors"])

    return result["data"]["user"]


# ==========================================
# ACTUALIZAR VALORES EN EL SVG
# ==========================================

def replace_tspan(svg, element_id, value):
    pattern = (
        rf'(<tspan\b(?=[^>]*\bid="{re.escape(element_id)}")'
        rf'[^>]*>)(.*?)(</tspan>)'
    )

    updated, count = re.subn(
        pattern,
        lambda match: (
            match.group(1)
            + str(value)
            + match.group(3)
        ),
        svg,
        count=1,
        flags=re.S,
    )

    if count == 0:
        print(f"Advertencia: no se encontró {element_id}")

    return updated


# ==========================================
# OBTENER ESTADÍSTICAS
# ==========================================

def get_github_stats():
    after = None
    stars = 0
    stats = {}

    while True:
        user = graphql(
            QUERY,
            {
                "login": USERNAME,
                "after": after,
            }
        )

        if user is None:
            raise RuntimeError(
                f"No se encontró el usuario {USERNAME}"
            )

        repositories = user["repositories"]

        stars += sum(
            repo["stargazerCount"]
            for repo in repositories["nodes"]
        )

        if not stats:
            stats = {
                "repo_data": repositories["totalCount"],
                "contrib_data": user[
                    "repositoriesContributedTo"
                ]["totalCount"],
                "commit_data": user[
                    "contributionsCollection"
                ]["totalCommitContributions"],
                "follower_data": user[
                    "followers"
                ]["totalCount"],
            }

        if not repositories["pageInfo"]["hasNextPage"]:
            break

        after = repositories["pageInfo"]["endCursor"]

    stats["star_data"] = stars

    # GitHub no proporciona directamente el total
    # histórico de líneas de código.
    stats["loc_data"] = "N/A"
    stats["loc_add"] = "N/A"
    stats["loc_del"] = "N/A"

    return stats


# ==========================================
# ACTUALIZAR ARCHIVOS
# ==========================================

def update_svg(path, stats):
    if not path.exists():
        print(f"No se encontró el archivo: {path}")
        return

    svg = path.read_text(encoding="utf-8")

    for element_id, value in stats.items():
        if isinstance(value, int):
            value = f"{value:,}"

        svg = replace_tspan(
            svg,
            element_id,
            value,
        )

    path.write_text(svg, encoding="utf-8")

    print(f"SVG actualizado: {path}")


# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================

def main():
    if not USERNAME or not TOKEN:
        raise SystemExit(
            "Faltan GITHUB_USERNAME o GITHUB_TOKEN"
        )

    print(f"Consultando estadísticas de {USERNAME}...")

    stats = get_github_stats()

    for key, value in stats.items():
        print(f"{key}: {value}")

    for svg_file in SVG_FILES:
        update_svg(svg_file, stats)

    print("Actualización terminada.")


if __name__ == "__main__":
    main()
