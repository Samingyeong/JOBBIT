"""Date-based Obsidian checklists owned by the calendar."""
import os
import re
from tempfile import NamedTemporaryFile


FOLDER = '06 Daily Todos'
CHECKBOX = re.compile(r'^- \[([ xX])] ([^\r\n]+)(\r?\n)?$')


def task_path(root, day):
    folder = root / FOLDER
    if folder.resolve() != folder:
        raise ValueError('할 일 폴더는 Vault 안의 일반 폴더여야 합니다.')
    path = folder / f'{day.isoformat()}.md'
    if path.resolve() != path:
        raise ValueError('할 일 파일은 Vault 안의 일반 파일이어야 합니다.')
    return path


def read_lines(path):
    try:
        with path.open(encoding='utf-8-sig', newline='') as file:
            return file.readlines()
    except FileNotFoundError:
        return []


def tasks_for(path):
    return [(index, match[1] != ' ', match[2])
            for index, line in enumerate(read_lines(path))
            if (match := CHECKBOX.fullmatch(line))]


def write_lines(path, lines):
    path.parent.mkdir(exist_ok=True)
    with NamedTemporaryFile(mode='w', encoding='utf-8', newline='', dir=path.parent,
                            suffix='.tmp', delete=False) as file:
        temp = file.name
        try:
            file.writelines(lines)
            file.close()
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)


def add_task(path, day, text):
    lines = read_lines(path)
    if not lines:
        lines = ['---\n','type: daily-todo\n',f'date: {day.isoformat()}\n','---\n',
                 f'\n# {day.isoformat()} 할 일\n','\n']
    elif not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    lines.append(f'- [ ] {text}\n')
    write_lines(path,lines)


def toggle_task(path, task):
    index,done,text = task
    lines = read_lines(path)
    match = CHECKBOX.fullmatch(lines[index]) if index<len(lines) else None
    if not match or (match[1]!=' ',match[2]) != (done,text):
        raise ValueError('Obsidian에서 변경된 할 일을 다시 선택해 주세요.')
    lines[index] = f"- [{' ' if done else 'x'}] {text}{match[3] or ''}"
    write_lines(path,lines)
