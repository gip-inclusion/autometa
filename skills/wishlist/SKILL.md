# Wishlist Skill

Log capability requests, tool wishes, blocked operations, and improvement ideas.

Use this skill when:
- A tool requires approval you cannot obtain
- A command is blocked or denied (permission, path, network)
- You wish you had a tool or capability you don't have
- You notice gaps in documentation or knowledge files
- You have ideas for improving workflows

## Usage

```bash
# Add a wish
python skills/wishlist/scripts/wishlist.py add \
    --category "tool" \
    --title "WebFetch for documentation sites" \
    --description "Would help when needing to read external API docs"

# List recent wishes
python skills/wishlist/scripts/wishlist.py list

# List by category
python skills/wishlist/scripts/wishlist.py list --category tool
```

## Categories

- `permission` - Blocked commands, approval required, access denied
- `tool` - Missing or restricted tool capabilities
- `knowledge` - Gaps in knowledge files
- `skill` - Ideas for new skills
- `workflow` - Process improvements
- `other` - Anything else

## Examples

**Blocked operation:**
```bash
python skills/wishlist/scripts/wishlist.py add \
    --category "permission" \
    --title "git clone requires approval" \
    --description "Tried to clone les-emplois repo to explore tracking code"
```

**Tool wish:**
```bash
python skills/wishlist/scripts/wishlist.py add \
    --category "tool" \
    --title "curl to external documentation" \
    --description "Needed to fetch Django docs to understand QuerySet API"
```

**Knowledge gap:**
```bash
python skills/wishlist/scripts/wishlist.py add \
    --category "knowledge" \
    --title "Metabase SQL dialect reference" \
    --description "Unclear which SQL functions are available in Metabase queries"
```

**Workflow idea:**
```bash
python skills/wishlist/scripts/wishlist.py add \
    --category "workflow" \
    --title "Auto-save report drafts" \
    --description "Would help avoid losing work on long reports"
```
