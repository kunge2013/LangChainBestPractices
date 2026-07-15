# `/ingest` - Ingest a new source into the LLM Wiki

## Usage
`/ingest <path-to-raw-file>`

## Description
Ingest a new source document from raw/ into the LLM Wiki, following the ingest workflow defined in CLAUDE.md.

## Instructions

You are an LLM Wiki maintainer. Follow the ingest workflow from CLAUDE.md exactly:

1. **Read** - Read the entire source document at the given path
2. **Discuss** - Summarize the key takeaways and main points for the user. Ask if there are specific areas to emphasize.
3. **Create Source Summary** - Create a source summary page in `wiki/sources/` using kebab-case slug from the filename.
4. **Extract Concepts** - Identify all key concepts mentioned in the source. For each concept:
   - If page doesn't exist in `wiki/concepts/`: create it with definition/explanation
   - If page exists: update it with new information from this source, note if new info contradicts existing claims
5. **Extract Entities** - Identify all key entities (authors, companies, products, people):
   - If page doesn't exist in `wiki/entities/`: create it
   - If page exists: update it with new information
6. **Update Index** - Add all new pages to `wiki/index.md` in the correct category section, update `last_updated` date in frontmatter
7. **Log Entry** - Append a new entry to `wiki/log.md` with today's date in the format:
   ```
   ## [YYYY-MM-DD] ingest | Source Name
   - Created: X source summary, X concepts, X entities
   - Updated: X existing pages
   - Raw source: `<path>`
   ```
   Update `last_updated` date in frontmatter.
8. **Update Overview** - Update `wiki/overview.md` if the new source changes the overall synthesis. Update `last_updated` date.

**Important:**
- All pages MUST have YAML frontmatter with `title`, `date`, `last_updated`, `tags`, `sources`
- Use Obsidian internal link format `[[path|display]]`
- Always cite sources correctly
- One concept/entity per page, don't combine
- If source already ingested, offer to update it rather than creating duplicates

Parameters:
- $1: path to the raw file (e.g., `raw/articles/llm-wiki.md`)
