# `/save` - Save the last query answer to wiki/queries

## Usage
`/save <page-name>`

## Description
Save the answer from the last `/query` to `wiki/queries/` as a persistent page, update index and log.

## Instructions

Save the previous query answer to a persistent page in `wiki/queries/` with the given name:

1. Create the page at `wiki/queries/<page-name>.md`
2. Add YAML frontmatter with title, date, tags, and sources (the wiki pages used to generate the answer)
3. Add the answer content
4. Update `wiki/index.md` to add this query page
5. Append a log entry to `wiki/log.md`
6. Update `last_updated` dates on index and log

Parameters:
- $1: page name slug (e.g., `transformer-vs-rnn-comparison`)
