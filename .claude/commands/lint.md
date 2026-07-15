# `/lint` - Lint and health-check the LLM Wiki

## Usage
`/lint`

## Description
Run a health check on the LLM Wiki to find issues: contradictions, stale content, orphan pages, missing pages, missing cross-references. Report issues and fix them after confirmation.

## Instructions

You are an LLM Wiki maintainer. Follow the lint workflow from CLAUDE.md exactly:

1. **Scan** - Scan all wiki pages in `wiki/sources/`, `wiki/concepts/`, `wiki/entities/`, `wiki/queries/`
2. **Check for these issues:**
   - Contradictions between pages (conflicting claims)
   - Stale claims that newer sources contradict or supersede
   - Orphan pages with no inbound links from other wiki pages
   - Concepts mentioned in text but don't have their own page
   - Missing cross-references between related pages
   - Broken internal links
   - Data gaps that suggest new questions to investigate
3. **Report** - Summarize all findings to the user, categorize by severity
4. **Fix** - After user approval, fix the issues found:
   - Create missing concept pages
   - Add missing cross-references
   - Fix broken links
   - Flag contradictions for user attention
   - Update the index and log after fixes

**Important:**
- Be thorough - this is a health check to keep the wiki in good condition
- Don't modify anything without user confirmation after reporting
- Update `last_updated` dates on any pages you modify
- Add a lint entry to `wiki/log.md` when done
