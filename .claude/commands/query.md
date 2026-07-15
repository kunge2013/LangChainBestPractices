# `/query` - Query the LLM Wiki

## Usage
`/query <your-question>`

## Description
Query the LLM Wiki for an answer based on the already synthesized knowledge in the wiki. Synthesize the answer with citations, and offer to save it if it's valuable.

## Instructions

You are an LLM Wiki maintainer. Follow the query workflow from CLAUDE.md exactly:

1. **Locate** - Read `wiki/index.md` to identify all relevant pages for the query
2. **Read** - Read all relevant wiki pages identified from the index
3. **Synthesize** - Answer the user's question based on the wiki content. Always cite the wiki pages (and through them the original sources) you used.
4. **Preserve** - If the answer is a valuable, enduring synthesis or analysis that future queries will benefit from, ask the user if you should save it as a new page in `wiki/queries/`. If they agree, save it, update the index, and add a log entry.

**Important:**
- Base your answer ONLY on the content already in the wiki
- Always cite your sources with internal links
- Don't make up information not present in the wiki
