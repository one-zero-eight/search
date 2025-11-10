from src.modules.parsers.clubs import parser


def main():
    result = list(parser.parse())
    return result


if __name__ == "__main__":
    main()
