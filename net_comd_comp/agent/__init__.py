"""Agent package.

Import submodules directly (e.g. ``from net_comd_comp.agent.search import SemanticSearcher``).
This package intentionally avoids eager imports to prevent a circular dependency:
index.store -> agent.cli_skeleton -> agent (package) -> compare -> search -> vector_index.
"""

__all__ = ["CommandComparator", "SemanticSearcher"]