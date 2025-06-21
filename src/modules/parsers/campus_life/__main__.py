import clubs
import handbook


def main():
    result = {*handbook.parse(), *clubs.parse()}

    return result


if __name__ == "__main__":
    main()
