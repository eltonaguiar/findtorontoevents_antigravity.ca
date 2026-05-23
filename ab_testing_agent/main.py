#!/usr/bin/env python3
"""
A/B Testing Agent - Main entry point

This script provides command-line interface to run different components
of the A/B Testing Agent.
"""

import argparse
import sys
import os

# Add the ab_testing_agent directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from ab_testing_agent import ABTestingAgent, quick_experiment
from config import Config

def main():
    parser = argparse.ArgumentParser(description='A/B Testing Agent')
    parser.add_argument('command', choices=[
        'api', 'dashboard', 'agent', 'quick-experiment'
    ], help='Component to run')

    # API and Dashboard options
    parser.add_argument('--host', default=None, help='Host to bind to')
    parser.add_argument('--port', type=int, default=None, help='Port to bind to')

    # Quick experiment options
    parser.add_argument('--name', help='Experiment name')
    parser.add_argument('--variants', help='Comma-separated list of variants')
    parser.add_argument('--metric', help='Target metric')

    args = parser.parse_args()

    config = Config()

    if args.command == 'api':
        agent = ABTestingAgent(config)
        agent.run_api_server(host=args.host, port=args.port)

    elif args.command == 'dashboard':
        agent = ABTestingAgent(config)
        agent.run_dashboard(host=args.host, port=args.port)

    elif args.command == 'agent':
        agent = ABTestingAgent(config)
        agent.start_monitoring()

        try:
            # Keep the agent running
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            agent.stop_monitoring()
            print("Agent stopped")

    elif args.command == 'quick-experiment':
        if not all([args.name, args.variants, args.metric]):
            print("Error: --name, --variants, and --metric are required for quick-experiment")
            sys.exit(1)

        variants = [v.strip() for v in args.variants.split(',')]
        exp_id = quick_experiment(args.name, variants, args.metric, config)
        print(f"Created experiment '{args.name}' with ID: {exp_id}")
        print(f"Variants: {', '.join(variants)}")
        print(f"Target metric: {args.metric}")

if __name__ == '__main__':
    main()