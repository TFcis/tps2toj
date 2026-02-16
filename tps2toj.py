import argparse
import json
import logging
import os
import sys
import lzma
import tarfile
import tempfile
import shutil
from datetime import datetime
from function import makedirs, copyfile, copyfolder

# progress bar
def progress_bar(ratio, width=40):
    filled = int(width * ratio)
    bar = '#' * filled + '-' * (width - filled)
    sys.stdout.write(f"\rCompression Progress: [{bar}] {ratio*100:5.1f}%")
    sys.stdout.flush()

def make_tar_xz_with_progress(src_dir, dest_path):
    members = []
    base_dir = src_dir
    for root, dirs, files in os.walk(src_dir):
        for fn in files:
            full = os.path.join(root, fn)
            arcname = os.path.relpath(full, base_dir)
            members.append((full, arcname))

    total_bytes = sum(os.path.getsize(full) for full, _ in members)
    processed = 0

    with lzma.open(dest_path, "wb") as xz_out:
        with tarfile.open(mode="w|", fileobj=xz_out) as tar:
            for full, arcname in members:
                tarinfo = tar.gettarinfo(full, arcname)
                with open(full, "rb") as f:
                    tar.addfile(tarinfo, fileobj=f)
                processed += os.path.getsize(full)
                if total_bytes > 0:
                    progress_bar(processed / total_bytes)
    sys.stdout.write("\n")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description='tps2toj')
    parser.add_argument('inputpath', type=str, help='input directory')
    parser.add_argument('outputpath', type=str, help='output directory')
    parser.add_argument('-d', '--debug', action='store_const', dest='loglevel', const=logging.DEBUG)
    parser.add_argument('-k', '--keep-progressing-directory', action='store_true', dest='is_keep_progressing_directory', help='保留過程產出的資料夾')
    parser.set_defaults(loglevel=logging.INFO)
    args = parser.parse_args()
    inputpath = args.inputpath
    outputpath = os.path.abspath(args.outputpath)

    logging.basicConfig(level=args.loglevel, format='%(asctime)s %(levelname)s %(message)s')

    problem_json_path = os.path.join(inputpath, 'problem.json')
    try:
        with open(problem_json_path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logging.error("problem.json not found at '%s'", problem_json_path)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error("Invalid JSON in problem.json at '%s': %s", problem_json_path, e)
        sys.exit(1)
    except OSError as e:
        logging.error("Failed to open problem.json at '%s': %s", problem_json_path, e)
        sys.exit(1)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dirname = os.path.dirname(outputpath) or '.'
    basename = os.path.basename(outputpath)
    stamped_basename = f"{basename}_{timestamp}"
    dest = os.path.join(dirname, f"{stamped_basename}.tar.xz")
    final_output_dir = os.path.join(dirname, stamped_basename)
    work_dir = tempfile.mkdtemp(prefix=f"{stamped_basename}_")

    if os.path.exists(dest):
        os.remove(dest)
    if args.is_keep_progressing_directory and os.path.exists(final_output_dir):
        shutil.rmtree(final_output_dir)
    
    logging.info('Working directory: %s', work_dir)
    makedirs(work_dir)
    
    conf = {
        'timelimit': int(data['time_limit'] * 1000),
        'memlimit': int(data['memory_limit'] * 1024),
        'score': 'rate',
        'check': 'cms' if data['has_checker'] else 'diff',
        'has_grader': data['has_grader'],
        'test': [],
        'metadata': [],
    }
    
    # res/validator
    validator_src = os.path.join(inputpath, 'validator')
    if os.path.isdir(validator_src):
        logging.info('Copying validator')
        makedirs(work_dir, 'res/validator')
        copyfolder((inputpath, 'validator'), (work_dir, 'res/validator'))
    
    # res/checker
    if data['has_checker']:
        logging.info('Copying checker')
        makedirs(work_dir, 'res/checker')
        copyfolder((inputpath, 'checker'), (work_dir, 'res/checker'))
        
    # res/grader
    if data['has_grader']:
        logging.info('Copying grader')
        makedirs(work_dir, 'res/grader')
        copyfolder((inputpath, 'grader'), (work_dir, 'res/grader'))

    # res/testdata/testcases
    logging.info('Copying testcases')
    makedirs(work_dir, 'res/testdata')
    
    offset = 1

    subtasks_json_src = os.path.join(inputpath, 'subtasks.json')
    mapping_src = os.path.join(inputpath, 'tests', 'mapping')
    mapping_data = {}
    with open(subtasks_json_src, 'rt', encoding='utf-8') as json_file:
        subtasks_data = json.load(json_file)
    for sub in subtasks_data['subtasks']:
        mapping_data[sub] = []
    with open(mapping_src, 'rt', encoding='utf-8') as mapping_file:
        for row in mapping_file:
            parts = row.strip().split()
            if len(parts) == 2:
                mapping_data[parts[0]].append(offset)
                copyfile((inputpath, 'tests', f"{parts[1]}.in"),
                    (work_dir, 'res/testdata', f"{offset}.in"))
    try:
        with open(subtasks_json_src, 'rt', encoding='utf-8') as json_file:
            subtasks_data = json.load(json_file)
    except FileNotFoundError:
        logging.error("subtasks.json not found at %s", subtasks_json_src)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON in subtasks.json at %s: %s", subtasks_json_src, e)
        sys.exit(1)
    except OSError as e:
        logging.error("Error reading subtasks.json at %s: %s", subtasks_json_src, e)
        sys.exit(1)

    if 'subtasks' not in subtasks_data or not isinstance(subtasks_data['subtasks'], dict):
        logging.error(
            "subtasks.json at %s has unexpected format: expected a 'subtasks' object",
            subtasks_json_src,
        )
        sys.exit(1)

    for sub in subtasks_data['subtasks']:
        mapping_data[sub] = []

    try:
        with open(mapping_src, 'rt', encoding='utf-8') as mapping_file:
            for lineno, row in enumerate(mapping_file, start=1):
                stripped = row.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                parts = stripped.split()
                if len(parts) != 2:
                    logging.warning(
                        "Skipping malformed line %d in mapping file %s: %r",
                        lineno,
                        mapping_src,
                        row.rstrip("\n"),
                    )
                    continue
                subtask_name, test_name = parts
                if subtask_name not in mapping_data:
                    logging.warning(
                        "Subtask %r in mapping file %s (line %d) is not defined in subtasks.json; skipping.",
                        subtask_name,
                        mapping_src,
                        lineno,
                    )
                    continue
                mapping_data[subtask_name].append(offset)
                copyfile((inputpath, 'tests', f"{test_name}.in"),
                    (work_dir, 'res/testdata', f"{offset}.in"))
                copyfile((inputpath, 'tests', f"{test_name}.out"),
                    (work_dir, 'res/testdata', f"{offset}.out"))
                offset += 1
    except FileNotFoundError:
        logging.error("Mapping file not found at %s", mapping_src)
        sys.exit(1)
    except OSError as e:
        logging.error("Error reading mapping file at %s: %s", mapping_src, e)
        sys.exit(1)

    for sub, cases in mapping_data.items():
        subtask_info = subtasks_data['subtasks'].get(sub)
        if not isinstance(subtask_info, dict) or 'score' not in subtask_info:
            logging.error(
                "Subtask %r in subtasks.json at %s is missing a 'score' field or has unexpected format",
                sub,
                subtasks_json_src,
            )
            sys.exit(1)
        conf['test'].append({
            'data': cases,
            'weight': subtask_info['score'],
        })

    logging.info('Creating config file')
    with open(os.path.join(work_dir, 'conf.json'), 'w', encoding='utf-8') as conffile:
        json.dump(conf, conffile, indent=4)

    # http/statement
    makedirs(work_dir, 'http')
    statement_path = os.path.join(inputpath, 'statement', 'index.pdf')
    if os.path.exists(statement_path):
        logging.info('Copying statements')
        copyfile((statement_path,), 
                 (work_dir, 'http', 'cont.pdf'))

    logging.info('Start compressing with progress...')
    try:
        make_tar_xz_with_progress(work_dir, dest)

        if args.is_keep_progressing_directory:
            logging.info('Preserving working directory -> %s', final_output_dir)
            shutil.move(work_dir, final_output_dir)
    finally:
        if not args.is_keep_progressing_directory and os.path.isdir(work_dir):
            logging.info('Cleaning working directory')
            shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == '__main__':
    main()