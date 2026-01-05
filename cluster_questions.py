import re
import os

def clean_file(filepath):
    """
    Reads the file and removes page headers/footers to create a continuous stream of text.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern for the page break section
    # Expecting:
    # ========================================
    # PAGE <number>
    # ========================================
    # <date/time>
    # <url>
    # <url>
    # <page X/Y>

    # We will build a regex to identify and remove these blocks.
    # The block seems sufficiently characterized by the ====== lines and PAGE markers.

    # Let's try to remove lines that match specific patterns
    lines = content.splitlines()
    cleaned_lines = []

    skip_mode = False

    # Simple state machine or regex approach.
    # Given the complexity of the header variability, regex replacement on the full string might be safer if the pattern is consistent.
    # However, let's look at the structure from view_file again.
    # Lines 3-10 ish are garbage.
    # Patterns to ignore:
    # ^={20,}$
    # ^PAGE \d+$
    # ^\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2} [AP]M$  (Date)
    # ^https?://.*$
    # ^\d+/\d+$ (Page number)

    # Actually, looking at the file, the text "Q.No:" is a very strong delimiter for the start of a question.
    # The content *between* questions might be broken by page headers.
    # If we just remove the specific header lines, we rejoin the text.

    regex_patterns = [
        r'^={10,}$',                 # Divider lines
        r'^PAGE \s*\d+$',            # PAGE 1
        r'^\d{1,2}/\d{1,2}/\d{2}.*?$', # Date lines like 4/16/23...
        r'^https?://.*$',            # URLs
        r'^\d+/\d+$',                # Page numbers like 1/89
        r'^MPESB 2023$',
        r'^Group-2.*$',
        r'^equivalent direct and backlog.*$',
        r'^2022-Reports$',
        r'^View\s+.*$',              # View items
        r'^Moderator loggedin.*$',
        r'^Logout ]\s*$',
        r'^Print$',
        r'^Testdate$',
        r'^TestSlot$',
        r'^Shift \d+$',
        r'^Submit$',
        r'^\s*$'                     # Empty lines (we can clean these up later, but keep for now to avoid merging words)
    ]

    combined_regex = re.compile('|'.join(regex_patterns))

    clean_buffer = []
    for line in lines:
        if combined_regex.match(line.strip()):
            continue
        # Also, specific date matches can be tricky if not at start.
        if "13 Feb 2023" in line: # Specific date in text
             continue
        clean_buffer.append(line)

    return "\n".join(clean_buffer)

def parse_questions(text):
    """
    Splits the cleaned text into individual question blocks.
    """
    # Questions start with "Q.No: <number>"
    # We can split by this pattern, but keep the delimiter.
    # Using re.split with capturing group.

    # Pattern: \nQ.No:\s*\d+\n
    # Note: In the file it looks like "Q.No: 1"

    # Regex to find start of questions.
    pattern = re.compile(r'(Q\.No:\s*\d+)')
    parts = pattern.split(text)

    # parts[0] is preamble (if any)
    # parts[1] is "Q.No: 1"
    # parts[2] is body of Q1
    # parts[3] is "Q.No: 2"
    # parts[4] is body of Q2

    questions = []

    if len(parts) < 2:
        return []

    # Start from index 1 safely
    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i+1] if i+1 < len(parts) else ""
        questions.append(header + body)

    return questions

def extract_subject(question_text):
    """
    Finds 'Subject : <Subject Name>' in the question text.
    """
    match = re.search(r'Subject\s*:\s*(.*)', question_text)
    if match:
        return match.group(1).strip()
    return "Unknown"

def main():
    input_file = "Swachhta_2022_QB.txt"
    output_dir = "clustered_output"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Reading {input_file}...")
    cleaned_text = clean_file(input_file)

    print("Parsing questions...")
    questions = parse_questions(cleaned_text)
    print(f"Found {len(questions)} questions.")

    # Group by subject
    subjects = {}
    for q in questions:
        subj = extract_subject(q)
        if subj not in subjects:
            subjects[subj] = []
        subjects[subj].append(q)

    # Write to files
    for subj, q_list in subjects.items():
        safe_subj_name = re.sub(r'[^\w\s-]', '', subj).strip().replace(' ', '_')
        if not safe_subj_name:
            safe_subj_name = "Unknown_Subject"

        # Chunking
        chunk_size = 50
        for i in range(0, len(q_list), chunk_size):
            chunk = q_list[i:i+chunk_size]
            part_num = (i // chunk_size) + 1
            filename = f"{output_dir}/{safe_subj_name}_Part{part_num}.txt"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Subject: {subj}\n")
                f.write(f"Questions: {len(chunk)}\n")
                f.write("="*40 + "\n\n")
                for q in chunk:
                    f.write(q)
                    f.write("\n" + "-"*40 + "\n")

            print(f"Wrote {filename} ({len(chunk)} questions)")

if __name__ == "__main__":
    main()
