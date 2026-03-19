"""
Libya PMM - QA/QC Notebook Generator
Creates a month-specific copy of the QA/QC notebook with injected parameters

This script:
1. Copies the template notebook
2. Injects year/month parameters
3. Replaces hardcoded paths with config-based paths
4. Executes the notebook (by default)
5. Saves to the monthly QA_QC folder

Usage:
    # Generate and execute notebook (default)
    python scripts/02_QAQC/generate_qaqc_notebook.py <year> <month>

    # Generate only, don't execute
    python scripts/02_QAQC/generate_qaqc_notebook.py <year> <month> --no-execute

    Examples:
    python scripts/02_QAQC/generate_qaqc_notebook.py 2025 12
    python scripts/02_QAQC/generate_qaqc_notebook.py 2025 12 --no-execute
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import argparse
import shutil
import os

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/02_QAQC/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_month_paths, ensure_month_directories

def create_parameterized_notebook(template_path: Path, year: int, month: int, execute: bool = True):
    """
    Create a month-specific copy of the QA/QC notebook
    
    Args:
        template_path: Path to template notebook
        year: Target year
        month: Target month (1-12)
        execute: Whether to execute the notebook
    
    Returns:
        Path to the generated notebook
    """
    
    print("="*70)
    print("LIBYA PMM - QA/QC NOTEBOOK GENERATOR")
    print("="*70)
    
    # Get paths for this month
    paths = ensure_month_directories(year, month)
    month_tag = paths['month_tag']  # e.g., "Nov25"
    month_name = paths['month_name']  # e.g., "November"
    qaqc_folder = paths['qaqc']  # QA_QC folder from config
    
    # Get absolute project root path to inject into notebook
    from config import PROJECT_ROOT
    project_root_abs = str(PROJECT_ROOT.resolve())
    
    print(f"\nTarget: {month_name} {year}")
    print(f"Month tag: {month_tag}")
    print(f"Output folder: {qaqc_folder}")
    print(f"Project root: {project_root_abs}")
    
    # Load template notebook
    print(f"\n📖 Loading template: {template_path.name}")
    with open(template_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    print(f"   ✓ Loaded {len(nb['cells'])} cells")
    
    # Inject parameters at the top
    parameter_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {
            "tags": ["parameters"]
        },
        "outputs": [],
        "source": [
            "# PARAMETERS - Auto-generated\n",
            f"YEAR = {year}\n",
            f"MONTH = {month}\n",
            f"MONTH_TAG = '{month_tag}'\n",
            f"MONTH_NAME = '{month_name}'\n",
            "\n",
            "# Project root path - Auto-detect (works in Docker or locally)\n",
            "import sys\n",
            "import os\n",
            "from pathlib import Path\n",
            "\n",
            "# Auto-detect project root\n",
            "if os.path.exists('/app'):  # Running in Docker\n",
            "    PROJECT_ROOT = Path('/app')\n",
            "else:  # Running locally\n",
            "    # Get notebook location using ipynb magic\n",
            "    try:\n",
            "        # In Jupyter, get the notebook path\n",
            "        import ipynbname\n",
            "        nb_path = ipynbname.path()\n",
            "        # Notebook is in: Monthly Reports/YYYY/Month/QAQC/\n",
            "        # Go up 4 levels to project root\n",
            "        PROJECT_ROOT = nb_path.parent.parent.parent.parent\n",
            "    except:\n",
            "        # Fallback: use absolute path injected during generation\n",
            f"        PROJECT_ROOT = Path('{project_root_abs}')\n",
            "\n",
            "# Add to path so we can import config\n",
            "sys.path.insert(0, str(PROJECT_ROOT))\n",
            "\n",
            "# Verify config can be imported\n",
            "try:\n",
            "    from config import get_month_paths\n",
            "except ModuleNotFoundError:\n",
            "    print(f'ERROR: Cannot find config.py')\n",
            "    print(f'PROJECT_ROOT: {PROJECT_ROOT}')\n",
            "    print(f'sys.path: {sys.path[:3]}')\n",
            "    raise\n",
            "\n",
            "# Get all paths for this month\n",
            f"paths = get_month_paths(YEAR, MONTH)\n",
            "\n",
            "# Key paths\n",
            "RAW_DATA_PATH = paths['raw_codes']  # Input data (PMM_MonthYY_Codes.xlsx)\n",
            "PROGRESS_FOLDER = paths['progress']  # Output folder for progress tracking\n",
            "QAQC_FOLDER = paths['qaqc']  # This notebook's folder\n",
            "FOLLOWUP_FILE = paths['followup']    # Follow-up output\n",
            "MISSING_PRICES_FILE = paths['missing_prices']  # Missing prices output\n"
        ]
    }
    
    # Insert parameter cell after the first markdown cell (title)
    nb['cells'].insert(1, parameter_cell)
    print(f"   ✓ Injected parameter cell")
    
    # Save the parameterized notebook
    output_notebook = qaqc_folder / f"PMM_QAQC_{month_tag}.ipynb"
    with open(output_notebook, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    
    print(f"\n💾 Saved notebook:")
    print(f"   {output_notebook}")
    
    # Execute if requested
    if execute:
        print(f"\n🔄 Executing notebook...")
        try:
            import nbformat
            from nbconvert.preprocessors import ExecutePreprocessor
            
            # Read the notebook
            with open(output_notebook, 'r', encoding='utf-8') as f:
                nb_obj = nbformat.read(f, as_version=4)
            
            # Execute
            ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
            ep.preprocess(nb_obj, {'metadata': {'path': str(qaqc_folder)}})
            
            # Save executed notebook (overwrite the original)
            with open(output_notebook, 'w', encoding='utf-8') as f:
                nbformat.write(nb_obj, f)
            
            print(f"   ✓ Executed successfully")
            print(f"   Saved: {output_notebook}")
            
        except ImportError:
            print("   ⚠️  nbconvert not installed. Install with:")
            print("      pip install nbconvert nbformat")
        except Exception as e:
            print(f"   ✗ Execution failed: {e}")
    
    print(f"\n{'='*70}")
    print("✅ NOTEBOOK GENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"\nNotebook location:")
    print(f"   {output_notebook}")
    print(f"\nTo open in Jupyter:")
    print(f"   jupyter notebook \"{output_notebook}\"")
    
    return output_notebook


def main():
    parser = argparse.ArgumentParser(
        description="Generate month-specific QA/QC notebook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate and execute notebook for December 2025 (default)
  python scripts/02_QAQC/generate_qaqc_notebook.py 2025 12
  
  # Generate only, don't execute
  python scripts/02_QAQC/generate_qaqc_notebook.py 2025 12 --no-execute

Output:
  The notebook is saved to:
    Monthly Reports/YYYY/Month/QA_QC/PMM_QAQC_MonYY.ipynb
  
  The project root path is injected into the notebook during generation.
  This allows the notebook to import config.py even though it's in a 
  different OneDrive location (team drive vs personal drive).
  
  This creates a permanent, standalone record of the QA/QC process.
        """
    )
    
    parser.add_argument('year', type=int, help='Year (e.g., 2025)')
    parser.add_argument('month', type=int, help='Month (1-12)')
    parser.add_argument('--no-execute', action='store_true',
                       help='Skip execution (just generate the notebook without running it)')
    parser.add_argument('--template', type=str,
                       default='inputs/PMM_QAQC_Template.ipynb',
                       help='Path to template notebook (default: inputs/PMM_QAQC_Template.ipynb)')
    
    args = parser.parse_args()
    
    # Validate month
    if not 1 <= args.month <= 12:
        print(f"Error: Month must be between 1 and 12, got {args.month}")
        sys.exit(1)
    
    # Get template path
    project_root = Path(__file__).resolve().parent.parent.parent
    template_path = project_root / args.template
    
    if not template_path.exists():
        print(f"Error: Template notebook not found at: {template_path}")
        print(f"\nMake sure you have a template at:")
        print(f"  inputs/PMM_QAQC_Template.ipynb")
        sys.exit(1)
    
    try:
        output_notebook = create_parameterized_notebook(
            template_path, 
            args.year, 
            args.month,
            execute=not args.no_execute  # Execute by default, skip if --no-execute flag
        )
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()