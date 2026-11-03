"""Synthetic regression evaluation; never present it as real-world accuracy."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from silvertrap.config import Config
from silvertrap.scenarios import SCENARIOS
from silvertrap.service import Service


def main():
    failures = 0
    with TemporaryDirectory() as directory:
        service = Service(Config(Path(directory)))
        try:
            for scenario in SCENARIOS:
                case = service.create_case(scenario=scenario['id'])
                case = service.simulate(case['id'], all_steps=True)
                analysis = case['analysis']
                correct = analysis['classification'] == scenario['category']
                linked = analysis['quality']['findings'] == analysis['quality']['evidence_linked']
                control = not analysis['objectives'] if scenario['id']=='benign' else case['status']=='paused' if scenario['id']=='injection' else True
                passed = correct and linked and control and case['integrity']['valid']
                failures += not passed
                print(f"{'PASS' if passed else 'FAIL'} {scenario['id']}: {analysis['classification']}; observed stages {analysis['coverage']['observed']}/6; literal source links {analysis['quality']['evidence_linked']}/{analysis['quality']['findings']}")
        finally:
            service.store.close()
    print(f'\n{len(SCENARIOS)-failures}/{len(SCENARIOS)} synthetic fixtures passed. This is a regression check, not an independent accuracy benchmark.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
