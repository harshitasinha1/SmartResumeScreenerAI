import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import PyPDF2
import docx2txt
import spacy
from sentence_transformers import SentenceTransformer, util

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ============================================================
# 1. LOAD NLP MODELS
# ============================================================

print("Step 1/3: Loading Sentence Transformer (BERT) model... Please wait.")

try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ BERT Model Loaded successfully.")
except Exception as e:
    print(f"❌ Error loading Transformer: {e}")
    model = None


print("Step 2/3: Loading SpaCy English model...")

try:
    nlp = spacy.load("en_core_web_sm")
    print("✅ SpaCy Loaded successfully.")
except Exception as e:
    print(f"❌ Error loading SpaCy: {e}")
    nlp = None


# ============================================================
# 2. LINGUISTIC CUES
# ============================================================
#
# IMPORTANT:
# These are NOT a list of technologies.
#
# They only tell NLP:
# "This sentence/section is probably talking about skills."
#
# Therefore a completely new technology can still be extracted.
# ============================================================

TECHNICAL_CONTEXTS = [
    "experience in",
    "experience with",
    "experienced in",
    "experienced with",
    "proficient in",
    "proficient with",
    "knowledge of",
    "familiar with",
    "expertise in",
    "worked with",
    "working with",
    "built with",
    "built using",
    "developed with",
    "developed using",
    "using",
    "used",
    "implemented using",
    "skills in",
    "skills include",
    "technologies include",
    "technology stack",
    "tech stack",
    "hands-on experience",
    "hands on experience",
    "developed",
    "implemented",
    "designed",
    "deployed",
]


# These are section/category words, NOT technologies.
SKILL_SECTION_WORDS = [
    "skill",
    "skills",
    "technical skills",
    "technologies",
    "technology",
    "programming",
    "languages",
    "frontend",
    "front end",
    "backend",
    "back end",
    "database",
    "databases",
    "framework",
    "frameworks",
    "libraries",
    "library",
    "tools",
    "tool",
    "machine learning",
    "ml",
    "nlp",
    "ai",
    "devops",
    "cloud",
]


# Words which are normally not useful as a standalone skill.
GENERIC_WORDS = {
    "skill",
    "skills",
    "technical",
    "technology",
    "technologies",
    "experience",
    "experienced",
    "knowledge",
    "expertise",
    "proficient",
    "proficiency",
    "familiar",
    "worked",
    "working",
    "using",
    "used",
    "built",
    "developed",
    "development",
    "implemented",
    "implementation",
    "project",
    "projects",
    "application",
    "applications",
    "software",
    "engineering",
    "engineer",
    "developer",
    "developers",
    "education",
    "certificate",
    "certificates",
    "achievement",
    "achievements",
    "research",
    "internship",
    "course",
    "courses",
    "training",
    "frontend",
    "backend",
    "database",
    "databases",
    "framework",
    "frameworks",
    "library",
    "libraries",
    "tool",
    "tools",
    "resume",
    "profile",
    "objective",
    "summary",
    "candidate",
    "student",
    "school",
    "college",
    "university",
    "system",
    "systems",
    "management",
    "website",
    "web application",
    "web applications",
    "application development",
    "work",
    "experience",
    "responsibility",
    "responsibilities",
    "india",
    "government",
    "national",
    "science",
    "scientist",
}


# ============================================================
# 3. FILE TEXT EXTRACTION
# ============================================================

def extract_text(file):

    filename = file.filename.lower()

    try:

        if filename.endswith(".pdf"):

            pdf_reader = PyPDF2.PdfReader(file)

            pages = []

            for page in pdf_reader.pages:

                page_text = page.extract_text()

                if page_text:
                    pages.append(page_text)

            return "\n".join(pages)


        elif filename.endswith(".docx"):

            return docx2txt.process(file)

    except Exception as e:

        print(f"Error extracting {filename}: {e}")

    return ""


# ============================================================
# 4. NAME EXTRACTION
# ============================================================

def get_name(text):

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    if not lines:
        return None

    for i in range(min(3, len(lines))):

        line = lines[i]

        # Don't consider contact information as a name
        if "@" in line or "|" in line or ":" in line:
            continue

        if nlp:

            doc = nlp(line)

            for ent in doc.ents:

                if ent.label_ == "PERSON":

                    name = ent.text.strip()

                    if 1 <= len(name.split()) <= 3:
                        return name

        # Simple fallback for first line
        if i == 0:

            words = line.split()

            if 1 <= len(words) <= 3:

                if all(
                    word.replace(".", "").isalpha()
                    for word in words
                ):
                    return line

    return None


# ============================================================
# 5. TEXT CLEANING
# ============================================================

def clean_text(text):

    text = text.lower()

    # Remove URLs
    text = re.sub(
        r"https?://\S+",
        " ",
        text
    )

    # Remove emails
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        " ",
        text
    )

    # Remove @mentions
    text = re.sub(
        r"@\S+",
        " ",
        text
    )

    # Remove hashtags
    text = re.sub(
        r"#\S+",
        " ",
        text
    )

    # Remove control characters
    text = re.sub(
        r"[\x00-\x1f\x7f]",
        " ",
        text
    )

    # Normalize whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# 6. NORMALIZE A CANDIDATE
# ============================================================

def normalize_candidate(candidate):

    candidate = candidate.strip()

    # Remove bullets and separators
    candidate = re.sub(
        r"^[•●▪️\-–—:;,/]+",
        "",
        candidate
    )

    candidate = re.sub(
        r"[•●▪️\-–—:;,/]+$",
        "",
        candidate
    )

    candidate = re.sub(
        r"\s+",
        " ",
        candidate
    )

    candidate = candidate.strip().lower()

    # Common linguistic normalization.
    # This is NOT a skill dictionary.
    aliases = {
        "react.js": "react",
        "reactjs": "react",

        "nodejs": "node.js",

        "expressjs": "express.js",

        "nextjs": "next.js",

        "postgres": "postgresql",

        "scikit learn": "scikit-learn",

        "spa cy": "spacy",

        "restful api": "rest api",

        "restful apis": "rest apis",

        "rest api": "rest api",

        "rest apis": "rest apis",

        "cicd": "ci/cd",

        "power bi": "powerbi",

        "machine learning / nlp": "machine learning / nlp",
    }

    return aliases.get(candidate, candidate)


# ============================================================
# 7. BASIC CANDIDATE VALIDATION
# ============================================================

def is_valid_candidate(candidate):

    candidate = normalize_candidate(candidate)

    if not candidate:
        return False

    # Generic words are not skills
    if candidate in GENERIC_WORDS:
        return False

    # Reject phrases built around common action verbs
    # ("designed pages", "developed applications", "built a
    # platform") — these are activity descriptions, not skills,
    # but spaCy's noun_chunks / ORG-PRODUCT NER sometimes still
    # picks them up.
    ACTION_VERB_WORDS = {
        "designed", "developed", "built", "created", "implemented",
        "managed", "led", "handled", "worked", "wrote", "maintained",
        "deployed", "improved", "optimized", "responsible",
    }

    candidate_words = set(candidate.split())

    if candidate_words & ACTION_VERB_WORDS:
        return False

    # Reject leading articles combined with generic nouns
    # ("a job application platform", "an innovative e-commerce
    # platform") — these are project descriptions, not skills.
    if candidate.split()[0] in {"a", "an", "the"}:
        return False

    # URLs / emails
    if "http://" in candidate:
        return False

    if "https://" in candidate:
        return False

    if "linkedin.com" in candidate:
        return False

    if "github.com" in candidate:
        return False

    if "@" in candidate:
        return False

    # Percentages / dates / pure numbers
    if re.fullmatch(r"[\d.%/\-]+", candidate):
        return False

    # Too long = probably a sentence, not a skill
    if len(candidate.split()) > 6:
        return False

    # One-character candidates
    #
    # C is allowed.
    # Other random one-character words are rejected.
    if len(candidate) == 1:

        if candidate == "c":
            return True

        return False

    return True


# ============================================================
# 8. SPECIAL TECHNICAL TOKEN EXTRACTION
# ============================================================
#
# This is NOT hardcoding a skill list.
#
# It simply handles technologies containing symbols that normal
# NLP tokenization can split:
#
# C++
# C#
# .NET
# Node.js
# etc.
# ============================================================

def extract_symbol_technologies(text):

    found = set()

    # C++ must be detected as C++,
    # and MUST NOT subsequently become C.
    if re.search(
        r"(?<![\w+#])c\+\+(?!\w)",
        text,
        flags=re.IGNORECASE
    ):
        found.add("c++")

    if re.search(
        r"(?<![\w+#])c#(?!\w)",
        text,
        flags=re.IGNORECASE
    ):
        found.add("c#")

    if re.search(
        r"(?<!\w)\.net(?!\w)",
        text,
        flags=re.IGNORECASE
    ):
        found.add(".net")

    return found


# ============================================================
# 9. EXTRACT FROM SKILL SECTIONS
# ============================================================
#
# Example (same-line format):
#
# Technical Skills: C, C++, Java, Python, React.js
#
# Example (multi-line format — very common in real resumes/JDs
# and the previous version of this function completely missed
# this case, which is why matched/missing skills were empty):
#
# Technical Skills
# C, C++, Java, Python, React.js
#
# Skills:
# - Python
# - Django
# - AWS
#
# We don't know beforehand which technologies are there.
#
# We simply identify that this is a SKILL SECTION (either via a
# "Heading: values" line, or a standalone heading line) and then
# keep consuming the following lines as skill-list content until
# we hit a blank line, a full sentence, or what looks like a new
# section heading.
# ============================================================

def _is_skill_heading(heading_text):

    heading_text = heading_text.strip().lower()

    if not heading_text:
        return False

    for keyword in SKILL_SECTION_WORDS:

        if keyword == heading_text or keyword in heading_text:

            # Keep this a "heading", not a full sentence that
            # happens to contain the word (e.g. "worked on tools
            # for the backend team all year").
            if len(heading_text.split()) <= 4:
                return True

    return False


def _looks_like_new_heading(line):

    line = line.strip()

    if not line:
        return True

    # Bulleted lines (e.g. "- AWS", "• Docker") are list items,
    # never new section headings — even if the item itself is a
    # short all-caps acronym like "AWS" or "SQL".
    starts_with_bullet = bool(
        re.match(r"^[•●▪️\-–—*]\s*", line)
    )

    if not starts_with_bullet:

        # ALL CAPS short lines are almost always section headings
        # (e.g. "EXPERIENCE", "EDUCATION") — but require more than
        # one word so a lone acronym like "SQL" isn't mistaken for
        # a heading.
        if (
            line.isupper()
            and 2 <= len(line.split()) <= 5
        ):
            return True

        # "Something:" where "Something" is a short, different
        # heading (not a skill keyword) signals a new section.
        if ":" in line:

            heading_part = line.split(":", 1)[0]

            if (
                len(heading_part.split()) <= 4
                and not _is_skill_heading(heading_part)
            ):
                return True

    return False


def extract_section_candidates(text):

    candidates = set()

    lines = text.splitlines()

    in_skill_section = False
    lines_consumed_in_section = 0

    # Safety cap so that if a resume never uses blank lines to
    # separate sections, we don't accidentally swallow the rest
    # of the document as "skills".
    MAX_CONTINUATION_LINES = 15

    for raw_line in lines:

        line = raw_line.strip()

        # Blank line always ends a skill section.
        if not line:

            in_skill_section = False
            lines_consumed_in_section = 0
            continue

        heading = None
        values = None

        if ":" in line:

            heading, values = line.split(":", 1)

            heading = heading.strip()
            values = values.strip()

        # ------------------------------------------------
        # Case 1: this line itself is a skill-section
        # heading ("Skills:", "Technical Skills", "Frontend:")
        # ------------------------------------------------

        heading_candidate = heading if heading is not None else line

        if _is_skill_heading(heading_candidate):

            in_skill_section = True
            lines_consumed_in_section = 0

            # If there are values on the same line
            # (e.g. "Skills: Python, SQL"), extract them too.
            if values:

                parts = re.split(r"[,;|•]+", values)

                for part in parts:

                    candidate = normalize_candidate(part)

                    if is_valid_candidate(candidate):
                        candidates.add(candidate)

            continue

        # ------------------------------------------------
        # Case 2: we're inside a skill section that started
        # on a previous line — keep consuming list-style
        # content from this line.
        # ------------------------------------------------

        if in_skill_section:

            lines_consumed_in_section += 1

            # A full sentence (ends in ./!/?) or a brand new
            # heading means the skills section has ended.
            if (
                line.endswith(".")
                or line.endswith("!")
                or line.endswith("?")
                or _looks_like_new_heading(line)
                or lines_consumed_in_section > MAX_CONTINUATION_LINES
            ):

                in_skill_section = False
                lines_consumed_in_section = 0
                continue

            # Strip leading bullet markers (-, •, ●, ▪, *, etc.)
            cleaned_line = re.sub(
                r"^[•●▪️\-–—*]+\s*",
                "",
                line
            )

            parts = re.split(
                r"[,;|•]+",
                cleaned_line
            )

            for part in parts:

                candidate = normalize_candidate(part)

                if is_valid_candidate(candidate):

                    candidates.add(candidate)

    return candidates


# ============================================================
# 10. NLP-BASED CANDIDATE EXTRACTION
# ============================================================
#
# This is the main dynamic extraction mechanism.
#
# SpaCy analyzes sentences and noun phrases.
#
# We do NOT ask:
#
#     "Is React in my hardcoded list?"
#
# Instead we ask:
#
#     "Does this sentence look like it is talking about
#      technical experience, and what noun phrases occur in it?"
# ============================================================

def extract_nlp_candidates(text):

    candidates = set()

    if not nlp:
        return candidates

    doc = nlp(text)

    for sentence in doc.sents:

        sentence_text = sentence.text.strip()

        if not sentence_text:
            continue

        sentence_lower = sentence_text.lower()

        # ----------------------------------------------------
        # Determine whether this sentence has technical context
        # ----------------------------------------------------

        technical_context = False

        for context in TECHNICAL_CONTEXTS:

            if context in sentence_lower:

                technical_context = True
                break

        # Also consider sentences containing technical-looking
        # punctuation such as:
        #
        # React.js, MongoDB and Docker
        #
        has_technical_punctuation = bool(
            re.search(
                r"\b[\w.-]+\.(js|net|io)\b",
                sentence_lower
            )
        )

        if not technical_context and not has_technical_punctuation:
            continue

        # ----------------------------------------------------
        # Extract noun phrases
        # ----------------------------------------------------

        for chunk in sentence.noun_chunks:

            candidate = normalize_candidate(
                chunk.text
            )

            if is_valid_candidate(candidate):

                candidates.add(candidate)

        # ----------------------------------------------------
        # Extract proper nouns
        # ----------------------------------------------------

        for ent in sentence.ents:

            if ent.label_ in {
                "ORG",
                "PRODUCT",
                "WORK_OF_ART",
            }:

                candidate = normalize_candidate(
                    ent.text
                )

                if is_valid_candidate(candidate):

                    candidates.add(candidate)

        # ----------------------------------------------------
        # Extract meaningful individual tokens
        # ----------------------------------------------------

        for token in sentence:

            if token.is_stop:
                continue

            if token.is_punct:
                continue

            if token.is_space:
                continue

            candidate = normalize_candidate(
                token.text
            )

            if not is_valid_candidate(candidate):
                continue

            # Keep technical-looking tokens.
            #
            # Examples:
            # Kubernetes
            # Kafka
            # Docker
            # React
            # TensorFlow
            #
            # We are NOT checking them against a technology list.
            #
            # IMPORTANT: spaCy's POS tagger is unreliable on short,
            # isolated acronyms/language names sitting in terse
            # sentences (e.g. "Java and c experience in ai" — "c"
            # and "ai" can get mistagged as something other than
            # PROPN/NOUN and silently dropped). Since we already
            # gated entry into this loop on the sentence having
            # technical context, and is_valid_candidate() already
            # filtered out generic/stopword-like text, any short
            # (<=3 character) surviving token is very likely a
            # real acronym (c, ai, ml, js, r, go, css) — accept it
            # directly instead of trusting POS tagging alone.

            if (
                token.pos_ in {"PROPN", "NOUN", "ADJ", "X"}
                or "." in candidate
                or "/" in candidate
                or "+" in candidate
                or "#" in candidate
                or len(candidate) <= 3
            ):

                candidates.add(candidate)

    return candidates


# ============================================================
# 11. FILTER NLP CANDIDATES USING SENTENCE TRANSFORMER
# ============================================================
#
# Generic NLP can produce candidates such as:
#
# "applications"
# "web development"
# "projects"
#
# Some are useful, some are not.
#
# Instead of maintaining a list of every possible technology,
# we compare candidate meanings with descriptions of technical
# concepts.
# ============================================================

TECHNICAL_PROTOTYPES = [

    "a programming language or coding language",
    "a software framework or web framework",
    "a software library or programming library",
    "a database or database management technology",
    "a web development technology",
    "a backend development technology",
    "a frontend development technology",
    "an API technology or communication protocol",
    "a machine learning technology",
    "an artificial intelligence technology",
    "a natural language processing technology",
    "a deep learning framework or neural network technology",
    "a data science technology or data analysis library",
    "a cloud computing technology",
    "a cloud platform or cloud service",
    "a DevOps or deployment technology",
    "a software development tool",
    "a version control technology",
    "a containerization technology",
    "a testing framework or testing technology",
    "a semantic search or vector search technology",
    "a large language model technology",
    "an AI model or AI development framework",
    "a computer graphics or rendering technology",
    "a geospatial or mapping software library",
]


NON_TECHNICAL_PROTOTYPES = [

    "a person's name",
    "a school or university",
    "an academic degree",
    "a date or year",
    "a percentage or score",
    "a person's achievement",
    "a location or city",
    "a generic business activity",
    "a general project description",
    "a job responsibility",
]


def semantic_candidate_filter(candidates):

    if not model:
        return candidates

    if not candidates:
        return set()

    try:

        candidate_list = list(candidates)

        candidate_embeddings = model.encode(
            candidate_list,
            convert_to_tensor=True
        )

        technical_embeddings = model.encode(
            TECHNICAL_PROTOTYPES,
            convert_to_tensor=True
        )

        nontechnical_embeddings = model.encode(
            NON_TECHNICAL_PROTOTYPES,
            convert_to_tensor=True
        )

        technical_similarity = util.cos_sim(
            candidate_embeddings,
            technical_embeddings
        )

        nontechnical_similarity = util.cos_sim(
            candidate_embeddings,
            nontechnical_embeddings
        )

        filtered = set()

        for i, candidate in enumerate(candidate_list):

            best_technical = technical_similarity[i].max().item()

            best_nontechnical = nontechnical_similarity[i].max().item()

            # Technical similarity must be reasonably strong
            # AND stronger than nontechnical similarity.
            #
            # This threshold is intentionally moderate because
            # the candidate was already produced by NLP context.

            if (
                best_technical >= 0.32
                and best_technical > best_nontechnical + 0.03
            ):

                filtered.add(candidate)

        return filtered

    except Exception as e:

        print(
            f"Semantic candidate filtering error: {e}"
        )

        return candidates


# ============================================================
# 12. COMPLETE DYNAMIC SKILL EXTRACTION
# ============================================================

def extract_skills(text):

    # --------------------------------------------------------
    # A. NLP candidate extraction
    # --------------------------------------------------------

    nlp_candidates = extract_nlp_candidates(text)

    # --------------------------------------------------------
    # B. Skill-section extraction
    # --------------------------------------------------------

    section_candidates = extract_section_candidates(text)

    # --------------------------------------------------------
    # C. Symbol-based technical terms
    # --------------------------------------------------------

    symbol_candidates = extract_symbol_technologies(text)

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    all_candidates = (
        nlp_candidates
        | section_candidates
        | symbol_candidates
    )

    # Normalize everything
    normalized_candidates = set()

    for candidate in all_candidates:

        candidate = normalize_candidate(candidate)

        if is_valid_candidate(candidate):

            normalized_candidates.add(candidate)

    # --------------------------------------------------------
    # Semantic filtering
    #
    # Section candidates are already very strong because they
    # came directly from a section such as "Technical Skills".
    #
    # Therefore we preserve them.
    #
    # NLP candidates need filtering, but a single embedding
    # comparison behaves very differently for a 1-word token
    # ("java", "ai") than for a 4-5 word noun phrase
    # ("an innovative e-commerce platform") — cosine similarity
    # against long descriptive prototype sentences is noisy and
    # unreliable for very short tokens, which was causing real
    # skills like "java" / "c" / "ai" to be dropped, while long
    # noun phrases like "a job application platform" were
    # sometimes kept.
    #
    # So: trust short (<=2 word) single/compound technical-looking
    # tokens directly (they already passed POS / symbol checks in
    # extract_nlp_candidates), and only run the semantic filter on
    # longer noun phrases, where it's actually useful for weeding
    # out generic descriptive text.
    # --------------------------------------------------------

    short_nlp_candidates = {
        c for c in nlp_candidates
        if len(c.split()) <= 2
    }

    long_nlp_candidates = {
        c for c in nlp_candidates
        if len(c.split()) > 2
    }

    filtered_long_nlp = semantic_candidate_filter(
        long_nlp_candidates
    )

    final_skills = set()

    final_skills.update(section_candidates)
    final_skills.update(symbol_candidates)
    final_skills.update(short_nlp_candidates)
    final_skills.update(filtered_long_nlp)

    # --------------------------------------------------------
    # Final cleanup
    # --------------------------------------------------------

    final_skills = {
        normalize_candidate(skill)
        for skill in final_skills
        if is_valid_candidate(skill)
    }

    return final_skills


# ============================================================
# 13. SEMANTIC SKILL MATCHING
# ============================================================
#
# Example:
#
# JD:       RESTful APIs
# Resume:   REST APIs
#
# Exact string match may fail.
#
# Sentence Transformer can identify semantic similarity.
#
# IMPORTANT:
# Very short skills such as "C" are not semantically matched
# against other skills because that creates false positives.
#
# NOTE ON THRESHOLD:
# This was originally 0.72, which is a very high bar for cosine
# similarity between short phrases — plenty of genuinely
# equivalent skills (e.g. "ci/cd" vs "continuous integration")
# score lower than that and were being silently rejected,
# which is why matched/missing skills were coming back empty.
# 0.55 is a more realistic threshold for short technical terms.
# ============================================================

def semantic_skill_match(
    jd_skills,
    resume_skills,
    threshold=0.55
):

    if not jd_skills or not resume_skills or not model:

        return set()

    jd_list = list(jd_skills)
    resume_list = list(resume_skills)

    try:

        jd_embeddings = model.encode(
            jd_list,
            convert_to_tensor=True
        )

        resume_embeddings = model.encode(
            resume_list,
            convert_to_tensor=True
        )

        similarity_matrix = util.cos_sim(
            jd_embeddings,
            resume_embeddings
        )

        matched = set()

        for i, jd_skill in enumerate(jd_list):

            # ------------------------------------------------
            # Exact match should already be handled separately.
            # Don't perform semantic matching for extremely
            # short skills because C vs C++ is dangerous.
            # ------------------------------------------------

            if len(jd_skill) <= 2:
                continue

            best_similarity = 0
            best_resume_skill = None

            for j, resume_skill in enumerate(resume_list):

                # Avoid comparing very short skills semantically
                if len(resume_skill) <= 2:
                    continue

                similarity = (
                    similarity_matrix[i][j].item()
                )

                if similarity > best_similarity:

                    best_similarity = similarity
                    best_resume_skill = resume_skill

            if best_similarity >= threshold:

                matched.add(jd_skill)

                print(
                    f"Semantic match: "
                    f"{jd_skill} -> "
                    f"{best_resume_skill} "
                    f"({best_similarity:.3f})"
                )

        return matched

    except Exception as e:

        print(
            f"Semantic skill matching error: {e}"
        )

        return set()


# ============================================================
# 14. ANALYZE RESUMES
# ============================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    if (
        "resumes" not in request.files
        or "jd" not in request.form
    ):

        return jsonify(
            {"error": "Missing JD or Resumes"}
        ), 400


    # ========================================================
    # JOB DESCRIPTION
    # ========================================================

    jd_raw = request.form["jd"]

    jd_clean = clean_text(jd_raw)

    jd_skills = extract_skills(jd_raw)


    print("\n====================================")
    print("JOB DESCRIPTION:")
    print(jd_raw)

    print("\nJOB DESCRIPTION SKILLS:")
    print(jd_skills)

    print("====================================")


    resumes = request.files.getlist("resumes")

    print(f"\nReceived {len(resumes)} resume file(s): "
          f"{[f.filename for f in resumes]}")

    results = []


    # Encode JD only once
    if model:

        jd_embedding = model.encode(
            jd_clean,
            convert_to_tensor=True
        )

    else:

        jd_embedding = None


    # ========================================================
    # PROCESS EACH RESUME
    # ========================================================

    for file in resumes:

        raw_text = extract_text(file)

        if not raw_text.strip():

            print(f"⚠️  No text extracted from {file.filename} — skipping.")
            continue


        # ----------------------------------------------------
        # Candidate name
        # ----------------------------------------------------

        extracted_name = get_name(
            raw_text
        )

        display_name = (
            extracted_name
            if extracted_name
            else file.filename
        )


        # ----------------------------------------------------
        # Resume cleaning
        # ----------------------------------------------------

        resume_clean = clean_text(
            raw_text
        )


        # ----------------------------------------------------
        # Dynamic NLP skill extraction
        # ----------------------------------------------------

        resume_skills = extract_skills(
            raw_text
        )


        print("\n====================================")
        print(
            f"RESUME: {display_name}"
        )

        print("\nRESUME SKILLS:")
        print(resume_skills)

        print("====================================")


        # ====================================================
        # DOCUMENT SEMANTIC SIMILARITY
        # ====================================================

        if (
            model
            and jd_embedding is not None
        ):

            resume_embedding = model.encode(
                resume_clean,
                convert_to_tensor=True
            )

            cosine_score = util.cos_sim(
                jd_embedding,
                resume_embedding
            ).item()

            cosine_score = max(
                0,
                cosine_score
            )

        else:

            cosine_score = 0


        # ====================================================
        # EXACT SKILL MATCH
        # ====================================================

        exact_matches = (
            jd_skills.intersection(
                resume_skills
            )
        )


        # ====================================================
        # SEMANTIC SKILL MATCH
        # ====================================================

        semantic_matches = semantic_skill_match(
            jd_skills,
            resume_skills
        )


        # ====================================================
        # FINAL MATCHED SKILLS
        # ====================================================

        matched_skills = (
            exact_matches
            | semantic_matches
        )


        print(
            "EXACT MATCHES:",
            exact_matches
        )

        print(
            "SEMANTIC MATCHES:",
            semantic_matches
        )

        print(
            "FINAL MATCHED SKILLS:",
            matched_skills
        )


        # ====================================================
        # SKILL SCORE
        # ====================================================

        if jd_skills:

            skill_score = (
                len(matched_skills)
                / len(jd_skills)
            )

        else:

            skill_score = cosine_score


        # ====================================================
        # FINAL SCORE
        # ====================================================
        #
        # 50% document semantic similarity
        # 50% skill matching
        #
        # ====================================================

        final_score = (
            0.50 * cosine_score
            +
            0.50 * skill_score
        )

        final_score = max(
            0,
            min(1, final_score)
        )

        final_percentage = round(
            final_score * 100,
            2
        )


        # ====================================================
        # STATUS
        # ====================================================

        if final_percentage >= 75:

            status = "Strong Match"

        elif final_percentage >= 50:

            status = "Good Match"

        elif final_percentage >= 30:

            status = "Partial Match"

        else:

            status = "Review"


        # ====================================================
        # MISSING SKILLS
        # ====================================================

        missing_skills = (
            jd_skills
            - matched_skills
        )


        # ====================================================
        # RESULT
        # ====================================================

        results.append({

            "name": display_name,

            "score": final_percentage,

            "status": status,

            "skills_found": sorted(
                list(resume_skills)
            ),

            "matched_skills": sorted(
                list(matched_skills)
            ),

            "missing_skills": sorted(
                list(missing_skills)
            )[:5],

        })


    # ========================================================
    # SORT BY SCORE
    # ========================================================

    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )


    return jsonify(results)


# ============================================================
# 15. START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    print(
        f"Step 3/3: Server is starting "
        f"on http://0.0.0.0:{port}"
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )