"""Generación de notas clínicas SOAP en español con Claude (opcional)."""

from .claude_notes import generate_note, attach_notes_to_cohort

__all__ = ["generate_note", "attach_notes_to_cohort"]
