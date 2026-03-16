#!/usr/bin/env python3

import argparse
import datetime
import json
import re
import urllib.request
from pathlib import Path

import tomllib


ORCID_ID_RE = re.compile(r"(\d{4}-\d{4}-\d{4}-[\dX]{4})", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Sync ORCID works into Hugo content/publications as markdown files."
	)
	parser.add_argument(
		"--config",
		default="config.toml",
		help="Path to Hugo config.toml",
	)
	parser.add_argument(
		"--output",
		default="content/publications",
		help="Output directory for generated markdown files",
	)
	parser.add_argument(
		"--keep-stale",
		action="store_true",
		help="Do not delete previously generated ORCID files that no longer exist in ORCID.",
	)
	return parser.parse_args()


def get_orcid_url(config_path: Path) -> str:
	data = tomllib.loads(config_path.read_text(encoding="utf-8"))
	return (
		data.get("params", {})
		.get("social", {})
		.get("orcid", "")
		.strip()
	)


def extract_orcid_id(orcid_url_or_id: str) -> str:
	match = ORCID_ID_RE.search(orcid_url_or_id)
	return match.group(1) if match else ""


def fetch_json(url: str) -> dict:
	request = urllib.request.Request(
		url,
		headers={
			"Accept": "application/json",
			"User-Agent": "hugo-orcid-sync/1.0",
		},
	)
	with urllib.request.urlopen(request, timeout=30) as response:
		return json.loads(response.read().decode("utf-8"))


def sanitize_slug(text: str) -> str:
	slug = text.lower()
	slug = re.sub(r"[^a-z0-9]+", "-", slug)
	return slug.strip("-")[:60] or "untitled"


def escape_yaml(value: str) -> str:
	return value.replace("\\", "\\\\").replace('"', '\\"').strip()


def format_summary(text: str) -> str:
	text = re.sub(r"\s+", " ", text or "").strip()
	if not text:
		return "Imported from ORCID."
	return text[:300]


def build_front_matter(
	*,
	title: str,
	authors: str,
	venue: str,
	year: str,
	summary: str,
	orcid_put_code: str,
) -> str:
	lines = [
		"---",
		f'title: "{escape_yaml(title)}"',
		f'authors: "{escape_yaml(authors)}"',
		f'venue: "{escape_yaml(venue)}"',
		f"year: {year if year else datetime.date.today().year}",
		f'summary: "{escape_yaml(format_summary(summary))}"',
		f'orcid_put_code: "{escape_yaml(orcid_put_code)}"',
		'source: "orcid"',
		"---",
		"",
	]
	return "\n".join(lines)


def pick_external_url(work_detail: dict) -> str:
	url_data = work_detail.get("url", {})
	value = (url_data or {}).get("value", "")
	if value:
		return value

	external_ids = (
		work_detail.get("external-ids", {})
		.get("external-id", [])
	)
	for ext in external_ids:
		ext_url = (ext.get("external-id-url", {}) or {}).get("value", "")
		if ext_url:
			return ext_url
	return ""


def pick_doi(work_detail: dict) -> str:
	external_ids = (
		work_detail.get("external-ids", {})
		.get("external-id", [])
	)
	for ext in external_ids:
		if (ext.get("external-id-type", "").lower() == "doi"):
			return ext.get("external-id-value", "")
	return ""


def main() -> int:
	args = parse_args()
	root = Path.cwd()
	config_path = root / args.config
	output_dir = root / args.output
	output_dir.mkdir(parents=True, exist_ok=True)

	orcid_value = get_orcid_url(config_path)
	orcid_id = extract_orcid_id(orcid_value)
	if not orcid_id:
		raise SystemExit("No valid ORCID found at params.social.orcid in config.toml")

	works_url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
	works_payload = fetch_json(works_url)
	groups = works_payload.get("group", [])

	generated_files: set[Path] = set()

	for group in groups:
		summaries = group.get("work-summary", [])
		if not summaries:
			continue

		item = summaries[0]
		put_code = str(item.get("put-code", "")).strip()
		if not put_code:
			continue

		title = (
			(item.get("title") or {}).get("title") or {}
		).get("value", "Untitled")
		venue = (
			(item.get("journal-title") or {}).get("value", "")
			or item.get("type", "")
		)
		year = (
			((item.get("publication-date") or {}).get("year") or {}).get("value", "")
		)

		detail_url = f"https://pub.orcid.org/v3.0/{orcid_id}/work/{put_code}"
		detail = fetch_json(detail_url)
		work_title = (
			((detail.get("title") or {}).get("title") or {}).get("value", "")
		) or title

		contributors = []
		contribs = (
			(detail.get("contributors") or {}).get("contributor") or []
		)
		for contributor in contribs:
			name = contributor.get("credit-name", {})
			value = (name or {}).get("value", "").strip()
			if value:
				contributors.append(value)
		authors = ", ".join(contributors) if contributors else ""

		# external_url = pick_external_url(detail)  # 已移除
		doi = pick_doi(detail)
		abstract = detail.get("short-description", "") or ""

		front_matter = build_front_matter(
			title=work_title,
			authors=authors,
			venue=venue,
			year=year,
			summary=abstract,
			orcid_put_code=put_code,
		)

		body_lines = [
			"This publication was synced automatically from ORCID.",
			"",
		]
		if doi:
			body_lines.append(f"- DOI: https://doi.org/{doi}")
		body = "\n".join(body_lines) + "\n"

		filename = f"orcid-{put_code}-{sanitize_slug(work_title)}.md"
		out_file = output_dir / filename
		out_file.write_text(front_matter + body, encoding="utf-8")
		generated_files.add(out_file)

	if not args.keep_stale:
		for existing in output_dir.glob("orcid-*.md"):
			if existing not in generated_files:
				existing.unlink()

	print(f"Synced {len(generated_files)} ORCID publications to {output_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
