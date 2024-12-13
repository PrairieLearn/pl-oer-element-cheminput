import base64
import hashlib
import os
from enum import Enum
import re
import chevron
import lxml.html
import prairielearn as pl


QUILL_THEME_DEFAULT = "snow"
PLACEHOLDER_DEFAULT = "Your answer here"
ALLOW_BLANK_DEFAULT = False
SOURCE_FILE_NAME_DEFAULT = None
DIRECTORY_DEFAULT = "."
MARKDOWN_SHORTCUTS_DEFAULT = False
SHOW_HELP_TEXT_DEFAULT = True
PREFILL_DEFAULT = None
SIZE_DEFAULT = 100
SHOW_SCORE_DEFAULT = True
WEIGHT_DEFAULT = 1
GRADE_STATES_DEFAULT = False
INCLUDE_FEEDBACK_DEFAULT = True


def get_answer_name(file_name):
    return "_rich_text_editor_{0}".format(
        hashlib.sha1(file_name.encode("utf-8")).hexdigest()
    )


def element_inner_html(element):
    return (element.text or "") + "".join(
        [str(lxml.html.tostring(c), "utf-8") for c in element.iterchildren()]
    )


def prepare(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    required_attribs = ["question-name"]
    optional_attribs = [
        "quill-theme",
        "source-file-name",
        "directory",
        "placeholder",
        "allow-blank",
        "markdown-shortcuts",
        "show-help-text",
        "prefill",
        "size",
        "show-score",
        "weight",
        "grade-states",
        "include-feedback"
    ]
    pl.check_attribs(element, required_attribs, optional_attribs)
    source_file_name = pl.get_string_attrib(
        element, "source-file-name", SOURCE_FILE_NAME_DEFAULT
    )
    element_text = element_inner_html(element)

    file_name = pl.get_string_attrib(element, "question-name")
    if "_required_file_names" not in data["params"]:
        data["params"]["_required_file_names"] = []
    elif file_name in data["params"]["_required_file_names"]:
        raise Exception("There is more than one file editor with the same file name.")
    data["params"]["_required_file_names"].append(file_name)

    if source_file_name is not None:
        if element_text and not str(element_text).isspace():
            raise Exception(
                'Existing text cannot be added inside rich-text element when "source-file-name" attribute is used.'
                + element_text
            )


def render(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    file_name = pl.get_string_attrib(element, "question-name", "")
    answer_name = get_answer_name(file_name)
    quill_theme = pl.get_string_attrib(element, "quill-theme", QUILL_THEME_DEFAULT)
    placeholder = pl.get_string_attrib(element, "placeholder", PLACEHOLDER_DEFAULT)
    show_help_text = pl.get_boolean_attrib(element, "show-help-text", SHOW_HELP_TEXT_DEFAULT)
    prefill = pl.get_string_attrib(element, "prefill", PREFILL_DEFAULT)
    question_name = pl.get_string_attrib(element, "question-name", "")
    show_score = pl.get_boolean_attrib(element, "show-score", SHOW_SCORE_DEFAULT)
    score = data["partial_scores"].get(question_name, {}).get("score")
    try:
        size = pl.get_integer_attrib(element, "size", SIZE_DEFAULT)
        size = str(max(min(int(size), 100), 0))
    except (ValueError, TypeError):
        size = SIZE_DEFAULT
    
    if show_help_text == False:
        show_help_text = None
    elif show_help_text == True:
        show_help_text = True

    uuid = pl.get_uuid()
    source_file_name = pl.get_string_attrib(
        element, "source-file-name", SOURCE_FILE_NAME_DEFAULT
    )
    directory = pl.get_string_attrib(element, "directory", DIRECTORY_DEFAULT)
    markdown_shortcuts = pl.get_boolean_attrib(
        element, "markdown-shortcuts", MARKDOWN_SHORTCUTS_DEFAULT
    )

    element_text = element_inner_html(element)
    help_text = "The leftmost button is the subscript button, the middle button is the superscript button, and the rightmost button is the clear formatting button. Any value can be inputted in place of x or 2 for the superscript and subscript values. You can use -> (dash and greater than sign) to indicate an arrow. States of matter can be indicates using (l), (s), and (g)."
    if data["panel"] == "question" or data["panel"] == "submission":
        html_params = {
            "name": answer_name,
            "file_name": file_name,
            "quill_theme": quill_theme,
            "placeholder": placeholder,
            "editor_uuid": uuid,
            "question": data["panel"] == "question",
            "submission": data["panel"] == "submission",
            "read_only": (
                "true"
                if (data["panel"] == "submission" or not data["editable"])
                else "false"
            ),
            "format": "html",
            "markdown_shortcuts": "true" if markdown_shortcuts else "false",
            "show_help_text": show_help_text,
            "help_text": help_text,
            "prefill":prefill,
            "show_score":show_score
        }

        if score is not None:
            html_params["feedback"] = data["partial_scores"].get(question_name, {}).get("feedback")
        if show_score and score is not None:
            score_type, score_value = pl.determine_score_params(score)
            html_params[score_type] = score_value

        if size != SIZE_DEFAULT:
            html_params["size"] = size

        if source_file_name is not None:
            if directory == "serverFilesCourse":
                directory = data["options"]["server_files_course_path"]
            elif directory == "clientFilesCourse":
                directory = data["options"]["client_files_course_path"]
            else:
                directory = os.path.join(data["options"]["question_path"], directory)
            file_path = os.path.join(directory, source_file_name)
            text_display = convert_notation_to_html(format_latex(open(file_path).read()))
        else:
            if element_text is not None:
                text_display = convert_notation_to_html(format_latex(str(element_text)))
            else:
                text_display = ""
        if prefill is not None:
            text_display = convert_notation_to_html(format_latex(prefill))
        
        html_params["original_file_contents"] = base64.b64encode(
            text_display.encode("UTF-8").strip()
        ).decode()

        submitted_files = data["submitted_answers"].get("_files", [])
        submitted_file_contents = [
            f.get("contents", None)
            for f in submitted_files
            if f.get("name", None) == file_name
        ]
        if submitted_file_contents:
            html_params["current_file_contents"] = submitted_file_contents[0]
        else:
            html_params["current_file_contents"] = html_params["original_file_contents"]
        html_params["question"] = data["panel"] == "question"
        with open("pl-chem-input.mustache", "r", encoding="utf-8") as f:
            rendered_html = chevron.render(f, html_params).strip()

    elif data["panel"] == "answer":
        html_params = {
            "name": answer_name,
            "file_name": file_name,
            "quill_theme": quill_theme,
            "editor_uuid": uuid,
            "question": data["panel"] == "question",
            "submission": data["panel"] == "submission",
            "answer": data["panel"] == "answer",
            "read_only": (
                "true"
                if (data["panel"] == "submission" or data["panel"] == "answer" or not data["editable"])
                else "false"
            ),
            "format": "html",
            "markdown_shortcuts": "true" if markdown_shortcuts else "false",
            "show_help_text": show_help_text,
            "help_text": help_text,
            "prefill":prefill,
        }
        raw_answer = data["correct_answers"][question_name]
        raw_answer_format = format_latex(convert_arrow(convert_notation_to_html(raw_answer)))
        raw_answer_html = latex_to_html(raw_answer_format)
        html_params["answer_contents"] = base64.b64encode(
            raw_answer_html.encode("UTF-8").strip()
        ).decode()
        with open("pl-chem-input.mustache", "r", encoding="utf-8") as f:
            rendered_html = chevron.render(f, html_params).strip()
    else:
        raise Exception("Invalid panel type: " + data["panel"])

    return rendered_html


def parse(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    allow_blank = pl.get_boolean_attrib(element, "allow-blank", ALLOW_BLANK_DEFAULT)
    file_name = pl.get_string_attrib(element, "question-name", "")
    answer_name = get_answer_name(file_name)

    file_contents = data["submitted_answers"].get(answer_name, None)
    if not file_contents and not allow_blank:
        pl.add_files_format_error(data, f"No submitted answer for {file_name}")
        return

    file_contents_decode = base64.b64decode(file_contents).decode("utf-8").strip() if file_contents else ""
    if not file_contents_decode.startswith("<"):
        file_contents_decode = f"<p>{file_contents_decode}</p>"
    try:
        parsed_content = lxml.html.fragment_fromstring(file_contents_decode)
        for element in parsed_content.iter():
            if element.text:
                element.text = element.text.strip()
            if element.tail:
                element.tail = element.tail.strip()
        file_contents_cleaned = lxml.html.tostring(parsed_content, encoding="unicode")
        file_contents = base64.b64encode(
            file_contents_cleaned.encode("UTF-8").strip()
        ).decode()
    except lxml.etree.XMLSyntaxError:
        pl.add_files_format_error(data, f"Invalid HTML structure in {file_name}")
        return

    del data["submitted_answers"][answer_name]
    pl.add_submitted_file(data, file_name, file_contents)

def grade(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    question_name = pl.get_string_attrib(element, "question-name", "")
    weight = pl.get_integer_attrib(element, "weight", WEIGHT_DEFAULT)
    grade_states = show_score = pl.get_boolean_attrib(element, "grade-states", GRADE_STATES_DEFAULT)
    include_feedback = pl.get_boolean_attrib(element, "include-feedback", INCLUDE_FEEDBACK_DEFAULT)
    file_contents_encode = None
    for file in data["submitted_answers"]["_files"]:
        if file["name"] == question_name:
            file_contents_encode = file["contents"]
            break
    student_answer = html_to_latex(base64.b64decode(file_contents_encode))

    reactants, products, states_of_matter, coefficients = parse_answer(student_answer, "-&gt;")

    actual_answer = pl.from_json(data["correct_answers"].get(question_name, None))
    if actual_answer != None:
        actual_answer = format_latex(actual_answer)
    reactants2, products2, states_of_matter2, coefficients2 = parse_answer(actual_answer, "/rarrow")
    reactants_correct = True
    products_correct = True
    coefficients_correct = True
    states_of_matter_correct = True
    if sorted(reactants) != sorted(reactants2):
        reactants_correct = False
    if sorted(products) != sorted(products2):
        products_correct = False
    if grade_states and states_of_matter != states_of_matter2:
        states_of_matter_correct = False
    if coefficients != coefficients2:
        coefficients_correct = False
    if reactants_correct and products_correct and states_of_matter_correct and coefficients_correct:
        data["partial_scores"][question_name]={"score": 1, "weight":weight}
    else:
        feedback_string = "There are issues with your: "
        if not reactants_correct:
            feedback_string += "reactants"
        if not products_correct:
            if not reactants_correct:
                feedback_string += " and "
            feedback_string += "products"
        if not states_of_matter_correct:
            if not reactants_correct or not products_correct:
                feedback_string += " and "
            feedback_string += "states of matter"
        if not coefficients_correct:
           if not reactants_correct or not products_correct or not states_of_matter_correct:
                feedback_string += " and "
           feedback_string += "\ncoefficients"
        
        if not include_feedback:
            feedback_string = "Feedback has been disabled for this question."
        data["partial_scores"][question_name]={"score": 0, "feedback":feedback_string, "weight":weight}
       



def html_to_latex(html_text):
    if isinstance(html_text, bytes):
        html_text = html_text.decode("utf-8")
    latex_text = re.sub(r"<p>(.*?)</p>", r"\1\n\n", html_text)
    latex_text = re.sub(r"<sup[^>]*>(.*?)</sup>", r"^{\1}", latex_text)
    latex_text = re.sub(r"<sub[^>]*>(.*?)</sub>", r"_{\1}", latex_text)
    latex_text = re.sub(r"<.*?>", "", latex_text)

    return latex_text


def latex_to_html(latex_text):
    html_text = re.sub(r"\n\n+", r"</p><p>", latex_text)
    html_text = f"<p>{html_text}</p>"
    html_text = re.sub(r"\^\{(.*?)\}", r"<sup>\1</sup>", html_text)
    html_text = re.sub(r"_\{(.*?)\}", r"<sub>\1</sub>", html_text)
    html_text = re.sub(r"<p></p>", "", html_text)

    return html_text


def format_latex(latex_text):
    latex_text = re.sub(r'_(\w)', r'_{\1}', latex_text)
    latex_text = re.sub(r'\^(\w)', r'^{\1}', latex_text)
    return latex_text


def parse_answer(equation, arrow):
    if arrow in equation:
        left, right = equation.split(arrow)
    else:
        left, right = equation, ""

    left = left.split('+')
    right = right.split('+') if right else []

    reactants = []
    products = []
    states_of_matter = {}
    coefficients = {}

    for elem in left:
        elem = elem.strip()
        state = None
        state_index = len(elem)
        coeff = ""
        for i in elem:
            if not i.isalpha():
                coeff += i
            else:
                elem_index = elem.index(i)
                elem = elem[elem_index:]
                break

        if "(" in elem and ")" in elem:
            state_index = elem.index("(")
            state = elem[state_index:]
        elem = elem[:state_index]

        reactants.append(elem)
        if state:
            states_of_matter[elem] = state
        if coeff != "":
            coefficients[elem] = coeff

    # Process the right (products)
    for elem in right:
        elem = elem.strip()
        state = None
        state_index = len(elem)
        coeff = ""
        for i in elem:
            if not i.isalpha():
                coeff += i
            else:
                elem_index = elem.index(i)
                elem = elem[elem_index:]
                break

        if "(" in elem and ")" in elem:
            state_index = elem.index("(")
            state = elem[state_index:]
        elem = elem[:state_index]

        products.append(elem)
        if state:
            states_of_matter[elem] = state
        if coeff != "":
            coefficients[elem] = coeff

    return reactants, products, states_of_matter, coefficients

def convert_notation_to_html(text):
    text = re.sub(r'_(\{[^{}]*\})', lambda m: '<sub>{}</sub>'.format(m.group(1)[1:-1]), text)
    text = re.sub(r'\^(\{[^{}]*\})', lambda m: '<sup>{}</sup>'.format(m.group(1)[1:-1]), text)
    return text

def convert_arrow(text):
    return text.replace('/rarrow', '-&gt;')

