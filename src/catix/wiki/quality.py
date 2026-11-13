"""Whether the wiki's search still finds the answers: the check a commit of the wiki's own run must pass (autopilot.py).

Questions of every kind of reader, worded as a person would ask, each with the pages and the words that answer it (both
regexes, case-insensitive, picked by reading the documents; experiments/eval_wiki.py compares the search methods on them).
A piece is relevant when its page (path or title) matches `page` and its text (with the title and headings) matches `text`.
"""

from dataclasses import dataclass

from catix.db import pg, wiki

# (reader, question, page regex, text regex)
QUESTIONS = [
    # student
    ("student", "сколько раз можно пересдавать экзамен", r"attestation-regulation|(site-university-4b7f1759)|remote-attestation|knowledge/academic-failure-and-retakes", r"повторн\w* промежуточн\w* аттестац|пересдач|retake"),
    ("student", "как оформить академический отпуск", r"academic-leave", r"академическ\w+ отпуск"),
    ("student", "на какой срок дают академ", r"academic-leave", r"не более|двух лет|календарных месяц|12 calendar months"),
    ("student", "за что могут отчислить из университета", r"transfer-expulsion", r"отчислен|отчисляется"),
    ("student", "можно ли восстановиться после отчисления", r"transfer-expulsion", r"восстановл"),
    ("student", "как перейти с платного обучения на бюджет", r"tuition-to-budget", r"бюджетн|state-funded"),
    ("student", "какие оценки считаются неудовлетворительными", r"attestation-regulation|(site-university-4b7f1759)|grading", r"неудовлетворительн|D and F|D и F"),
    ("student", "как перезачесть курсы, пройденные в другом вузе", r"credit-transfer", r"зач[её]т|перезач|recogni"),
    ("student", "кто получает государственную академическую стипендию", r"site-university-c181849d|financial-aid|grant-retention", r"академическ\w+ стипенди|academic scholarship"),
    ("student", "как получить материальную помощь", r"site-university-46dce1d9|site-university-c181849d|financial-aid", r"материальн\w+ помощ|material (aid|support)"),
    ("student", "что запрещено студентам на территории университета", r"site-university-cad8a0f5|site-university-0c9681fa|campus-behavior", r"запрещ|prohibit|must not|\*\*4\.3\.\d"),
    ("student", "какое наказание за списывание и плагиат", r"academic-integrity", r"плагиат|списыв|заимствов|plagiar|cheat"),
    ("student", "какие требования к компьютеру и камере на дистанционном экзамене", r"remote|eodot|(site-university-c1a38b32)", r"камер|веб|видео|camera"),
    ("student", "как выбрать элективные курсы", r"site-university-6b085525|electives|faculty-vs-elective", r"электив|elective"),
    ("student", "сколько нужно заниматься физкультурой", r"site-university-06bad90f|site-university-24bc2b4e|courses/.*physical-education", r"физическ\w+ культур"),
    ("student", "можно ли учиться по индивидуальному учебному плану", r"polozh-iup|individual-study-plan", r"индивидуальн\w+ учебн\w+ план"),
    ("student", "можно ли закончить университет быстрее", r"polozh-uskor|accelerated", r"ускоренн|accelerated"),
    ("student", "как подать апелляцию после защиты диплома", r"final-attestation|polozh-gia|defense-appeal|graduation|site-university-222c22bc", r"апелляц|appeal"),
    ("student", "how many retakes are allowed if I fail an exam", r"attestation-regulation|(site-university-4b7f1759)|retakes", r"повторн\w* промежуточн\w* аттестац|retake"),
    ("student", "can I get a scholarship as a master student", r"site-university-c181849d|financial-aid|grant-retention|scholarship", r"стипенди|scholarship"),
    ("student", "куда обратиться, если конфликт с преподавателем из-за оценки", r"site-university-3bfa0f24|attestation|academic-integrity|dispute-resolution", r"комисси\w+ по урегулированию|апелляц|спор|disput|appeal"),
    ("student", "как заключается договор на платное обучение", r"site-university-4bc2f821|enrollment", r"договор"),
    # postgraduate
    ("postgraduate", "как сдают кандидатские экзамены", r"site-university-781ed349", r"кандидатск\w+ экзамен"),
    ("postgraduate", "что входит в индивидуальный план работы аспиранта", r"site-university-e1d5b53a|site-university-a1f98bed", r"индивидуальн\w+ план"),
    ("postgraduate", "как проходит итоговая аттестация в аспирантуре", r"site-university-7df6cbdc", r"итогов\w+ аттестац"),
    ("postgraduate", "сколько длятся каникулы у аспиранта", r"site-university-a1f98bed", r"каникул"),
    ("postgraduate", "как получить свидетельство об окончании аспирантуры", r"site-university-dcc8ca92", r"свидетельств"),
    # applicant
    ("applicant", "какие вступительные испытания при поступлении в магистратуру", r"pravila-priema|site-university-5f37d92a|site-university-e1710f30|vstupit|site-university-fcd8fe0a|site-university-90f0d232|site-university-21ac31e5", r"магистр\w*.{0,250}вступительн\w+ испытан|вступительн\w+ испытан.{0,250}магистр"),
    ("applicant", "какие индивидуальные достижения учитываются при поступлении", r"site-university-a66e663e|pravila-priema|site-university-5f37d92a|site-university-e1710f30", r"индивидуальн\w+ достижен"),
    ("applicant", "куда отправлять документы для поступления", r"(site-university-5ce9eab8|site-university-3485084a)|pravila-priema|site-university-5f37d92a|site-university-e1710f30", r"почтов|адрес|прием\w* документ|приема заявлений"),
    ("applicant", "есть ли особые права при поступлении на бакалавриат", r"site-university-55c3388d|pravila-priema|site-university-5f37d92a|site-university-e1710f30", r"особ\w+ прав"),
    ("applicant", "как поступить иностранному гражданину", r"site-university-0fab07fb|pravila-priema|site-university-5f37d92a|site-university-e1710f30", r"иностранн"),
    ("applicant", "как получить грант на обучение при поступлении", r"site-university-e58c64a8|grant", r"грант|grant"),
    ("applicant", "как перевестись в Иннополис из другого вуза", r"site-university-812469aa|transfer-expulsion|transfer-between", r"перевод"),
    ("applicant", "what is the entrance exam in mathematics for bachelor", r"site-university-601fd657|pravila-priema|site-university-5f37d92a|site-university-e1710f30", r"математик|mathemat"),
    # teacher / staff
    ("teacher", "как разрабатывается и утверждается образовательная программа", r"site-university-d412a435", r"разработк|утвержд"),
    ("teacher", "как в университете оценивается качество образования", r"site-university-6e75290e", r"оценк\w+ качеств"),
    ("teacher", "как реализуется сетевая форма образовательной программы", r"site-university-a5f0e359", r"сетев"),
    ("teacher", "что такое электронная информационно-образовательная среда университета", r"site-university-73841fa9|eios|regulations/site-university-", r"электронн\w+ информационно-образовательн\w+ сред\w+ университета"),
    ("teacher", "как обучать студентов с инвалидностью", r"site-university-253dacb0|exam-accommodations|adapt", r"инвалид|ограниченн\w+ возможност|disabilit"),
    ("teacher", "сколько академических часов в одной зачетной единице", r"site-university-f35fa0ce|polozh-razrabotka", r"зачетн\w+ единиц"),
    ("teacher", "who teaches the operating systems course", r"courses/.*operating-systems|people/", r"operating systems"),
    ("teacher", "what should students know before taking control theory", r"courses/bsc-control-theory", r"prerequisit"),
    # management / public
    ("public", "кто директор университета", r"Вандюков|ustav", r"директор"),
    ("public", "есть ли у университета лицензия на образовательную деятельность", r"site-university-f5f6b1c9|site-university-c4cbfd1e", r"лиценз"),
    ("public", "на каком языке ведется обучение", r"site-university-212d9d70", r"язык"),
    ("public", "по каким направлениям университет ведет прием", r"site-university-c4cbfd1e|pravila-priema|site-university-5f37d92a|site-university-e1710f30", r"направлени|специальност"),
    ("management", "какие результаты промежуточной аттестации студентов за последний год", r"site-university-4f1f0456", r"промежуточн\w+ аттестац"),
    ("management", "как организована практика студентов и ее результаты", r"site-university-a319022a", r"практик"),
    ("public", "how is the bachelor programme structured into tracks", r"programs/|bsc-structure", r"track|stream|software engineering"),
    # course programmes (РПД, wiki/raw/course-programmes)
    ("student", "как оценивается курс вычислительная математика", r"vychislitelnaya-matematika", r"критери\w+ оценивания|«отлично»"),
    ("student", "сколько зачетных единиц и часов у дисциплины вычислительная математика", r"vychislitelnaya-matematika", r"зачетн\w+ единиц"),
    ("student", "какие темы изучаются в курсе компьютерные сети", r"kompyuternye-seti|networks", r"содержани\w+ дисциплин|тем\w* \d|раздел"),
    ("student", "какую литературу читать по машинному обучению", r"mashinnoe-obuchenie", r"литератур|учебно-методическ"),
    ("applicant", "какая форма промежуточной аттестации по физкультуре в колледже", r"fizicheskaya-kultura", r"зач[её]т|дифференцированн"),
    ("teacher", "what learning outcomes does the deep learning course have", r"glubokoe-obuchenie|deep-learning", r"результат\w* обучения|компетенц"),
    ("teacher", "какие компетенции формирует дисциплина операционные системы", r"operatsionnye-sistemy|operating-systems", r"компетенц|ОПК-|ПК-"),
]  # fmt: skip


@dataclass
class Relevant:
    """The pieces that answer a question. A piece the search finds in place of one of them (search_index.mark_copies)
    answers too when the agent can get from it to the page: one of the same course (the programme of another intake, the
    same text), or one whose list of pages with the same text shows that page."""

    ids: set[int]
    pages: set[str]
    courses: set[str]
    mains: set[int]

    @classmethod
    def of(cls, rows: list[dict]) -> "Relevant":
        return cls({r["id"] for r in rows}, {r["path"] for r in rows}, {c for r in rows if (c := wiki.course_of(r["path"], r["title"]))},
                   {r["copy_of"] for r in rows if r["copy_of"]})

    def __contains__(self, hit) -> bool:
        return hit.id in self.ids or hit.id in self.mains and (
            wiki.course_of(hit.path, hit.title) in self.courses or any(a["page"] in self.pages for a in hit.also_in[:wiki.ALSO_SHOWN]))

    def __len__(self) -> int:
        return len(self.ids)


def relevant(conn, page: str, text: str) -> Relevant:
    return Relevant.of(conn.execute(
        "SELECT c.id, c.path, p.title, c.copy_of FROM wiki_chunks c JOIN wiki_pages p ON p.path = c.path "
        "WHERE (c.path ~* %s OR p.title ~* %s) AND c.search_text ~* %s", (page, page, text)).fetchall())


@dataclass
class Score:
    hit5: float  # share of questions with a relevant piece among the first 5 of search_wiki
    hit10: float
    missed: list[str]  # questions with none among the first 10


def score() -> Score:
    """The search the agent uses (search_wiki: hybrid, reranked) on every question."""
    conn = pg.connect()
    firsts, missed = [], []
    for _, question, page, text in QUESTIONS:
        rel = relevant(conn, page, text)
        first = next((i for i, h in enumerate(wiki.search([question], limit=10), 1) if h in rel), None)
        firsts.append(first)
        if not first:
            missed.append(question)
    n = len(firsts)
    return Score(sum(1 for f in firsts if f and f <= 5) / n, sum(1 for f in firsts if f) / n, missed)
