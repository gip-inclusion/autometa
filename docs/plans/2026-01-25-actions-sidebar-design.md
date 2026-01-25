# Actions Sidebar for Conversation View

## Overview

Add a collapsible right sidebar to the conversation view that displays tool calls as condensed "pills". The main chat area shows footnote-style icon markers linking to sidebar items. This replaces the current view mode toggle (minimal/normal/verbose).

## Data Model

No changes required. Uses existing fields:

**tool_use messages:**
```json
{
  "tool": "Read",
  "input": {"file_path": "/app/knowledge/sites/dora.md"},
  "category": "Read: knowledge"
}
```

**tool_result messages:**
```json
{
  "output": "...",
  "api_calls": [
    {"source": "matomo", "instance": "inclusion", "method": "VisitsSummary.get", "url": "https://..."}
  ]
}
```

## Layout

### Desktop (>= 992px)

```
+-------------+----------------------------+--------------+
|   Left      |      Main Chat Area        |   Actions    |
|  Sidebar    |   (messages, responses)    |   Sidebar    |
|   (nav)     |         flex: 1            |    280px     |
|   280px     |                            |  collapsible |
+-------------+----------------------------+--------------+
```

- Actions sidebar has collapse toggle (chevron)
- Collapsed: 48px wide, shows only toggle button
- Main content expands to fill space

### Mobile (< 992px)

- Single column layout
- Toggle button in section header
- Sidebar opens as Bootstrap offcanvas from right

## CSS Grid Structure

```css
.chat-with-sidebar {
  display: grid;
  grid-template-columns: 1fr 280px;
  grid-template-rows: 1fr;
  height: calc(100vh - var(--section-header-height) - 90px);
  overflow: hidden;
}

.chat-with-sidebar.sidebar-collapsed {
  grid-template-columns: 1fr 48px;
}

@media (max-width: 991.98px) {
  .chat-with-sidebar {
    grid-template-columns: 1fr;
  }
}
```

### Scroll Containment

```css
.chat-main {
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0; /* critical for grid child scroll */
}

.actions-sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-left: 1px solid var(--bs-border-color);
  background: var(--sidebar-bg);
}

.actions-sidebar-header {
  flex-shrink: 0;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--bs-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.actions-sidebar-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0; /* critical */
  padding: 0.5rem;
}
```

## Pill Design

### Structure

```html
<div class="action-pill" data-action-index="1">
  <div class="action-pill-header">
    <i class="ri-cloud-line"></i>
    <span class="action-pill-label">API: Matomo</span>
  </div>
  <div class="action-pill-content">
    <!-- Expanded content -->
  </div>
</div>
```

### Icon Mapping

| Category prefix | Icon |
|-----------------|------|
| `API:` | `ri-cloud-line` |
| `Read:` | `ri-file-text-line` |
| `Write:` | `ri-file-add-line` |
| `Edit:` | `ri-edit-line` |
| `Search:` | `ri-search-line` |
| `Execute:` | `ri-play-line` |
| `Query:` | `ri-database-2-line` |
| `Shell:` | `ri-terminal-line` |
| `Skill:` | `ri-magic-line` |
| `Thinking:` | `ri-lightbulb-line` |
| `System:` | `ri-settings-3-line` |
| `Web:` | `ri-global-line` |
| `Interaction:` | `ri-question-line` |

### States

- Default: subtle background (#f8f9fa), compact
- Hover: slightly darker
- Expanded: shows content panel below
- Highlighted: primary border glow (when footnote hovered)

### Rich Content (Expanded)

**API: Matomo / API: Metabase:**
- List api_calls as clickable links: `[icon] VisitsSummary.get`

**Read: knowledge / Read: docs:**
- Show filename: `dora.md`

**Default:**
- Truncated input preview, full JSON on expand

## Footnote Markers

After each assistant message, show icon badges for tools used:

```html
<div class="action-footnotes">
  <span class="action-footnote" data-action-index="1">
    <i class="ri-cloud-line"></i>
  </span>
  <span class="action-footnote" data-action-index="2">
    <i class="ri-file-text-line"></i>
  </span>
</div>
```

### Interactions

- Hover footnote -> highlight corresponding pill (CSS class toggle)
- Hover pill -> highlight corresponding footnote
- Click footnote -> scroll sidebar to pill, expand it
- Click pill -> toggle expand inline

## Implementation Steps

### Step 1: CSS Layout Foundation

File: `web/static/css/style.css`

1. Add `.chat-with-sidebar` grid container styles
2. Add `.chat-main` scroll styles
3. Add `.actions-sidebar` and children styles
4. Add `.sidebar-collapsed` state
5. Add mobile offcanvas overrides
6. Add CSS variables for sidebar width

### Step 2: Pill & Footnote Styles

File: `web/static/css/style.css`

1. Add `.action-pill` base styles
2. Add `.action-pill-header`, `.action-pill-content`
3. Add `.action-pill.expanded` state
4. Add `.action-pill.highlighted` state
5. Add `.action-footnotes` container styles
6. Add `.action-footnote` badge styles
7. Add `.action-footnote.highlighted` state

### Step 3: HTML Structure

File: `web/templates/explorations.html`

1. Wrap chat output in `.chat-with-sidebar` grid
2. Add `.chat-main` wrapper around existing chat-output
3. Add `.actions-sidebar` structure (header + content)
4. Add mobile toggle button in section header
5. Add mobile offcanvas markup
6. Remove view mode toggle (segmented control)

### Step 4: JavaScript - Data Structures

File: `web/static/js/chat.js`

1. Add `actionIndex` counter (global, increments per tool)
2. Add `actionsMap` to store action data by index
3. Add `getIconForCategory(category)` function
4. Add `extractPillLabel(toolUse)` function

### Step 5: JavaScript - Pill Rendering

File: `web/static/js/chat.js`

1. Modify `appendEvent()` for tool_use/tool_result:
   - Don't append to chat-output
   - Instead, create pill and append to sidebar
   - Store in actionsMap
2. Add `createActionPill(toolUse, toolResult, index)` function
3. Add `formatPillContent(toolUse, toolResult)` for expanded view
4. Add `appendFootnote(index, category)` after assistant messages

### Step 6: JavaScript - Interactions

File: `web/static/js/chat.js`

1. Add hover handlers for footnotes -> highlight pills
2. Add hover handlers for pills -> highlight footnotes
3. Add click handler for footnotes -> scroll to pill, expand
4. Add click handler for pills -> toggle expand
5. Add sidebar collapse/expand toggle

### Step 7: JavaScript - Load Existing

File: `web/static/js/chat.js`

1. Modify `loadConversation()` to build sidebar from history
2. Pair tool_use with following tool_result
3. Track which assistant message each tool belongs to
4. Render footnotes retroactively

### Step 8: Mobile Offcanvas

File: `web/static/js/chat.js`

1. Initialize Bootstrap offcanvas for mobile sidebar
2. Wire up toggle button
3. Ensure scroll position preserved

### Step 9: Cleanup

1. Remove `.view-minimal`, `.view-normal`, `.view-verbose` classes
2. Remove segmented control JS handlers
3. Remove related CSS

## Files Modified

- `web/templates/explorations.html`
- `web/static/css/style.css`
- `web/static/js/chat.js`

## Testing

1. Test sidebar scroll independence from main area
2. Test collapse/expand animation
3. Test mobile offcanvas open/close
4. Test hover highlight bidirectional
5. Test click-to-scroll behavior
6. Test with conversation that has many tools
7. Test with conversation that has zero tools (empty sidebar)
8. Test API calls show clickable links
9. Test Read: knowledge shows filename
