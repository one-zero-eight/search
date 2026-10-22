from catix.wiki.graph import course_title_of, norm, prerequisite_items


def test_title_is_taken_from_a_code_line():
    assert course_title_of("CSE201 — Mathematical Analysis I: derivatives") == "Mathematical Analysis I"
    assert course_title_of("CSE112: Software Systems Analysis and Design") == "Software Systems Analysis and Design"
    assert course_title_of("Basic programming skills") is None


def test_norm_ignores_case_spaces_and_url_escapes():
    assert norm("BSc%3A_Game_Theory") == norm("bsc: game theory")


def test_empty_prerequisites_are_dropped():
    body = "#### Prerequisite subjects\n- N/A\n- CSE101\n\n#### Prerequisite topics\n- Python\n"
    assert prerequisite_items(body) == ["CSE101"]
