#!/usr/bin/env python3
"""
Run LVBOT Availability Diagnostics
=================================

Purpose: Run all debugging tools to diagnose availability detection issues.
This script coordinates all three debugging tools and provides a summary.
"""
from tracking import t
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
import json


def print_header(text: str):
    """Print a formatted header"""
    t('archive.scripts.monitoring.run_availability_diagnostics.print_header')
    print(f"\n{'='*60}")
    print(f"🔍 {text}")
    print(f"{'='*60}\n")


def print_summary(title: str, content: str):
    """Print a formatted summary box"""
    t('archive.scripts.monitoring.run_availability_diagnostics.print_summary')
    print(f"\n┌─ {title} {'─' * (55 - len(title))}┐")
    for line in content.split('\n'):
        if line:
            print(f"│ {line:<56} │")
    print(f"└{'─'*58}┘\n")


async def run_debug_court_availability():
    """Run the comprehensive court availability debugger"""
    t('archive.scripts.monitoring.run_availability_diagnostics.run_debug_court_availability')
    print_header("Running Court Availability Debugger")
    print("This will navigate to each court, take screenshots, and compare")
    print("what's displayed vs what the bot detects...")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, 'debug_court_availability.py',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            print("✅ Court availability debug completed successfully")
            # Try to find and read the latest debug results
            debug_dirs = list(Path('.').glob('debug_court_availability_*'))
            if debug_dirs:
                latest_dir = sorted(debug_dirs)[-1]
                results_file = latest_dir / 'debug_results.json'
                if results_file.exists():
                    with open(results_file) as f:
                        results = json.load(f)
                    
                    # Print summary
                    summary_lines = []
                    for court in [1, 2, 3]:
                        court_summary = results['summary'].get(f'court_{court}', {})
                        if court_summary.get('status') == 'error':
                            summary_lines.append(f"Court {court}: ERROR")
                        else:
                            debug_count = court_summary.get('debug_detected', 0)
                            bot_count = court_summary.get('bot_detected', 0)
                            match = "✅" if court_summary.get('match') else "❌"
                            summary_lines.append(f"Court {court}: Debug={debug_count}, Bot={bot_count} {match}")
                    
                    print_summary("Debug Results", '\n'.join(summary_lines))
                    return latest_dir
        else:
            print(f"❌ Debug failed: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Error running debug: {e}")
        
    return None


async def run_visual_comparison():
    """Run the visual slot comparison tool"""
    t('archive.scripts.monitoring.run_availability_diagnostics.run_visual_comparison')
    print_header("Running Visual Slot Comparison")
    print("This will create annotated screenshots showing detected vs missed slots...")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, 'visual_slot_comparison.py',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            print("✅ Visual comparison completed successfully")
            # Find the latest visual comparison directory
            visual_dirs = list(Path('.').glob('visual_comparison_*'))
            if visual_dirs:
                latest_dir = sorted(visual_dirs)[-1]
                report_file = latest_dir / 'comparison_report.json'
                if report_file.exists():
                    with open(report_file) as f:
                        report = json.load(f)
                    
                    # Print summary
                    summary_lines = []
                    for court in [1, 2, 3]:
                        court_data = report['courts'].get(court, {})
                        if 'error' in court_data:
                            summary_lines.append(f"Court {court}: ERROR")
                        else:
                            detected = court_data.get('detected_count', 0)
                            summary_lines.append(f"Court {court}: {detected} slots detected")
                    
                    print_summary("Visual Comparison", '\n'.join(summary_lines))
                    return latest_dir
        else:
            print(f"❌ Visual comparison failed: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Error running visual comparison: {e}")
        
    return None


async def run_realtime_monitor(duration_seconds: int = 30):
    """Run the real-time monitor for a short duration"""
    t('archive.scripts.monitoring.run_availability_diagnostics.run_realtime_monitor')
    print_header("Running Real-time Monitor")
    print(f"This will monitor availability for {duration_seconds} seconds...")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, 'realtime_availability_monitor.py',
            '--interval', '5',
            '--duration', str(duration_seconds // 60 + 1),  # Convert to minutes
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Let it run for the specified duration
        await asyncio.sleep(duration_seconds)
        
        # Terminate the process
        proc.terminate()
        await proc.wait()
        
        print("✅ Real-time monitoring completed")
        
        # Find the latest monitor directory
        monitor_dirs = list(Path('.').glob('realtime_monitor_*'))
        if monitor_dirs:
            latest_dir = sorted(monitor_dirs)[-1]
            state_file = latest_dir / 'monitor_state.json'
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                
                # Print summary
                summary_lines = []
                current = state.get('current_availability', {})
                for court in sorted(current.keys()):
                    if isinstance(current[court], dict) and 'error' not in current[court]:
                        total = sum(len(times) for times in current[court].values())
                        summary_lines.append(f"Court {court}: {total} slots")
                    else:
                        summary_lines.append(f"Court {court}: ERROR")
                
                changes = len(state.get('change_history', []))
                summary_lines.append(f"\nTotal changes detected: {changes}")
                
                print_summary("Monitor Results", '\n'.join(summary_lines))
                return latest_dir
                
    except Exception as e:
        print(f"❌ Error running monitor: {e}")
        
    return None


def create_final_report(debug_dir: Path, visual_dir: Path, monitor_dir: Path):
    """Create a consolidated final report"""
    t('archive.scripts.monitoring.run_availability_diagnostics.create_final_report')
    print_header("Creating Consolidated Report")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(f"diagnostics_report_{timestamp}")
    report_dir.mkdir(exist_ok=True)
    
    # Consolidate findings
    findings = {
        'timestamp': timestamp,
        'tools_run': {
            'debug_court_availability': str(debug_dir) if debug_dir else 'Failed',
            'visual_slot_comparison': str(visual_dir) if visual_dir else 'Failed',
            'realtime_monitor': str(monitor_dir) if monitor_dir else 'Failed'
        },
        'recommendations': []
    }
    
    # Analyze results and provide recommendations
    if debug_dir and visual_dir:
        # Check if selectors need updating
        debug_results = debug_dir / 'debug_results.json'
        if debug_results.exists():
            with open(debug_results) as f:
                data = json.load(f)
                
            # Check for selector issues
            for court in [1, 2, 3]:
                court_data = data['court_analysis'].get(court, {})
                if 'selector_results' in court_data:
                    working_selectors = [
                        s for s, r in court_data['selector_results'].items()
                        if isinstance(r, dict) and r.get('count', 0) > 0
                    ]
                    if len(working_selectors) < 3:
                        findings['recommendations'].append(
                            f"⚠️ Court {court}: Only {len(working_selectors)} selectors working. "
                            "Consider updating TIME_SLOT_SELECTORS in constants.py"
                        )
                        
            # Check for detection mismatches
            summary = data.get('summary', {})
            for court in [1, 2, 3]:
                court_summary = summary.get(f'court_{court}', {})
                if not court_summary.get('match', True):
                    findings['recommendations'].append(
                        f"❌ Court {court}: Bot detection doesn't match visual elements. "
                        f"Debug found {court_summary.get('debug_detected', 0)} but "
                        f"bot found {court_summary.get('bot_detected', 0)}."
                    )
                    
    # Save consolidated report
    report_file = report_dir / 'diagnostics_summary.json'
    with open(report_file, 'w') as f:
        json.dump(findings, f, indent=2)
        
    # Create markdown summary
    md_lines = [
        "# LVBOT Availability Diagnostics Report",
        f"\nGenerated: {timestamp}",
        "\n## Tools Run\n"
    ]
    
    for tool, result in findings['tools_run'].items():
        status = "✅" if result != 'Failed' else "❌"
        md_lines.append(f"- {tool}: {status} {result}")
        
    if findings['recommendations']:
        md_lines.append("\n## Recommendations\n")
        for rec in findings['recommendations']:
            md_lines.append(f"- {rec}")
    else:
        md_lines.append("\n## Status\n")
        md_lines.append("✅ All systems appear to be functioning correctly!")
        
    md_file = report_dir / 'diagnostics_summary.md'
    md_file.write_text('\n'.join(md_lines))
    
    print(f"\n📊 Consolidated report saved to: {report_dir}")
    print(f"📄 View summary: {md_file}")
    
    # Print recommendations
    if findings['recommendations']:
        print_summary("⚠️  Recommendations", '\n'.join(findings['recommendations']))
    else:
        print_summary("✅ Status", "All systems functioning correctly!")


async def main():
    """Main diagnostic coordinator"""
    t('archive.scripts.monitoring.run_availability_diagnostics.main')
    print("\n" + "="*60)
    print("🏥 LVBOT AVAILABILITY DIAGNOSTICS")
    print("="*60)
    print("\nThis will run comprehensive diagnostics to compare:")
    print("1. What the bot detects vs what's actually visible")
    print("2. Create visual comparisons with annotations")
    print("3. Monitor real-time changes")
    print("\nEstimated time: 2-3 minutes\n")
    
    # Ask for confirmation
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Diagnostics cancelled.")
        return
        
    # Run all tools
    debug_dir = await run_debug_court_availability()
    visual_dir = await run_visual_comparison()
    monitor_dir = await run_realtime_monitor(30)  # Run for 30 seconds
    
    # Create final report
    create_final_report(debug_dir, visual_dir, monitor_dir)
    
    print("\n✨ Diagnostics complete!")


if __name__ == "__main__":
    asyncio.run(main())
