## SQL-101 Import Notes

This directory stores a teacher-material import for the teacher customization
stage.

Imported source:
- Repository: `https://github.com/s-shemmee/SQL-101`

Import policy:
- Files under `original/` are kept in their original form.
- Do not edit or rewrite files inside `original/`.
- Any preprocessing, extraction, or dataset-building for teacher-stage training
  should happen in separate derived directories, for example:
  - `data/teachers/sql101/processed/`
  - `data/teachers/sql101/metadata/`

Current imported materials:
- `original/README.md`
- `original/LICENSE`
- `original/Sql Notes Part 1 & Part 2 marged.pdf`
- `original/Sql Short Notes Part 3.pdf`

Role in this project:
- `generated_modules/` remains the source for general cybersecurity SFT.
- `data/teachers/sql101/original/` is a teacher-provided course corpus for
  teacher-stage customization.
