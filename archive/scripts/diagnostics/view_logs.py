#!/usr/bin/env python3
"""
Simple log viewer to analyze bot logs
"""
from tracking import t
import pathlib
import sys

from pathlib import Path

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import os
from datetime import datetime

# Log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

def view_logs(log_type='debug', lines=100, filter_text=None):
    """
    View recent log entries
    
    Args:
        log_type: 'main', 'debug', or 'error'
        lines: Number of recent lines to show
        filter_text: Optional text to filter lines
    """
    t('archive.scripts.diagnostics.view_logs.view_logs')
    log_files = {
        'main': 'bot.log',
        'debug': 'bot_debug.log',
        'error': 'bot_errors.log'
    }
    
    log_file = os.path.join(LOG_DIR, log_files.get(log_type, 'bot_debug.log'))
    
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return
    
    print(f"\n{'='*80}")
    print(f"Viewing {log_type} log: {log_file}")
    print(f"Last {lines} lines" + (f" filtered by '{filter_text}'" if filter_text else ""))
    print(f"{'='*80}\n")
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
        # Get last N lines
        recent_lines = all_lines[-lines:]
        
        # Apply filter if specified
        if filter_text:
            recent_lines = [line for line in recent_lines if filter_text.lower() in line.lower()]
        
        # Print lines
        for line in recent_lines:
            print(line.rstrip())
            
        print(f"\n{'='*80}")
        print(f"Total lines shown: {len(recent_lines)}")
        
    except Exception as e:
        print(f"Error reading log: {e}")

def search_errors():
    """Search for errors in all logs"""
    t('archive.scripts.diagnostics.view_logs.search_errors')
    print("\n" + "="*80)
    print("SEARCHING FOR ERRORS IN ALL LOGS")
    print("="*80 + "\n")
    
    error_keywords = ['ERROR', 'CRITICAL', 'Exception', 'Failed', 'failed', 'Error', 'error']
    
    for log_name in ['main', 'debug', 'error']:
        log_file = os.path.join(LOG_DIR, {'main': 'bot.log', 'debug': 'bot_debug.log', 'error': 'bot_errors.log'}[log_name])
        
        if not os.path.exists(log_file):
            continue
            
        print(f"\n--- {log_name.upper()} LOG ---")
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            error_lines = []
            for i, line in enumerate(lines):
                if any(keyword in line for keyword in error_keywords):
                    error_lines.append((i+1, line.rstrip()))
            
            if error_lines:
                print(f"Found {len(error_lines)} error lines:")
                for line_num, line in error_lines[-10:]:  # Show last 10 errors
                    print(f"  Line {line_num}: {line}")
            else:
                print("No errors found")
                
        except Exception as e:
            print(f"Error reading {log_name} log: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View bot logs')
    parser.add_argument('--type', choices=['main', 'debug', 'error'], default='debug', help='Log type to view')
    parser.add_argument('--lines', type=int, default=100, help='Number of lines to show')
    parser.add_argument('--filter', help='Filter lines containing this text')
    parser.add_argument('--errors', action='store_true', help='Search for errors in all logs')
    
    args = parser.parse_args()
    
    if args.errors:
        search_errors()
    else:
        view_logs(args.type, args.lines, args.filter)
