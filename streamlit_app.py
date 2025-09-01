import streamlit as st
import pandas as pd
import json
import re

# Title of the app
st.title("Test Case Quality Scoring")

# File uploader for CSV
uploaded_file = st.file_uploader("Upload Test Cases CSV", type="csv")
if uploaded_file is not None:
    try:
        # Read CSV into DataFrame (assuming semicolon delimiter as in provided examples)
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
    else:
        if df.empty:
            st.error("The uploaded CSV is empty.")
        else:
            # Define helper function to analyze test cases
            def analyze_test_cases(dataframe):
                results = []  # to store detailed results for each test case
                category_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
                # Define environment keywords to look for in labels (lowercased for comparison)
                env_keywords = ["android", "ios", "mobil", "mobile", "web", "backend"]
                for _, row in dataframe.iterrows():
                    # Fetch fields from the row with safe defaults
                    title = str(row.get('Summary', '') or '')
                    priority = str(row.get('Priority', '') or '')
                    # Precondition fields
                    pre1 = str(row.get('Custom field (Pre-Conditions association with a Test)', '') or '')
                    pre2 = str(row.get('Custom field (Tests association with a Pre-Condition)', '') or '')
                    # Manual Test Steps field (which contains JSON)
                    steps_field = row.get('Custom field (Manual Test Steps)', None)
                    steps = []
                    if isinstance(steps_field, str) and steps_field.strip():
                        try:
                            steps = json.loads(steps_field)
                        except Exception:
                            # Attempt to correct common quoting issues if JSON fails to load
                            fixed = steps_field.strip()
                            if fixed.startswith('"') and fixed.endswith('"'):
                                # Remove outer quotes and replace doubled quotes with single
                                try:
                                    fixed_json = fixed[1:-1].replace('""', '"')
                                    steps = json.loads(fixed_json)
                                except Exception:
                                    steps = []
                            else:
                                steps = []
                    else:
                        steps = []
                    # Flags and counters
                    has_expected = False
                    expected_texts = []
                    has_data_field = False
                    # Check each step for expected result text and data usage
                    for step in steps:
                        fields = step.get('fields', {})
                        # Check expected result presence
                        exp = fields.get('Expected Result')
                        if isinstance(exp, str) and exp.strip():
                            has_expected = True
                            expected_texts.append(exp.strip())
                        # Check data field presence
                        data_field = fields.get('Data')
                        if isinstance(data_field, str) and data_field.strip():
                            has_data_field = True
                    # Check if any precondition field is filled
                    has_pre_field = bool(pre1.strip() or pre2.strip())
                    # Determine if test content indicates need for data or precondition
                    needs_data = False
                    needs_pre = False
                    for step in steps:
                        fields = step.get('fields', {})
                        action = fields.get('Action', '')
                        if isinstance(action, str):
                            text = action.lower()
                            # Keywords indicating input data usage in steps
                            if re.search(r"\b(?:giril|güncellenir|seçilir|yazılır|yapılır|eklenir)", text):
                                needs_data = True
                            # Numeric values (e.g. IDs, phone numbers) that suggest test data
                            if re.search(r"\d{5,}", text):
                                needs_data = True
                            # Placeholder patterns (e.g. "XX", "XXXX") indicating test data
                            if re.search(r"\bx{2,}\b", text):
                                needs_data = True
                            # Keywords indicating a login/precondition scenario in steps
                            if "giriş yap" in text or "login" in text:
                                needs_pre = True
                            # If mentions "already" or "beforehand" in context of login, mark needs_pre
                            if ("önceden" in text or "zaten" in text) and ("giriş" in text or "login" in text):
                                needs_pre = True
                    # If no steps provided, check title for login context
                    if not steps:
                        title_low = title.lower()
                        if "giriş yap" in title_low or "login" in title_low:
                            needs_pre = True
                    # Scoring for each aspect
                    score = 0
                    # Title (Summary) present
                    if title.strip():
                        score += 5
                    # Priority present
                    if priority.strip():
                        score += 5
                    # Steps present
                    if steps:
                        score += 20
                    # Expected result quality
                    expected_score = 0
                    if has_expected:
                        expected_score = 30
                        # Check for past tense usage in expected results and apply penalty
                        past_issues_count = 0
                        for exp_text in expected_texts:
                            exp_low = exp_text.lower()
                            # Turkish past tense indicators (-dı, -di, -du, -dü and participles -dığı, -diği, -duğu, -düğü, and -mıştır, -miştir)
                            turk_past_pattern = r"\b(dı|di|du|dü|dığı|diği|duğu|düğü|mıştır|miştir)\b"
                            # English past tense indicators (was, were, has been, had been)
                            eng_past_pattern = r"\bwas\b|\bwere\b|\bhas been\b|\bhad been\b"
                            # Count occurrences of these patterns
                            past_issues_turk = re.findall(turk_past_pattern, exp_low)
                            past_issues_eng = re.findall(eng_past_pattern, exp_low)
                            past_issues_count += len(past_issues_turk) + len(past_issues_eng)
                        if past_issues_count > 0:
                            # Deduct 1 point per issue, up to 5 points max
                            deduction = past_issues_count if past_issues_count <= 5 else 5
                            expected_score = max(0, expected_score - deduction)
                    else:
                        expected_score = 0
                    score += expected_score
                    # Data field scoring
                    if needs_data:
                        score += 15 if has_data_field else 0
                    else:
                        score += 15  # Not needed or provided even if not needed
                    # Precondition field scoring
                    if needs_pre:
                        score += 15 if has_pre_field else 0
                    else:
                        score += 15
                    # Client (environment) info scoring via labels
                    env_score = 0
                    env_found = False
                    for label_col in ['Labels', 'Labels.1', 'Labels.2', 'Labels.3', 'Labels.4']:
                        lab_value = row.get(label_col)
                        if isinstance(lab_value, str):
                            lab_low = lab_value.lower()
                            if any(env_key in lab_low for env_key in env_keywords):
                                env_found = True
                                break
                    if env_found:
                        env_score = 10
                    # If no environment info found in labels, env_score remains 0 (penalty for missing client info)
                    score += env_score
                    # Determine category based on rules and score thresholds
                    category = None
                    # Override rule: If both Data and Precondition fields are filled
                    if has_data_field and has_pre_field:
                        category = "D"
                    # Override rule: If both Data and Precondition were needed but neither provided
                    elif needs_data and needs_pre and not has_data_field and not has_pre_field:
                        category = "D"
                    # Override rule: If no steps at all, consider it an incomplete test case
                    elif not steps:
                        category = "D"
                    # Assign category by score if no override applied
                    if category is None:
                        if score >= 90:
                            category = "A"
                        elif score >= 75:
                            category = "B"
                        elif score >= 50:
                            category = "C"
                        else:
                            category = "D"
                    # Record the category count
                    category_counts[category] += 1
                    # Append detailed result (Issue key, truncated title, score, category)
                    issue_key = str(row.get('Issue key', '') or '')
                    short_title = title
                    if len(short_title) > 100:
                        short_title = short_title[:100] + "..."
                    results.append({
                        "Issue Key": issue_key,
                        "Title": short_title,
                        "Priority": priority,
                        "Score": score,
                        "Category": category
                    })
                return results, category_counts

            # Analyze the uploaded test cases DataFrame
            results_list, counts = analyze_test_cases(df)

            # Display overall distribution of categories
            total_tests = len(df)
            st.subheader("Overall Category Distribution")
            st.write(f"Total Test Cases: **{total_tests}**")
            dist_text = (f"**A**: {counts['A']} &nbsp; &nbsp; "
                         f"**B**: {counts['B']} &nbsp; &nbsp; "
                         f"**C**: {counts['C']} &nbsp; &nbsp; "
                         f"**D**: {counts['D']}")
            st.write(dist_text, unsafe_allow_html=True)

            # Prepare DataFrame for sample output
            results_df = pd.DataFrame(results_list)
            # If more than 100 test cases, sample 100 for display
            if len(results_df) > 100:
                results_df = results_df.sample(100, random_state=1).reset_index(drop=True)
                st.subheader("Sample Test Cases (100 sampled)")
            else:
                st.subheader("Test Case Results")
            # Display the table of test cases with scores and categories
            st.dataframe(results_df[["Issue Key", "Title", "Priority", "Score", "Category"]])
