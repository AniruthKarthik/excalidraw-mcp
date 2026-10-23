"""Comprehensive diagram design guidelines for AI agents and developers."""

from typing import Any

from excalidraw_mcp.errors import SceneError

DESIGN_TOPICS: dict[str, dict[str, Any]] = {
    "layout": {
        "title": "Diagram Layout & Flow Structure",
        "principles": [
            "Establish a clear primary reading direction: Left-to-Right (LR) for pipelines and time sequences; Top-to-Bottom (TD/TB) for hierarchies, dependencies, and layered architectures.",
            "Align related elements horizontally or vertically along common axes. Irregular placement increases visual friction.",
            "Minimize line intersections and backwards-pointing arrows. When loops are necessary, route feedback paths around the perimeter rather than cutting through core tiers.",
            "Group sub-systems and services into clearly framed clusters or subgraphs before routing cross-cluster connectors.",
        ],
        "recommendations": {
            "primary_direction": "horizontal for data processing / user workflows; vertical for client-server-database tiering",
            "alignment": "grid-aligned with snapped centers or tops",
            "tiering": "Layer 1 (Clients/Edge) -> Layer 2 (Gateways) -> Layer 3 (Compute/Services) -> Layer 4 (Databases/Caches)",
        },
    },
    "spacing": {
        "title": "Spacing, Dimensions & Margins",
        "principles": [
            "Use consistent inter-node gaps: 60px to 100px for horizontal stages, 40px to 80px for vertical layers.",
            "Ensure frame containers have at least 30px to 50px of internal padding around all contained child shapes.",
            "Maintain balanced node sizing: standard service boxes should be 120-160px wide by 60-80px tall.",
            "Avoid crowded label text: ensure shapes have at least 10px internal text margin so labels never touch borders.",
        ],
        "standards": {
            "node_gap_x": 80,
            "node_gap_y": 60,
            "frame_padding": 40,
            "canvas_padding": 40,
            "standard_box": {"width": 140, "height": 70},
            "standard_database": {"width": 120, "height": 70},
            "standard_decision": {"width": 120, "height": 70},
        },
    },
    "colors": {
        "title": "Color Palettes, Fills & Semantic Styling",
        "principles": [
            "Follow the 60-30-10 rule: 60% neutral backgrounds, 30% structural secondary tones, 10% high-contrast accent colors.",
            "Use semantic color conventions consistently across the diagram so viewers grasp component roles immediately.",
            "Avoid overly saturated or glaring background colors; prefer muted, readable pastels for shapes and dark tones for text.",
            "Ensure high contrast between background fills and text labels (e.g. dark text #1e1e1e on light fills; light text on dark fills).",
        ],
        "palette": {
            "frontend_clients": {"stroke": "#1971c2", "background": "#e7f5ff", "label": "Client / UI"},
            "api_gateways": {"stroke": "#0c8599", "background": "#e3fafc", "label": "Gateway / Edge"},
            "services_compute": {"stroke": "#5f3dc4", "background": "#f3f0ff", "label": "Backend Service"},
            "databases_storage": {"stroke": "#2f9e44", "background": "#ebfbee", "label": "Database / Store"},
            "message_queues": {"stroke": "#d9480f", "background": "#fff4e6", "label": "Queue / Streaming"},
            "security_auth": {"stroke": "#c92a2a", "background": "#ffe3e3", "label": "Auth / Firewall"},
            "external_third_party": {"stroke": "#495057", "background": "#f1f3f5", "label": "External / 3rd Party"},
        },
        "fill_styles": {
            "solid": "Default for core active components",
            "hachure": "Secondary, cached, or transient components",
            "cross-hatch": "Legacy or third-party external dependencies",
        },
    },
    "typography": {
        "title": "Typography, Text Sizing & Hierarchy",
        "principles": [
            "Establish a clear type hierarchy: Diagram Title (28-36px), Frame/Cluster Headers (20-24px), Shape Labels (16-20px), Annotations & Connectors (12-14px).",
            "Keep labels concise and punchy. Aim for 1 to 3 words per node. Break longer labels across multiple lines (max 20 chars per line).",
            "Use monospace fonts for code snippets, database table names, HTTP routes, ports, and file names.",
            "Always center bound labels inside shapes to maintain visual symmetry.",
        ],
        "font_scale": {
            "title": 28,
            "frame_header": 20,
            "node_label": 16,
            "connector_label": 14,
            "annotation": 12,
        },
    },
    "grouping": {
        "title": "Frames, Groups & Hierarchical Boundaries",
        "principles": [
            "Use Frames (`add_frame`) for visual system boundaries, networks, VPCs, and microservice clusters. Frames visually contain children.",
            "Use Groups (`group_elements`) for tightly-coupled multi-element assemblies (e.g. icon + text card) that should transform and move together as a single unit.",
            "Do not overload a single frame with more than 6-8 components; nest subgraphs or break into separate diagrams if complexity grows.",
        ],
        "criteria": {
            "use_frame_when": "Visual container with boundary border, background grouping, and named subsystem title",
            "use_group_when": "Elements need coupled dragging, coordinated selection, or unified translation",
        },
    },
    "arrows": {
        "title": "Arrows, Connectors & Routing",
        "principles": [
            "Always bind arrows to shapes using `connect` so connections track node movements dynamically.",
            "Use straight connectors for direct, unobstructed paths. Use elbowed connectors (`elbowed=True`) for orthogonal multi-tier routing.",
            "Label connector arrows with active verbs describing the communication or protocol (e.g., 'GET /orders', 'publishes event', 'queries SQL').",
            "Use dashed arrows (`strokeStyle='dashed'`) for asynchronous messages, event broadcasts, or optional fallbacks.",
            "Ensure arrows point in the direction of data initiation or dependency flow.",
        ],
        "styles": {
            "solid": "Synchronous request/response (HTTP, gRPC, direct function call)",
            "dashed": "Asynchronous messaging (Kafka, SQS, Webhook, pub/sub)",
            "dotted": "Weak reference, observation, telemetry, or optional dependency",
        },
    },
    "readability": {
        "title": "Readability, Cognitive Load & Best Practices",
        "principles": [
            "Keep the 7±2 rule: Aim for no more than 7 primary components per view to avoid cognitive overload.",
            "Use the C4 model level-of-detail: System Context -> Container Diagram -> Component Diagram.",
            "Avoid orphan elements: every element should either connect to a workflow or sit inside a contextual frame.",
            "Include a descriptive title and subtitle so viewers immediately understand the diagram's scope and context.",
        ],
        "anti_patterns": [
            "Crossing lines (Spider-web diagram): reorder nodes or use elbowed routing to keep paths separated.",
            "Unlabeled mystery arrows: always annotate arrows with protocol or intent.",
            "Wall of text: summarize in node titles and place extended details in captions or code blocks.",
        ],
    },
}


def get_diagram_guide(topic: str | None = None) -> dict[str, Any]:
    """Retrieve diagram design guidelines, either complete or filtered by topic."""
    if topic:
        normalized_topic = topic.strip().lower()
        if normalized_topic in DESIGN_TOPICS:
            return {
                "topic": normalized_topic,
                "guide": DESIGN_TOPICS[normalized_topic],
                "available_topics": list(DESIGN_TOPICS.keys()),
            }
        # Fuzzy match / topic aliases
        aliases = {
            "color": "colors",
            "palette": "colors",
            "font": "typography",
            "text": "typography",
            "arrow": "arrows",
            "connector": "arrows",
            "connectors": "arrows",
            "frame": "grouping",
            "frames": "grouping",
            "groups": "grouping",
            "space": "spacing",
            "padding": "spacing",
            "margin": "spacing",
            "flow": "layout",
        }
        matched = aliases.get(normalized_topic)
        if matched and matched in DESIGN_TOPICS:
            return {
                "topic": matched,
                "guide": DESIGN_TOPICS[matched],
                "available_topics": list(DESIGN_TOPICS.keys()),
            }
        raise SceneError(
            f"Unknown topic '{topic}'. Available topics: {list(DESIGN_TOPICS.keys())}"
        )

    return {
        "topic": "all",
        "guide": DESIGN_TOPICS,
        "available_topics": list(DESIGN_TOPICS.keys()),
    }
