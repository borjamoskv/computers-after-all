"""
Track Ingestion and Acquisition via yt-dlp.
Enforces the Sovereign Music Centralization Invariant (~/Music/Computers After All Vault/).
"""

from pathlib import Path
import subprocess
from typing import List, Optional


CANONICAL_VAULT_DIR = Path.home() / "Music" / "Computers After All Vault"


class TrackDownloader:
    """Acquires audio tracks from search queries or URLs via yt-dlp."""

    def __init__(self, vault_dir: Optional[Path] = None):
        self.vault_dir = Path(vault_dir or CANONICAL_VAULT_DIR).resolve()
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def fetch_track(self, query_or_url: str) -> Optional[Path]:
        """
        Downloads a single track by search query or URL in best audio quality.
        Returns the path to the downloaded audio file.
        """
        out_template = str(self.vault_dir / "%(artist,uploader)s - %(title)s.%(ext)s")

        # Determine if it's a URL or search query
        is_url = query_or_url.startswith("http://") or query_or_url.startswith("https://")
        target = query_or_url if is_url else f"ytsearch1:{query_or_url}"

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", out_template,
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            target
        ]

        try:
            subprocess.run(cmd, check=True)
            # Find the most recently created mp3 in vault
            mp3_files = list(self.vault_dir.glob("*.mp3"))
            if mp3_files:
                latest = max(mp3_files, key=lambda f: f.stat().st_mtime)
                return latest
        except Exception:
            return None

        return None

    def fetch_tracks(self, queries: List[str]) -> List[Path]:
        """Batch fetches a list of track queries or URLs."""
        paths: List[Path] = []
        for q in queries:
            path = self.fetch_track(q)
            if path:
                paths.append(path)
        return paths
