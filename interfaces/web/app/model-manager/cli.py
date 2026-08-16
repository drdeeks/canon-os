#!/usr/bin/env python3
"""
CLI tool for managing AI Creative Studio models.

Installed as 'studio-model' command.
"""

import argparse
import json
import os
import sys
import signal
import shutil
import hashlib
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__version__ = "1.0.0"

# Default timeout for HTTP operations (seconds)
DEFAULT_TIMEOUT = 300

# Track partial downloads for cleanup on interrupt
_partial_downloads: List[Path] = []


def _cleanup_partial_downloads():
    """Remove any tracked partial download files."""
    for path in _partial_downloads:
        try:
            if path.exists():
                path.unlink()
                print(colored(f"Cleaned up partial download: {path}", Colors.YELLOW))
        except OSError as e:
            print(colored(f"Warning: Could not clean up {path}: {e}", Colors.YELLOW))


def _signal_handler(signum, frame):
    """Handle termination signals: clean up partial downloads."""
    print(colored("\nReceived signal, cleaning up...", Colors.YELLOW))
    _cleanup_partial_downloads()
    sys.exit(130)


# Register signal handlers
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


# Add parent directory to path to import catalog
import importlib.util
import os

def _import_catalog():
    catalog_path = Path(__file__).parent.parent / "dashboard" / "model_catalog.py"
    spec = importlib.util.spec_from_file_location("catalog", catalog_path)
    catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    return catalog

_catalog = _import_catalog()
MODEL_CATALOG = _catalog.MODEL_CATALOG
search_models = _catalog.search_models
get_model = _catalog.get_model
get_models_by_type = _catalog.get_models_by_type
get_models_by_use_case = _catalog.get_models_by_use_case

# Constants
STATE_DIR = Path("/opt/ai-studio/config")
STATE_FILE = STATE_DIR / "model-state.json"
MODELS_DIR = Path("/mnt/studio/models")
BACKUP_DIR = Path("/opt/ai-studio/backups")

# ANSI colors
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"

def colored(text: str, color: str) -> str:
    """Return colored text for terminal output."""
    return f"{color}{text}{Colors.END}"

def ensure_dirs():
    """Ensure required directories exist."""
    for d in (STATE_DIR, MODELS_DIR, BACKUP_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(colored(f"Warning: Cannot create directory {d}. Permission denied.", Colors.YELLOW))
            # Fallback to user home?
            # For now, continue; commands may fail later.
        except OSError as e:
            print(colored(f"Warning: Could not create directory {d}: {e}", Colors.YELLOW))

def load_state() -> Dict:
    """Load model state from JSON file."""
    ensure_dirs()
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # Default state
    return {
        "installed": {},
        "disk_usage_gb": 0.0,
        "vram_budget_gb": 0.0,
        "last_updated": "",
    }

def save_state(state: Dict):
    """Save model state to JSON file."""
    ensure_dirs()
    state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except OSError as e:
        print(colored(f"Error: Could not save state file: {e}", Colors.RED))

def get_disk_space(path: Path) -> Tuple[float, float]:
    """Return (free_gb, total_gb) for the given path."""
    try:
        usage = shutil.disk_usage(str(path))
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        return free_gb, total_gb
    except OSError:
        return 0.0, 0.0

def human_readable_size(size_gb: float) -> str:
    """Convert GB to human readable string."""
    if size_gb >= 1000:
        return f"{size_gb/1000:.1f} TB"
    elif size_gb >= 1:
        return f"{size_gb:.1f} GB"
    else:
        return f"{size_gb*1024:.0f} MB"

def download_with_progress(url: str, dest: Path, resume: bool = True) -> bool:
    """
    Download file with progress bar using wget or curl.
    Supports resume if interrupted.
    Returns True on success.
    """
    # Check if wget or curl available
    use_wget = shutil.which("wget") is not None
    use_curl = shutil.which("curl") is not None
    
    if not use_wget and not use_curl:
        print(colored("Error: Neither wget nor curl found. Install one to download models.", Colors.RED))
        return False
    
    # Determine partial file
    partial = dest.with_suffix(dest.suffix + ".partial")
    
    # Track partial download for cleanup on interrupt
    _partial_downloads.append(dest)
    _partial_downloads.append(partial)
    
    # If destination already exists and resume is True, maybe download already completed
    if dest.exists() and resume:
        print(colored(f"Destination file already exists: {dest}", Colors.YELLOW))
        # Assume download already completed, skip
        return True
    
    # Build command
    if use_wget:
        cmd = ["wget", "--timeout=60", "--tries=3", "-c", "-O", str(dest), url]
        cmd.append("--show-progress")
        cmd.append("--progress=bar:force:noscroll")
    else:  # curl
        cmd = ["curl", "--max-time", "120", "--retry", "3", "-L", "-o", str(dest), url]
        if resume and partial.exists():
            cmd.append("-C")
            cmd.append("-")
        cmd.append("--progress-bar")
        cmd.append("--fail")
    
    print(colored(f"Downloading from: {url}", Colors.CYAN))
    print(colored(f"Destination: {dest}", Colors.CYAN))
    
    try:
        # Run download command
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(colored(f"Download failed with exit code {result.returncode}", Colors.RED))
            return False
        
        # Move partial to final if needed (wget may create .partial)
        if partial.exists() and not dest.exists():
            partial.rename(dest)
        # Clean up partial if download succeeded and dest exists
        if partial.exists() and dest.exists():
            partial.unlink()
        
        return True
    except KeyboardInterrupt:
        print(colored("\nDownload interrupted. Resume with same command.", Colors.YELLOW))
        return False
    except Exception as e:
        print(colored(f"Download error: {e}", Colors.RED))
        return False

def verify_integrity(file_path: Path, expected_sha256: str) -> bool:
    """Verify file SHA256 hash if expected hash provided."""
    if not expected_sha256:
        print(colored("No SHA256 hash provided, skipping integrity check.", Colors.YELLOW))
        return True
    
    print(colored("Verifying file integrity...", Colors.CYAN))
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        actual = sha256_hash.hexdigest()
        if actual == expected_sha256:
            print(colored("Integrity check passed.", Colors.GREEN))
            return True
        else:
            print(colored(f"Integrity check failed!", Colors.RED))
            print(colored(f"Expected: {expected_sha256}", Colors.RED))
            print(colored(f"Actual:   {actual}", Colors.RED))
            return False
    except IOError as e:
        print(colored(f"Error reading file for integrity check: {e}", Colors.RED))
        return False

def get_installed_models(state: Dict) -> List[str]:
    """Return list of installed model IDs."""
    return list(state.get("installed", {}).keys())

def is_installed(state: Dict, model_id: str) -> bool:
    """Check if model is installed."""
    return model_id in state.get("installed", {})

def format_model_table(models: Dict, state: Dict, show_installed: bool = True) -> str:
    """Format models as a nice table."""
    if not models:
        return colored("No models found.", Colors.YELLOW)
    
    lines = []
    # Header
    header = f"{'Model ID':<40} {'Name':<30} {'Type':<8} {'Size':<8} {'VRAM':<8}"
    if show_installed:
        header += " Status"
    lines.append(colored(header, Colors.BOLD + Colors.UNDERLINE))
    
    for model_id, info in sorted(models.items()):
        size = human_readable_size(info.get("size_gb", 0))
        vram = f"{info.get('vram_gb', 0):.1f} GB"
        status = colored("INSTALLED", Colors.GREEN) if is_installed(state, model_id) else ""
        
        line = f"{model_id:<40} {info.get('name', ''):<30} {info.get('type', ''):<8} {size:<8} {vram:<8}"
        if show_installed:
            line += f" {status}"
        lines.append(line)
    
    return "\n".join(lines)

def cmd_list(args):
    """List models with optional filters."""
    state = load_state()
    models = MODEL_CATALOG.copy()
    
    # Apply filters
    if args.use_case:
        models = {k: v for k, v in models.items() if args.use_case in v.get("use_cases", [])}
    if args.type:
        models = {k: v for k, v in models.items() if v.get("type") == args.type}
    if args.installed:
        installed = get_installed_models(state)
        models = {k: v for k, v in models.items() if k in installed}
    if args.available:
        installed = get_installed_models(state)
        models = {k: v for k, v in models.items() if k not in installed}
    
    if args.json:
        print(json.dumps(models, indent=2))
    else:
        print(colored(f"\nFound {len(models)} model(s):", Colors.CYAN))
        print(format_model_table(models, state))
        print()

def cmd_search(args):
    """Search models by query."""
    results = search_models(args.query)
    state = load_state()
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(colored(f"\nSearch results for '{args.query}':", Colors.CYAN))
        print(format_model_table(results, state))
        print()

def cmd_info(args):
    """Show detailed info about a model."""
    model = get_model(args.model_id)
    if not model:
        print(colored(f"Model '{args.model_id}' not found in catalog.", Colors.RED))
        sys.exit(1)
    
    state = load_state()
    installed = is_installed(state, args.model_id)
    
    if args.json:
        output = model.copy()
        output["installed"] = installed
        if installed:
            output["install_info"] = state["installed"][args.model_id]
        print(json.dumps(output, indent=2))
    else:
        print(colored(f"\nModel: {args.model_id}", Colors.BOLD))
        print(f"  Name: {model.get('name', 'N/A')}")
        print(f"  Description: {model.get('description', 'N/A')}")
        print(f"  Type: {model.get('type', 'N/A')}")
        print(f"  Use Cases: {', '.join(model.get('use_cases', []))}")
        print(f"  Size: {human_readable_size(model.get('size_gb', 0))}")
        print(f"  VRAM Required: {model.get('vram_gb', 0):.1f} GB")
        print(f"  Download URL: {model.get('download_url', 'N/A')}")
        if model.get('sha256'):
            print(f"  SHA256: {model['sha256']}")
        if model.get('alternatives'):
            print(f"  Alternatives: {', '.join(model['alternatives'])}")
        if model.get('api_based'):
            print(colored("  Note: This is an API-based model, no local download required.", Colors.YELLOW))
        
        status = colored("INSTALLED", Colors.GREEN) if installed else colored("NOT INSTALLED", Colors.RED)
        print(f"  Status: {status}")
        if installed:
            info = state["installed"][args.model_id]
            print(f"  Installed at: {info.get('path', 'N/A')}")
            print(f"  Installed on: {info.get('installed_at', 'N/A')}")
        print()

def cmd_pull(args):
    """Download a model."""
    model = get_model(args.model_id)
    if not model:
        print(colored(f"Model '{args.model_id}' not found in catalog.", Colors.RED))
        sys.exit(1)
    
    if model.get("api_based"):
        print(colored(f"Model '{args.model_id}' is API-based and cannot be downloaded locally.", Colors.YELLOW))
        print(colored("Configure API keys instead of downloading.", Colors.YELLOW))
        sys.exit(1)
    
    state = load_state()
    if is_installed(state, args.model_id) and not args.force:
        print(colored(f"Model '{args.model_id}' is already installed. Use --force to re-download.", Colors.YELLOW))
        sys.exit(0)
    
    # Disk space check
    model_size_gb = model.get("size_gb", 0)
    free_gb, total_gb = get_disk_space(MODELS_DIR)
    required_gb = model_size_gb * 2  # Need 2x model size free
    
    print(colored(f"Model size: {human_readable_size(model_size_gb)}", Colors.CYAN))
    print(colored(f"Required free space: {human_readable_size(required_gb)} (2x model size)", Colors.CYAN))
    print(colored(f"Available free space: {human_readable_size(free_gb)}", Colors.CYAN))
    
    if free_gb < required_gb:
        print(colored(f"Insufficient disk space! Need {human_readable_size(required_gb)}, have {human_readable_size(free_gb)}", Colors.RED))
        print(colored("Free up space or choose a smaller model.", Colors.RED))
        sys.exit(1)
    
    # Prepare download
    download_url = model.get("download_url", "")
    if not download_url:
        print(colored(f"No download URL for model '{args.model_id}'.", Colors.RED))
        sys.exit(1)

    # Use local_path from catalog if available, otherwise fall back to MODELS_DIR/<id>/<filename>
    local_path = model.get("local_path", "")
    if local_path:
        dest_path = Path(local_path)
    else:
        filename = download_url.split("/")[-1] or f"{args.model_id}.bin"
        dest_path = MODELS_DIR / args.model_id / filename

    # Create destination directory
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(colored(f"\nPulling model: {args.model_id}", Colors.CYAN))
    
    # Download
    success = download_with_progress(download_url, dest_path, resume=not args.no_resume)
    if not success:
        print(colored("Download failed.", Colors.RED))
        sys.exit(1)
    
    # Verify integrity
    expected_sha256 = model.get("sha256", "")
    if expected_sha256:
        if not verify_integrity(dest_path, expected_sha256):
            print(colored("Integrity verification failed. Removing corrupted file.", Colors.RED))
            dest_path.unlink(missing_ok=True)
            sys.exit(1)
    
    # Update state
    if "installed" not in state:
        state["installed"] = {}
    
    state["installed"][args.model_id] = {
        "path": str(dest_path),
        "size_gb": model_size_gb,
        "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sha256": expected_sha256,
    }
    
    # Update disk usage
    total_installed_gb = sum(
        info.get("size_gb", 0) for info in state["installed"].values()
    )
    state["disk_usage_gb"] = total_installed_gb
    
    save_state(state)
    print(colored(f"\nModel '{args.model_id}' installed successfully!", Colors.GREEN))
    print(colored(f"Location: {dest_path}", Colors.GREEN))

def cmd_remove(args):
    """Remove a model."""
    state = load_state()
    if not is_installed(state, args.model_id):
        print(colored(f"Model '{args.model_id}' is not installed.", Colors.YELLOW))
        sys.exit(0)
    
    model_info = state["installed"].get(args.model_id, {})
    model_path = Path(model_info.get("path", ""))
    model_dir = model_path.parent if model_path.exists() else MODELS_DIR / args.model_id
    
    if args.json:
        print(json.dumps({"action": "remove", "model_id": args.model_id, "path": str(model_dir)}))
    
    if not args.yes:
        confirm = input(colored(f"Remove model '{args.model_id}'? (y/N): ", Colors.YELLOW))
        if confirm.lower() != "y":
            print("Cancelled.")
            sys.exit(0)
    
    # Remove files
    if model_dir.exists():
        try:
            shutil.rmtree(model_dir)
            print(colored(f"Removed directory: {model_dir}", Colors.GREEN))
        except OSError as e:
            print(colored(f"Error removing directory: {e}", Colors.RED))
            sys.exit(1)
    
    # Update state
    state["installed"].pop(args.model_id, None)
    total_installed_gb = sum(
        info.get("size_gb", 0) for info in state["installed"].values()
    )
    state["disk_usage_gb"] = total_installed_gb
    save_state(state)
    
    print(colored(f"Model '{args.model_id}' removed.", Colors.GREEN))

def cmd_status(args):
    """Show overview of installed models and system resources."""
    state = load_state()
    free_gb, total_gb = get_disk_space(MODELS_DIR)
    
    if args.json:
        output = {
            "installed_models": state.get("installed", {}),
            "disk_usage_gb": state.get("disk_usage_gb", 0),
            "vram_budget_gb": state.get("vram_budget_gb", 0),
            "disk_free_gb": free_gb,
            "disk_total_gb": total_gb,
            "last_updated": state.get("last_updated", ""),
        }
        print(json.dumps(output, indent=2))
    else:
        print(colored("\n=== AI Creative Studio Model Status ===", Colors.BOLD))
        print(f"\nDisk Usage:")
        print(f"  Models directory: {MODELS_DIR}")
        print(f"  Total installed size: {human_readable_size(state.get('disk_usage_gb', 0))}")
        print(f"  Free space: {human_readable_size(free_gb)} / {human_readable_size(total_gb)}")
        
        installed = state.get("installed", {})
        print(f"\nInstalled Models ({len(installed)}):")
        if installed:
            for model_id, info in sorted(installed.items()):
                size = human_readable_size(info.get("size_gb", 0))
                installed_at = info.get("installed_at", "N/A")
                print(colored(f"  {model_id}", Colors.GREEN))
                print(f"    Size: {size}, Installed: {installed_at}")
        else:
            print(colored("  No models installed.", Colors.YELLOW))
        
        print(f"\nVRAM Budget: {state.get('vram_budget_gb', 0):.1f} GB")
        print(f"Last updated: {state.get('last_updated', 'N/A')}")
        print()

def cmd_backup(args):
    """Backup model configs and state."""
    ensure_dirs()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"model-backup-{timestamp}"
    
    try:
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Backup state file
        if STATE_FILE.exists():
            shutil.copy2(STATE_FILE, backup_path / "model-state.json")
        
        # Backup catalog (optional)
        catalog_src = Path(__file__).parent.parent / "dashboard" / "model_catalog.py"
        if catalog_src.exists():
            shutil.copy2(catalog_src, backup_path / "model_catalog.py")
        
        # Create tar archive
        archive = backup_path.with_suffix(".tar.gz")
        try:
            subprocess.run(["tar", "-czf", str(archive), "-C", str(backup_path.parent), backup_path.name], check=True)
            # Remove uncompressed directory
            shutil.rmtree(backup_path)
            print(colored(f"Backup created: {archive}", Colors.GREEN))
        except subprocess.CalledProcessError:
            print(colored("Failed to create archive. Backup directory left intact.", Colors.YELLOW))
            print(colored(f"Backup directory: {backup_path}", Colors.YELLOW))
    except OSError as e:
        print(colored(f"Backup failed: {e}", Colors.RED))
        sys.exit(1)

def cmd_restore(args):
    """Restore from backup."""
    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        print(colored(f"Backup directory '{backup_dir}' not found.", Colors.RED))
        sys.exit(1)
    
    # If it's a tar.gz, extract first
    if backup_dir.suffix == ".gz" and backup_dir.with_suffix("").suffix == ".tar":
        extract_dir = backup_dir.parent / "extracted"
        try:
            extract_dir.mkdir(exist_ok=True)
            subprocess.run(["tar", "-xzf", str(backup_dir), "-C", str(extract_dir)], check=True)
            # Find extracted directory
            extracted = list(extract_dir.iterdir())
            if extracted:
                backup_dir = extracted[0]
        except subprocess.CalledProcessError:
            print(colored("Failed to extract backup archive.", Colors.RED))
            sys.exit(1)
        except OSError as e:
            print(colored(f"Failed to create extract directory: {e}", Colors.RED))
            sys.exit(1)
    
    # Look for state file
    state_file = backup_dir / "model-state.json"
    if state_file.exists():
        try:
            shutil.copy2(state_file, STATE_FILE)
            print(colored(f"Restored model state from {state_file}", Colors.GREEN))
        except OSError as e:
            print(colored(f"Failed to restore state file: {e}", Colors.RED))
            sys.exit(1)
    else:
        print(colored("No model-state.json found in backup.", Colors.RED))
        sys.exit(1)
    
    print(colored("Restore completed.", Colors.GREEN))

def cmd_recommend(args):
    """Recommend models based on use case or hardware."""
    state = load_state()
    
    if args.use_case:
        models = get_models_by_use_case(args.use_case)
        if not models:
            print(colored(f"No models found for use case '{args.use_case}'.", Colors.YELLOW))
            sys.exit(0)
        
        if args.json:
            print(json.dumps(models, indent=2))
        else:
            print(colored(f"\nRecommended models for '{args.use_case}':", Colors.CYAN))
            print(format_model_table(models, state))
            print()
    
    elif args.hardware:
        # Estimate VRAM from GPU (simplified)
        vram_gb = 0.0
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                vram_mb = int(result.stdout.strip().split("\n")[0])
                vram_gb = vram_mb / 1024
        except (FileNotFoundError, ValueError, IndexError):
            pass
        
        if vram_gb == 0:
            print(colored("Could not detect GPU VRAM. Assuming 8 GB.", Colors.YELLOW))
            vram_gb = 8.0
        
        print(colored(f"\nDetected VRAM: {vram_gb:.1f} GB", Colors.CYAN))
        
        # Filter models that fit in VRAM
        suitable = {k: v for k, v in MODEL_CATALOG.items() if v.get("vram_gb", 0) <= vram_gb and not v.get("api_based")}
        
        if args.json:
            print(json.dumps(suitable, indent=2))
        else:
            print(colored(f"\nModels that fit in {vram_gb:.1f} GB VRAM:", Colors.CYAN))
            print(format_model_table(suitable, state))
            print()
    else:
        print(colored("Specify --use-case or --hardware for recommendations.", Colors.YELLOW))

def main():
    # Python version check
    if sys.version_info < (3, 6):
        sys.exit("Error: studio-model requires Python 3.6 or later.")
    parser = argparse.ArgumentParser(
        prog="studio-model",
        description="AI Creative Studio Model Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  studio-model list --type image
  studio-model search "product shots"
  studio-model info stable-diffusion-xl-base-1.0
  studio-model pull stable-diffusion-xl-base-1.0
  studio-model remove stable-diffusion-xl-base-1.0
  studio-model status
  studio-model recommend --use-case product-shots
  studio-model recommend --hardware
        """
    )
    
    # Global options
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List available models")
    list_parser.add_argument("--use-case", help="Filter by use case")
    list_parser.add_argument("--type", help="Filter by model type")
    list_parser.add_argument("--installed", action="store_true", help="Show only installed models")
    list_parser.add_argument("--available", action="store_true", help="Show only available (not installed) models")
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search models")
    search_parser.add_argument("query", help="Search query")
    
    # info command
    info_parser = subparsers.add_parser("info", help="Show model details")
    info_parser.add_argument("model_id", help="Model identifier")
    
    # pull command
    pull_parser = subparsers.add_parser("pull", help="Download a model")
    pull_parser.add_argument("model_id", help="Model identifier")
    pull_parser.add_argument("--force", "-f", action="store_true", help="Force re-download")
    pull_parser.add_argument("--no-resume", action="store_true", help="Do not resume interrupted downloads")
    
    # remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a model")
    remove_parser.add_argument("model_id", help="Model identifier")
    remove_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    
    # backup command
    backup_parser = subparsers.add_parser("backup", help="Backup model state")
    
    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_dir", help="Backup directory or archive")
    
    # recommend command
    recommend_parser = subparsers.add_parser("recommend", help="Get model recommendations")
    recommend_parser.add_argument("--use-case", help="Recommend for use case")
    recommend_parser.add_argument("--hardware", action="store_true", help="Recommend based on hardware")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch commands
    commands = {
        "list": cmd_list,
        "search": cmd_search,
        "info": cmd_info,
        "pull": cmd_pull,
        "remove": cmd_remove,
        "status": cmd_status,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "recommend": cmd_recommend,
    }
    
    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print(colored("\nInterrupted.", Colors.YELLOW))
        sys.exit(130)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(colored(f"Error: {e}", Colors.RED))
        sys.exit(1)

if __name__ == "__main__":
    main()
