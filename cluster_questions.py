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
        # r'^PAGE \s*\d+$',          # KEEP PAGE NUMBERS!
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

    current_page = 0
    clean_buffer = []

    for line in lines:
        # Detect Page
        page_match = re.search(r'^PAGE \s*(\d+)$', line)
        if page_match:
            current_page = page_match.group(1)
            # Insert a marker we can easily find later.
            # We insert it into the buffer so it appears in the flow.
            # But wait, parse_questions splits by "Q.No".
            # If we just put it in the text, it will be inside the *previous* question's body or the current one.
            # Let's insert it as a special tag.
            clean_buffer.append(f"<<<PAGE:{current_page}>>>")
            continue

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
    current_page_num = "Unknown"

    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i+1] if i+1 < len(parts) else ""

        full_text = header + body

        # Look for PAGE markers in this block OR use the last seen one.
        # Actually, the parsing split removes the text *between* Q.No blocks?
        # No, parts[i+1] is the text between "Q.No: 1" and "Q.No: 2".
        # So it contains the body of Q1.

        # If there's a PAGE marker in 'full_text', it means the page changed *during* or *after* the previous valid text?
        # A simpler way: Find all markers in the body. The *last* marker seen applies to subsequent content?
        # Or, usually, Q.No starts on a page.

        # Let's just grep for the marker in the body.
        # Ideally, we track the page number in the stream.
        # But `re.split` approach makes stream tracking hard.

        # Hack: The marker `<<<PAGE:X>>>` will be present in the `body`.
        # If present, update `current_page_num`.
        # We assign the *last seen* page number to the *current* question?
        # No, if Q1 body contains PAGE 2, it probably means Q1 ended on Page 1, then Page 2 started, then Q2 started.
        # Wait, the body of Q1 goes until Q2 starts.
        # So if PAGE 2 marker is in Q1 body, it likely appeared *after* Q1's options?
        # Usually headers appear at top of page.
        # So: Q1 ... options ... Correct Ans ... PAGE 2 ... Q2.
        # Thus, when we process Q1, we might see PAGE 2 at the end.

        # Let's check for markers.
        found_pages = re.findall(r'<<<PAGE:(\d+)>>>', full_text)
        if found_pages:
            # If we found pages, the question *might* straddle pages.
            # But usually we just want to know "on which page does this question start/exist".
            # Let's capture the *first* page found in the preceding block?
            # Actually, `parts[0]` (preamble) might have the first page.
            pass

        # Refined Logic:
        # The page for Q(i) is likely the page active when "Q.No: i" was encountered.
        # "Q.No: i" is `header`.
        # The text *before* `header` is `parts[i-1]` (which is the body of the previous question).

        # Let's look at `parts[i-1]` to find the latest page marker.
        prev_block = parts[i-1] if i > 0 else parts[0]
        # Find all page markers in previous block
        markers = re.findall(r'<<<PAGE:(\d+)>>>', prev_block)
        if markers:
            current_page_num = markers[-1]

        # Append meta to question text so generator can find it
        questions.append(f"Page: {current_page_num}\n" + full_text)

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
