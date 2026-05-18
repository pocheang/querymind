"""Fix Chinese quotes in Python files."""

def fix_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()

    # Replace Chinese quotes (UTF-8 bytes) with ASCII quotes
    content = content.replace(b'\xe2\x80\x9c', b'"')  # " -> "
    content = content.replace(b'\xe2\x80\x9d', b'"')  # " -> "
    content = content.replace(b'\xe2\x80\x98', b"'")  # ' -> '
    content = content.replace(b'\xe2\x80\x99', b"'")  # ' -> '

    with open(filepath, 'wb') as f:
        f.write(content)

    print(f'Fixed: {filepath}')

if __name__ == '__main__':
    fix_file('app/services/prompt_checker.py')
    print('All Chinese quotes fixed!')
