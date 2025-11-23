# 🛠️ Technical Requirements & Stack

> **2025 Standard**: Modern, reproducible, and scalable Python environment.

## 💻 System Prerequisites

| Component | Requirement | Reason |
| :--- | :--- | :--- |
| **OS** | macOS / Linux / Windows | Cross-platform compatibility |
| **Python** | **3.12+** | Performance improvements & strict typing |
| **Manager** | **Poetry** | Deterministic dependency management |

## 🏗️ Technology Stack

### Core Processing Engine
- **Pandas (2.3+)**: High-performance data manipulation and analysis.
- **NumPy (2.3+)**: Vectorized numerical operations for financial calculations.

### Data Acquisition & Automation
- **Playwright**: Next-gen browser automation for reliable data scraping (replaces Selenium).
- **OpenPyXL**: Native Excel file handling for report generation.

### Visualization Layer
- **Matplotlib (3.10+)**: Enterprise-grade plotting and charting library.

### Quality Assurance (DevDependencies)
- **Pytest**: Advanced testing framework with fixture support.
- **Black**: Uncompromising code formatter.
- **Flake8**: Style guide enforcement.
- **Bandit**: Security vulnerability scanner.

## 📦 Dependency Management Strategy

We use **Poetry** for dependency resolution and packaging. This ensures:
1.  **Reproducibility**: `poetry.lock` guarantees the exact same environment on every machine.
2.  **Isolation**: Virtual environments are managed automatically.
3.  **Security**: Dependency vulnerabilities are easily tracked and updated.

## 🚀 Installation Guide

```bash
# 1. Install Poetry (if not present)
curl -sSL https://install.python-poetry.org | python3 -

# 2. Clone & Install
git clone https://github.com/darekwojciechowski/xtb-dividend-analysis.git
cd xtb-dividend-analysis
poetry install

# 3. Activate Environment
poetry shell
```

---
*Stack selected for performance, maintainability, and developer experience.*
