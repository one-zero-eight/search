"""How well the agent's wiki search finds the piece that answers a question (catix/db/wiki.py).

Questions of every kind of reader (student, postgraduate, applicant, teacher/staff, management/public), worded as a person
would ask, not as the document says. A piece is relevant when its page (path or title) matches `page` and its text (with the title and headings) matches `text` (both
regexes, case-insensitive), picked by reading the documents. Methods: words only, meaning only, both fused, both fused and
reranked (what search_wiki does). Small sample: read the per-question table, not only the averages.

Usage: uv run python experiments/eval_wiki.py [--check]   (--check: only count the relevant pieces of each question)
"""

import re
import statistics
import sys
import time

from catix.db import pg
from catix.db import store
from catix.db import wiki

TOP = 10

# (reader, question, page regex, text regex)
QUESTIONS = [
    # student
    ("student", "сколько раз можно пересдавать экзамен", r"attestation-regulation|sveden-(117f90c4|2edceae4|d40bccec)|remote-attestation|guides/retakes", r"повторн\w* промежуточн\w* аттестац|пересдач|retake"),
    ("student", "как оформить академический отпуск", r"academic-leave", r"академическ\w+ отпуск"),
    ("student", "на какой срок дают академ", r"academic-leave", r"не более|двух лет|календарных месяц|12 calendar months"),
    ("student", "за что могут отчислить из университета", r"transfer-expulsion", r"отчислен|отчисляется"),
    ("student", "можно ли восстановиться после отчисления", r"transfer-expulsion", r"восстановл"),
    ("student", "как перейти с платного обучения на бюджет", r"tuition-to-budget", r"бюджетн|state-funded"),
    ("student", "какие оценки считаются неудовлетворительными", r"attestation-regulation|sveden-(117f90c4|2edceae4|d40bccec)|grading", r"неудовлетворительн|D and F|D и F"),
    ("student", "как перезачесть курсы, пройденные в другом вузе", r"credit-transfer", r"зач[её]т|перезач|recogni"),
    ("student", "кто получает государственную академическую стипендию", r"sveden-4940ff25|financial-aid|grant-retention", r"академическ\w+ стипенди|academic scholarship"),
    ("student", "как получить материальную помощь", r"sveden-0a5d0a37|sveden-4940ff25|financial-aid", r"материальн\w+ помощ|material (aid|support)"),
    ("student", "что запрещено студентам на территории университета", r"sveden-7600a171|sveden-d0c4586d|campus-behavior", r"запрещ|prohibit|must not|\*\*4\.3\.\d"),
    ("student", "какое наказание за списывание и плагиат", r"academic-integrity", r"плагиат|списыв|заимствов|plagiar|cheat"),
    ("student", "какие требования к компьютеру и камере на дистанционном экзамене", r"remote|eodot|sveden-(9312cfff|e6989528|c1a38b32)", r"камер|веб|видео|camera"),
    ("student", "как выбрать элективные курсы", r"sveden-21777590|electives|faculty-vs-elective", r"электив|elective"),
    ("student", "сколько нужно заниматься физкультурой", r"sveden-d171dac5|sveden-45f82e4f|courses/.*physical-education", r"физическ\w+ культур"),
    ("student", "можно ли учиться по индивидуальному учебному плану", r"polozh-iup|individual-study-plan", r"индивидуальн\w+ учебн\w+ план"),
    ("student", "можно ли закончить университет быстрее", r"polozh-uskor|accelerated", r"ускоренн|accelerated"),
    ("student", "как подать апелляцию после защиты диплома", r"final-attestation|polozh-gia|defense-appeal|graduation|sveden-222c22bc", r"апелляц|appeal"),
    ("student", "how many retakes are allowed if I fail an exam", r"attestation-regulation|sveden-(117f90c4|2edceae4|d40bccec)|retakes", r"повторн\w* промежуточн\w* аттестац|retake"),
    ("student", "can I get a scholarship as a master student", r"sveden-4940ff25|financial-aid|grant-retention", r"стипенди|scholarship"),
    ("student", "куда обратиться, если конфликт с преподавателем из-за оценки", r"sveden-3bfa0f24|attestation|academic-integrity", r"комисси\w+ по урегулированию|апелляц|спор"),
    ("student", "как заключается договор на платное обучение", r"sveden-cc874693|enrollment", r"договор"),
    # postgraduate
    ("postgraduate", "как сдают кандидатские экзамены", r"sveden-1aec3b46", r"кандидатск\w+ экзамен"),
    ("postgraduate", "что входит в индивидуальный план работы аспиранта", r"sveden-d8ce08d8|sveden-a1f98bed", r"индивидуальн\w+ план"),
    ("postgraduate", "как проходит итоговая аттестация в аспирантуре", r"sveden-a2611be0", r"итогов\w+ аттестац"),
    ("postgraduate", "сколько длятся каникулы у аспиранта", r"sveden-a1f98bed", r"каникул"),
    ("postgraduate", "как получить свидетельство об окончании аспирантуры", r"sveden-dcc8ca92", r"свидетельств"),
    # applicant
    ("applicant", "какие вступительные испытания при поступлении в магистратуру", r"pravila-priema|sveden-62dee06c|sveden-f8519483|sveden-923ead02|vstupit|sveden-fcd8fe0a|sveden-fa2df28f|sveden-80ba544a", r"магистр\w*.{0,250}вступительн\w+ испытан|вступительн\w+ испытан.{0,250}магистр"),
    ("applicant", "какие индивидуальные достижения учитываются при поступлении", r"sveden-1b9872b0|pravila-priema|sveden-62dee06c|sveden-f8519483", r"индивидуальн\w+ достижен"),
    ("applicant", "куда отправлять документы для поступления", r"sveden-(68f6b922|bb8f8f9c)|pravila-priema|sveden-62dee06c|sveden-f8519483", r"почтов|адрес|прием\w* документ|приема заявлений"),
    ("applicant", "есть ли особые права при поступлении на бакалавриат", r"sveden-779846ee|pravila-priema|sveden-62dee06c|sveden-f8519483", r"особ\w+ прав"),
    ("applicant", "как поступить иностранному гражданину", r"sveden-9316bc2a|pravila-priema|sveden-62dee06c|sveden-f8519483", r"иностранн"),
    ("applicant", "как получить грант на обучение при поступлении", r"sveden-9d0974a5|grant", r"грант|grant"),
    ("applicant", "как перевестись в Иннополис из другого вуза", r"sveden-08e4b66a|transfer-expulsion|transfer-between", r"перевод"),
    ("applicant", "what is the entrance exam in mathematics for bachelor", r"sveden-601fd657|pravila-priema|sveden-62dee06c|sveden-f8519483", r"математик|mathemat"),
    # teacher / staff
    ("teacher", "как разрабатывается и утверждается образовательная программа", r"sveden-d412a435", r"разработк|утвержд"),
    ("teacher", "как в университете оценивается качество образования", r"sveden-e035bc97", r"оценк\w+ качеств"),
    ("teacher", "как реализуется сетевая форма образовательной программы", r"sveden-a5f0e359", r"сетев"),
    ("teacher", "что такое электронная информационно-образовательная среда университета", r"sveden-73841fa9|eios|regulations/sveden-", r"электронн\w+ информационно-образовательн\w+ сред\w+ университета"),
    ("teacher", "как обучать студентов с инвалидностью", r"sveden-426e3e76|exam-accommodations|adapt", r"инвалид|ограниченн\w+ возможност|disabilit"),
    ("teacher", "сколько академических часов в одной зачетной единице", r"sveden-65b76d47|polozh-razrabotka", r"зачетн\w+ единиц"),
    ("teacher", "who teaches the operating systems course", r"courses/.*operating-systems|people/", r"operating systems"),
    ("teacher", "what should students know before taking control theory", r"courses/bsc-control-theory", r"prerequisit"),
    # management / public
    ("public", "кто директор университета", r"Вандюков|ustav", r"директор"),
    ("public", "есть ли у университета лицензия на образовательную деятельность", r"sveden-3ee95d5d|sveden-88c90ae0", r"лиценз"),
    ("public", "на каком языке ведется обучение", r"sveden-212d9d70", r"язык"),
    ("public", "по каким направлениям университет ведет прием", r"sveden-88c90ae0|pravila-priema|sveden-62dee06c|sveden-f8519483", r"направлени|специальност"),
    ("management", "какие результаты промежуточной аттестации студентов за последний год", r"sveden-4f1f0456", r"промежуточн\w+ аттестац"),
    ("management", "как организована практика студентов и ее результаты", r"sveden-b3da8fdf", r"практик"),
    ("public", "how is the bachelor programme structured into tracks", r"programs/|bsc-structure", r"track|stream|software engineering"),
    # course programmes (РПД, wiki/course-programmes)
    ("student", "как оценивается курс вычислительная математика", r"vychislitelnaya-matematika", r"критери\w+ оценивания|«отлично»"),
    ("student", "сколько зачетных единиц и часов у дисциплины вычислительная математика", r"vychislitelnaya-matematika", r"зачетн\w+ единиц"),
    ("student", "какие темы изучаются в курсе компьютерные сети", r"kompyuternye-seti|networks", r"содержани\w+ дисциплин|тем\w* \d|раздел"),
    ("student", "какую литературу читать по машинному обучению", r"mashinnoe-obuchenie", r"литератур|учебно-методическ"),
    ("applicant", "какая форма промежуточной аттестации по физкультуре в колледже", r"fizicheskaya-kultura", r"зач[её]т|дифференцированн"),
    ("teacher", "what learning outcomes does the deep learning course have", r"glubokoe-obuchenie|deep-learning", r"результат\w* обучения|компетенц"),
    ("teacher", "какие компетенции формирует дисциплина операционные системы", r"operatsionnye-sistemy|operating-systems", r"компетенц|ОПК-|ПК-"),
]  # fmt: skip


def relevant(conn, page: str, text: str) -> set[int]:
    return {r["id"] for r in conn.execute(
        "SELECT c.id FROM wiki_chunks c JOIN wiki_pages p ON p.path = c.path WHERE (c.path ~* %s OR p.title ~* %s) AND c.search_text ~* %s", (page, page, text))}


def main() -> None:
    conn = pg.connect()
    if "--check" in sys.argv:
        for reader, q, page, text in QUESTIONS:
            n = len(relevant(conn, page, text))
            print(f"{n:>4}  {reader:<12} {q}")
        return
    pg.embed(["warm-up"])
    trust = list(wiki.TRUST)
    methods = {
        "words": lambda q: wiki._bm25(store._words(q), trust)[:TOP],
        "meaning": lambda q: wiki._vector(pg.embed([q])[0], trust)[:TOP],
        "fused": lambda q: store._combine([store._rrf(wiki._bm25(store._words(q), trust), wiki._vector(pg.embed([q])[0], trust))], TOP),
        "reranked": lambda q: [h.id for h in wiki.search([q], limit=TOP)],
    }
    ranks = {m: [] for m in methods}
    times = {m: [] for m in methods}
    by_reader: dict[str, dict[str, list]] = {}
    print(f"{'reader':<12} {'question':<70} rel | first relevant rank ({' / '.join(methods)})")
    for reader, q, page, text in QUESTIONS:
        rel = relevant(conn, page, text)
        cells = []
        for name, fn in methods.items():
            started = time.perf_counter()
            result = fn(q)
            times[name].append(time.perf_counter() - started)
            first = next((i for i, x in enumerate(result, 1) if x in rel), None)
            ranks[name].append(first)
            by_reader.setdefault(reader, {m: [] for m in methods})[name].append(first)
            cells.append(f"{first:>2}" if first else " -")
        print(f"{reader:<12} {q[:70]:<70} {len(rel):>3} | " + " / ".join(cells))

    def stats(firsts: list) -> str:
        n = len(firsts)
        return (f"{sum(1 for f in firsts if f and f <= 5) / n:>6.0%} {sum(1 for f in firsts if f) / n:>7.0%} "
                f"{sum(1 / f for f in firsts if f) / n:>7.2f}")

    print(f"\n{'method':<10} {'hit@5':>6} {'hit@10':>7} {'MRR':>7} {'median s':>9}")
    for name in methods:
        print(f"{name:<10} {stats(ranks[name])} {statistics.median(times[name]):>9.2f}")
    print(f"\n{'reader':<12} {'n':>3}  hit@5 / hit@10 / MRR of 'reranked'")
    for reader, per in by_reader.items():
        print(f"{reader:<12} {len(per['reranked']):>3}  {stats(per['reranked'])}")
    pg.close()


if __name__ == "__main__":
    main()
