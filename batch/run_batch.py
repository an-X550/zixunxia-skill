#!/usr/bin/env python
import argparse, sys, uuid
from pathlib import Path
_BATCH_DIR = Path(__file__).resolve().parent
if str(_BATCH_DIR) not in sys.path:
    sys.path.insert(0, str(_BATCH_DIR))

def main():
    parser = argparse.ArgumentParser(description='ZixunXia Batch')
    parser.add_argument('input_file')
    parser.add_argument('--concurrency', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    from config import DEEPSEEK_API_KEY
    if not DEEPSEEK_API_KEY and not args.dry_run:
        print('ERROR: DEEPSEEK_API_KEY not set'); sys.exit(1)
    input_path = Path(args.input_file)
    if not input_path.is_absolute(): input_path = Path.cwd() / input_path
    if not input_path.exists(): print(f'ERROR: not found: {input_path}'); sys.exit(1)
    print(f'ZixunXia Batch v0.1.0 | {input_path}')
    from data_loader import parse_input_file, validate_student
    students = parse_input_file(str(input_path))
    print(f'Students: {len(students)}')
    for s in students:
        for w in validate_student(s): print(f'  WARN: {w}')
    if args.dry_run:
        print('Dry run OK.'); sys.exit(0)
    if args.resume:
        from output_writer import read_goal_state
        active = [s for s in students if not (read_goal_state(s['nickname']) or {}).get('goals',{}).get('pre_consultation',{}).get('major_recommendations_generated')]
        print(f'Resume: {len(active)} remaining'); students = active
        if not students: print('All done.'); sys.exit(0)
    if args.concurrency:
        import config; config.MAX_CONCURRENT_STUDENTS = args.concurrency
    from graph import app
    batch_id = f'batch_{uuid.uuid4().hex[:8]}'
    state = {'students': students, 'results': [], 'batch_id': batch_id, 'input_file': str(input_path), 'total': len(students), 'completed': 0, 'failed': 0, 'flagged': 0}
    print(f'Batch: {batch_id}')
    try:
        result = app.invoke(state, {'configurable': {'thread_id': batch_id}, 'recursion_limit': 100})
        print(f'Done! OK:{result.get("completed",0)} FAIL:{result.get("failed",0)} FLAG:{result.get("flagged",0)}')
    except KeyboardInterrupt: print('Interrupted. Use --resume.'); sys.exit(130)
    except Exception as e: print(f'ERROR: {e}'); sys.exit(1)
if __name__ == '__main__': main()
