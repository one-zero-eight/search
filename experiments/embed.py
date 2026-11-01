"""Every pair of texts scored by the embedder (cosine) and by the reranker (row is the query, column the document), with an unrelated text as the floor."""

import math

from catix.settings import settings

TEXTS = {
    "fact": "Guests can pay for accommodation services online using the payment methods offered through the Uniteller payment service [1]. After booking confirmation, the guest is redirected to Uniteller's secure payment page where payment details must be entered [2]. After successful payment, an electronic receipt with booking information and payment details is sent to the email address specified in the payment form [3]",
    "ocr": """Уважаемый гость! Для оплаты вам нужно явится лично в кабинет 301. После успешной оплаты на указанную в форме оплаты электронную почту будет направлен электронный чек с информацией о бронировании и данными по произведенной оплате. Гарантии безопасности Безопасность процессинга Uniteller подтверждена сертификатом стандарта безопасности данных индустрии платежных карт PCI DSS. Надежность сервиса обеспечивается интеллектуальной системой мониторинга мошеннических операций, а также применением 3D Secure - современной технологией безопасности интернет-платежей. Данные Вашей карты вводятся на специальной защищенной платежной странице. Передача информации в Uniteller происходит с применением технологии шифрования TLS. Дальнейшая передача информации осуществляется по закрытым банковским каналам, имеющим наивысший уровень надежности. Uniteller не передает данные Вашей карты магазину и иным третьим лицам! Если Ваша карта поддерживает технологию 3D Secure, для осуществления платежа, Вам необходимо будет пройти дополнительную проверку пользователя в банке- эмитенте (банк, который выпустил Вашу карту). Для этого Вы будете направлены на страницу банка, выдавшего карту. Вид проверки зависит от банка. Как правило, это дополнительный пароль, который отправляется в SMS, карта переменных кодов, либо другие способы. Если у Вас возникли вопросы по совершенному платежу, Вы можете обратиться в службу технической поддержки процессингового центра Uniteller: или по телефону 8 800 100 19 60.""",
    "ocr-true": """Уважаемый гость! Вы можете оплатить услугу размещения онлайн с помощью предложенных методов оплат через платежный сервис компании. После подтверждения бронирования Вы будете перенаправлены на защищенную платежную страницу Uniteller, где необходимо будет ввести данные для оплаты услуги. После успешной оплаты на указанную в форме оплаты электронную почту будет направлен электронный чек с информацией о бронировании и данными по произведенной оплате. Гарантии безопасности Безопасность процессинга Uniteller подтверждена сертификатом стандарта безопасности данных индустрии платежных карт PCI DSS. Надежность сервиса обеспечивается интеллектуальной системой мониторинга мошеннических операций, а также применением 3D Secure - современной технологией безопасности интернет-платежей. Данные Вашей карты вводятся на специальной защищенной платежной странице. Передача информации в Uniteller происходит с применением технологии шифрования TLS. Дальнейшая передача информации осуществляется по закрытым банковским каналам, имеющим наивысший уровень надежности. Uniteller не передает данные Вашей карты магазину и иным третьим лицам! Если Ваша карта поддерживает технологию 3D Secure, для осуществления платежа, Вам необходимо будет пройти дополнительную проверку пользователя в банке- эмитенте (банк, который выпустил Вашу карту). Для этого Вы будете направлены на страницу банка, выдавшего карту. Вид проверки зависит от банка. Как правило, это дополнительный пароль, который отправляется в SMS, карта переменных кодов, либо другие способы. Если у Вас возникли вопросы по совершенному платежу, Вы можете обратиться в службу технической поддержки процессингового центра Uniteller: или по телефону 8 800 100 19 60.""",
    "unrelated": "Расписание занятий по физкультуре на осенний семестр: секция плавания проходит по вторникам и четвергам в спорткомплексе.",
}


def cosine(x: list[float], y: list[float]) -> float:
    return sum(a * b for a, b in zip(x, y, strict=True)) / (
        math.sqrt(sum(a * a for a in x)) * math.sqrt(sum(b * b for b in y))
    )


def table(title: str, names: list[str], score) -> None:
    width = max(map(len, names)) + 2
    print(title)
    print(" " * width, *(name.rjust(width) for name in names))
    for row in names:
        print(row.ljust(width), *(f"{score(row, column):.4f}".rjust(width) for column in names))
    print()


def main() -> None:
    settings.phoenix_endpoint = None
    from catix.db import pg

    names = list(TEXTS)
    vectors = dict(zip(names, pg.embed(list(TEXTS.values())), strict=True))
    logits = {row: dict(zip(names, pg.rerank(TEXTS[row], list(TEXTS.values())), strict=True)) for row in names}
    table("embedder, cosine", names, lambda row, column: cosine(vectors[row], vectors[column]))
    table("reranker, raw logit", names, lambda row, column: logits[row][column])
    table("reranker, sigmoid", names, lambda row, column: 1 / (1 + math.exp(-logits[row][column])))


if __name__ == "__main__":
    main()
