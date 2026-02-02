# 🔐 pypirc_gen (Archived)

A small utility for **generating and validating `.pypirc` files** for PyPI and TestPyPI uploads.

This project is archived and was created to solve repeated authentication and configuration issues when publishing Python packages.

---

## 🚀 What problem does this solve?

Publishing to PyPI often fails because of subtle `.pypirc` issues:
- incorrect repository URLs
- malformed API tokens
- wrong file placement
- confusion between PyPI and TestPyPI

`pypirc_gen` exists to remove guesswork and reduce human error.

---

## ✨ What it does

- Generates a valid `.pypirc` file
- Supports PyPI and TestPyPI repositories
- Validates token formatting
- Writes config to the correct location
- Helps diagnose common auth failures

This tool does **not** upload packages — it ensures your auth config is correct *before* you try.

---

## ▶️ Usage (example)

```bash
python pypirc_gen.py
```
Follow the prompts to:

- select repository (PyPI / TestPyPI)
- enter your API token
- generate a .pypirc file

## 🧠 Why this exists

This project was created after repeated real-world issues with:

- twine upload
- PyPI token errors
- broken or inconsistent .pypirc files

It later informed authentication features in larger tooling.

## ⚠️ Project status

Archived / Utility Prototype

- Minimal by design
- No GUI
- No package upload logic
- Preserved as a focused auth-helper tool

## 📜 License

Unlicensed (personal archive).

## 🏷️ Status
Archived — small, focused, and problem-driven.
