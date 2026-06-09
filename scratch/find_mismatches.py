import os

def find_mismatches(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r') as f:
        content = f.read()

    # Simple state machine to strip comments and strings
    clean = []
    i = 0
    n = len(content)
    line_nums = [] # map index in clean to line number in original
    current_line = 1
    
    in_string = None # '"', "'", "`"
    in_single_comment = False
    in_multi_comment = False
    escaped = False

    while i < n:
        char = content[i]
        
        # Track line numbers before any state changes
        if char == '\n':
            current_line += 1

        if in_single_comment:
            if char == '\n':
                in_single_comment = False
                clean.append(char)
                line_nums.append(current_line)
        elif in_multi_comment:
            if char == '/' and content[i-1] == '*':
                in_multi_comment = False
        elif in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == in_string:
                in_string = None
        else:
            # Check for comment start
            if char == '/' and i + 1 < n and content[i+1] == '/':
                in_single_comment = True
                i += 1
            elif char == '/' and i + 1 < n and content[i+1] == '*':
                in_multi_comment = True
                i += 1
            # Check for string start
            elif char in ['"', "'", "`"]:
                in_string = char
            # Keep braces and tracking
            elif char in ['{', '}', '(', ')', '[', ']']:
                clean.append(char)
                line_nums.append(current_line)
        i += 1

    # Now parse brackets
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    total_clean = len(clean)
    mismatches = 0
    
    for idx, char in enumerate(clean):
        if char in ['(', '{', '[']:
            stack.append((char, line_nums[idx]))
        elif char in [')', '}', ']']:
            expected = pairs[char]
            if not stack:
                print(f"Mismatched closing bracket '{char}' on line {line_nums[idx]}")
                mismatches += 1
                continue
            open_char, open_line = stack.pop()
            if open_char != expected:
                print(f"Mismatched bracket on line {line_nums[idx]}: found '{char}' matching '{open_char}' from line {open_line}")
                mismatches += 1

    print("\n--- Parsing Complete ---")
    print(f"Total mismatches found: {mismatches}")
    if stack:
        print(f"Unmatched opening brackets remaining: {len(stack)}")
        for char, line in stack:
            print(f"Unmatched opening bracket '{char}' from line {line}")
    else:
        print("All brackets are balanced at the end of the file!")

if __name__ == '__main__':
    find_mismatches('/Users/rashed/PyCharmMiscProject/nutriquant/static/js/main.js')
