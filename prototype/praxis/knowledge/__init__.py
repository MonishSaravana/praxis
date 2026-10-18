"""Company knowledge backend (ours): per-company profiles, document ingest, local retrieval, per-procedure compile.

Ingest runs once per file, locally: parse pages -> find sections and procedures -> chunk -> index (all on this
machine, keyed by the file's SHA-256). Only the procedures a manager picks are compiled with Claude, and only from
their own section's text (cached by content hash). The live engine gets the compiled graph plus short knowledge
cards quoted from the source; it never reads a document. Questions retrieve a few chunks locally and send only
those. See docs/BACKEND.md.
"""
