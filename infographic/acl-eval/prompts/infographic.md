Create a professional infographic following these specifications:

## Image Specifications

- **Type**: Infographic
- **Layout**: linear-progression
- **Style**: craft-handmade
- **Aspect Ratio**: landscape
- **Language**: en

## Core Principles

- Follow the layout structure precisely for information architecture
- Apply style aesthetics consistently throughout
- If content involves sensitive or copyrighted figures, create stylistically similar alternatives
- Keep information concise, highlight keywords and core concepts
- Use ample whitespace for visual clarity
- Maintain clear visual hierarchy

## Text Requirements

- All text must match the specified style treatment
- Main titles should be prominent and readable
- Key concepts should be visually emphasized
- Labels should be clear and appropriately sized
- Use the specified language for all text content

## Layout Guidelines

# linear-progression

Sequential progression showing steps, timeline, or chronological events.

## Structure

- Linear arrangement (horizontal or vertical)
- Nodes/markers at key points
- Connecting line or path between nodes
- Clear start and end points
- Directional flow indicators

## Variants

| Variant | Focus | Visual Emphasis |
|---------|-------|-----------------|
| **Timeline** | Chronological events, dates | Time markers, period labels |
| **Process** | Action steps, numbered sequence | Step numbers, action icons |

## Best For

- Step-by-step tutorials and how-tos
- Historical timelines and evolution
- Project milestones and roadmaps
- Workflow documentation
- Onboarding processes

## Visual Elements

- Numbered steps or date markers
- Arrows or connectors showing direction
- Icons representing each step/event
- Consistent node spacing
- Progress indicators optional

## Text Placement

- Title at top
- Step/event titles at each node
- Brief descriptions below nodes
- Dates or numbers clearly visible

## Recommended Pairings

- `craft-handmade`: Friendly tutorials and timelines
- `ikea-manual`: Clean assembly instructions
- `corporate-memphis`: Business process flows
- `aged-academia`: Historical discoveries

## Style Guidelines

# craft-handmade (DEFAULT)

Hand-drawn and paper craft aesthetic with warm, organic feel.

## Color Palette

- Primary: Warm pastels, soft saturated colors, craft paper tones
- Background: Light cream (#FFF8F0), textured paper (#F5F0E6)
- Accents: Bold highlights, construction paper colors

## Variants

| Variant | Focus | Visual Emphasis |
|---------|-------|-----------------|
| **Hand-drawn** | Cartoon illustration | Simple icons, slightly imperfect lines |
| **Paper-cutout** | Layered paper craft | Drop shadows, torn edges, texture |

## Visual Elements

- Hand-drawn or cut-paper quality
- Organic, slightly imperfect shapes
- Layered depth with shadows (paper variant)
- Simple cartoon elements and icons
- Character illustrations (people, personalities in cartoon form)
- Ample whitespace, clean composition
- Keywords and core concepts highlighted
- **Strictly hand-drawn—no realistic or photographic elements**

## Style Enforcement

- All imagery must maintain cartoon/illustrated aesthetic
- Replace real photos or realistic figures with hand-drawn equivalents
- Maintain consistent line weight and illustration style throughout

## Typography

- Hand-drawn or casual font style
- Clear, readable labels
- Keywords emphasized with larger/bolder text
- Cut-out letter style for paper variant

## Best For

Educational content, general explanations, friendly infographics, children's content, playful hierarchies

---

Generate the infographic based on the content below:

# ServiceNow ACL Evaluation Flow

## Learning Objectives
- Understand the order of ACL evaluation in ServiceNow.
- Distinguish between table-level and field-level ACLs.
- Recognize the role of conditions and scripts in ACLs.
- Know how to debug ACL effectiveness.

## Section 1: ACL Evaluation Order
**Key Concept:** ServiceNow evaluates ACLs in a specific sequence.
**Content Verbatim:** When a user attempts to read, write, create, or delete a record, ServiceNow evaluates Access Control Lists (ACLs) in the following order:
1. Table-level ACL (record ACL) for the requested operation.
   - If no table ACL grants access, evaluation stops and access is denied.
   - If table ACL grants access, proceed to step 2.
2. Field-level ACL (if applicable) for each field being accessed.
   - Field ACLs only run when the parent table ACL permits the operation.
   - If any field ACL denies access, that field is not accessible (read/write) or the operation may be blocked depending on the operation type.
**Visual Element:** Flowchart with two steps: Table ACL → Field ACL, each with decision diamonds (Grant/Deny).
**Text Labels:** Step 1: Table-level ACL, Step 2: Field-level ACL
**Data Points:** None

## Section 2: ACL Components
**Key Concept:** ACLs consist of conditions or scripts.
**Content Verbatim:** ACL Components:
- Condition builder (preferred) or Script.
- Scripts must set answer = true to grant access.
- Field-level scripts have access to current and previous (on update) but not gs; use current instead.
- ACLs can be role-specific or global (blank role).
**Visual Element:** Icons representing Condition builder (gear) and Script (</>).
**Text Labels:** Condition Builder, Script
**Data Points:** None

## Section 3: Debugging ACLs
**Key Concept:** Use built‑in debugging to see ACL evaluation results.
**Content Verbatim:** Debugging:
- Enable glide.sys.log_security or use Session Debug → Security to see evaluated ACLs with pass/fail.
**Visual Element:** Bug/magnifying glass icon.
**Text Labels:** Debug ACLs
**Data Points:** None

## Section 4: Best Practices
**Key Concept:** Follow recommended practices for effective ACL design.
**Content Verbatim:** Best Practices:
- Prefer Condition builder over scripts for performance.
- Separate create and write ACLs when needed.
- Layer ACLs with Data Policies (mandatory/read-only) and Business Rules for server‑side logic that must always run.
**Visual Element:** Checklist icon.
**Text Labels:** Best Practices
**Data Points:** None

Text labels (in en):
Step 1: Table-level ACL
Step 2: Field-level ACL
Condition Builder
Script
Debug ACLs
Best Practices